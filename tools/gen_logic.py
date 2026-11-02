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
  as F_010CF2 returned them (0 where a car read none: a drone, or a wrecked car).
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logic_maps as L

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


def main(trace_path, out):
    t = json.load(open(trace_path))
    frames = t['frames']
    assert [f['frame'] for f in frames] == list(range(len(frames))), 'the trace\'s frames run from 0'
    m = frames[1]['mem']
    drone = [m[str(0x1E34C + 2 * c)] << 8 | m[str(0x1E34C + 2 * c + 1)] for c in range(4)]
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'tables.6502'), 'w').write(tables())
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
