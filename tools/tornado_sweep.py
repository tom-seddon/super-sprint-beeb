"""A race for testing the tornado's clipping: st_race.py's frames with the tornado's place swept instead,
y from -17 to 201 a line a frame (past the ST's own -15 to 199 at both ends), x across the screen.

Usage: tornado_sweep.py RACE.json OUT.json, then make check TRACE=sweep TRACEFILE=OUT.json
"""
import json, sys

frames = json.load(open(sys.argv[1]))
for i, fr in enumerate(frames):
    for c in fr['calls']:
        if c[0] == 'tornado':
            c[1][1] = i * 7 % 301
            c[1][2] = (i % 219 - 17) & 0xFFFF
json.dump(frames, open(sys.argv[2], 'w'))
