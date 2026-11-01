"""Decode the ST track maps in SUPER.DAT (the background builder at &15A24 in SUPER.PRG).

Each map is 25 rows x 40 columns of 16-bit words, one per 8x8 cell (2,000 bytes a map).
- Bit 15 clear: copy the cell already drawn at that byte offset in the 320x200 screen buffer.
- Bit 15 set: a tile. Bits 0-10 index, bits 11-12 the tile type t, bit 13 vertical flip, bit 14 horizontal
  flip. Type t < 3 stores t+1 bitplanes (8 bytes each, a byte per row) and then a word whose set bits are
  the colours used: pixel code k is the k-th set bit counting down from bit 15. Type 3 is a full 4-plane
  tile, 32 bytes, no colour word.
"""
import struct, sys
import numpy as np

MAP_OFF = 0xCD60            # in SUPER.DAT; the tile set offsets below are as the game sets them up
TILE_OFFS = (0x12350, 0x13AFC, 0x18C68, 0x1FDA6)
TILE_SIZES = (10, 18, 26, 32)
N_MAPS = 11


def decode_tile(dat, t, index):
    """8x8 array of colour indices."""
    off = TILE_OFFS[t] + index * TILE_SIZES[t]
    if t == 3:
        planes = [dat[off + 8 * p:off + 8 * p + 8] for p in range(4)]
        out = np.zeros((8, 8), np.uint8)
        for p in range(4):
            for y in range(8):
                for x in range(8):
                    out[y, x] |= ((planes[p][y] >> (7 - x)) & 1) << p
        return out
    n = t + 1
    planes = [dat[off + 8 * p:off + 8 * p + 8] for p in range(n)]
    used = struct.unpack('>H', dat[off + 8 * n:off + 8 * n + 2])[0]
    colours = [c for c in range(15, -1, -1) if used >> c & 1]
    out = np.zeros((8, 8), np.uint8)
    for y in range(8):
        for x in range(8):
            k = 0
            for p in range(n):
                k |= ((planes[p][y] >> (7 - x)) & 1) << p
            out[y, x] = colours[k] if k < len(colours) else 0
    return out


def decode_map(dat, m, stats=None):
    img = np.zeros((200, 320), np.uint8)
    base = MAP_OFF + m * 2000
    for r in range(25):
        for c in range(40):
            w = struct.unpack('>H', dat[base + (r * 40 + c) * 2:base + (r * 40 + c) * 2 + 2])[0]
            y, x = r * 8, c * 8
            if w & 0x8000 == 0:
                line, rest = divmod(w, 160)
                group, byte = divmod(rest, 8)
                assert byte in (0, 1), hex(w)
                sx = group * 16 + byte * 8
                img[y:y + 8, x:x + 8] = img[line:line + 8, sx:sx + 8]
                if stats is not None:
                    stats['copy'] += 1
            else:
                t = (w >> 11) & 3
                tile = decode_tile(dat, t, w & 0x7FF)
                if w & 0x2000:
                    tile = tile[::-1]
                if w & 0x4000:
                    tile = tile[:, ::-1]
                img[y:y + 8, x:x + 8] = tile
                if stats is not None:
                    stats[f't{t}'] += 1
                    stats.setdefault(f'max{t}', 0)
                    stats[f'max{t}'] = max(stats[f'max{t}'], w & 0x7FF)
    return img


if __name__ == '__main__':
    sys.path.insert(0, 'tools')
    from stgfx import palette_from_words, indices_to_png
    from collections import Counter
    dat = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]
    pal = palette_from_words([0x000, 0x126, 0x500, 0x222, 0x550, 0x040, 0x345, 0x555,
                              0x333, 0x147, 0x703, 0x444, 0x773, 0x153, 0x567, 0x777])
    for m in range(N_MAPS):
        st = Counter()
        img = decode_map(dat, m, st)
        indices_to_png(img, pal, f'{out}/map{m:02d}.png')
        np.save(f'{out}/map{m:02d}.npy', img)
        print(m, dict(st))
