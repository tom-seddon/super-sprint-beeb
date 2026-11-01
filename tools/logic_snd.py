#!/usr/bin/env python3
"""Decode Super Sprint's sound data from SUPER.DAT: the 35 instruments (60-byte records at SUPER.DAT+&30F66,
copied to G_01F250 by F_0136C4) and the effect/tune sequences (10000 bytes at SUPER.DAT+&3179A, copied to G_01F260).
Usage: tools/logic_snd.py [instruments|sequences|durations|all]"""
import struct, sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D = open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read()
INS, SEQ = 0x30F66, 0x3179A
def w(o): return struct.unpack_from('>h', D, o)[0]
def uw(o): return struct.unpack_from('>H', D, o)[0]
# sequence entry points used by the code: offset -> (starter function, what)
ENTRIES = {0x0: 'F_012C74', 0xE: 'F_013032', 0x1C: 'F_012E00', 0x4A: 'F_0130A0', 0x58: 'F_012EDC', 0xA6: 'F_012E6E',
           0xB4: 'F_012F4A', 0xC2: 'F_01310E tr0', 0xD0: 'F_01310E tr1', 0xDE: 'F_01310E tr2', 0xEC: 'F_013284',
           0xF2: 'F_0131A8', 0x110: 'F_0131DE', 0x12E: 'F_012FB8', 0x13C: 'F_013582/F_012D38', 0x142: 'F_013214',
           0x150: 'F_013252', 0x38A: 'F_0134B6', 0xA14: 'F_01353E', 0xD46: 'F_013362(0)', 0x1188: 'F_013362(1)',
           0x14B6: 'F_013362(2)', 0x171C: 'F_013362(3)', 0x1A8A: 'F_013362(4)', 0x1E64: 'F_0134FA'}
FIELDS = ['step', 'period', 'wobcnt', 'rate', 'vol0', 'len1', 'len2', 'len3', 'seg0', 'loop', 'dv1', 'dv2', 'dv3',
          'sweep', 'noise', 'x1E', 'prio']
def instruments():
    print('idx  ' + ' '.join('%6s' % f for f in FIELDS))
    for i in range(35):
        o = INS + i * 60
        print('%3d  ' % i + ' '.join('%6d' % w(o + 2 * k) for k in range(17)))
def seq(off, maxn=400):
    o = SEQ + off; out = []; n = 0
    while n < maxn:
        c = w(o); o += 2
        if 0 <= c <= 2: out.append('ch%d:ins%d' % (c, w(o))); o += 2
        elif 3 <= c <= 5: out.append('ch%d:per%d' % (c - 3, w(o))); o += 2
        elif c == 6: out.append('wait%d' % w(o)); o += 2
        else: out.append('end(%d)' % c); break
        n += 1
    return out
if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('instruments', 'all'): instruments()
    if what == 'durations':
        for off in sorted(ENTRIES):
            q = seq(off, 5000); t = sum(int(x[4:]) + 1 for x in q if x.startswith('wait'))
            ins = sorted(set(x.split(':')[1] for x in q if ':ins' in x), key=lambda x: int(x[3:]))
            print('&%04X %-18s %4d cmds %5d ticks (%.2f s) %s' % (off, ENTRIES[off], len(q), t, t / 83.25, ' '.join(ins)))
    if what in ('sequences', 'all'):
        for off in sorted(ENTRIES):
            s = seq(off)
            print('&%04X %-18s %d cmds: %s' % (off, ENTRIES[off], len(s), ' '.join(s[:60]) + (' ...' if len(s) > 60 else '')))
