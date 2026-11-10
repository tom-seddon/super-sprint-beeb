"""The BBC's data for the renderer test (Phase 3): one track's background, the cars' frames, the priority
cells and an ST race's car positions, as binaries and Baron source in build/gen.

Usage: gendata.py TRACK TRACE.json OUTDIR [--logic]

--play (with --logic): a build to play, three players on the keys and car 3 the drone: every car's frame set.
--ta (with --play): the time attack variant's (docs/brief-timeattack-2026-11-10.md): GenTimeAttack = 1.

--logic (Phase 4, step 8): the race is drawn from the BBC's own logic, not the trace, so every moving object's
key the logic can draw is made (the explosion's 26 frames, the sparks' 41, the track's banner's 36, the
helicopter's all as always), and logickeys.6502 gives the 6502 each key's pieces, and the car frame sets;
the trace is still read for the sets and the HUD (its frames are the check's model's), but no trace.bin.

- bg.bin: the play area, 16,000 bytes of MODE 1 in the screen's cell order (option B, convert.py's).
- cars.bin: each car frame (car * 16 + facing, 0-63) at each of 4 pixel shifts, trimmed to the bytes and rows
  its pixels cover, column by column (each column's rows together). Every pixel is a 2-bit value: 0 black,
  1 the body colour, 2 transparent (the key), 3 white. The yellow car's yellow is stored as 1 and drawn
  through a table that makes 1 yellow; the others' 1 is green (or unused).
- cars.6502: per frame-shift (frame * 4 + shift) its first byte column (from the box's x DIV 4), width in
  bytes and data offset; per frame its first row and height.
- prio.bin, prioclass.bin, priomap.bin, prio.6502: the priority mask (where a car on the ground is hidden),
  for the 8 x 8 cells with a hidden pixel only: each one's 8 lines of 1-bit masks, and a class byte for its
  two halves (nothing, all or some hidden); a map of the 40 x 25 cells (0, or the cell's number in its row
  from 1), each row stored from 2 cells before its first to 2 after its last, with its offset, first and
  last; and each row's first cell's number, less 1, from which its data and class are found.
- trace.bin, trace.6502: the race, 12 bytes a frame: per car in draw order, x's low byte, y, and frame |
  elevated << 6 | x's high bit << 7.
- hudevents.bin: the HUD's changes, 10 bytes each: the frame (2 bytes), the car, its laps completed, and its
  score's 6 bytes as the ST has them (a BCD digit each, &80 a leading blank); a frame of &FFFF ends them.
- font.6502: the HUD's glyphs (tools/font.py).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from st_sprites import car_frame
from convert import OPTIONS, car_table, logical_map, apply_map, mode1_bytes
from font import Glyphs, glyph_bytes
import objects
import logic_maps

Opt = OPTIONS['B']
# each track's banner's place (G_01EBE0, G_01EBF0): the ST draws it there with F_0148BE
BannerPlace = list(zip(logic_maps.words(logic_maps.tb(0x1EBE0))[:8], logic_maps.words(logic_maps.tb(0x1EBF0))[:8]))
Key = 2


def pixel_byte(vals):
    """Four 2-bit values, left to right -> a MODE 1 byte."""
    b = 0
    for n, v in enumerate(vals):
        b |= ((v >> 1) & 1) << (7 - n) | (v & 1) << (3 - n)
    return b


def car_values(dat, car, droned, facing):
    """A car's frame (or the drone-driven set's, with car 1's colours) as 12 x 17 2-bit values, transparent
    as Key. The drone-driven set's stripes are value 1, coloured by the car's data table."""
    f = (64 if droned else 0) + (1 if droned else car) * 16 + facing
    st = car_frame(dat, f)[:, :17]
    lidx = apply_map(st, logical_map(Opt, car_table(Opt, 1 if droned else car, droned))).astype(np.uint8)
    opaque = st != 8
    v = lidx.copy()
    if car == 2 and not droned:
        assert not (opaque & (lidx == 1)).any()
        v[lidx == 2] = 1
    else:
        assert not (opaque & (lidx == 2)).any()
    v[~opaque] = Key
    return v, opaque


def car_sets(frames):
    """The frame sets a race draws: the cars' own, and the drone-driven one if any car is driven by a drone
    (in a real race car 3 always is; the attract race draws every car in its own). -> [(car, droned)], car
    None for the shared drone-driven set."""
    used = set()
    for fr in frames:
        for c in fr['order']:
            used.add((None, True) if fr['drone'][c] else (c, False))
    return sorted(used, key=lambda k: (k[0] is None, k[0] or 0))


def set_of(sets, car, droned):
    return sets.index((None, True) if droned else (car, False))


# a car's data table, by car and drone-driven: 0 DataId (1 green), 1 DataYellow, 2 DataWhite, 3 DataBlack. Car 3
# isn't a drone only in the demo, which draws it from the drone-driven set (D20): black, as in a race, not green
# (its own frames have no value 1, so the attract trace's builds, which have them, draw the same)
CarTable = {(0, 0): 0, (1, 0): 0, (2, 0): 1, (3, 0): 3, (0, 1): 2, (1, 1): 0, (2, 1): 1, (3, 1): 3}


def cars(dat, sets):
    blocks = []                 # per frame * 4 + shift: its bytes
    fs = []                     # (dx, w) per frame * 4 + shift
    fr = []                     # (dy, h) per frame
    for f in range(16 * len(sets)):
        car, droned = sets[f // 16]
        v, opaque = car_values(dat, car, droned, f % 16)
        ys = np.where(opaque.any(1))[0]
        xs = np.where(opaque.any(0))[0]
        y0, h = ys.min(), ys.max() - ys.min() + 1
        fr.append((int(y0), int(h)))
        for sh in range(4):
            canvas = np.full((12, 20), Key, np.uint8)
            canvas[:, sh:sh + 17] = v
            dx = (xs.min() + sh) // 4
            w = (xs.max() + sh) // 4 - dx + 1
            fs.append((int(dx), int(w)))
            blocks.append(bytes(pixel_byte(canvas[r, (dx + n) * 4:(dx + n) * 4 + 4])
                                for n in range(w) for r in range(y0, y0 + h)))
    # each block wholly in a page and at least 7 bytes in: the plotter's operands point up to 7 bytes before
    # a block (less the band's first line) and keep its page's high byte
    offsets, size = pack_pages([len(b) for b in blocks], 7)
    data = bytearray(size)
    for i, b in enumerate(blocks):
        data[offsets[i]:offsets[i] + len(b)] = b
    return bytes(data), [(d, w, o) for (d, w), o in zip(fs, offsets)], fr


def pack_pages(sizes, head):
    """Blocks of these sizes packed into pages, each wholly in one and head bytes or more in: a page at a
    time, the largest block left first, then the subset of the rest that fills the page most. -> (each
    block's offset, the bytes to the last page's last block). (First fit, largest first, left 365 bytes
    at pages' ends in the play build's cars' frames; this 25.)"""
    left = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))
    offsets, page = [None] * len(sizes), 0
    while left:
        first, room = left[0], 256 - head - sizes[left[0]]
        reach = {0: []}                 # a fill of the room -> the blocks that make it
        for i in left[1:]:
            for s, items in list(reach.items()):
                if s + sizes[i] <= room and s + sizes[i] not in reach:
                    reach[s + sizes[i]] = items + [i]
        at = page * 256 + head
        for i in [first] + reach[max(reach)]:
            offsets[i] = at
            at += sizes[i]
        chosen = set([first] + reach[max(reach)])
        left = [i for i in left if i not in chosen]
        page += 1
    return offsets, at


