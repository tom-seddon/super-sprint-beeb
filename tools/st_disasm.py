"""Disassemble the ST Super Sprint program (Megamax C) at its run-time addresses.

Usage: st_disasm.py <SUPER.PRG> <out.s> [<out.json>] [--seeds file]

- The text segment is placed where TOS 1.04 loads it under Hatari (TEXT_BASE), so addresses match the
  debugger. The relocation table is applied.
- Megamax C: far calls are `jsr n(a5)`, through the jump table of `jmp abs.l` at the start of the text
  (a5 = text base); near calls are `jsr d16(pc)`. Globals are `d16(a4)`, a4 = the start of initialised
  data, with the BSS below it (the start-up code moves the data up by the BSS's length).
- Code is found by recursive descent from the entry, the jump table, every `link a6` at a gap, and any
  extra seeds (Hatari profile addresses, one hex address a line).
"""
import json, struct, sys, re
from collections import defaultdict
import capstone

TEXT_BASE = 0xAA56

HW = {
    0xFF8201: 'VIDEO_BASE_HI', 0xFF8203: 'VIDEO_BASE_MID', 0xFF8205: 'VIDEO_COUNT_HI',
    0xFF8207: 'VIDEO_COUNT_MID', 0xFF8209: 'VIDEO_COUNT_LO', 0xFF820A: 'SYNC_MODE', 0xFF8260: 'SHIFTER_RES',
    0xFF8800: 'YM_SELECT', 0xFF8802: 'YM_WRITE', 0xFF8604: 'DMA_DATA', 0xFF8606: 'DMA_MODE',
    0xFFFA01: 'MFP_GPIP', 0xFFFA03: 'MFP_AER', 0xFFFA05: 'MFP_DDR', 0xFFFA07: 'MFP_IERA', 0xFFFA09: 'MFP_IERB',
    0xFFFA0B: 'MFP_IPRA', 0xFFFA0D: 'MFP_IPRB', 0xFFFA0F: 'MFP_ISRA', 0xFFFA11: 'MFP_ISRB',
    0xFFFA13: 'MFP_IMRA', 0xFFFA15: 'MFP_IMRB', 0xFFFA17: 'MFP_VR', 0xFFFA19: 'MFP_TACR', 0xFFFA1B: 'MFP_TBCR',
    0xFFFA1D: 'MFP_TCDCR', 0xFFFA1F: 'MFP_TADR', 0xFFFA21: 'MFP_TBDR', 0xFFFA23: 'MFP_TCDR',
    0xFFFA25: 'MFP_TDDR', 0xFFFC00: 'ACIA_KBD_CTRL', 0xFFFC02: 'ACIA_KBD_DATA',
    0x70: 'VEC_VBL', 0x68: 'VEC_HBL', 0x118: 'VEC_ACIA', 0x120: 'VEC_TIMER_B', 0x134: 'VEC_TIMER_A',
    0x110: 'VEC_TIMER_D', 0x114: 'VEC_TIMER_C', 0x44E: '_v_bas_ad', 0x452: 'vblsem', 0x454: 'nvbls',
    0x456: '_vblqueue', 0x45A: 'colorptr', 0x45E: 'screenpt', 0x462: '_vbclock', 0x466: '_frclock',
    0x484: 'conterm', 0x4BA: '_hz_200', 0x4CE: 'vbl_list',
}
for i in range(16):
    HW[0xFF8240 + 2 * i] = f'PALETTE_{i}'

GEMDOS = {0x00: 'Pterm0', 0x01: 'Cconin', 0x02: 'Cconout', 0x06: 'Crawio', 0x07: 'Crawcin', 0x08: 'Cnecin',
          0x09: 'Cconws', 0x0B: 'Cconis', 0x19: 'Dgetdrv', 0x1A: 'Fsetdta', 0x20: 'Super', 0x2C: 'Tgettime',
          0x30: 'Sversion', 0x31: 'Ptermres', 0x3C: 'Fcreate', 0x3D: 'Fopen', 0x3E: 'Fclose', 0x3F: 'Fread',
          0x40: 'Fwrite', 0x41: 'Fdelete', 0x42: 'Fseek', 0x48: 'Malloc', 0x49: 'Mfree', 0x4A: 'Mshrink',
          0x4B: 'Pexec', 0x4C: 'Pterm', 0x4E: 'Fsfirst', 0x4F: 'Fsnext'}
