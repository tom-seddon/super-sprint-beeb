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
- prio.bin, prio.6502: the priority mask (where a car on the ground is hidden), as 1 bit a pixel, 8 bytes
  (lines) per 8 x 8 cell, only for cells with a hidden pixel; a map of the 40 x 25 cells (0, or the cell's
  number in its row from 1) and each row's first cell's offset.
- trace.bin, trace.6502: the race, 12 bytes a frame: per car in draw order, x's low byte, y, and frame |
  elevated << 6 | x's high bit << 7.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from st_sprites import car_frame
from convert import OPTIONS, car_table, logical_map, apply_map, mode1_bytes

Opt = OPTIONS['B']
Key = 2


def pixel_byte(vals):
    """Four 2-bit values, left to right -> a MODE 1 byte."""
    b = 0
    for n, v in enumerate(vals):
        b |= ((v >> 1) & 1) << (7 - n) | (v & 1) << (3 - n)
    return b


def car_values(dat, f):
    """Frame f (0-63) as 12 x 17 2-bit values, transparent as Key."""
    car = f // 16
    st = car_frame(dat, f)[:, :17]
    lidx = apply_map(st, logical_map(Opt, car_table(Opt, car))).astype(np.uint8)
    opaque = st != 8
    v = lidx.copy()
    if car == 2:
        assert not (opaque & (lidx == 1)).any()
        v[lidx == 2] = 1
    else:
        assert not (opaque & (lidx == 2)).any()
    v[~opaque] = Key
    return v, opaque


def cars(dat):
    blocks = []                 # per frame * 4 + shift: its bytes
    fs = []                     # (dx, w) per frame * 4 + shift
    fr = []                     # (dy, h) per frame
    for f in range(64):
        v, opaque = car_values(dat, f)
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


def prio(track):
    hidden = np.load(f'build/gfx/mask2_t{track}.npy') == 0
    cells = hidden.reshape(25, 8, 40, 8)
    data = bytearray()
    cellmap = np.zeros((25, 40), np.uint8)
    rowoff = []
    for r in range(25):
        rowoff.append(len(data))
        k = 0
        for c in range(40):
            if cells[r, :, c, :].any():
                k += 1
                cellmap[r, c] = k
                for line in range(8):
                    data.append(int(np.packbits(cells[r, line, c, :])[0]))
    return bytes(data), cellmap, rowoff


def trace(path):
    frames = json.load(open(path))
    out = bytearray()
    for fr in frames:
        for c in fr['order']:
            x, y, facing, flags = fr['cars'][c]
            on_top = 1 if flags & 0x0401 else 0
            out += bytes([x & 255, y, (c * 16 + facing) | on_top << 6 | (x >> 8) << 7])
    return bytes(out), len(frames)


def lst(name, vals):
    return f'{name} = {{{", ".join(str(v) for v in vals)}}}\n'


def main(track, tracepath, out):
    os.makedirs(out, exist_ok=True)
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    bg = np.load(f'build/conv/B_t{track}_bg.npy')
    open(f'{out}/bg.bin', 'wb').write(mode1_bytes(bg))

    data, fs, fr = cars(dat)
    open(f'{out}/cars.bin', 'wb').write(data)
    with open(f'{out}/cars.6502', 'w') as f:
        f.write('\\\\ cars.6502 - made by tools/gendata.py: the car frames\' layout in cars.bin\n\n')
        f.write(lst('GenFsDX', [d for d, w, o in fs]))
        f.write(lst('GenFsW', [w for d, w, o in fs]))
        f.write(lst('GenFsOff', [o for d, w, o in fs]))
        f.write(lst('GenFrDY', [d for d, h in fr]))
        f.write(lst('GenFrH', [h for d, h in fr]))
        f.write(f'CarDataSize = {len(data)}\n')

    pdata, cellmap, rowoff = prio(track)
    open(f'{out}/prio.bin', 'wb').write(pdata)
    open(f'{out}/priomap.bin', 'wb').write(cellmap.tobytes())
    with open(f'{out}/prio.6502', 'w') as f:
        f.write('\\\\ prio.6502 - made by tools/gendata.py: the priority cells\' layout\n\n')
        f.write(lst('GenPrioRowOff', [o - 8 for o in rowoff]))
        f.write(f'PrioDataSize = {len(pdata)}\n')

    tdata, nframes = trace(tracepath)
    open(f'{out}/trace.bin', 'wb').write(tdata)
    with open(f'{out}/trace.6502', 'w') as f:
        f.write('\\\\ trace.6502 - made by tools/gendata.py\n\n')
        f.write(f'TraceFrames = {nframes}\n')
    print(f'cars {len(data)} bytes, prio {len(pdata)} + {cellmap.size} bytes ({int((cellmap > 0).sum())} cells), '
          f'trace {nframes} frames {len(tdata)} bytes')


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
