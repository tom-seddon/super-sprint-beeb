"""Mask B (walls) stored as its mixed cells only (D13, docs/brief-phase4.md §3): the encoder the build will use,
its decoder, and the proof that the two give back the ST's mask.

Usage: .venv/bin/python tools/maskb.py   (every track: sizes, and the round trip; track 1 also against the ST's RAM)

Mask B is 320 x 200 at 1 bit a pixel, bit 7 the leftmost, 1 a wall (the ST's layout, tools/logic_maps.py).
Each 8 x 8 cell is all road, all wall, or mixed. A cell row is stored as:
- its span: from its first cell that isn't the row's left fill (the class of its column 0) to its last that
  isn't its right fill (the class of column 39); outside the span the cell is that fill (an empty span's
  start is where the left fill gives way to the right);
- the map, a byte for each cell of the span: 0 all road, &FF all wall, n (1 to 40) the row's nth mixed cell;
- the row's mixed cells, 8 bytes each, a line a byte.
A cell a gate or pop-up barrier can cover (tools/logic_maps.py fixed) is kept as mixed even if it isn't, so
the gates' and barriers' frames can be written into it while the race runs. A row numbers its mixed cells
that never change first, then those (each kind in column order), so a number tells which it is (dyn_first).

A row's header: span start, span length, left fill, right fill, the map's offset (2 bytes), the cells' (2):
8 bytes, 200 for the 25 rows.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logic_maps as L

ROAD, WALL = 0x00, 0xFF


def mask_bytes(track):
    """The ST's mask B as 200 lines of 40 bytes."""
    m = L.wall_mask(track)
    return [[sum(m[y][x * 8 + b] << (7 - b) for b in range(8)) for x in range(40)] for y in range(200)]


def reserved(track):
    """The cells a gate (48 x 16) or pop-up barrier (16 x 8) of the track can cover: {(row, col)}."""
    ng = L.words(L.tb(0x1ED88)); gp = L.words(L.tb(0x1ED98), False); bp = L.words(L.tb(0x1EC00), False)
    boxes = [L.scr(gp[track + i]) + (48, 16) for i in range(ng[track])]
    boxes += [L.scr(bp[track * 3 + i]) + (16, 8) for i in range(3)]
    return {(y // 8, x // 8) for bx, by, w, h in boxes for y in range(by, by + h) for x in range(bx, bx + w)}


def encode(track):
    """-> (header, maps, cells): the header 25 x 8 bytes, then the maps and the cells as byte strings."""
    return encode_dyn(track)[:3]


def dyn_first(track):
    """Each row's first number of a mixed cell a gate or barrier can change (255 if none)."""
    return encode_dyn(track)[3]


def encode_dyn(track):
    """-> encode()'s, and dyn_first()'s."""
    mb, keep = mask_bytes(track), reserved(track)
    header, maps, cells, first = bytearray(), bytearray(), bytearray(), []
    for r in range(25):
        lines = [[mb[r * 8 + l][c] for l in range(8)] for c in range(40)]
        cls = []
        for c in range(40):
            v = set(lines[c])
            cls.append(ROAD if v == {0} and (r, c) not in keep else
                       WALL if v == {0xFF} and (r, c) not in keep else None)
        left, right = cls[0], cls[39]
        lo = next((c for c in range(40) if cls[c] != left), 40)
        hi = next((c for c in range(39, -1, -1) if cls[c] != right), -1)
        if left is None or right is None:            # a mixed cell at the screen's side: the span takes it
            lo, hi = (0 if left is None else lo), (39 if right is None else hi)
            left = ROAD if left is None else left
            right = ROAD if right is None else right
        n = max(0, hi - lo + 1)
        header += bytes([min(lo, 40), n, left, right]) + len(maps).to_bytes(2, 'little') + \
            len(cells).to_bytes(2, 'little')
        mixed = [c for c in range(lo, lo + n) if cls[c] is None]
        order = [c for c in mixed if (r, c) not in keep] + [c for c in mixed if (r, c) in keep]
        num = {c: k + 1 for k, c in enumerate(order)}
        for c in range(lo, lo + n):
            maps.append(num[c] if cls[c] is None else cls[c])
        for c in order:
            cells += bytes(lines[c])
        statics = len(mixed) - sum((r, c) in keep for c in mixed)
        first.append(statics + 1 if statics < len(mixed) else 255)
    return bytes(header), bytes(maps), bytes(cells), first


def read(enc, x, y):
    """The mask byte holding pixel (x, y), as the 6502 will find it."""
    header, maps, cells = enc
    r, c = y >> 3, x >> 3
    lo, n, left, right, mo, co = header[r * 8], header[r * 8 + 1], header[r * 8 + 2], header[r * 8 + 3], \
        int.from_bytes(header[r * 8 + 4:r * 8 + 6], 'little'), int.from_bytes(header[r * 8 + 6:r * 8 + 8], 'little')
    if c < lo:
        return left
    if c >= lo + n:
        return right
    v = maps[mo + c - lo]
    if v in (ROAD, WALL):
        return v
    return cells[co + (v - 1) * 8 + (y & 7)]


def main():
    ok = True
    for t in range(8):
        enc = encode(t)
        mb = mask_bytes(t)
        bad = sum(read(enc, c * 8, y) != mb[y][c] for y in range(200) for c in range(40))
        ok &= bad == 0
        h, m, c = (len(p) for p in enc)
        print(f'track {t + 1} (index {t}): header {h}, maps {m}, cells {c} ({c // 8} mixed or reserved): '
              f'{h + m + c} bytes; {bad} of 8,000 mask bytes wrong decoded')
    dump = os.path.join(L.ROOT, 'build/logic/attract2600.bin')
    if os.path.exists(dump):
        ref = L.mask_from_dump(dump, 0x63A76)
        m = L.wall_mask(0)
        bad = sum(m[y][x] != ref[y][x] for y in range(200) for x in range(320))
        ok &= bad == 0
        print(f'track 1 against the ST\'s RAM (attract2600.bin, &63A76): {bad} pixels differ')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