XBIOS = {0x00: 'Initmous', 0x02: 'Physbase', 0x03: 'Logbase', 0x04: 'Getrez', 0x05: 'Setscreen',
         0x06: 'Setpalette', 0x07: 'Setcolor', 0x08: 'Floprd', 0x09: 'Flopwr', 0x0A: 'Flopfmt',
         0x0D: 'Mfpint', 0x0E: 'Iorec', 0x10: 'Keytbl', 0x11: 'Random', 0x17: 'Gettime', 0x19: 'Ikbdws',
         0x1A: 'Jdisint', 0x1B: 'Jenabint', 0x1C: 'Giaccess', 0x1D: 'Offgibit', 0x1E: 'Ongibit',
         0x1F: 'Xbtimer', 0x20: 'Dosound', 0x21: 'Setprt', 0x22: 'Kbdvbase', 0x23: 'Kbrate', 0x25: 'Vsync',
         0x26: 'Supexec', 0x40: 'Blitmode'}
BIOS = {0x01: 'Bconstat', 0x02: 'Bconin', 0x03: 'Bconout', 0x05: 'Setexc', 0x0B: 'Kbshift'}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Prg:
    def __init__(self, path):
        d = open(path, 'rb').read()
        magic, self.tlen, self.dlen, self.blen, self.slen = struct.unpack('>HIIII', d[:18])
        assert magic == 0x601A
        img = bytearray(d[28:28 + self.tlen + self.dlen])
        rel = d[28 + self.tlen + self.dlen + self.slen:]
        self.relocs = set()
        off = struct.unpack('>I', rel[:4])[0]
        i = 4
        if off:
            while True:
                self.relocs.add(off)
                v = struct.unpack('>I', img[off:off + 4])[0]
                struct.pack_into('>I', img, off, v + TEXT_BASE)
                b = rel[i]; i += 1
                while b == 1:
                    off += 254; b = rel[i]; i += 1
                if b == 0:
                    break
                off += b
        self.img = bytes(img)
        self.text_end = TEXT_BASE + self.tlen
        self.data_base = self.text_end           # where TOS loads the data
        # After start-up: BSS at [data_base, data_base+blen), the data moved up after it; a4 between.
        self.a4 = self.data_base + self.blen

    def w(self, a):
        o = a - TEXT_BASE
        return struct.unpack('>H', self.img[o:o + 2])[0]

    def l(self, a):
        o = a - TEXT_BASE
        return struct.unpack('>I', self.img[o:o + 4])[0]

    def in_text(self, a):
        return TEXT_BASE <= a < self.text_end


def flow(p, a):
    """Control flow of the instruction at a: (kind, target or None). kind: seq, call, jump, branch, stop, table."""
    op = p.w(a)
    if op & 0xF000 == 0x6000:
        cond = (op >> 8) & 0xF
        d = op & 0xFF
        if d == 0:
            t = a + 2 + s16(p.w(a + 2))
        else:
            t = a + 2 + (d - 0x100 if d & 0x80 else d)
        return {0: 'jump', 1: 'call'}.get(cond, 'branch'), t
    if op & 0xF0F8 == 0x50C8:
        return 'branch', a + 2 + s16(p.w(a + 2))
    if op in (0x4E75, 0x4E73, 0x4E77):
        return 'stop', None
    if op & 0xFF80 == 0x4E80:                  # JSR / JMP
        kind = 'call' if op & 0x40 == 0 else 'jump'
        mode, reg = (op >> 3) & 7, op & 7
        t = None
        if mode == 7 and reg == 2:
            t = a + 2 + s16(p.w(a + 2))
        elif mode == 7 and reg == 1:
            t = p.l(a + 2)
        elif mode == 7 and reg == 0:
            t = s16(p.w(a + 2)) & 0xFFFFFF
        elif mode == 5 and reg == 5:           # d16(a5): the jump table
            e = TEXT_BASE + s16(p.w(a + 2))
            if p.in_text(e) and p.w(e) == 0x4EF9:
                t = p.l(e + 2)
        elif mode == 7 and reg == 3:
            return ('table' if kind == 'jump' else 'call'), None
        return kind, t
    return 'seq', None


