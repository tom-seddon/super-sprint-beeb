"""The race logic's data for the BBC (Phase 4, D9): the ST's tables, and a traced race's inputs for the logic test.

Usage: gen_logic.py TRACE.json OUTDIR   (TRACE from tools/st_trace_logic.py)

Writes:
- OUTDIR/tables.6502: the ST's tables the logic reads, as bytes: the direction vectors (G_01E280, G_01E260,
  INIT.DAT), the coasting table (G_01D17A, 6 levels x 7 phases) and the jump sequences (G_01D1FC frames a step,
  G_01D1CE the facing change), both made by F_012276 and read here from a RAM dump, and the start grid
  (G_01EDA8: x, y, y step and facing a track);
- OUTDIR/race.6502: the traced race's constants: its track, race counter, the drone flags, TOS's generator's
  seed before the race's first draw, and how many frames the trace has;
- OUTDIR/inputs.bin: from the race's first frame (the trace's frame 2) on, 3 bytes a frame: cars 0-2's inputs
  as F_010CF2 returned them (0 where a car read none: a drone, or a wrecked car);
- OUTDIR/cells.6502: the track's attribute map (F_015CA2's, from INIT.DAT's runs: 40 x 25 bytes, one a cell),
  its rows' addresses, and the two attribute probe points per facing (G_01E0C0);
- OUTDIR/path.6502: the track's drone path (F_00FAD8's: SUPER.DAT's entries x8, y8, length, direction word),
  as tables by entry, with 4 entries more than the track has (the ST reads on into the next track's past a
  fork or skip at the end; none does, but the tables cover it);
- OUTDIR/walls.6502: the track's mask B as D13 stores it (tools/maskb.py), and the walls' probes: per facing
  the probed lines and columns (G_01E160), and per car and facing what of its frame's shape they test.

The probes. F_01519C ANDs each of a car's 12 lines of opacity (its frame's pixels that aren't colour 8,
the frame car * 16 + facing, + 64 if a drone drives it) with mask B, the opacity's column j over the
pixel x + j; F_00C4F6 tests the top probe line and the bottom one whole, and one column on each side over
the lines from the top probe to the one above the bottom. So per car and facing: the top and bottom
lines' opaque columns as 3 bytes (bit 7 of the first column 0; no frame is opaque past column 16), and for
each side column, the lines it's tested on where the frame is opaque there (bit n line n).
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logic_maps as L
import maskb
import st_sprites

ROOT = L.ROOT
FirstFrame = 2                          # the trace's first race frame: frames 0 and 1 are the set-up's two flips
A4 = 0x1F296                            # the ST's a4, its globals' base


def st_consts():
    """The constants F_012276 stores at start-up, by running its stores from the disassembly (build/super.s):
    `lea.l +-$n(a4), a1`, then `move.w|b|l #$v, (a1)+`, `adda.w #$n, a1`, and `move.w #$v, -$n(a4)`.
    -> {address: byte}."""
    mem, a1, on = {}, None, False
    put = lambda a, v, n: mem.update({a + i: (v >> (8 * (n - 1 - i))) & 0xFF for i in range(n)})
    size = {'b': 1, 'w': 2, 'l': 4}
    for line in open(os.path.join(ROOT, 'build/super.s')):
        if line.startswith('F_012276:'):
            on = True
            continue
        if not on:
            continue
        if line.startswith('; ----'):
            break
        m = re.search(r'lea\.l\s+(-?)\$([0-9a-f]+)\(a4\), a1', line)
        if m:
            a1 = A4 + (-1 if m.group(1) else 1) * int(m.group(2), 16)
            continue
        m = re.search(r'move\.([bwl])\s+#\$([0-9a-f]+), \(a1\)\+', line)
        if m:
            n = size[m.group(1)]
            put(a1, int(m.group(2), 16), n)
            a1 += n
            continue
        m = re.search(r'move\.l\s+a0, \(a1\)\+', line)
        if m:
            a1 += 4                     # an address: not one of the logic's tables
            continue
        m = re.search(r'adda\.w\s+#\$([0-9a-f]+), a1', line)
        if m:
            a1 += int(m.group(1), 16)
            continue
        m = re.search(r'move\.([bwl])\s+#\$([0-9a-f]+), -\$([0-9a-f]+)\(a4\)', line)
        if m:
            put(A4 - int(m.group(3), 16), int(m.group(2), 16), size[m.group(1)])
    return mem


Consts = None


def dump_words(addr, n):
    global Consts
    Consts = Consts or st_consts()            # (a byte it never stores is BSS: 0)
    return [int.from_bytes(bytes(Consts.get(addr + 2 * i + k, 0) for k in range(2)), 'big', signed=True) for i in range(n)]


def byte_list(vals):
    return ', '.join('&%02X' % (v & 0xFF) for v in vals)


def tables():
    dx = L.words(L.tb(0x1E280))[:16]
    dy = L.words(L.tb(0x1E260))[:16]
    coast = dump_words(0x1D17A, 42)
    jframes = dump_words(0x1D1FC, 24)
    jturn = dump_words(0x1D1CE, 23)
    grid = L.words(L.tb(0x1EDA8))[:32]
    assert coast[:7] == [0] * 7 and coast[35:42] == [1, 0, 1, 1, 1, 0, 1], 'the coasting table, as st-logic §2'
    assert all(-128 <= v < 128 for v in dx + dy + jturn) and all(0 <= v < 256 for v in coast + jframes + grid)
    return '\n'.join([
        '\\\\ tables.6502 - the ST\'s tables the race logic reads (tools/gen_logic.py)',
        '',
        '.DirX                                   ; G_01E280: a facing\'s x step, signed (facing 0 up, clockwise)',
        '    EQUB ' + byte_list(dx),
        '.DirY                                   ; G_01E260: its y step',
        '    EQUB ' + byte_list(dy),
        '.Coast                                  ; G_01D17A: [level * 7 + phase] 1 to take 1 off (see human.6502)',
        '    EQUB ' + byte_list(coast),
        '.JumpFrames                             ; G_01D1FC: a jump step\'s frames, 0 the sequence\'s end',
        '    EQUB ' + byte_list(jframes),
        '.JumpTurn                               ; G_01D1CE: the facing change at a step\'s start, signed',
        '    EQUB ' + byte_list(jturn),
        '.GridX                                  ; G_01EDA8: a track\'s start grid: x,',
        '    EQUB ' + byte_list(grid[0::4]),
        '.GridY                                  ; car 0\'s y,',
        '    EQUB ' + byte_list(grid[1::4]),
        '.GridStep                               ; the y step a car,',
        '    EQUB ' + byte_list(grid[2::4]),
        '.GridDir                                ; and the facing',
        '    EQUB ' + byte_list(grid[3::4]),
        ''])


def walls(track, drones):
    hdr, maps, cells = maskb.encode(track)
    rows = [hdr[r * 8:r * 8 + 8] for r in range(25)]
    lo = [h[0] for h in rows]
    n = [h[1] for h in rows]
    moff = [int.from_bytes(h[4:6], 'little') for h in rows]
    coff = [int.from_bytes(h[6:8], 'little') for h in rows]
    words = L.words(L.tb(0x1E160))
    top, bot, left, right = [], [], [], []
    for d in range(16):
        w = words[d * 8:d * 8 + 8]
        long = lambda k: ((w[2 * k] & 0xFFFF) << 16) | (w[2 * k + 1] & 0xFFFF)
        top.append(long(0) // 4)
        bot.append(long(1) // 4)
        for k, side in ((2, left), (3, right)):
            m = long(k)
            assert m and m & (m - 1) == 0, 'a probe column is one bit'
            side.append(31 - m.bit_length() + 1)
    push = [v & 0xFF for v in L.words(L.tb(0x1E140))[:16]]
    dat = open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read()
    pt, pb, pl, pr = [], [], [], []
    for car in range(4):
        for d in range(16):
            o = st_sprites.car_frame(dat, (car + 4 * drones[car]) * 16 + d) != 8
            assert not o[:, 17:].any(), 'no frame is opaque past column 16'
            pattern = lambda l: sum(int(o[l, j]) << (23 - j) for j in range(17))
            pt.append(pattern(top[d]))
            pb.append(pattern(bot[d]))
            pl.append(sum(int(o[l, left[d]]) << l for l in range(top[d], bot[d])))
            pr.append(sum(int(o[l, right[d]]) << l for l in range(top[d], bot[d])))
    rowlist = lambda v: '{' + ', '.join(map(str, v)) + '}'
    eq = lambda name, comment, v: [f'.{name:<38}; {comment}', '    EQUB ' + byte_list(v)]
    return '\n'.join([
        '\\\\ walls.6502 - track %d\'s mask B (D13) and the race\'s cars\' wall probes (tools/gen_logic.py)' % (track + 1),
        '',
        *eq('MbLo', 'a cell row\'s span: its first column', lo),
        *eq('MbEnd', 'and the column after it', [a + b for a, b in zip(lo, n)]),
        *eq('MbLeft', 'the fill left of the span: 0 road, &FF wall', [h[2] for h in rows]),
        *eq('MbRight', 'and right of it', [h[3] for h in rows]),
        f'.{"MbMapL":<38}; the row\'s map, less its first column: a byte a cell, 0, &FF or the nth mixed cell',
        f'    EQUB LO(MbMaps + {rowlist(moff)} - {rowlist(lo)})',
        '.MbMapH',
        f'    EQUB HI(MbMaps + {rowlist(moff)} - {rowlist(lo)})',
        f'.{"MbCellL":<38}; the row\'s mixed cells, 8 lines each, less 8',
        f'    EQUB LO(MbCells + {rowlist(coff)} - 8)',
        '.MbCellH',
        f'    EQUB HI(MbCells + {rowlist(coff)} - 8)',
        *eq('MbMaps', 'the maps', maps),
        *eq('MbCells', 'the cells', cells),
        *eq('ProbeTop', 'G_01E160 by facing: the top probe line,', top),
        *eq('ProbeBot', 'the bottom one,', bot),
        *eq('ProbeLeft', 'the left column,', left),
        *eq('ProbeRight', 'the right one', right),
        *eq('PushDir', 'G_01E140: a probe code\'s push direction, &FF none, &80 a wreck', push),
        *eq('PTop0', 'by car * 16 + facing: the top line\'s opaque columns, 0-7,', [v >> 16 for v in pt]),
        *eq('PTop1', '8-15,', [v >> 8 for v in pt]),
        *eq('PTop2', '16-23', pt),
        *eq('PBot0', 'the bottom line\'s', [v >> 16 for v in pb]),
        *eq('PBot1', '', [v >> 8 for v in pb]),
        *eq('PBot2', '', pb),
        *eq('PLeftLo', 'the lines the left column is opaque on, tested: 0-7,', pl),
        *eq('PLeftHi', '8-15', [v >> 8 for v in pl]),
        *eq('PRightLo', 'the right column\'s', pr),
        *eq('PRightHi', '', [v >> 8 for v in pr]),
        ''])


def path(track):
    n = L.PATH_COUNT[track]
    w = L.words(L.SUPER[L.PATH_OFF:L.PATH_OFF + 7100 + 64])
    base = (L.PATH_START[track] + 2) // 2
    e = [tuple(v & 0xFFFF for v in w[base + 4 * k:base + 4 * k + 4]) for k in range(n + 4)]
    assert all(ln < 256 and d < 0x800 for x, y, ln, d in e[:n]), 'lengths a byte, flags in bits 8-10'
    eq = lambda name, comment, v: [f'.{name:<38}; {comment}', '    EQUB ' + byte_list(v)]
    return '\n'.join([
        '\\\\ path.6502 - track %d\'s drone path (tools/gen_logic.py)' % (track + 1),
        '',
        'PathCount = %d                          ; G_01D168: its entries' % n,
        *eq('PathX8Lo', 'by entry: its start, x in eighths', [v[0] for v in e]),
        *eq('PathX8Hi', '', [v[0] >> 8 for v in e]),
        *eq('PathY8Lo', 'y', [v[1] for v in e]),
        *eq('PathY8Hi', '', [v[1] >> 8 for v in e]),
        *eq('PathLen', 'its length', [v[2] for v in e]),
        *eq('PathDirLo', 'its direction (bits 0-3), a gate (bits 0-1) or a skip (0-7)', [v[3] for v in e]),
        *eq('PathDirHi', 'its flags: 1 a fork (the word &100 exactly), 2 a gate, 4 a skip', [v[3] >> 8 for v in e]),
        ''])


def cells(track):
    m, _ = L.attr_map(track)
    pts = L.words(L.tb(0x1E0C0))[:64]
    assert all(0 <= v < 128 for v in pts), 'the probe points are small and positive'
    eq = lambda name, comment, v: [f'.{name:<38}; {comment}', '    EQUB ' + byte_list(v)]
    return '\n'.join([
        '\\\\ cells.6502 - track %d\'s attribute map and its probe points (tools/gen_logic.py)' % (track + 1),
        '',
        *eq('AttrProbe', 'G_01E0C0 by facing * 4: the probes\' dx1, dy1, dx2, dy2 from the sprite box', pts),
        f'.{"AttrRowL":<38}; a cell row\'s first cell',
        '    EQUB LO(AttrMap + (0..24) * 40)',
        '.AttrRowH',
        '    EQUB HI(AttrMap + (0..24) * 40)',
        '    ALIGN 2                             ; (an object\'s pair of cells: the first\'s address even)',
        *eq('AttrMap', 'a byte a cell: bit 7 a stripe, bits 0-1 the class, 2-6 the type', m),
        ''])


def main(trace_path, out):
    t = json.load(open(trace_path))
    frames = t['frames']
    assert [f['frame'] for f in frames] == list(range(len(frames))), 'the trace\'s frames run from 0'
    m = frames[1]['mem']
    drone = [m[str(0x1E34C + 2 * c)] << 8 | m[str(0x1E34C + 2 * c + 1)] for c in range(4)]
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'tables.6502'), 'w').write(tables())
    open(os.path.join(out, 'walls.6502'), 'w').write(walls(t['track'], drone))
    open(os.path.join(out, 'cells.6502'), 'w').write(cells(t['track']))
    open(os.path.join(out, 'path.6502'), 'w').write(path(t['track']))
    inputs = bytearray()
    for f in frames[FirstFrame:]:
        b = [0, 0, 0]
        for car, bits in f['inputs']:
            b[car] = bits
        inputs += bytes(b)
    open(os.path.join(out, 'inputs.bin'), 'wb').write(inputs)
    open(os.path.join(out, 'race.6502'), 'w').write('\n'.join([
        '\\\\ race.6502 - the traced race the logic test plays (tools/gen_logic.py, from %s)' % os.path.basename(trace_path),
        '',
        'TraceTrack = %d' % t['track'],
        'TraceRace = %d' % t['race'],
        'TraceDrones = {%s}' % ', '.join(map(str, drone)),
        'TraceSeed = &%08X                   ; TOS\'s Random\'s state before the race\'s first draw' % t['seed'],
        'TraceFrames = %d                    ; the trace\'s frames, the set-up\'s two included' % len(frames),
        'TraceFirst = %d                     ; the first race frame\'s counter' % FirstFrame,
        '']))
    print(f'{len(frames) - FirstFrame} race frames of inputs; drones {drone}; seed &{t["seed"]:08X}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
