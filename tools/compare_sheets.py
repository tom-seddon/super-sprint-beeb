"""Comparison images for the palette options (docs/img): every track per option, one track across options,
and the cars close up. Run after tools/convert.py build/conv."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from convert import OPTIONS, car_table, logical_map, apply_map, to_rgb
from st_sprites import car_frame
from stgfx import palette_from_words

ST = np.array(palette_from_words([0x000, 0x126, 0x500, 0x222, 0x550, 0x040, 0x345, 0x555,
                                  0x333, 0x147, 0x703, 0x444, 0x773, 0x153, 0x567, 0x777]), np.uint8)
OUT = 'docs/img'


def tracks_sheet(key):
    s = Image.new('RGB', (4 * 330, 2 * 210), (50, 50, 50))
    for t in range(8):
        im = Image.open(f'build/conv/{key}_t{t}.png') if key else Image.fromarray(ST[np.load(f'build/gfx/bg_t{t}.npy')])
        s.paste(im, ((t % 4) * 330 + 5, (t // 4) * 210 + 5))
    s.save(f'{OUT}/{"option-" + key.lower() if key else "st"}-tracks.png')


def one_track(t, keys):
    ims = [Image.fromarray(ST[np.load(f'build/gfx/bg_t{t}.npy')])] + [Image.open(f'build/conv/{k}_t{t}.png') for k in keys]
    labels = ['ST'] + [f'Option {k}' for k in keys]
    cols = 3
    z = Image.new('RGB', (cols * 650, -(-len(ims) // cols) * 425), (50, 50, 50))
    d = ImageDraw.Draw(z)
    for i, (im, l) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * 650, (i // cols) * 425
        z.paste(im.resize((640, 400), Image.Resampling.NEAREST), (x + 5, y + 20))
        d.text((x + 5, y + 4), f'{l} (track {t + 1})', fill=(255, 255, 255))
    z.save(f'{OUT}/track{t + 1}-options.png')


def cars(keys, dat):
    S, dirs = 4, (0, 2, 4, 6)
    rows = [('ST', None)] + [(f'Option {k}', k) for k in keys]
    img = Image.new('RGB', (16 * 25 * S + 120, len(rows) * (16 * S + 8)), (50, 50, 50))
    d = ImageDraw.Draw(img)
    for r, (lab, k) in enumerate(rows):
        d.text((4, r * (16 * S + 8) + 24), lab, fill=(255, 255, 255))
        road = np.full((16, 16 * 25), 8, np.uint8)
        if k is None:
            out = road.copy()
        else:
            opt = OPTIONS[k]
            out = apply_map(road, logical_map(opt, opt['bg']))
        for n, (car, droned) in enumerate(((0, False), (1, False), (2, False), (3, False), (0, True))):
            lm = None if k is None else logical_map(OPTIONS[k], car_table(OPTIONS[k], car, droned))
            for j, dd in enumerate(dirs):
                f = car_frame(dat, car * 16 + dd + (64 if droned else 0))[:, :16]
                x = (n * 5 + j) * 16 + 2
                m = f != 8
                out[2:14, x:x + 16][m] = (f if lm is None else apply_map(f, lm))[m]
        rgb = ST[out] if k is None else to_rgb(out, OPTIONS[k]['pal'])
        img.paste(Image.fromarray(rgb).resize((16 * 25 * S, 16 * S), Image.Resampling.NEAREST),
                  (110, r * (16 * S + 8) + 4))
    img.save(f'{OUT}/cars-options.png')


if __name__ == '__main__':
    keys = list(OPTIONS)
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    tracks_sheet(None)
    for k in keys:
        tracks_sheet(k)
    one_track(3, keys)
    one_track(5, keys)
    cars(keys, dat)
