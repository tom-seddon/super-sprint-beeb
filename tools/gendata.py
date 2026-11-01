"""The BBC's data for the renderer test (Phase 3): one track's background, the cars' frames, the priority
cells and an ST race's car positions, as binaries and Baron source in build/gen.

Usage: gendata.py TRACK TRACE.json OUTDIR

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

Opt = OPTIONS['B']
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


# a car's data table, by car and drone-driven: 0 DataId (1 green), 1 DataYellow, 2 DataWhite, 3 DataBlack
CarTable = {(0, 0): 0, (1, 0): 0, (2, 0): 1, (3, 0): 0, (0, 1): 2, (1, 1): 0, (2, 1): 1, (3, 1): 3}


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
    # a block (less the band's first line) and keep its page's high byte. First fit, largest first
    pages, offsets = [], [None] * len(blocks)
    for i in sorted(range(len(blocks)), key=lambda i: -len(blocks[i])):
        for p, used in enumerate(pages):
            if used + len(blocks[i]) <= 256:
                break
        else:
            pages.append(7)
            p = len(pages) - 1
        offsets[i] = p * 256 + pages[p]
        pages[p] += len(blocks[i])
    data = bytearray(256 * len(pages))
    for i, b in enumerate(blocks):
        data[offsets[i]:offsets[i] + len(b)] = b
    data = bytes(data[:256 * (len(pages) - 1) + pages[-1]])
    return data, [(d, w, o) for (d, w), o in zip(fs, offsets)], fr


def prio(track, reserved=()):
    """Each 8 x 8 cell with hidden pixels, or reserved (a gate's or barrier's, whose bits change in the race):
    its 8 lines of bits (1 hidden), and a class byte: per half (left in bits 0-1, right in bits 2-3), 0 nothing
    hidden, 1 all hidden, 2 some. A reserved cell's class is always 2 for both: its bits decide."""
    hidden = np.load(f'build/gfx/mask2_t{track}.npy') == 0
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
    and object calls (none in the attract race, whose cars are all drawn in their own colours)."""
    frames = json.load(open(path))
    for fr in frames:
        fr.setdefault('drone', [0, 0, 0, 0])
        fr.setdefault('calls', [])
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


def object_variants(dat):
    """Every variant of the background objects: the slots' 22 sprites; the gates' 5 frames and the barriers' 8,
    each for a top line even or odd (the patterns' phase). -> per kind, a list of (w bytes, h, data, mask or
    None, priority bits or None); the data and mask column by column, the mask's set bits keep the screen (a
    barrier's colour 0); the priority bits too, a byte per 8 pixels, each 8-pixel column's lines together, 1
    where a car on the ground is hidden."""
    lmap = logical_map(Opt, Opt['bg'])
    out = {'slot': [], 'gate': [], 'barrier': []}
    for sprite in range(22):
        out['slot'].append((4, 8, rows_bytes(map_at(objects.slot(dat, sprite), lmap, 0, 0)), None, None))
    for frame in range(5):
        col, mc = objects.gate(dat, frame)
        pb = bytes(np.packbits(1 - mc, axis=1).T.flatten())     # (column by column)
        for parity in range(2):
            out['gate'].append((12, 16, rows_bytes(map_at(col, lmap, 0, parity)), None, pb))
    for frame in range(8):
        col, mc = objects.barrier(dat, frame)
        pb = bytes(np.packbits(1 - mc, axis=1).T.flatten())     # (column by column)
        keep = np.where(col == 0, 3, 0).astype(np.uint8)
        for parity in range(2):
            lidx = map_at(col, lmap, 0, parity)
            lidx[col == 0] = 0
            out['barrier'].append((4, 8, rows_bytes(lidx), rows_bytes(keep), pb))
    return out


def variant_of(kind, args, y):
    return args[0] if kind == 'slot' else args[0] * 2 + (y & 1)


# The moving objects: what each frame's calls draw after the background objects, as (key, x, y) in the BBC's
# places (D8: the explosion on 4-pixel steps; the banner's frames shifted for its place; the sparks and the
# helicopter where the ST has them, on 8- and 16-pixel steps). A key names a sprite: ('explosion', frame),
# ('banner', frame, shift), ('spark', frame), ('heli', variant, colour, frame). The explosion is drawn in its
# car's place among the cars; the others after the cars, in the ST's order.

def frame_draws(fr, heli):
    """A frame's draws, in order: ('car', car) or ('explosion', key, x, y) among the cars, then the moving
    objects as (key, x, y). heli: the helicopter's composed frames, (variant, colour) by buffer frame,
    updated by the frame's composing calls."""
    cars, movers = [], []
    for c in fr['calls']:
        n, w = c[0], c[1]
        if n == 'car':
            cars.append(('car', w[0]))
        elif n == 'explosion':
            x, y = fr['cars'][w[0]][:2]
            cars.append(('explosion', ('explosion', w[1]), x & ~3, y))
        elif n == 'small':
            movers.append((('banner', w[0], w[1] & 3), w[1] & ~3, w[2]))
        elif n == 'spark':
            st = objects.spark_state(c[2] if len(c) > 2 else {}, w[0])
            if st:
                movers.append((('spark', st[0]), st[1], st[2]))
        elif n == 'heli':
            heli[w[2]] = (w[0], w[1])
        elif n == 'heli2':
            y = w[2] - 65536 if w[2] >= 32768 else w[2]
            movers.append((('heli',) + heli[w[0]] + (w[0],), w[1] & ~15, y))
    return cars, movers