def prio(track, reserved=()):
    """Each 8 x 8 cell with hidden pixels, or reserved (a gate's or barrier's, whose bits change in the race):
    its 8 lines of bits (1 hidden), and a class byte: per half (left in bits 0-1, right in bits 2-3), 0 nothing
    hidden, 1 all hidden, 2 some. A reserved cell's class is always 2 for both: its bits decide."""
    hidden = np.load(f'build/gfx/maskclean2_t{track}.npy') == 0
    cells = hidden.reshape(25, 8, 40, 8)
    data = bytearray()
    classes = bytearray()
    cellmap = np.zeros((25, 40), np.uint8)
    rowoff = []
    for r in range(25):
        rowoff.append(len(classes))
        k = 0
        for c in range(40):
            if cells[r, :, c, :].any() or (r, c) in reserved:
                k += 1
                cellmap[r, c] = k
                for line in range(8):
                    data.append(int(np.packbits(cells[r, line, c, :])[0]))
                cls = 0
                for half in range(2):
                    h = cells[r, :, c, half * 4:half * 4 + 4]
                    cls |= (0 if not h.any() else 1 if h.all() else 2) << (2 * half)
                classes.append(2 | 2 << 2 if (r, c) in reserved else cls)
    return bytes(data), bytes(classes), cellmap, rowoff


def load_race(path):
    """A trace (st_trace_cars.py's attract race, or st_race.py's real one), every frame with its drone flags
    and calls (the attract race's only the car plotter's, from its draw order; its cars are all drawn in
    their own colours)."""
    frames = json.load(open(path))
    for fr in frames:
        fr.setdefault('drone', [0, 0, 0, 0])
        fr.setdefault('calls', [['car', [c]] for c in fr['order']])
    return frames


def map_at(idx, lmap, x0, y0):
    """apply_map for a patch whose top-left is at (x0, y0) on the screen: the patterns' phase the screen's."""
    h, w = idx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ph = ((x0 + xx) & 1) + 2 * ((y0 + yy) & 1)
    out = np.zeros((h, w), np.uint8)
    for c, pat in lmap.items():
        m = idx == c
        for k in range(4):
            out[m & (ph == k)] = pat[k]
    return out


