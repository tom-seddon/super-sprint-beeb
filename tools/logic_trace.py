#!/usr/bin/env python3
"""Parse Hatari 'm' dumps logged at a breakpoint into frames of memory.
Usage: tools/logic_trace.py <hatari output> <frame marker addr hex> -- prints per-frame car fields."""
import sys, re, struct
def frames(path, marker):
    cur = None; out = []
    for l in open(path, errors='replace'):
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', l)
        if not m:
            continue
        a = int(m.group(1), 16); bs = bytes(int(x, 16) for x in m.group(2).split())
        if a == marker:
            cur = {}; out.append(cur)
        if cur is not None:
            for i, b in enumerate(bs):
                cur[a + i] = b
    return out
def w(f, a, signed=True):
    v = f.get(a, 0) << 8 | f.get(a + 1, 0)
    return v - 65536 if signed and v >= 32768 else v
if __name__ == '__main__':
    fr = frames(sys.argv[1], int(sys.argv[2], 16))
    F = {'spd': 0x1E404, 'top': 0x1E374, 'div': 0x1E36C, 'trac': 0x1E364, 'dir': 0x1E41C, 'tdir': 0x1E414,
         'x': 0x1E42C, 'y': 0x1E424, 'x8': 0x1E3FC, 'y8': 0x1E3F4, 'vx': 0x1E2FC, 'vy': 0x1E2F4, 'flags': 0x1E3A4,
         'spin': 0x1E37C, 'bnc': 0x1E3B4, 'wpt': 0x1E3BC, 'lap': 0x1E354, 'cp': 0x1E38C, 'str': 0x1E394,
         'crash': 0x1E3D4, 'offx': 0x1E30C, 'offy': 0x1E304}
    cars = [int(c) for c in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 3]
    fields = sys.argv[4].split(',') if len(sys.argv) > 4 else ['spd', 'dir', 'tdir', 'x', 'y', 'vx', 'vy', 'flags', 'spin', 'bnc', 'lap', 'cp', 'str']
    print('frame ' + ' | '.join(' '.join('%5s' % f for f in fields) for c in cars))
    for f in fr:
        print('%5d ' % w(f, 0x1D30E) + ' | '.join(' '.join('%5d' % w(f, F[k] + 2 * c) for k in fields) for c in cars))