def moving_sprite(dat, key):
    """A moving object's sprite: (ST colours, opaque)."""
    if key[0] == 'explosion':
        idx = objects.explosion(dat, key[1])
    elif key[0] == 'banner':
        idx = objects.banner(dat, key[1])
    elif key[0] == 'spark':
        idx = objects.spark(dat, key[1])
    else:
        idx, mask = objects.heli_compose(dat, key[1], key[2], key[3])
        return idx, mask == 0
    return idx, idx != 8


def moving_variant(dat, key):
    """A moving object's sprite as the BBC stores it: trimmed, column by column, 2-bit values (Key
    transparent), shifted by the banner's shift. -> (dx bytes, dy, w bytes, h, table 0 DataId or 1 DataYellow,
    bytes)."""
    idx, opaque = moving_sprite(dat, key)
    lidx = apply_map(idx, logical_map(Opt, Opt['bg'])).astype(np.uint8)
    used = set(lidx[opaque].tolist())
    if used <= {0, 1, 3}:
        table, v = 0, lidx.copy()
    else:
        assert used <= {0, 2, 3}, (key, used)
        table, v = 1, np.where(lidx == 2, 1, lidx).astype(np.uint8)
    v[~opaque] = Key
    shift = key[2] if key[0] == 'banner' else 0
    h0, w0 = v.shape
    canvas = np.full((h0, w0 + 4), Key, np.uint8)
    canvas[:, shift:shift + w0] = v
    op = np.zeros(canvas.shape, bool)
    op[:, shift:shift + w0] = opaque
    ys, xs = np.where(op.any(1))[0], np.where(op.any(0))[0]
    y0, y1, c0, c1 = ys.min(), ys.max(), xs.min() // 4, xs.max() // 4
    data = bytes(pixel_byte(canvas[r, 4 * n:4 * n + 4]) for n in range(c0, c1 + 1) for r in range(y0, y1 + 1))
    return int(c0), int(y0), int(c1 - c0 + 1), int(y1 - y0 + 1), table, data


MaxMovers = 8


def trace(frames, sets, movkeys, room):
    """The race's frames, as many as fit in room bytes with the HUD's events: per frame the cars drawn
    (their count, then 4 bytes each: car | drone-driven << 2, x's low byte, y, frame | on top << 6 | x's
    high bit << 7) and the background objects' calls (their count, then 4 bytes each: kind | again << 6 | x's
    high bit << 7, variant, x's low byte, y). The ST calls each a second time the frame after, for its other
    screen: "again" marks that call, for which the BBC only copies the background into the screen. A wrecked
    car's explosion is among the cars: &80 | x's high bit << 6, x's low byte, y, its moving variant. Then the
    moving objects (their count, then 5 bytes each: the variant, x, y as 16-bit words)."""
    out, starts, prev, heli = bytearray(), [], [], {}
    for fr in frames:
        cars, movers = frame_draws(fr, heli)
        rec = bytearray([len(cars)])
        for d in cars:
            if d[0] == 'explosion':
                key, x, y = d[1], d[2], d[3]
                rec += bytes([0x80 | (x >> 8) << 6, x & 255, y, movkeys.index(key)])
                continue
            c = d[1]
            x, y, facing, flags = fr['cars'][c]
            droned = 1 if fr['drone'][c] else 0
            on_top = 1 if flags & 0x0401 else 0
            rec += bytes([c | droned << 2, x & 255, y, set_of(sets, c, droned) * 16 + facing | on_top << 6 | (x >> 8) << 7])
        # each call's own arguments (3 for a slot, 2 for a gate or barrier; the ST's stack has others after)
        objs = [(n, w[:3] if n == 'slot' else w[:2]) for n, w in ((c[0], c[1]) for c in fr['calls']) if n in ObjKinds]
        rec.append(len(objs))
        for n, w in objs:
            x, y = objects.place(n, w)
            again = 1 if (n, w) in prev else 0          # the ST's second call, for its other screen
            rec += bytes([ObjKinds[n] | again << 6 | (x >> 8) << 7, variant_of(n, w, y), x & 255, y])
        prev = objs
        assert len(movers) <= MaxMovers
        rec.append(len(movers))
        for key, x, y in movers:
            rec += bytes([movkeys.index(key), x & 255, x >> 8, y & 255, (y >> 8) & 255])
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


