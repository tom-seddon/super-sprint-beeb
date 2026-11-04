"""tools/st_screens.py's pictures against Hatari's own (Phase 5, step 7): each shot's screen in its bands of palette,
against the screenshot Hatari took at the same moment, each colour taken to the ST's 3 bits a channel. Hatari's is
the last frame shown and the dump is memory at that instant, so what's moving differs (the dial, the sparkles, the
cars' flickers), and on a busy frame the palette's change lands part way along its line (circle0's line 74): small
patches, 1,145 pixels at most (upgrade1's moving box). A band's wrong palette is 2,078 at least, so a screen may
differ in Limit pixels. ONE_PALETTE in the environment uses the Shifter's palette alone, as this project first
did: every screen with bands must then fail (a limit by the row didn't: recolouring a car touches few of any row).
Exit status 1 if a screen's over the limit. Usage: st_screens_check.py"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import st_screens as S, stgfx

Limit = 1500
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'st_screens')


def main():
    bad = 0
    if os.environ.get('ONE_PALETTE'):
        S.bands = lambda e: [(0, e['palette'])]
    for f in ('screens', 'options'):
        for name, e, raw in S.shots(f'{D}/{f}.json', D):
            mine = S.rgb(stgfx.planar_to_indices(raw, 320, 200), e)
            im = np.array(Image.open(f'{D}/{name}_hatari.png').convert('RGB'))
            h, w = im.shape[:2]
            sy, sx = (2 if h >= 400 else 1), (2 if w >= 640 else 1)
            top, left = 29, 48          # (Hatari's borders: measured on the title, no raster: 0 pixels differ there)
            hat = im[::sy, ::sx][top:top + 200, left:left + 320]
            q = lambda a: (a.astype(int) * 7 + 127) // 255
            per = (q(hat) != q(mine)).any(axis=2).sum(axis=1)
            ok = per.sum() <= Limit
            print(f'{name}: {per.sum()} pixels differ, bands {[y for y, _ in S.bands(e)]}{"" if ok else ": WRONG"}')
            bad += not ok
    print(f'{bad} wrong' if bad else 'every screen in the colours Hatari showed')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
