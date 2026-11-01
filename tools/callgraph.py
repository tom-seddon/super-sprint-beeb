"""Print the call tree of the disassembly (build/super.s) from a function, with sizes and profile cycles.
Usage: callgraph.py <super.s> <root hex> [depth] [profile lines]"""
import re, sys
from collections import defaultdict
lines = open(sys.argv[1]).read().split('\n')
root = int(sys.argv[2], 16); depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
callees = defaultdict(list); size = defaultdict(int); cur = None
for l in lines:
    m = re.match(r'; ---- (\S+)', l)
    if m:
        cur = int(m.group(1)[-6:], 16) if re.search(r'[0-9A-F]{6}$', m.group(1)) else None
        continue
    m = re.match(r'([0-9A-F]{6})  (\S+)', l)
    if m and cur is not None and m.group(2) != 'dc.b':
        size[cur] += 1
        c = re.search(r'-> F_([0-9A-F]{6})|-> (?:xbios|gemdos|bios)_([0-9A-F]{6})', l)
        if c and m.group(2) in ('jsr', 'bsr.w', 'bsr.b', 'bsr.s', 'bsr', 'jmp'):
            t = int(c.group(1) or c.group(2), 16)
            if t not in callees[cur]:
                callees[cur].append(t)
cyc = defaultdict(int)
if len(sys.argv) > 4:
    import bisect
    fs = sorted(size)
    for l in open(sys.argv[4]):
        m = re.match(r'^([0-9a-f]{8}) .*% \((\d+), (\d+),', l)
        a = int(m.group(1), 16)
        i = bisect.bisect_right(fs, a) - 1
        if i >= 0: cyc[fs[i]] += int(m.group(3))
seen = set()
def walk(f, d, ind):
    rep = f in seen
    print(f'{"  " * ind}{f:06X} ({size[f]} insns{", %dK cyc" % (cyc[f] // 1000) if cyc[f] else ""}){" ..." if rep and callees[f] else ""}')
    if rep or d == 0: return
    seen.add(f)
    for c in callees[f]:
        walk(c, d - 1, ind + 1)
walk(root, depth, 0)
