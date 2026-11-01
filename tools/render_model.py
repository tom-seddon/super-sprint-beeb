"""The renderer test's model: each frame of the ST race as the BBC should draw it, from the ST's own data.

Usage: render_model.py TRACK TRACE.json OUT.bin   (OUT: 16,000 bytes a frame, the play area in screen order)

Independent of the BBC's data (gendata.py's trimming, shifts, key colour and priority cells): the clean
background (option B), then each car in the ST's draw order, its frame mapped through the car's colours
(convert.py), drawn where the ST frame isn't colour 8, and, for a car on the ground (not elevated or airborne),
not where the priority mask (mask C) is 0.
"""
import json, sys
import numpy as np
sys.path.insert(0, 'tools')
from st_sprites import car_frame
from convert import OPTIONS, car_table, logical_map, apply_map, mode1_bytes


def main(track, tracepath, out):
    opt = OPTIONS['B']
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    bg = np.load(f'build/conv/B_t{track}_bg.npy')
    shows = np.load(f'build/gfx/mask2_t{track}.npy') == 1
    frames = []
    for f in range(64):
        st = car_frame(dat, f)[:, :17]
        frames.append((apply_map(st, logical_map(opt, car_table(opt, f // 16))), st != 8))
    with open(out, 'wb') as fo:
        for fr in json.load(open(tracepath)):
            lidx = bg.copy()
            for c in fr['order']:
                x, y, facing, flags = fr['cars'][c]
                sprite, opaque = frames[c * 16 + facing]
                draw = opaque.copy()
                if not flags & 0x0401:
                    draw &= shows[y:y + 12, x:x + 17]
                lidx[y:y + 12, x:x + 17][draw] = sprite[draw]
            fo.write(mode1_bytes(lidx))


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3])
