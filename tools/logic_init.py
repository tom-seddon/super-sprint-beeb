#!/usr/bin/env python3
"""Split INIT.DAT into the BSS tables F_0104EC copies it to, and print them as signed 16-bit words.
Usage: tools/logic_init.py [G_name ...]   (no args: list all tables)"""
import sys, struct, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# (global, bytes) in the order F_0104EC (&104EC) copies them
TABLES = [(0x1EDA8,0x40),(0x1ED88,0x10),(0x1ED98,0x10),(0x1EC48,0x140),(0x1E2CC,8),(0x1E280,0x20),(0x1E260,0x20),
 (0x1E160,0x100),(0x1E140,0x20),(0x1E0C0,0x80),(0x1DFCC,6),(0x1DF8A,6),(0x1DF72,0x18),(0x1DF1A,0x2C),(0x1DEC2,0x58),
 (0x1DD82,0x140),(0x1DD62,0x20),(0x1DD42,0x20),(0x1DD22,0x20),(0x1DCC2,0x60),(0x1DC42,0x80),(0x1DC18,0x2A),
 (0x1DBB8,0x60),(0x1DB78,0x40),(0x1DAF8,0x80),(0x1DAD8,0x20),(0x1DAC4,8),(0x1DABC,8),(0x1DAB4,8),(0x1DAAC,8),
 (0x1EE14,0x20E),(0x1EE02,0x12),(0x1E488,0x698),(0x1EBE0,0x10),(0x1EBF0,0x10),(0x1EC30,0x18),(0x1EC00,0x30),
 (0x1F1F8,8),(0x1F1F0,8),(0x1F022,0x1CE),(0x1D2BE,0x4B),(0x1D29C,0x21),(0x1D22C,0x6F)]
def tables():
    d = open(os.path.join(ROOT, 'orig/st/INIT.DAT'), 'rb').read()
    off = 0; out = {}
    for g, n in TABLES:
        out[g] = (off, d[off:off + n]); off += n
    return out
if __name__ == '__main__':
    t = tables()
    want = [int(a.replace('G_', ''), 16) for a in sys.argv[1:]]
    per = 8
    for g, n in TABLES:
        off, b = t[g]
        if want and g not in want:
            continue
        print('G_%06X  INIT.DAT+&%04X  %d bytes' % (g, off, n))
        if want:
            if n % 2:
                print('  bytes:', ' '.join('%d' % x for x in b))
            else:
                w = struct.unpack('>%dh' % (n // 2), b)
                for i in range(0, len(w), per):
                    print('  +%03X: ' % (i * 2) + ' '.join('%6d' % x for x in w[i:i + per]))