def rows_bytes(lidx):
    """A patch of logical colours, 4n wide -> its MODE 1 bytes, column by column (each column's rows together)."""
    return bytes(pixel_byte(lidx[r, 4 * n:4 * n + 4]) for n in range(lidx.shape[1] // 4) for r in range(lidx.shape[0]))


# the background objects' kinds in the trace, and the variants each has
ObjKinds = {'slot': 1, 'gate': 2, 'barrier': 3}
ObjSizes = {'gate': (48, 16), 'barrier': (16, 8)}       # (w, h): the kinds that write mask C
ObjFrames = {'gate': 5, 'barrier': 12}           # (a barrier: 3 kinds of 4 frames, by track)


def instances(frames):
    """The race's gates and barriers, each at its place: [(kind, x, y)], in the order they first come."""
    out = []
    for fr in frames:
        for c in fr['calls']:
            if c[0] in ObjSizes:
                key = (c[0],) + objects.place(c[0], c[1])
                if key not in out:
                    out.append(key)
    return out


def transitions(frames, insts):
    """Each gate's or barrier's call, as an entry: (instance, from frame or None, to frame), the ST's second
    call for its other screen the same entry as its first. -> (the entries in the order they first come,
    per frame a list of entry numbers for its gate and barrier calls in order)."""
    entries, per, prev, now, last = [], [], [], {}, {}
    for fr in frames:
        objs = [(c[0], tuple(c[1][:2])) for c in fr['calls'] if c[0] in ObjKinds]
        mine = []
        for n, w in objs:
            if n not in ObjSizes:
                continue
            i = insts.index((n,) + objects.place(n, w))
            if (n, w) not in prev:
                e = (i, now.get(i), w[0])
                if e not in entries:
                    entries.append(e)
                now[i] = w[0]
                last[i] = entries.index(e)
            mine.append(last[i])
        per.append(mine)
        prev = objs
    assert len(entries) * 3 <= 256
    return entries, per


def logic_objects(track):
    """The logic build's gates and barriers (step 11): every one the track has, the barriers first as the ST
    draws them, each at rest in its first frame (a barrier's kind + 3, a gate shut); every frame of each; and
    every entry the logic can ask for, by instance: its first draw (code 0), a step up to frame t (code t,
    1-4), a step down to t (code 5 + t, 0-3), t a gate's position or a barrier's frame within its kind.
    -> (insts, rest, objframes, entries, the entry for each instance * 9 + code, 255 none)."""
    ng, gp = logic_maps.words(logic_maps.tb(0x1ED88))[track], logic_maps.words(logic_maps.tb(0x1ED98), False)
    bp, bk = logic_maps.words(logic_maps.tb(0x1EC00), False), logic_maps.tb(0x1EC30)
    insts = [('barrier',) + logic_maps.scr(bp[track * 3 + i]) for i in range(3)]
    insts += [('gate',) + logic_maps.scr(gp[track + i]) for i in range(ng)]
    base = [bk[track * 3 + i] for i in range(3)] + [0] * ng
    top = [3] * 3 + [4] * ng
    rest = {i: base[i] + top[i] if i < 3 else 0 for i in range(len(insts))}
    objframes = {'gate': list(range(5)) if ng else [],
                 'barrier': sorted({base[i] + f for i in range(3) for f in range(4)})}
    entries, codes = [], [255] * (9 * len(insts))
    for i in range(len(insts)):
        steps = [(0, None, rest[i])] + [(t, base[i] + t - 1, base[i] + t) for t in range(1, top[i] + 1)] \
            + [(5 + t, base[i] + t + 1, base[i] + t) for t in range(top[i])]
        for code, f0, f1 in steps:
            codes[9 * i + code] = len(entries)
            entries.append((i, f0, f1))
    return insts, rest, objframes, entries, codes


def instance_cells(kind, x, y):
    """The 8 x 8 cells an instance covers, by cell row: [(row, first column, columns)]."""
    w, h = ObjSizes[kind]
    return [(r, x // 8, w // 8) for r in range(y // 8, (y + h - 1) // 8 + 1)]


def frames_used(frames):
    """The gates' and barriers' frames the race draws, in order: only they are stored (a race's data is
    loaded per race, D3; a track's barriers are of one or two of the 3 kinds, and only 3 tracks have gates).
    A variant, and an instance's priority entry, is numbered by its frame's place here."""
    return {k: sorted({c[1][0] for fr in frames for c in fr['calls'] if c[0] == k}) for k in ObjSizes}


def object_variants(dat, used):
    """The background objects' variants: the slots' 22 sprites; the gates' and barriers' frames the race uses (of
    5 and 12: a barrier's 3 kinds of 4), each for a top line even or odd (the patterns' phase). -> per kind, a list of (w bytes, h, data, mask or
    None, priority bits or None); the data and mask column by column, the mask's set bits keep the screen (a
    barrier's colour 0); the priority bits too, a byte per 8 pixels, each 8-pixel column's lines together, 1
    where a car on the ground is hidden."""
    lmap = logical_map(Opt, Opt['bg'])
    out = {'slot': [], 'gate': [], 'barrier': []}
    for sprite in range(22):
        out['slot'].append((4, 8, rows_bytes(map_at(objects.slot_bbc(dat, sprite), lmap, 0, 0)), None, None))
    for frame in used['gate']:
        col, mc = objects.gate(dat, frame)
        for parity in range(2):
            out['gate'].append((12, 16, rows_bytes(map_at(col, lmap, 0, parity)), None, None))
    for frame in used['barrier']:
        col, mc = objects.barrier(dat, frame)
        keep = np.where(col == 0, 3, 0).astype(np.uint8)
        for parity in range(2):
            lidx = map_at(col, lmap, 0, parity)
            lidx[col == 0] = 0
            out['barrier'].append((4, 8, rows_bytes(lidx), rows_bytes(keep), None))
    return out


def variant_of(kind, args, y, used):
    return args[0] if kind == 'slot' else used[kind].index(args[0]) * 2 + (y & 1)


# The moving objects: what each frame's calls draw after the background objects, as (key, x, y) in the BBC's
# places (D8: the explosion on 4-pixel steps; the banner's and the tornado's frames shifted for their places,
# x then on a 4-pixel step and the shift in the key; the sparks and the helicopter where the ST has them, on
# 8- and 16-pixel steps). A key names a sprite: ('explosion', frame), ('banner', frame, shift), ('tornado',
# frame, shift), ('spark', frame), ('heli', variant, colour, frame). The explosion is drawn in its car's
# place among the cars; the others after the cars, in the ST's order.

def frame_draws(fr, heli):
    """A frame's draws, in order: ('car', car) or ('explosion', key, x, y, car) among the cars, then the moving
    objects as (key, x, y). heli: the helicopter's composed frames, (variant, colour) by buffer frame,
    updated by the frame's composing calls."""
    cars, movers = [], []
    for c in fr['calls']:
        n, w = c[0], c[1]
        if n == 'car':
            cars.append(('car', w[0]))
        elif n == 'explosion':
            x, y = fr['cars'][w[0]][:2]
            cars.append(('explosion', ('explosion', w[1]), x & ~3, y, w[0]))
        elif n == 'small':
            movers.append((('banner', w[0], w[1] & 3), w[1] & ~3, w[2]))
        elif n == 'tornado':
            y = w[2] - 65536 if w[2] >= 32768 else w[2]
            movers.append((('tornado', w[0], w[1] & 3), w[1] & ~3, y))
        elif n == 'spark':
            st = objects.spark_state(c[2] if len(c) > 2 else {}, w[0])
            if st:
                movers.append((('spark', st[0]), st[1], st[2]))
        elif n == 'heli':
            heli[w[2]] = (w[0], w[1])
        elif n == 'heli2':
            y = w[2] - 65536 if w[2] >= 32768 else w[2]
            movers.append((('heli',) + heli[w[0]] + (w[0],), w[1] & ~15, y))
        elif n == 'heli3':                      # sideways: clipped to the screen a 16-pixel group at a time
            x = w[1] - 65536 if w[1] >= 32768 else w[1]
            assert -48 <= x < 320, "the ST draws garbage further out"
            movers.append((('heli',) + heli[w[0]] + (w[0],), x & ~15, w[2]))
    return cars, movers


def moving_sprite(dat, key):
    """A moving object's sprite: (ST colours, opaque)."""
    if key[0] == 'explosion':
        idx = objects.explosion(dat, key[1])
    elif key[0] == 'banner':
        idx = objects.banner(dat, key[1])
    elif key[0] == 'spark':
        idx = objects.spark(dat, key[1])
    elif key[0] == 'tornado':
        idx = objects.tornado(dat, key[1])
        return idx, idx != 0
    else:
        idx, mask = objects.heli_compose(dat, key[1], key[2], key[3])
        return idx, mask == 0
    return idx, idx != 8


def key_shift(key):
    """The pixels (0-3) a moving object's sprite is shifted right of its x, which is on a 4-pixel step."""
    return key[2] if key[0] in ('banner', 'tornado') else 0


MovCols = 8                             # the plotter's widest piece, in bytes (macros.6502)
PieceCost = 50                          # a piece's cost beyond its bytes, in bytes (its set-up and erase box)


def moving_pieces(dat, key):
    """A moving object's sprite as the BBC stores it: 2-bit values (Key transparent), shifted by its key's
    shift, cut into pieces: rectangles of neighbouring byte columns, each trimmed to the rows its columns
    cover, chosen to draw the fewest bytes, PieceCost a piece more (a helicopter's columns run from 2 rows
    to 33). -> [(dx bytes, dy, w bytes, h, table 0 DataId or 1 DataYellow, bytes column by column)]."""
    idx, opaque = moving_sprite(dat, key)
    lidx = apply_map(idx, logical_map(Opt, Opt['bg'])).astype(np.uint8)
    used = set(lidx[opaque].tolist())
    if used <= {0, 1, 3}:
        table, v = 0, lidx.copy()
    else:
        assert used <= {0, 2, 3}, (key, used)
        table, v = 1, np.where(lidx == 2, 1, lidx).astype(np.uint8)
    v[~opaque] = Key
    shift = key_shift(key)
    h0, w0 = v.shape
    grouped = key[0] == 'heli' and key[1] & 2   # (clipped at the screen's sides by whole groups)
    canvas = np.full((h0, w0 + 4), Key, np.uint8)
    canvas[:, shift:shift + w0] = v
    op = np.zeros(canvas.shape, bool)
    op[:, shift:shift + w0] = opaque
    cols = []
    for c in range(canvas.shape[1] // 4):
        rows = np.where(op[:, 4 * c:4 * c + 4].any(1))[0]
        cols.append((int(rows.min()), int(rows.max())) if len(rows) else None)
    # the best split of the columns into runs of neighbours (an empty column ends a run): cost[i], the least
    # for columns from i on
    n = len(cols)
    best = [(0, [])] * (n + 1)
    for i in range(n - 1, -1, -1):
        if cols[i] is None:
            best[i] = best[i + 1]
            continue
        choice = None
        r0, r1 = cols[i]
        for j in range(i, n):
            if cols[j] is None or j - i == MovCols or (j > i and j % 4 == 0 and grouped):
                break
            r0, r1 = min(r0, cols[j][0]), max(r1, cols[j][1])
            cost = (j - i + 1) * (r1 - r0 + 1) + PieceCost + best[j + 1][0]
            if choice is None or cost < choice[0]:
                choice = (cost, [(i, j, r0, r1)] + best[j + 1][1])
        best[i] = choice
    out = []
    for c0, c1, y0, y1 in best[0][1]:
        data = bytes(pixel_byte(canvas[r, 4 * c:4 * c + 4]) for c in range(c0, c1 + 1) for r in range(y0, y1 + 1))
        out.append((c0, y0, c1 - c0 + 1, y1 - y0 + 1, table, data))
    return out


MaxMovers = 12
HeliCode = 900                          # the fourth bank's copy of the moving objects' plotter, at most (Baron
                                        # checks: the bank's guard)


def tornado_code(dat, key, n):
    """A tornado frame-shift compiled (src/movers.6502's mov_tornado calls it): Baron source for routine
    TorCode{n}, drawing it from the 16 line pointers ts (each its line's cell in the box's first byte
    column, or junk), Y 8 * the byte column: an opaque byte LDA #:STA (no LDA if A has it already), a mixed
    one LDA:AND #:ORA #:STA (no ORA of 0), an empty one nothing. Its colours as the model maps them, the patterns' phase its own. -> (source, first
    byte column, width in bytes)"""
    idx, opaque = moving_sprite(dat, key)
    lidx = apply_map(idx, logical_map(Opt, Opt['bg'])).astype(np.uint8)
    h, w0 = idx.shape
    assert h == 16 and opaque[0].any() and opaque[-1].any(), "the tornado's lines all drawn"
    canvas = np.zeros((h, w0 + 4), np.uint8)
    op = np.zeros(canvas.shape, bool)
    canvas[:, key[2]:key[2] + w0] = lidx
    op[:, key[2]:key[2] + w0] = opaque
    cols = [c for c in range(canvas.shape[1] // 4) if op[:, 4 * c:4 * c + 4].any()]
    lines, a = [f'.TorCode{n}'], None          # (a: A's value, if known)
    for c in cols:
        lines.append(f'    LDY #{8 * (c - cols[0])}')
        for r in range(h):
            o = op[r, 4 * c:4 * c + 4]
            if not o.any():
                continue
            data = pixel_byte(np.where(o, canvas[r, 4 * c:4 * c + 4], 0))
            if o.all():
                lines.append(('' if a == data else f'    LDA #&{data:02X}\n') + f'    STA (ts+{2 * r}),Y')
                a = data
            else:
                keep = pixel_byte(np.where(o, 0, 3))
                lines.append(f'    LDA (ts+{2 * r}),Y:AND #&{keep:02X}' + (f':ORA #&{data:02X}' if data else '')
                             + f':STA (ts+{2 * r}),Y')
                a = None
    lines.append('    RTS')
    return '\n'.join(lines) + '\n', cols[0], cols[-1] - cols[0] + 1


def trace(frames, sets, movpieces, insts, room, piecedx, used, ent_per_frame):
    """The race's frames, as many as fit in room bytes with the HUD's events: per frame the cars drawn
    (their count, then 4 bytes each: car | drone-driven << 2, x's low byte, y, frame | on top << 6 | x's
    high bit << 7) and the background objects' calls (their count, then 4 bytes each: kind | instance << 3 |
    again << 6 | x's high bit << 7, variant, x's low byte, y; the instance a gate's or barrier's). The ST calls each a second time the frame after, for its other
    screen: "again" marks that call, for which the BBC only copies the background into the screen. A wrecked
    car's explosion is among the cars: &80 | x's high bit << 6, x's low byte, y, its moving variant. Then the
    moving objects' pieces (their count, then 5 bytes each: the piece's variant, the object's x, y as 16-bit
    words)."""
    out, starts, prev, heli = bytearray(), [], [], {}

    def onscreen(p, x):
        """A piece's columns wholly on the screen, or wholly off it (the sideways helicopter's)."""
        c0, w = x // 4 + piecedx[p][0], piecedx[p][1]
        assert c0 + w <= 0 or c0 >= 80 or (c0 >= 0 and c0 + w <= 80), "a piece across the screen's side"
        return c0 >= 0 and c0 + w <= 80
    for fi, fr in enumerate(frames):
        cars, movers = frame_draws(fr, heli)
        rec = bytearray([len(cars)])
        for d in cars:
            if d[0] == 'explosion':
                key, x, y = d[1], d[2], d[3]
                assert len(movpieces[key]) == 1, "an explosion in one piece"
                rec += bytes([0x80 | (x >> 8) << 6, x & 255, y, movpieces[key][0]])
                continue
            c = d[1]
            x, y, facing, flags = fr['cars'][c]
            droned = 1 if fr['drone'][c] else 0
            on_top = 1 if flags & 0x0401 else 0
            rec += bytes([c | droned << 2, x & 255, y, set_of(sets, c, droned) * 16 + facing | on_top << 6 | (x >> 8) << 7])
        # each call's own arguments (3 for a slot, 2 for a gate or barrier; the ST's stack has others after)
        objs = [(n, w[:3] if n == 'slot' else w[:2]) for n, w in ((c[0], c[1]) for c in fr['calls']) if n in ObjKinds]
        rec.append(len(objs))
        ents = iter(ent_per_frame[fi])
        for n, w in objs:
            x, y = objects.place(n, w)
            again = 1 if (n, w) in prev else 0          # the ST's second call, for its other screen
            inst = insts.index((n, x, y)) if n in ObjSizes else 0
            assert w[0] < (22 if n == 'slot' else ObjFrames[n]), (n, w)
            v = next(ents) if n in ObjSizes else w[0]   # a gate's or barrier's entry (its transition), or a sprite
            rec += bytes([ObjKinds[n] | inst << 3 | again << 6 | (x >> 8) << 7, v, x & 255, y])
        prev = objs
        rec.append(0)
        pieces = [(p, x, y) for key, x, y in movers for p in movpieces[key] if onscreen(p, x)]
        assert len(pieces) <= MaxMovers, len(pieces)
        rec[-1:] = bytes([len(pieces)])
        for p, x, y in pieces:
            rec += bytes([p, x & 255, (x >> 8) & 255, y & 255, (y >> 8) & 255])
        starts.append(len(out))
        out += rec
    # the HUD's events: a car's laps or score as it changes (every car's at frame 0), 10 bytes each
    def hud_events(n):
        ev, last = bytearray(), [None] * 4
        for i, fr in enumerate(frames[:n]):
            for c in range(4):
                now = (fr['laps'][c], fr['scores'][c])
                if now != last[c]:
                    ev += bytes([i & 255, i >> 8, c, now[0]]) + bytes.fromhex(now[1])
                    last[c] = now
        return ev + bytes([255, 255])
    n = len(frames)
    while (starts[n] if n < len(frames) else len(out)) + len(hud_events(n)) > room:
        n -= 1
    end = starts[n] if n < len(frames) else len(out)
    return bytes(out[:end]), n, hud_events(n)


ObjVariantsMax = 48                     # the background objects' variants, every track's (Phase 5, 3a: the most,
EntriesMax = 48                         # track 8's; the gates' and barriers' entries, track 5's)


def lst(name, vals):
    return f'{name} = {{{", ".join(str(v) for v in vals)}}}\n'


def main(track, tracepath, out, logic=False, play=False, ta=False):
    os.makedirs(out, exist_ok=True)
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    bg = np.load(f'build/conv/B_t{track}_bg.npy')
    bgbytes = mode1_bytes(bg)
    open(f'{out}/bg.bin', 'wb').write(bgbytes)
    frames = load_race(tracepath)
    sets = car_sets(frames)
    if logic:                           # the game's sets (D20): cars 0-2's own and the drone-driven, which
        sets = [(0, False), (1, False), (2, False), (None, True)]   # serve every mix of humans

    data, fs, fr = cars(dat, sets)
    open(f'{out}/cars.bin', 'wb').write(data)
    with open(f'{out}/cars.6502', 'w') as f:
        f.write('\\\\ cars.6502 - made by tools/gendata.py: the car frames\' layout in cars.bin\n\n')
        f.write(lst('GenFsDXW', [d * 8 + w for d, w, o in fs]))
        f.write(lst('GenFsOff', [o for d, w, o in fs]))
        f.write(lst('GenFrDY', [d for d, h in fr]))
        f.write(lst('GenFrH', [h for d, h in fr]))
        f.write(lst('GenCarTable', [CarTable[(c & 3, c >> 2)] for c in range(8)]))
        f.write(f'CarFrames = {len(fr)}\n')
        f.write(f'CarDataSize = {len(data)}\n')

    # the cells a gate or barrier of this race covers: their priority bits change as it moves
    if logic:
        insts, rest, objframes, entries, ent_codes = logic_objects(track)
    else:
        insts = instances(frames)
        objframes = frames_used(frames)
    assert len(insts) <= 8
    # Pop-up barriers can share a cell row (tracks 4 and 6: 9 lines apart). They move one at a time, the
    # others at rest in their first frame, so each one's frames carry its sharers' lines at rest; checked
    # against the race.
    owned = [{(r, c) for r, c0, n in instance_cells(*i) for c in range(c0, c0 + n)} for i in insts]
    reserved = set().union(*owned) if owned else set()
    sharers = [[j for j in range(len(insts)) if j != i and owned[i] & owned[j]] for i in range(len(insts))]
    assert all(insts[i][0] == 'barrier' for i in range(len(insts)) if sharers[i]), "only barriers share cells"
    if not logic:
        rest = {}
    now = {}
    for fr_ in frames if not logic else []:
        for c in fr_['calls']:
            if c[0] in ObjSizes:
                i = insts.index((c[0],) + objects.place(c[0], c[1]))
                rest.setdefault(i, c[1][0])
                if c[1][0] != now.get(i, rest[i]):
                    assert all(now.get(j, rest[j]) == rest[j] for j in sharers[i]), "barriers sharing cells, both moving"
                now[i] = c[1][0]
    pdata, classes, cellmap, rowoff = prio(track, reserved)

    # each instance's runs of cells (a cell row's, together in prio.bin: reserved cells side by side are
    # numbered in turn), and for each of its frames those cells' bits: the track's own, with the frame's
    # mask C over the lines it covers (over its sharers' at rest)
    dat_ = open('orig/st/SUPER.DAT', 'rb').read()
    base_mask = np.load(f'build/gfx/maskclean2_t{track}.npy')
    def cell_bits(i, f):
        """Instance i at frame f: its cells' bits, by (row, column), 8 bytes each."""
        kind, x, y = insts[i]
        m = base_mask.copy()
        bgc = np.zeros((200, 320), np.uint8)
        for j in sharers[i]:
            kj, xj, yj = insts[j]
            objects.apply(dat_, kj, [rest[j], (yj * 160 + xj // 16 * 8)], bgc, m)
        objects.apply(dat_, kind, [f, (y * 160 + x // 16 * 8)], bgc, m)
        hidden = (m == 0)
        return {(r, c): bytes(int(np.packbits(hidden[r * 8 + line, c * 8:c * 8 + 8])[0]) for line in range(8))
                for r, c0, n in instance_cells(kind, x, y) for c in range(c0, c0 + n)}

    # each entry's runs (up to 3: a cell row's cells, together in prio.bin, as reserved cells side by side
    # are numbered in turn), and their bits: a first draw's every cell, a step's only each row's span of
    # cells that change
    if not logic:
        entries, ent_per_frame = transitions(frames, insts)
    ent_runs, ent_bits = [], []
    for i, f0, f1 in entries:
        kind, x, y = insts[i]
        new_, old_ = cell_bits(i, f1), (cell_bits(i, f0) if f0 is not None else None)
        runs, bits = [], b''
        for r, c0, n in instance_cells(kind, x, y):
            v = int(cellmap[r, c0])
            assert all(cellmap[r, c0 + k] == v + k for k in range(n))
            cols = [c for c in range(c0, c0 + n) if old_ is None or old_[r, c] != new_[r, c]]
            if cols:
                runs.append((8 * (rowoff[r] + v - 1 + cols[0] - c0), 8 * (cols[-1] - cols[0] + 1)))
                bits += b''.join(new_[r, c] for c in range(cols[0], cols[-1] + 1))
        ent_runs.append(runs)
        ent_bits.append(bits)
    open(f'{out}/prio.bin', 'wb').write(pdata)
    open(f'{out}/prioclass.bin', 'wb').write(classes)
    # the map: each row from 2 cells before its first with hidden pixels to 2 after its last (a car covers 3
    # cells at most, so one that overlaps the span reads only the span and its zeroes); first and last for
    # the plotter to skip a row's span whole (a row with none: first 255, last 0)
    mapdata, mapoff, first, last = bytearray(), [], [], []
    for r in range(25):
        nz = np.where(cellmap[r])[0]
        if len(nz) == 0:
            mapoff.append(0)
            first.append(255)
            last.append(0)
            continue
        s0, e0 = max(0, nz[0] - 2), min(39, nz[-1] + 2)
        mapoff.append(len(mapdata) - s0)
        first.append(int(nz[0]))
        last.append(int(nz[-1]))
        mapdata += cellmap[r, s0:e0 + 1].tobytes()
    open(f'{out}/priomap.bin', 'wb').write(mapdata)
    with open(f'{out}/prio.6502', 'w') as f:
        f.write('\\\\ prio.6502 - made by tools/gendata.py: the priority cells\' layout\n\n')
        f.write(lst('GenPrioRowOff', [o - 1 for o in rowoff]))
        f.write(lst('GenPrioMapOff', mapoff))
        f.write(lst('GenPrioFirst', first))
        f.write(lst('GenPrioLast', last))
        f.write(f'PrioDataSize = {len(pdata)}\n')

    # the background objects' variants, for the objects' bank: each one's data, mask and priority bits
    variants = object_variants(dat, objframes)
    blocks = []                         # (variant, part, bytes): the background objects' data and masks, each in a
                                        # page, 7 bytes in
    for kind in ObjKinds:
        for i, (w, h, d, m, pb) in enumerate(variants[kind]):
            blocks.append(((kind, i), 0, d))
            if m:
                blocks.append(((kind, i), 1, m))
    movkeys = []
    heli = {}
    if logic:                           # every key the logic can draw, in an order the same on every track
        bx, by = BannerPlace[track]     # (Phase 5, 3a: the bank's code, the tornado's compiled, the same)
        movkeys = ([('explosion', f) for f in range(26)] + [('spark', f) for f in range(41)]
                   + [('banner', f, bx & 3) for f in range(36)] + [('tornado', f, x) for f in range(3) for x in range(4)])
    for fr_ in frames:
        cars_, movers = frame_draws(fr_, heli)
        for k in [d[1] for d in cars_ if d[0] == 'explosion'] + [m[0] for m in movers]:
            if k not in movkeys:
                movkeys.append(k)
    if logic:                           # every key the logic can draw
        bx, by = BannerPlace[track]
        for k in ([('explosion', f) for f in range(26)] + [('spark', f) for f in range(41)]
                  + [('banner', f, bx & 3) for f in range(36)] + [('tornado', f, x) for f in range(3) for x in range(4)]):
            if k not in movkeys:
                movkeys.append(k)
    movers_, movpieces = [], {}
    torkeys = [k for k in movkeys if k[0] == 'tornado']
    for k in movkeys:
        if k[0] in ('tornado', 'heli'):
            continue
        movpieces[k] = []
        for piece in moving_pieces(dat, k):
            movpieces[k].append(len(movers_))
            movers_.append(piece)
    pages, where = [], {}
    for key, part, b in sorted(blocks, key=lambda t: -len(t[2])):
        for p, used in enumerate(pages):
            if used + len(b) <= 256:
                break
        else:
            pages.append(7)
            p = len(pages) - 1
        where[key, part] = p * 256 + pages[p]
        pages[p] += len(b)
    obin = bytearray(256 * len(pages))
    for key, part, b in blocks:
        obin[where[key, part]:where[key, part] + len(b)] = b
    obin = obin[:256 * (len(pages) - 1) + pages[-1]]
    for i, mv in enumerate(movers_):    # (the moving objects' plotter carries each column's address in full:
        where[('move', i), 0] = len(obin)   # its variants go on after, a helicopter's more than a page)
        obin += mv[5]
    vt = []
    for kind in ObjKinds:
        for i, (w, h, d, m, pb) in enumerate(variants[kind]):
            vt.append((w, h, (1 if m else 0) | (2 if kind in ObjSizes else 0), where[(kind, i), 0],
                       where.get(((kind, i), 1), 0)))
    ent_data = []
    for b in ent_bits:
        ent_data.append(len(obin))
        obin += b
    ent_var = [variant_of(insts[i][0], [f1], insts[i][2], objframes) for i, f0, f1 in entries]
    mt = [(dx, dy, w, h, t, where[('move', i), 0]) for i, (dx, dy, w, h, t, d) in enumerate(movers_)]
    torcode = [tornado_code(dat, k, i) for i, k in enumerate(torkeys)] or [('.TorCode0\n    RTS\n', 0, 1)]
    for i, k in enumerate(torkeys):
        movpieces[k] = [len(mt) + i]

    # the helicopter, for the fourth bank: every variant (from below, above and either side) and frame, in
    # both data tables (the carried car's colour yellow, or green for car 3), whichever the race uses: any
    # car can be wrecked anywhere. The two tables' bytes are the same, stored once. Its pieces numbered after
    # the tornado's.
    heli0 = len(mt) + len(torcode)
    hbin, hdata, hpieces, hkey = bytearray(), {}, [], {}
    for v in range(4):
        for c in (0, 3):
            for fr_ in range(4):
                hkey[v, c, fr_] = []
                for dx, dy, w, h, t, d in moving_pieces(dat, ('heli', v, c, fr_)):
                    if d not in hdata:
                        hdata[d] = len(hbin)
                        hbin += d
                    hkey[v, c, fr_].append(heli0 + len(hpieces))
                    hpieces.append((dx, dy, w, h, t, hdata[d]))
    for k in movkeys:
        if k[0] == 'heli':
            canon = ('heli', k[1], 3 if k[2] == 3 else 0, k[3])
            assert moving_pieces(dat, k) == moving_pieces(dat, canon), "the helicopter's colours: one copy"
            movpieces[k] = hkey[canon[1:]]
    assert heli0 + len(hpieces) <= 256
    open(f'{out}/heli.bin', 'wb').write(hbin)
    with open(f'{out}/heli.6502', 'w') as f:
        f.write('\\\\ heli.6502 - made by tools/gendata.py: the helicopter\'s pieces in heli.bin, from variant HeliVar0 on\n\n')
        for i, name in enumerate(('GenHeliDX', 'GenHeliDY', 'GenHeliW', 'GenHeliH', 'GenHeliTable', 'GenHeliData')):
            f.write(lst(name, [m[i] for m in hpieces]))
        f.write(f'HeliVar0 = {heli0}\n')
        f.write(f'HeliVariants = {len(hpieces)}\n')
    open(f'{out}/objects.bin', 'wb').write(obin)
    with open(f'{out}/objects.6502', 'w') as f:
        f.write('\\\\ objects.6502 - made by tools/gendata.py: the background objects\' variants in objects.bin\n\n')
        base, bases = 0, []
        for kind in ObjKinds:
            bases.append(base)
            base += len(variants[kind])
        f.write(lst('GenObjKindBase', [0] + bases))
        assert not logic or len(vt) <= ObjVariantsMax and len(ent_runs) <= EntriesMax, 'the objects\' tables\' room'
        nvar, nent = max(len(vt), ObjVariantsMax), max(len(ent_runs), EntriesMax)  # (the traced tests' own, more)
        for i, name in enumerate(('GenObjW', 'GenObjH', 'GenObjFlags', 'GenObjData', 'GenObjMask')):
            f.write(lst(name, [v[i] for v in vt] + [0] * (nvar - len(vt))))
        # the gates' and barriers' entries (each a transition: an instance from one frame to the next, or
        # its first): its variant, its runs (up to 3: an offset in prio.bin, bytes), its bits in objects.bin
        # (the runs' bytes one after another)
        runs3 = [r + [(0, 0)] * (3 - len(r)) for r in ent_runs] or [[(0, 0)] * 3]
        pad = lambda v, n: v + [0] * (n - len(v))                  # (every track's tables the same size)
        f.write(lst('GenEntVar', pad(ent_var, nent)))
        f.write(lst('GenEntRuns', pad([len(r) for r in ent_runs], nent)))
        f.write(lst('GenEntRunOff', pad([o for r in runs3 for o, n in r], 3 * nent)))
        f.write(lst('GenEntRunLen', pad([n for r in runs3 for o, n in r], 3 * nent)))
        f.write(lst('GenEntData', pad(ent_data, nent)))
        f.write(f'Entries = {len(ent_runs)}\n')
        f.write(f'ObjVariants = {len(vt)}\n')
        for i, name in enumerate(('GenMovDX', 'GenMovDY', 'GenMovW', 'GenMovH', 'GenMovTable', 'GenMovData')):
            f.write(lst(name, [m[i] for m in mt]))
        f.write(f'MovVariants = {len(mt)}\n')
        f.write(f'MaxMovers = {MaxMovers}\n')
    with open(f'{out}/tornado.6502', 'w') as f:
        f.write('\\\\ tornado.6502 - made by tools/gendata.py: the tornado\'s frame-shifts in the race, compiled, from\n'
                '\\\\ variant MovVariants on; each one\'s first byte column in its box and width in bytes\n\n')
        for src, dx, w in torcode:
            f.write(src)
        f.write('.TorEntry\n')
        f.write(''.join(f'    EQUW TorCode{i}\n' for i in range(len(torcode))) or '    EQUW 0\n')
        f.write(lst('GenTorDX', [dx for s, dx, w in torcode] or [0]))
        f.write(lst('GenTorW', [w for s, dx, w in torcode] or [0]))
        f.write('.TorDX\n    EQUB GenTorDX\n.TorW\n    EQUB GenTorW\n')
        f.write(f'TorVariants = {len(torcode)}\n')
        f.write(lst('TorCodes', [f'TorCode{i}' for i in range(len(torcode))]))

    # the trace fills the fourth bank after the helicopter: its bytes, its plotter and their tables
    piecedx = {i: (m[0], m[2]) for i, m in enumerate(mt)}
    piecedx.update({heli0 + i: (m[0], m[2]) for i, m in enumerate(hpieces)})
    piecedx.update({len(mt) + i: (dx, w) for i, (s, dx, w) in enumerate(torcode)})
    if logic:
        bx, by = BannerPlace[track]
        with open(f'{out}/logickeys.6502', 'w') as f:
            f.write('\\\\ logickeys.6502 - made by tools/gendata.py --logic: each moving object\'s key\'s pieces, and the car sets\n\n')
            first = lambda k: movpieces[k][0] if movpieces[k] else 0
            assert all(len(movpieces[('explosion', i)]) == 1 for i in range(26)), "an explosion in one piece"
            f.write(lst('GenExplPiece', [movpieces[('explosion', i)][0] for i in range(26)]))
            for name, keys in (('Spark', [('spark', i) for i in range(41)]), ('Banner', [('banner', i, bx & 3) for i in range(36)])):
                assert all(movpieces[k] == list(range(first(k), first(k) + len(movpieces[k]))) for k in keys), "a key's pieces in turn"
                f.write(lst(f'Gen{name}First', [first(k) for k in keys]))
                f.write(lst(f'Gen{name}Count', [len(movpieces[k]) for k in keys]))
            hk = [hkey[v, c, fr_] for v in range(4) for c in (0, 3) for fr_ in range(4)]
            assert all(k == list(range(k[0], k[0] + len(k))) for k in hk if k), "a helicopter frame's pieces in turn"
            f.write(lst('GenHeliFirst', [k[0] if k else 0 for k in hk]))
            f.write(lst('GenHeliCount', [len(k) for k in hk]))
            f.write(lst('GenSetOf', [sets.index((None, True) if d else (c, False)) if ((None, True) if d else (c, False)) in sets
                                     else sets.index((None, True)) if (None, True) in sets else 255   # (the demo's car 3, for now)
                                     for c in range(4) for d in (0, 1)]))
            f.write(lst('GenTorPiece', [movpieces[('tornado', fr_, x)][0] for fr_ in range(3) for x in range(4)]))
            f.write(lst('GenEntCode', ent_codes + [255] * (9 * 6 - len(ent_codes))))   # (6 instances' room, every track)
            f.write(f'GenGateInst0 = 3\n')
        tdata, nframes, events = b'', len(frames), b''
    else:
        tdata, nframes, events = trace(frames, sets, movpieces, insts,
                                       16384 - len(hbin) - HeliCode - 9 * len(hpieces), piecedx, objframes, ent_per_frame)
    open(f'{out}/trace.bin', 'wb').write(tdata)
    open(f'{out}/hudevents.bin', 'wb').write(events)
    with open(f'{out}/trace.6502', 'w') as f:
        f.write('\\\\ trace.6502 - made by tools/gendata.py\n\n')
        f.write(f'TraceFrames = {nframes}\n')
        f.write(f'TraceTrack = {track}\n')
        f.write(f'GenLogic = {1 if logic else 0}\n')
        f.write(f'GenPlay = {1 if play else 0}\n')
        f.write(f'GenTimeAttack = {1 if ta else 0}\n')
    with open(f'{out}/font.6502', 'w') as f:
        f.write('\\\\ font.6502 - made by tools/gendata.py from tools/font.py: the HUD\'s glyphs, 8 lines each\n\n')
        f.write(lst('GenFont', [b for g in range(len(Glyphs)) for b in glyph_bytes(g)]))
        f.write(f'FontGlyphs = {len(Glyphs)}\n')
    print(f'sets {sets}; cars {len(data)} bytes, prio {len(pdata)} + {len(classes)} + {len(mapdata)} bytes '
          f'({int((cellmap > 0).sum())} cells), objects {len(obin)} bytes ({len(vt)} variants, {len(mt)} moving), '
          f'helicopter {len(hbin)} bytes ({len(hpieces)} pieces), '
          f'trace {nframes} frames {len(tdata)} bytes, HUD events {len(events)} bytes')


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3], '--logic' in sys.argv[4:], '--play' in sys.argv[4:], '--ta' in sys.argv[4:])
