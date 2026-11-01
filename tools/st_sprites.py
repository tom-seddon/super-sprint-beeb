"""Render sprite blocks from SUPER.DAT to PNG sheets.

Cars (+&4D56, &8000 bytes): 128 frames of 256 bytes. The plotter (&1519C) draws 12 rows of 16 bytes: four
longwords, each a plane 32 pixels wide (the sprite sits in the left 16-32, the rest is room for the shift),
in the order planes 0, 2, 1, 3: the plotter's word shuffle before the store swaps the middle two (checked
against the colours a car draws on screen in a Hatari dump). Colour 8 is transparent: the mask is NOT(plane 3)
OR the other three.
Frame = (car * 16 + direction) [+ 64 for the second set] (car 0-3, direction 0-15).

Objects (+&205D6 + &5BC0, &70 bytes each): 14 rows of 4 words, 16 pixels, planes 0, 2, 1, 3 as the cars
(&152E0). Sprites copied straight to the screen by other routines are in the screen's order, 0-3.
"""
import struct, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, 'tools')
from stgfx import palette_from_words

PLANE_OF = (0, 2, 1, 3)        # the plane each stored longword (or word) holds, for the cars and explosion
PAL = palette_from_words([0x000, 0x126, 0x500, 0x222, 0x550, 0x040, 0x345, 0x555,
                          0x333, 0x147, 0x703, 0x444, 0x773, 0x153, 0x567, 0x777])
CARS = 0x4D56
OBJS = 0x205D6


def car_frame(dat, f, rows=12):
    out = np.zeros((rows, 32), np.uint8)
    base = CARS + f * 256
    for y in range(rows):
        p = struct.unpack('>4I', dat[base + y * 16:base + y * 16 + 16])
        for x in range(32):
            b = 31 - x
            out[y, x] = sum(((p[k] >> b) & 1) << PLANE_OF[k] for k in range(4))
    return out


def word_frame(dat, off, rows, words=1, order=(0, 1, 2, 3)):
    """`rows` rows of `words` groups of 4 plane words (16 pixels each); order[k] is word k's plane."""
    out = np.zeros((rows, 16 * words), np.uint8)
    for y in range(rows):
        for g in range(words):
            p = struct.unpack('>4H', dat[off + (y * words + g) * 8:off + (y * words + g) * 8 + 8])
            for x in range(16):
                out[y, g * 16 + x] = sum(((p[k] >> (15 - x)) & 1) << order[k] for k in range(4))
    return out


def to_rgb(idx, key=8):
    rgb = np.array(PAL, np.uint8)[idx]
    if key is not None:
        rgb[idx == key] = (255, 0, 255)
    return rgb


def sheet(frames, cols, scale, path, labels=True):
    h, w = frames[0].shape
    cw, ch = w * scale + 4, h * scale + (12 if labels else 4)
    rows = -(-len(frames) // cols)
    img = Image.new('RGB', (cols * cw, rows * ch), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for i, f in enumerate(frames):
        x, y = (i % cols) * cw, (i // cols) * ch
        img.paste(Image.fromarray(to_rgb(f)).resize((w * scale, h * scale), Image.Resampling.NEAREST), (x + 2, y + 2))
        if labels:
            d.text((x + 2, y + h * scale + 2), str(i), fill=(200, 200, 200))
    img.save(path)


if __name__ == '__main__':
    dat = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]
    sheet([car_frame(dat, f, 16) for f in range(128)], 16, 3, f'{out}/cars.png')
    sheet([word_frame(dat, OBJS + 0x5BC0 + n * 0x70, 14, order=PLANE_OF) for n in range(26)], 13, 3,
          f'{out}/explosion.png')
