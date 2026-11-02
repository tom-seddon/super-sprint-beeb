"""Mask B (walls) by 8 x 8 cell, per track: all road, all wall, mixed, and the rows' spans of mixed
cells (D13); and how many of the 16 facings' opacities differ between the 8 car sets (st-logic §3).
.venv/bin/python tools/maskb_stats.py"""
import sys
sys.path.insert(0, 'tools')
import numpy as np
import logic_maps as L
import st_sprites as S

for t in range(8):
    m = (np.array(L.wall_mask(t), dtype=np.uint8) != 0).astype(np.uint8)
    c = m.reshape(25, 8, 40, 8).transpose(0, 2, 1, 3).reshape(25, 40, 64).sum(axis=2)
    road, wall = (c == 0).sum(), (c == 64).sum()
    mixed = 1000 - road - wall
    span = 0
    for r in range(25):
        idx = np.nonzero((c[r] > 0) & (c[r] < 64))[0]
        if len(idx):
            span += idx[-1] - idx[0] + 1
    print(f"track {t + 1} (index {t}): road {road} wall {wall} mixed {mixed} ({mixed * 8} bytes) spans {span}")

dat = open('orig/st/SUPER.DAT', 'rb').read()
for d in range(16):
    sh = {}
    for s in range(8):
        f = S.car_frame(dat, s * 16 + d)
        sh.setdefault((f != 8).tobytes(), []).append(s)
    if len(sh) > 1:
        print(f"facing {d}: sets with the same opacity {list(sh.values())}")