def lst(name, vals):
    return f'{name} = {{{", ".join(str(v) for v in vals)}}}\n'


def main(track, tracepath, out):
    os.makedirs(out, exist_ok=True)
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    bg = np.load(f'build/conv/B_t{track}_bg.npy')
    open(f'{out}/bg.bin', 'wb').write(mode1_bytes(bg))
    frames = load_race(tracepath)
    sets = car_sets(frames)

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
    reserved = set()
    for fr_ in frames:
        for call in fr_['calls']:
            if call[0] in ('gate', 'barrier'):
                x, y = objects.place(call[0], call[1])
                h, w = (16, 48) if call[0] == 'gate' else (8, 16)
                reserved |= {(r, c) for r in range(y // 8, (y + h - 1) // 8 + 1) for c in range(x // 8, (x + w) // 8)}
    pdata, classes, cellmap, rowoff = prio(track, reserved)
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
    variants = object_variants(dat)
    blocks = []                         # (variant, part, bytes): the background objects' data and masks, each in a
                                        # page, 7 bytes in
    for kind in ObjKinds:
        for i, (w, h, d, m, pb) in enumerate(variants[kind]):
            blocks.append(((kind, i), 0, d))
            if m:
                blocks.append(((kind, i), 1, m))
    movkeys = []
    heli = {}
    for fr_ in frames:
        cars_, movers = frame_draws(fr_, heli)
        for k in [d[1] for d in cars_ if d[0] == 'explosion'] + [m[0] for m in movers]:
            if k not in movkeys:
                movkeys.append(k)
    movers_ = [moving_variant(dat, k) for k in movkeys]
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
            po = 0
            if pb:
                po = len(obin)
                obin += pb
            vt.append((w, h, (1 if m else 0) | (2 if pb else 0), where[(kind, i), 0], where.get(((kind, i), 1), 0), po))
    mt = [(dx, dy, w, h, t, where[('move', i), 0]) for i, (dx, dy, w, h, t, d) in enumerate(movers_)]
    open(f'{out}/objects.bin', 'wb').write(obin)
    with open(f'{out}/objects.6502', 'w') as f:
        f.write('\\\\ objects.6502 - made by tools/gendata.py: the background objects\' variants in objects.bin\n\n')
        base, bases = 0, []
        for kind in ObjKinds:
            bases.append(base)
            base += len(variants[kind])
        f.write(lst('GenObjKindBase', [0] + bases))
        for i, name in enumerate(('GenObjW', 'GenObjH', 'GenObjFlags', 'GenObjData', 'GenObjMask', 'GenObjPrio')):
            f.write(lst(name, [v[i] for v in vt]))
        f.write(f'ObjVariants = {len(vt)}\n')
        for i, name in enumerate(('GenMovDX', 'GenMovDY', 'GenMovW', 'GenMovH', 'GenMovTable', 'GenMovData')):
            f.write(lst(name, [m[i] for m in mt]))
        f.write(f'MovVariants = {len(mt)}\n')
        f.write(f'MaxMovers = {MaxMovers}\n')

    tdata, nframes, events = trace(frames, sets, movkeys, 16384)
    open(f'{out}/trace.bin', 'wb').write(tdata)
    open(f'{out}/hudevents.bin', 'wb').write(events)
    with open(f'{out}/trace.6502', 'w') as f:
        f.write('\\\\ trace.6502 - made by tools/gendata.py\n\n')
        f.write(f'TraceFrames = {nframes}\n')
        f.write(f'TraceTrack = {track}\n')
    with open(f'{out}/font.6502', 'w') as f:
        f.write('\\\\ font.6502 - made by tools/gendata.py from tools/font.py: the HUD\'s glyphs, 8 lines each\n\n')
        f.write(lst('GenFont', [b for g in range(len(Glyphs)) for b in glyph_bytes(g)]))
        f.write(f'FontGlyphs = {len(Glyphs)}\n')
    print(f'sets {sets}; cars {len(data)} bytes, prio {len(pdata)} + {len(classes)} + {len(mapdata)} bytes '
          f'({int((cellmap > 0).sum())} cells), objects {len(obin)} bytes ({len(vt)} variants, {len(mt)} moving), '
          f'trace {nframes} frames {len(tdata)} bytes, HUD events {len(events)} bytes')


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
