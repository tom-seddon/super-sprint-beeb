#!/usr/bin/env python3
"""Decode Super Sprint's per-track logic data (attribute maps, wall vectors, priority rectangles, slots,
drone paths) from orig/st. Run with the project venv for PNG output.

  tools/logic_maps.py attr <track>            40x25 attribute map as hex (INIT.DAT G_01E488 runs)
  tools/logic_maps.py walls <track> [out.png] wall-vector polylines and fill seeds (SUPER.DAT+&27B06)
  tools/logic_maps.py wallmask <track> <out.png> [ramdump]  render mask B (lines + fill); compare to a dump
  tools/logic_maps.py prio <track>            priority-mask rectangles (INIT.DAT G_01EE14)
  tools/logic_maps.py slots <track>           pickup/hazard slots (INIT.DAT G_01EC48)
  tools/logic_maps.py path <track>            drone path entries (SUPER.DAT+&2CE3A)
  tools/logic_maps.py summary                 per-track table
Tracks are 0-7 (the game shows them as 1-8).
"""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logic_init import tables

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SUPER = open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read()
T = tables()
WALLS_OFF = 0x27B06      # G_01D30A = &51006 = &29500 + &27B06, 3000 bytes
PATH_OFF = 0x2CE3A       # G_01E2A6 = &5633A, 7100 bytes
PATH_START = [0, 0x2A2, 0x554, 0x826, 0xC78, 0xFAA, 0x13FC, 0x17CE]   # G_01D158 (bytes), set in F_012276
PATH_COUNT = [0x54, 0x56, 0x5A, 0x8A, 0x66, 0x8A, 0x7A, 0x7C]         # G_01D168 (entries)

