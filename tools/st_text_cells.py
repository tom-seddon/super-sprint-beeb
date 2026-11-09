"""The ST maps' "TRACK n" and "DRONE LAP": the bottom row's cells that hold them, and a map word for each that
draws the same cell without the text, for st_dump_tracks.py to write into the map before the track is built
(so the ST draws its trees over clean ground).

Usage: st_text_cells.py [--show PNG]   (prints the table; --show draws each map's bottom rows, before and after)

A text cell's text is its pixels in the text's colours: 3 and 15 (white, shadowed) in "TRACK n", columns 0-3;
0 (black) in "DRONE LAP", columns 15-21. A replacement is a tile, in any of its four flips, that agrees with the
cell at every other pixel and has no text colour where the text was (15 allowed under track 8's "TRACK 8",
which sits on the road's white edge). Of several, one this map already uses, then the lowest numbered, unflipped
first. The choice is printed with how many tiles fitted: where they differ under the text, the picture says
which is right.
"""
import os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from st_tracks import decode_map, decode_tile, MAP_OFF

ROW = 24
TEXT = {**{c: (3, 15) for c in range(4)}, **{c: (0,) for c in range(15, 22)}}
HIGHEST = (605, 1157, 1114, 64)         # the tile sets' highest used (docs/st-graphics.md)


def word(t, i, v, h):
    return 0x8000 | t << 11 | i | v << 13 | h << 14


def tiles(dat):
    out = []
    for t in range(4):
        for i in range(HIGHEST[t] + 1):
            a = decode_tile(dat, t, i)
            for v in (0, 1):
                for h in (0, 1):
                    b = a[::-1] if v else a
                    out.append(((t, i, v, h), b[:, ::-1] if h else b))
    return out


def map_words(dat, m):
    base = MAP_OFF + m * 2000
    return [struct.unpack('>H', dat[base + 2 * k:base + 2 * k + 2])[0] for k in range(1000)]


def cells(dat):
    """-> {track: {column: (word, fits, distinct)}}: the replacement word for each text cell, how many tiles fit
    and how many different cells they draw."""
    ts = tiles(dat)
    out = {}
    for m in range(8):
        img = decode_map(dat, m)
        used = {w & 0x1FFF | 0x8000 for w in map_words(dat, m) if w & 0x8000}   # (tile and type, unflipped)
        out[m] = {}
        for c, colours in TEXT.items():
            cell = img[ROW * 8:ROW * 8 + 8, c * 8:c * 8 + 8]
            keep = ~np.isin(cell, colours)
            if keep.all():
                continue
            banned = [3] if m == 7 and c < 4 else list(colours)
            fits = [(k, b) for k, b in ts if (b[keep] == cell[keep]).all() and not np.isin(b[~keep], banned).any()]
            if not fits:
                out[m][c] = (None, 0, 0)
                continue
            fits.sort(key=lambda kb: (word(*kb[0][:2], 0, 0) not in used, kb[0][0], kb[0][1], kb[0][2], kb[0][3]))
            distinct = len({b.tobytes() for k, b in fits})
            out[m][c] = (word(*fits[0][0]), len(fits), distinct)
    return out


def show(dat, table, path):
    from PIL import Image, ImageDraw
    from stgfx import palette_from_words
    pal = np.array(palette_from_words([0x000, 0x126, 0x500, 0x222, 0x550, 0x040, 0x345, 0x555,
                                       0x333, 0x147, 0x703, 0x444, 0x773, 0x153, 0x567, 0x777]), np.uint8)
    Z, pad, lab = 3, 8, 16
    w, h = 320 * Z, 24 * Z
    sheet = Image.new('RGB', (2 * w + 3 * pad, 8 * (h + lab + pad) + pad), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for m in range(8):
        before = decode_map(dat, m)
        after = before.copy()
        for c, (wd, n, k) in table[m].items():
            if wd is None:
                continue
            tile = decode_tile(dat, (wd >> 11) & 3, wd & 0x7FF)
            tile = tile[::-1] if wd & 0x2000 else tile
            after[ROW * 8:ROW * 8 + 8, c * 8:c * 8 + 8] = tile[:, ::-1] if wd & 0x4000 else tile
        y0 = pad + m * (h + lab + pad)
        d.text((pad, y0), f'track {m + 1}: the map as it is | the text cells replaced (before the trees)', fill=(255, 255, 255))
        for i, im in enumerate((before, after)):
            rgb = Image.fromarray(pal[im[176:200]]).resize((w, h), Image.NEAREST)
            sheet.paste(rgb, (pad + i * (w + pad), y0 + lab))
    sheet.save(path)


if __name__ == '__main__':
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dat = open(os.path.join(root, 'orig/st/SUPER.DAT'), 'rb').read()
    table = cells(dat)
    for m in range(8):
        row = []
        for c, (wd, n, k) in table[m].items():
            if wd is None:
                row.append(f'{c}: none')
                continue
            t, i = (wd >> 11) & 3, wd & 0x7FF
            flips = ('v' if wd & 0x2000 else '') + ('h' if wd & 0x4000 else '')
            row.append(f'{c}: {wd:04X} (set {t} #{i}{" " + flips if flips else ""}; {n} fit{", " + str(k) + " looks" if k > 1 else ""})')
        print(f'track {m + 1}: ' + ', '.join(row))
    if '--show' in sys.argv:
        show(dat, table, sys.argv[sys.argv.index('--show') + 1])
