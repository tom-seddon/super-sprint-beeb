#!/usr/bin/env python3
"""Print words from a RAM dump: tools/logic_mem.py <dump> <hex addr> <count> [w|b|l] [per line]"""
import sys, struct
d = open(sys.argv[1], 'rb').read()
a = int(sys.argv[2], 16); n = int(sys.argv[3]); k = sys.argv[4] if len(sys.argv) > 4 else 'w'
per = int(sys.argv[5]) if len(sys.argv) > 5 else 8
sz = {'b': 1, 'w': 2, 'l': 4}[k]; fmt = {'b': '>b', 'w': '>h', 'l': '>i'}[k]
vals = [struct.unpack_from(fmt, d, a + i * sz)[0] for i in range(n)]
for i in range(0, n, per):
    print('%06X: ' % (a + i * sz) + ' '.join('%6d' % v for v in vals[i:i + per]))
