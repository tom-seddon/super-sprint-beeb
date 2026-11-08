"""The renderer test's model: each frame of the ST race as the BBC should draw it, from the ST's own data.

Usage: render_model.py TRACK TRACE.json OUT.bin [--cue LOGIC.json]   (OUT: 16,640 bytes a frame, the HUD row
and the play area in screen order)

--cue LOGIC.json: the game's (drawn from the logic, D16): no helicopter; instead, in a wreck's last CueFrames
(its wait, G_01E3B4, from the race's logic trace, which tools/st_trace_logic.py records frame for frame with
this trace), its explosion replaced by the car where it's put back (its safe place), on the ground, shown for 4
frames and hidden for 4, shown in the first 4 and the last 4.

Independent of the BBC's data (gendata.py's trimming, shifts, key colour, priority cells and object
variants): the clean background in the ST's colours, changed by the frame's background objects as the ST
changes it (tools/objects.py), mask C likewise, mapped to option B; then each car the ST drew, in its order,
its frame (a player's car driven by a drone from the second set) mapped through the car's colours
(convert.py), drawn where the ST frame isn't colour 8, and, for a car on the ground (not elevated or airborne),
not where mask C is 0; a wrecked car's explosion in its place; then the moving objects (sparks, the banner,
the tornado, the helicopter) in the ST's order, each mapped with the patterns' phase its own, in the BBC's places
(gendata.py's frame_draws: the explosion on 4-pixel steps, D8). Above it the HUD row: the ST's scores and laps, as tools/hud.py
lays them out, in tools/font.py's glyphs, brought up to date as the BBC does it (D6): each screen keeps what
it shows, and after a change the screen drawn each frame (they take turns) has at most HudPerFrame of its
columns that differ redrawn, scanning from column 39 down, until a pass over each finds nothing.
"""

HudPerFrame = 4
CueFrames = 28                          # (logicframe.6502's)

import json, sys
import numpy as np
sys.path.insert(0, 'tools')
from st_sprites import car_frame
from convert import OPTIONS, car_table, logical_map, apply_map, mode1_bytes
from font import glyph_bytes
from gendata import load_race, frame_draws, moving_sprite, key_shift
import hud, objects


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


def cues(frames, logicpath):
    """By frame, each wrecked car's cue, from the ST's logic trace of the same race (tools/st_trace_logic.py,
    frame for frame): car -> (x, y, facing, drone) where it's put back (its safe place), or None (hidden)."""
    logic = json.load(open(logicpath))['frames']
    assert len(logic) >= len(frames) and all(logic[n]['frame'] == n for n in range(len(frames))), \
        'the logic trace: the same race, frame for frame (it may run on: track 8\'s race trace stops at 3,935)'
    word = lambda m, a: m[str(a)] << 8 | m[str(a + 1)]
    out = [dict() for _ in frames]
    for n, fr in enumerate(frames):
        m = logic[n]['mem']
        for car in range(4):
            left = word(m, 0x1E3B4 + 2 * car)                  # G_01E3B4: the wait left (a wreck's)
            if word(m, 0x1E3D4 + 2 * car) == 2 and 1 <= left <= CueFrames:   # G_01E3D4: 2 wrecked
                out[n][car] = ((word(m, 0x1E3EC + 2 * car) >> 3, word(m, 0x1E3E4 + 2 * car) >> 3,
                                word(m, 0x1E3DC + 2 * car), fr['drone'][car]) if (left - 1) & 4 == 0 else None)
    return out


def main(track, tracepath, out, cue=None):
    opt = OPTIONS['B']
    dat = open('orig/st/SUPER.DAT', 'rb').read()
    stbg = np.load(f'build/gfx/bg_t{track}.npy').copy()
    maskc = np.load(f'build/gfx/mask2_t{track}.npy').copy()
    bgmap = logical_map(opt, opt['bg'])
    frames = {}
    for car in range(4):
        for droned in (False, True):
            for facing in range(16):
                st = car_frame(dat, (64 if droned else 0) + car * 16 + facing)[:, :17]
                frames[car, droned, facing] = (apply_map(st, logical_map(opt, car_table(opt, car, droned))), st != 8)
    shown = [[hud.Blank] * hud.Width, [hud.Blank] * hud.Width]
    want, count = None, 0
    bg = apply_map(stbg, bgmap)
    heli = {}

    def put(lidx, key, x, y):
        """A moving object at (x, y) and its key's shift, its colours mapped with the patterns' phase its own,
        clipped."""
        idx, opaque = moving_sprite(dat, key)
        x += key_shift(key)
        sprite = apply_map(idx, bgmap)
        h, w = idx.shape
        c0, c1 = max(0, -x), min(w, 320 - x)
        for r in range(h):
            if 0 <= y + r < 200:
                row = opaque[r, c0:c1]
                lidx[y + r, x + c0:x + c1][row] = sprite[r, c0:c1][row]

    race = list(load_race(tracepath))
    cue_at = cues(race, cue) if cue else [dict() for _ in race]
    with open(out, 'wb') as fo:
        for n, fr in enumerate(race):
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
            calls = [c for c in fr['calls'] if c[0] in objects.Background]
            for kind, args, *_ in calls:
                objects.apply(dat, kind, args, stbg, maskc, bbc=True)
            if calls:
                bg = apply_map(stbg, bgmap)
            lidx = bg.copy()
            shows = maskc == 1
            cars, movers = frame_draws(fr, heli)
            for d in cars:
                if d[0] == 'explosion' and d[4] in cue_at[n]:
                    if cue_at[n][d[4]] is None:
                        continue
                    c = d[4]
                    x, y, facing, droned = cue_at[n][c]
                    flags = 0           # (on the ground: a safe place is)
                elif d[0] == 'explosion':
                    put(lidx, d[1], d[2], d[3])
                    continue
                else:
                    c = d[1]
                    x, y, facing, flags = fr['cars'][c]
                    droned = fr['drone'][c]
                sprite, opaque = frames[c, bool(droned), facing]
                draw = opaque.copy()
                if not flags & 0x0401:
                    draw &= shows[y:y + 12, x:x + 17]
                lidx[y:y + 12, x:x + 17][draw] = sprite[draw]
            for key, x, y in movers:
                if not (cue and key[0] == 'heli'):
                    put(lidx, key, x, y)
            fo.write(hud_row(screen))
            fo.write(mode1_bytes(lidx))


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[5] if sys.argv[4:5] == ['--cue'] else None)
