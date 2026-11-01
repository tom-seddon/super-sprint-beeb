"""Convert ST tracks and car sprites to BBC MODE 1 for each palette option (Phase 2).

Usage: convert.py <out dir>     (reads build/gfx/bg_t*.npy and mask*_t*.npy, made from Hatari dumps,
                                 and orig/st/SUPER.DAT for the cars)

Each ST colour becomes one MODE 1 logical colour or a checkerboard of two, fixed to the screen for the
background and to the sprite for sprites. Each car has its own map, so its body can take a different colour.
Writes, per option and track: a 16,000-byte MODE 1 play area (25 character rows, the BBC's cell layout) with
sample cars drawn in, and PNG previews; and a comparison sheet per option.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from stgfx import palette_from_words
from st_sprites import car_frame

ST_PAL = palette_from_words([0x000, 0x126, 0x500, 0x222, 0x550, 0x040, 0x345, 0x555,
                             0x333, 0x147, 0x703, 0x444, 0x773, 0x153, 0x567, 0x777])
BBC = dict(K=(0, 0, 0), R=(255, 0, 0), G=(0, 255, 0), Y=(255, 255, 0), B=(0, 0, 255), M=(255, 0, 255),
           C=(0, 255, 255), W=(255, 255, 255))
PHYS = dict(K=0, R=1, G=2, Y=3, B=4, M=5, C=6, W=7)

# The background's ST colours, by use (counts over the 8 tracks in docs/st-graphics.md):
#  0 black outlines, 1 dark blue (rare), 2 dark red (gates), 3 dark grey shadow, 4 dark yellow,
#  5 dark green, 6 slate, 7 light grey kerbs, 8 grey road (56%), 9 light blue (rare), 10 pink (arrows,
#  gates), 11 mid grey (rare), 12 light yellow stripes, 13 green grass (15%), 14 pale blue kerbs, 15 white.
# Cars (frame = car * 16 + direction): car 0 blue (body 9, trim 1), car 1 red (body 10, trim 2 and 4,
# highlights 12), car 2 yellow (body 12, trim 4), car 3 green, always a drone (body 13, trim 5). Frames 64-127
# are cars 0-3 driven by a drone: grey bodies (11) with the car's colour as stripes. All share 0, 3, 7, 11,
# 14 and 15 for the outline, wheels, windows and highlights.
# A map entry is one physical colour letter, two for a checkerboard, or four for a 2x2 tile.
# Per option: the three players' body colours (slots), car 3's body, a drone-driven car's body, and the
# outline (the cars' black).

BODY = (9, 10, 12, 13)
TRIM = (1, 2, 4, 5)

BG_A = {0: 'K', 1: 'K', 2: 'YK', 3: 'K', 4: 'YK', 5: 'GK', 6: 'WK', 7: 'W', 8: 'K', 9: 'W',
        10: 'Y', 11: 'WK', 12: 'Y', 13: 'G', 14: 'W', 15: 'W'}
BG_B = {**BG_A, 8: 'KW', 11: 'W'}

OPTIONS = {
    'A': dict(name='black, green, yellow, white; black road', pal='KGYW', bg=BG_A,
              slots='WGY', car3='WK', drone='WK', outline='K'),
    'A2': dict(name='as A, with the cars outlined in grey', pal='KGYW', bg=BG_A,
               slots='WGY', car3='K', drone='K', outline='WK'),
    'B': dict(name='black, green, yellow, white; grey road', pal='KGYW', bg=BG_B,
              slots='WGY', car3='K', drone='K', outline='K'),
    'B2': dict(name='as B, with a darker road: one white pixel in four', pal='KGYW', bg={**BG_B, 8: 'WKKK'},
               slots='WGY', car3='K', drone='K', outline='K'),
    'C': dict(name='black, red, green, white; grey road', pal='KRGW',
              bg={**BG_B, 2: 'R', 4: 'RK', 10: 'R', 12: 'R'},
              slots='WRG', car3='K', drone='K', outline='K'),
    'D': dict(name='black, blue, green, white; blue-black road', pal='KBGW',
              bg={0: 'K', 1: 'B', 2: 'BW', 3: 'K', 4: 'WK', 5: 'GK', 6: 'BW', 7: 'W', 8: 'BK', 9: 'BW',
                  10: 'W', 11: 'BW', 12: 'W', 13: 'G', 14: 'W', 15: 'W'},
              slots='BGW', car3='K', drone='K', outline='K'),
}


def car_table(opt, car, droned=False):
    """ST colour -> pattern for car 0-3, or for frames 64+ (a player's car driven by a drone)."""
    out = opt['outline']
    t = {0: out, 3: 'K', 7: 'W', 11: 'WK', 14: 'W', 15: 'W'}
    colour = opt['slots'][car] if car < 3 else opt['car3']
    if droned:
        t.update({11: opt['drone'], BODY[car]: colour, TRIM[car]: colour[0] + 'K'})
    else:
        t.update({BODY[car]: colour, TRIM[car]: colour[0] + 'K'})
        if car == 1:
            t.update({4: colour[0] + 'K', 12: 'W'})
    return t


def logical_map(opt, table):
    """ST colour -> logical colours for the 2x2 cell's (x even, y even), (odd, even), (even, odd), (odd, odd).
    A pattern is one letter (solid), two (a checkerboard) or four (a 2x2 tile in that order)."""
    pal = opt['pal']
    out = {}
    for c, pat in table.items():
        if len(pat) == 2:
            pat = pat[0] + pat[1] + pat[1] + pat[0]
        elif len(pat) == 1:
            pat = pat * 4
        out[c] = tuple(pal.index(p) for p in pat)
    return out


def apply_map(idx, lmap):
    h, w = idx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ph = (xx & 1) + 2 * (yy & 1)
    out = np.zeros((h, w), np.uint8)
    for c, pat in lmap.items():
        m = idx == c
        for k in range(4):
            out[m & (ph == k)] = pat[k]
    return out


def mode1_bytes(lidx):
    """(200, 320) logical colours -> 16,000 bytes in the BBC's cell order (rows of 80 cells of 8 lines)."""
    h, w = lidx.shape
    assert h % 8 == 0 and w % 4 == 0
    hi = (lidx >> 1) & 1
    lo = lidx & 1
    px = np.zeros((h, w // 4), np.uint8)
    for n in range(4):
        px |= (hi[:, n::4] << (7 - n)) | (lo[:, n::4] << (3 - n))
    # cell order: row r, column c, line l -> r*640 + c*8 + l
    return px.reshape(h // 8, 8, w // 4).transpose(0, 2, 1).tobytes()


def to_rgb(lidx, pal):
    return np.array([BBC[p] for p in pal], np.uint8)[lidx]


def car_positions(road, bg):
    """Sample car places: 16x12 boxes on the road (road mask 0, road colours), spread over the track."""
    ok = []
    for y in range(16, 186, 4):
        for x in range(8, 300, 4):
            box = bg[y:y + 12, x:x + 16]
            if not road[y:y + 12, x:x + 16].any() and np.isin(box, (8, 3)).mean() > 0.97:
                ok.append((x, y))
    picks = [ok[len(ok) // 7]]
    while len(picks) < 5:
        d = [min((x - px) ** 2 + (y - py) ** 2 for px, py in picks) for x, y in ok]
        picks.append(ok[int(np.argmax(d))])
    return picks


def draw_cars(lidx, opt, dat, places, prio):
    """Draw cars 0-3 and car 1 driven by a drone at the places, behind the priority mask's 0 pixels."""
    for k, (x, y) in enumerate(places):
        car, droned = (k, False) if k < 4 else (1, True)
        frame = car_frame(dat, car * 16 + (k * 5) % 16 + (64 if droned else 0))[:, :16]
        lmap = logical_map(opt, car_table(opt, car, droned))
        sprite = apply_map(frame, {c: v for c, v in lmap.items()})
        opaque = frame != 8
        vis = opaque & (prio[y:y + 12, x:x + 16] == 1)
        lidx[y:y + 12, x:x + 16][vis] = sprite[vis]


def main(out):
    os.makedirs(out, exist_ok=True)
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    for key, opt in OPTIONS.items():
        lmap = logical_map(opt, opt['bg'])
        sheet = Image.new('RGB', (4 * 330, 2 * 210), (50, 50, 50))
        for t in range(8):
            bg = np.load(f'build/gfx/bg_t{t}.npy')
            road = np.load(f'build/gfx/mask1_t{t}.npy')
            prio = np.load(f'build/gfx/mask2_t{t}.npy')
            lidx = apply_map(bg, lmap)
            np.save(f'{out}/{key}_t{t}_bg.npy', lidx)
            open(f'{out}/{key}_t{t}_bg.bin', 'wb').write(mode1_bytes(lidx))
            draw_cars(lidx, opt, dat, car_positions(road, bg), prio)
            open(f'{out}/{key}_t{t}.bin', 'wb').write(mode1_bytes(lidx))
            img = Image.fromarray(to_rgb(lidx, opt['pal']))
            img.save(f'{out}/{key}_t{t}.png')
            sheet.paste(img, ((t % 4) * 330 + 5, (t // 4) * 210 + 5))
        sheet.save(f'{out}/{key}_all.png')
        print(key, opt['name'])


if __name__ == '__main__':
    main(sys.argv[1])