def words(b, signed=True):
    return list(struct.unpack('>%d%s' % (len(b) // 2, 'h' if signed else 'H'), b[:len(b) // 2 * 2]))

def tb(g):
    return T[g][1]

# ---------------------------------------------------------------- attribute map
def attr_map(track):
    m = bytearray(1000)
    cum = words(tb(0x1EE02))
    recs = tb(0x1E488)
    runs = []
    for r in range(cum[track], cum[track + 1]):
        x, y, n, a = recs[r * 4:r * 4 + 4]
        horiz = n & 0x80
        n &= 0x7F
        runs.append((x, y, n, 'h' if horiz else 'v', a))
        o = y * 40 + x
        for i in range(n):
            if o < 1000: m[o] |= a
            else: runs[-1] = runs[-1] + ("OVERFLOW at %d" % o,)
            o += 1 if horiz else 40
    return m, runs

def describe(a):
    s = []
    if a & 0x80:
        s.append('stripe')
    v = a & 0x7F
    if v:
        c, t = v & 3, v >> 2
        if c == 0:
            s.append({1: 'up-to-bridge', 2: 'ground', 3: 'jump-mid', 4: 'ramp(dir8-15)', 8: 'ramp(dir0-7)',
                      9: 'ramp(dir12,long)', 6: 'nudge', 5: 'flag10', 7: 'flag20'}.get(t, 'c0t%d' % t))
        elif c == 1:
            s.append({0: 'slow', 1: 'oil', 2: 'slowspin', 3: 'wrench', 4: 'bonus'}.get(t, 'obj%d' % t))
        elif c == 2:
            s.append('checkpoint%d' % (t & 7))
        else:
            if v & 4:
                s.append('bridgewall(dir%d)' % ((v >> 3) & 15))
            elif v & 8:
                s.append('bridgeok')
            else:
                s.append('bridge-edge(crash)')
    return '+'.join(s)

# ---------------------------------------------------------------- wall vectors
def wall_data(track):
    w = words(SUPER[WALLS_OFF:WALLS_OFF + 3000])
    i = w[track]
    n = w[i] - 1; i += 1
    polys = [[(w[i], w[i + 1])]]; i += 2
    while n > 0:
        polys[-1].append((w[i], w[i + 1])); i += 2
        n -= 1
        if w[i] == -1:
            n -= 2; i += 2
            polys.append([(w[i], w[i + 1])]); i += 2
    i -= 2
    polys = [p for p in polys if len(p) > 1]   # the read-ahead after the last &FFFF is not a polyline
    nseeds = w[i]; i += 1
    seeds = [(w[i + 2 * k], w[i + 2 * k + 1]) for k in range(nseeds)]
    return polys, seeds

def draw_line(m, x0, y0, x1, y1):
    """F_015590: DDA with the error starting at half the major length; endpoints inclusive."""
    dx, dy = abs(x0 - x1), abs(y0 - y1)
    if dy >= dx:   # steep: step in y from the lower y
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        sx = 1 if x1 >= x0 else -1   # d3 = x1 - x0 sign
        e = dy >> 1; x = x0
        for y in range(y0, y1 + 1):
            m[y][x] = 1
            e += dx
            if e >= dy:
                e -= dy; x += sx
    else:
        if x0 > x1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        sy = 1 if y1 >= y0 else -1
        e = dx >> 1; y = y0
        for x in range(x0, x1 + 1):
            m[y][x] = 1
            e += dy
            if e >= dx:
                e -= dx; y += sy

def wall_mask(track):
    m = [[0] * 320 for _ in range(200)]
    polys, seeds = wall_data(track)
    for p in polys:
        for (a, b) in zip(p, p[1:]):
            draw_line(m, a[0], a[1], b[0], b[1])
    for sx, sy in seeds:      # flood fill of 0 pixels with 1 (4-connected)
        st = [(sx, sy)]
        while st:
            x, y = st.pop()
            if 0 <= x < 320 and 0 <= y < 200 and m[y][x] == 0:
                m[y][x] = 1
                st += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return m

def mask_from_dump(dump, addr):
    d = open(dump, 'rb').read()
    return [[(d[addr + y * 40 + x // 8] >> (7 - x % 8)) & 1 for x in range(320)] for y in range(200)]

# ---------------------------------------------------------------- other tables
def prio(track):
    b = tb(0x1EE14)
    cnt, start = b[track * 2], b[track * 2 + 1]
    out = []
    for k in range(cnt):
        r = b[16 + (start + k) * 6:16 + (start + k) * 6 + 6]
        x8, y, wb, h, lo, hi = r
        cols = [c for c in range(16) if (hi << 8 | lo) >> c & 1]
        out.append((x8 * 8, y, (wb >> 4) * 16 + (wb & 15), h, cols))
    return out

def slots(track):
    b = tb(0x1EC48)[track * 40:track * 40 + 40]
    return [(b[2 * i], b[2 * i + 1]) for i in range(20)]

def path(track):
    w = words(SUPER[PATH_OFF:PATH_OFF + 7100])
    base = (PATH_START[track] + 2) // 2
    return [tuple(w[base + 4 * k:base + 4 * k + 4]) for k in range(PATH_COUNT[track])]

def main():
    cmd = sys.argv[1]
    if cmd == 'attr':
        t = int(sys.argv[2])
        m, runs = attr_map(t)
        print('track %d: %d runs (x, y, length, v/h, attribute)' % (t, len(runs)))
        for r in runs:
            print('  %2d,%2d %2d%s &%02X %s' % (r[0], r[1], r[2], r[3], r[4], describe(r[4])))
        print('     ' + ''.join('%-3d' % x for x in range(0, 40, 1))[:120])
        for y in range(25):
            print('%2d  ' % y + ' '.join('%02X' % m[y * 40 + x] if m[y * 40 + x] else ' .' for x in range(40)))
    elif cmd == 'walls':
        t = int(sys.argv[2])
        polys, seeds = wall_data(t)
        for p in polys:
            print('polyline:', ' '.join('%d,%d' % q for q in p))
        print('fill seeds:', ' '.join('%d,%d' % q for q in seeds))
    elif cmd == 'wallmask':
        t = int(sys.argv[2])
        m = wall_mask(t)
        from PIL import Image
        im = Image.new('RGB', (320, 200))
        ref = mask_from_dump(sys.argv[4], int(sys.argv[5], 16)) if len(sys.argv) > 5 else None
        diff = 0
        for y in range(200):
            for x in range(320):
                v = m[y][x]
                if ref is not None and ref[y][x] != v:
                    diff += 1
                    im.putpixel((x, y), (255, 0, 0) if v else (0, 255, 0))
                else:
                    im.putpixel((x, y), (255, 255, 255) if v else (0, 0, 0))
        im.save(sys.argv[3])
        if ref is not None:
            print('pixels differing from the dump:', diff)
    elif cmd == 'prio':
        for r in prio(int(sys.argv[2])):
            print('x %3d y %3d w %3d h %3d colours %s' % r)
    elif cmd == 'slots':
        print(' '.join('%d,%d' % s for s in slots(int(sys.argv[2]))))
    elif cmd == 'path':
        t = int(sys.argv[2])
        for k, e in enumerate(path(t)):
            x8, y8, ln, d = e
            fl = ''
            if d & 0x100 and d < 0x200: fl = 'FORK'
            elif d & 0x200: fl = 'GATE%d' % (d & 3)
            elif d & 0x400: fl = 'SKIP+%d' % (d & 0xFF)
            print('%3d lane%d  x %5.1f y %5.1f  len %3d  dir %2d %s' % (k, k & 1, x8 / 8, y8 / 8, ln, d & 15, fl))
    elif cmd == 'summary':
        st = words(tb(0x1EDA8))
        ng = words(tb(0x1ED88)); gp = words(tb(0x1ED98))
        bx = words(tb(0x1EBE0)); by = words(tb(0x1EBF0))
        for t in range(8):
            m, runs = attr_map(t)
            polys, seeds = wall_data(t)
            print('track %d (shown as %d): start x %d y %d step %d dir %d; gates %d %s; banner at %d,%d; '
                  '%d attribute runs; %d wall polylines, %d points, %d fill seeds; %d path entries' % (
                      t, t + 1, st[4 * t], st[4 * t + 1], st[4 * t + 2], st[4 * t + 3], ng[t],
                      [gp[t + i] for i in range(ng[t])], bx[t], by[t], len(runs), len(polys),
                      sum(len(p) for p in polys), len(seeds), PATH_COUNT[t]))

if __name__ == '__main__':
    main()

def scr(off):
    """ST screen byte offset -> (x, y) of the 16-pixel group"""
    return (off % 160) // 8 * 16, off // 160

def fixed_objects():
    ng = words(tb(0x1ED88)); gp = words(tb(0x1ED98), False)
    bb = tb(0x1EC30); bp = words(tb(0x1EC00), False)
    for t in range(8):
        gates = ['%d,%d' % scr(gp[t + i]) for i in range(ng[t])]
        bars = ['%d,%d kind %d' % (scr(bp[t * 3 + i]) + (bb[t * 3 + i] // 4,)) for i in range(3)]
        print('track %d: gates (48x16) at %s; pop-up barriers (16x8) at %s' % (t, ', '.join(gates) or '-', '; '.join(bars)))

if __name__ == '__main__' and sys.argv[1] == 'fixed':
    fixed_objects()