def main(argv):
    prg_path, out_s = argv[0], argv[1]
    out_j = argv[2] if len(argv) > 2 and not argv[2].startswith('--') else None
    seeds = []
    if '--seeds' in argv:
        for line in open(argv[argv.index('--seeds') + 1]):
            m = re.match(r'\s*(?:\$|0x)?([0-9a-fA-F]+)', line)
            if m:
                seeds.append(int(m.group(1), 16))
    p = Prg(prg_path)
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)

    # Jump table.
    jt = {}
    a = TEXT_BASE
    while p.w(a) == 0x4EF9:
        jt[a] = p.l(a + 2)
        a += 6
    jt_end = a

    insns = {}                                  # addr -> capstone insn
    funcs = set()
    labels = set()
    callers = defaultdict(set)
    tables = []
    work = []

    def add(t, func=False, label=True):
        if not p.in_text(t) or t & 1:
            return
        if func:
            funcs.add(t)
        if label:
            labels.add(t)
        if t not in insns:
            work.append(t)

    entry = jt[TEXT_BASE]
    add(entry, True)
    for t in jt.values():
        add(t, True)
    for s in seeds:
        add(s, label=False)
    cur_func = {}

    def descend():
        while work:
            a = work.pop()
            while p.in_text(a) and a not in insns:
                try:
                    i = next(md.disasm(p.img[a - TEXT_BASE:a - TEXT_BASE + 10], a, 1))
                except StopIteration:
                    break
                insns[a] = i
                kind, t = flow(p, a)
                if kind == 'call':
                    if t is not None:
                        add(t, True)
                        callers[t].add(a)
                elif kind in ('jump', 'branch'):
                    if t is not None:
                        add(t)
                    if kind == 'jump':
                        break
                elif kind == 'stop':
                    break
                elif kind == 'table':
                    tables.append(a)
                    break
                a += i.size

    descend()
    # Gaps that start with `link a6`: functions reached only through pointers.
    while True:
        found = False
        a = jt_end
        while a < p.text_end - 1:
            if a not in insns and p.w(a) == 0x4E56:
                add(a, True); found = True
                descend()
            a += 2 if a not in insns else insns[a].size
        if not found:
            break

    # Function containing each instruction (for naming the trap wrappers).
    code = sorted(insns)
    owner = {}
    f = None
    for a in code:
        if a in funcs:
            f = a
        owner[a] = f
    names = {}
    trapkind = {}
    for a in code:
        op = p.w(a)
        if op in (0x4E41, 0x4E4D, 0x4E4E) and owner[a] is not None:
            k = {0x4E41: 'gemdos', 0x4E4D: 'bios', 0x4E4E: 'xbios'}[op]
            trapkind.setdefault(owner[a], k)
            names.setdefault(owner[a], f'{k}_{owner[a]:06X}')

    def name(t):
        if t in names:
            return names[t]
        if t in funcs:
            return f'F_{t:06X}'
        return f'L_{t:06X}'

    a4 = p.a4

    def comment_for(i, prev):
        cs = []
        ops = i.op_str
        for m in re.finditer(r'(-?)\$([0-9a-f]+)\(a4\)', ops):
            off = int(m.group(2), 16) * (-1 if m.group(1) else 1)
            g = a4 + off
            seg = 'bss' if g < a4 else 'data'
            cs.append(f'G_{g:06X} ({seg})')
        for m in re.finditer(r'\$([0-9a-f]+)\.([wl])', ops):
            v = int(m.group(1), 16)
            if m.group(2) == 'w' and v & 0x8000:
                v |= 0xFF0000
            v &= 0xFFFFFF
            if v in HW:
                cs.append(HW[v])
        kind, t = flow(p, i.address)
        if kind == 'call' and t is not None and t in trapkind:
            # Look back for the function number pushed last.
            for q in prev[::-1][:4]:
                m = re.match(r'#\$([0-9a-f]+), -\(a7\)', q.op_str)
                if q.mnemonic == 'move.w' and m:
                    n = int(m.group(1), 16)
                    tab = {'gemdos': GEMDOS, 'xbios': XBIOS, 'bios': BIOS}[trapkind[t]]
                    cs.append(f'{trapkind[t]} {tab.get(n, hex(n))}')
                    break
        return '; ' + ', '.join(cs) if cs else ''

    out = []
    out.append(f'; SUPER.PRG: text {TEXT_BASE:06X}-{p.text_end:06X}, data {p.data_base:06X} (+{p.dlen:X}, moved up '
               f'by the BSS at start-up), BSS +{p.blen:X}, a4 = {a4:06X}')
    out.append(f'; {len(insns)} instructions, {len(funcs)} functions, {len(tables)} computed jumps')
    a = TEXT_BASE
    prev = []
    data_run = []

    def flush():
        if not data_run:
            return
        for k in range(0, len(data_run), 16):
            chunk = bytes(data_run[k:k + 16])
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
            out.append(f'{data_start + k:06X}  dc.b    {",".join(f"${c:02x}" for c in chunk):<64} ; {asc}')
        data_run.clear()

    data_start = 0
    while a < p.text_end:
        if a in insns:
            flush()
            i = insns[a]
            if a in funcs:
                out.append('')
                cl = ', '.join(name(owner[c]) if owner.get(c) else f'{c:06X}' for c in sorted(callers[a]))
                out.append(f'; ---- {name(a)}' + (f'  (called from {cl})' if cl else ''))
            if a in labels or a in funcs:
                out.append(f'{name(a)}:')
            kind, t = flow(p, a)
            ops = i.op_str
            if t is not None and kind in ('call', 'jump', 'branch'):
                ops = ops + f'    -> {name(t)}'
            line = f'{a:06X}  {i.mnemonic:<8}{ops}'
            c = comment_for(i, prev)
            out.append(f'{line:<64}{c}' if c else line)
            prev = (prev + [i])[-6:]
            a += i.size
        else:
            if not data_run:
                data_start = a
            data_run.append(p.img[a - TEXT_BASE])
            a += 1
    flush()
    out.append('')
    out.append('; ---- data segment (as loaded; the program moves it up to a4 at start-up)')
    for k in range(0, p.dlen, 16):
        chunk = p.img[p.tlen + k:p.tlen + k + 16]
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        out.append(f'{a4 + k:06X}  dc.b    {",".join(f"${c:02x}" for c in chunk):<64} ; {asc}')
    open(out_s, 'w').write('\n'.join(out) + '\n')

    if out_j:
        json.dump({'text_base': TEXT_BASE, 'text_end': p.text_end, 'a4': a4,
                   'functions': {f'{f:06X}': {'name': name(f), 'callers': sorted(f'{c:06X}' for c in callers[f])}
                                 for f in sorted(funcs)},
                   'tables': [f'{t:06X}' for t in tables],
                   'code_bytes': sum(i.size for i in insns.values())}, open(out_j, 'w'), indent=1)
    cov = sum(i.size for i in insns.values())
    print(f'{len(funcs)} functions, {len(insns)} instructions, {cov} of {p.tlen} text bytes as code, '
          f'{len(tables)} computed jumps; wrappers {[(hex(k), v) for k, v in names.items()]}')


if __name__ == '__main__':
    main(sys.argv[1:])
