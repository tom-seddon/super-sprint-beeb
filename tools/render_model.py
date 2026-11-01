"""The renderer test's model: each frame of the ST race as the BBC should draw it, from the ST's own data.

Usage: render_model.py TRACK TRACE.json OUT.bin   (OUT: 16,640 bytes a frame, the HUD row and the play area
in screen order)

Independent of the BBC's data (gendata.py's trimming, shifts, key colour and priority cells): the clean
background (option B), then each car in the ST's draw order, its frame mapped through the car's colours
(convert.py), drawn where the ST frame isn't colour 8, and, for a car on the ground (not elevated or airborne),
not where the priority mask (mask C) is 0. Above it the HUD row: the ST's scores and laps, as tools/hud.py
lays them out, in tools/font.py's glyphs, brought up to date as the BBC does it (D6): each screen keeps what
it shows, and after a change the screen drawn each frame (they take turns) has at most HudPerFrame of its
columns that differ redrawn, scanning from column 39 down, until a pass over each finds nothing.
"""

HudPerFrame = 4

import json, sys
import numpy as np
sys.path.insert(0, 'tools')
from st_sprites import car_frame
from convert import OPTIONS, car_table, logical_map, apply_map, mode1_bytes
from font import glyph_bytes
import hud


def hud_row(text):
    """40 (glyph, colour) -> the HUD row's 640 bytes: a character's left 4 pixels at 16 * column + line, its
    right 4 at 16 * column + 8 + line."""
    out = bytearray(640)
    for col, (g, c) in enumerate(text):
        for line, bits in enumerate(glyph_bytes(g)):
            for half in range(2):
                nib = (bits >> (4 - 4 * half)) & 15
                byte = 0
                for n in range(4):
                    if nib >> (3 - n) & 1:
                        byte |= ((c >> 1) & 1) << (7 - n) | (c & 1) << (3 - n)
                out[16 * col + 8 * half + line] = byte
    return bytes(out)


def main(track, tracepath, out):
    opt = OPTIONS['B']
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    bg = np.load(f'build/conv/B_t{track}_bg.npy')
    shows = np.load(f'build/gfx/mask2_t{track}.npy') == 1
    frames = []
    for f in range(64):
        st = car_frame(dat, f)[:, :17]
        frames.append((apply_map(st, logical_map(opt, car_table(opt, f // 16))), st != 8))
    shown = [[hud.Blank] * hud.Width, [hud.Blank] * hud.Width]
    want, count = None, 0
    with open(out, 'wb') as fo:
        for n, fr in enumerate(json.load(open(tracepath))):
            now = hud.text(fr['laps'], fr['scores'], track)
            if now != want:
                want, count = now, 2
            screen = shown[n % 2]
            if count:
                budget = HudPerFrame
                for col in range(hud.Width - 1, -1, -1):
                    if screen[col] != want[col]:
                        screen[col] = want[col]
                        budget -= 1
                        if budget == 0:
                            break
                count = 2 if budget == 0 else count - 1
            lidx = bg.copy()
            for c in fr['order']:
                x, y, facing, flags = fr['cars'][c]
                sprite, opaque = frames[c * 16 + facing]
                draw = opaque.copy()
                if not flags & 0x0401:
                    draw &= shows[y:y + 12, x:x + 17]
                lidx[y:y + 12, x:x + 17][draw] = sprite[draw]
            fo.write(hud_row(screen))
            fo.write(mode1_bytes(lidx))


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
