"""The memory map, from a build's listing (beeb-ram-hunt): each region's parts by source file, its free bytes, and
the variables' sections' use. Figures off the build, never a doc.

Usage: memmap.py [LISTING] [--write]   (LISTING build/sprint.lst; --write: docs/memory-map.md, from the play build:
make beeb TRACE=play)

A part's size is from its INCLUDE to the next INCLUDE or the region's end in the same section; a file that only
includes others shows as 0 and is left out. A region's end is its PRINTed free figure where it has one. The
variables' sections (virtual) are read from their labels and SKIPs.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
Regions = [                             # (name, the PRINT that gives its end, its end)
    ('The background\'s bank', None, 0xC000),
    ('The cars\' bank', 'the cars\' bank', 0xC000),
    ('The fourth bank', 'the fourth bank', 0xC000),
    ('ANDY, over `&8000`-`&8FFF` (D15)', 'ANDY', 0x9000 - 0x1B0),
    ('The objects\' bank', 'the objects\' bank', 0xC000),
    ('Main RAM\'s code', 'main RAM\'s code', 0x2A00),
    ('Shared, both screens\' `&3070`-`&3EFF`', 'the &3000 area', 0x3F00),
]
Labels = ['FxImage', 'LogicInputs', 'TraceData', 'HudEvents']   # data INCBINned, not INCLUDEd: marked by label
Vars = {'GameVars': (0x2E00, 0x3000), 'ScreenVars': (0x3000, 0x3F00), 'LogicVars': (0x8E00, 0x9000),
        'FxData': (0x3000, 0x3F00), 'LogicZp': (0x00, 0x100), 'Shared': (0x3000, 0x3F00)}


def parse(path):
    lines = open(path, errors='replace').read().split('\n')
    marks, free, sections, stack = [], [], [], []
    for l in lines:
        m = re.match(r'^SECTION (\w+)', l)
        if m:
            stack.append(m.group(1))
            continue
        if l.startswith('ENDSECTION') and stack:
            stack.pop()
            continue
        m = re.match(r'^\s+([0-9A-F]{4})\s+INCLUDE "(.*)"', l)
        if m:
            marks.append((int(m.group(1), 16), m.group(2).replace('../build/', ''), tuple(stack)))
            continue
        m = re.match(r'^\s+([0-9A-F]{4})\s+\.(%s)$' % '|'.join(Labels), l)
        if m:
            marks.append((int(m.group(1), 16), m.group(2), tuple(stack)))
            continue
        m = re.match(r'^(.*): (\d+) bytes free', l)
        if m:
            free.append((m.group(1), int(m.group(2)), len(marks)))
    return lines, marks, free


def var_use(lines, name):
    """A virtual section's labels' extent: (first, end) over its reopenings."""
    lo, hi, on, last = None, None, False, None
    consts = {m.group(1): int(m.group(2)) for m in re.finditer(r'^(\w+) = (\d+)', '\n'.join(lines), re.M)}
    for l in lines:
        if re.match(r'^SECTION %s\b' % name, l):
            on = True
            continue
        if on and l.startswith('ENDSECTION'):
            on = False
            continue
        if not on:
            continue
        m = re.match(r'^  ([0-9A-F]{4})\s+SKIP (\d+|\w+)', l)
        if m:
            a = int(m.group(1), 16)
            n = int(m.group(2)) if m.group(2).isdigit() else consts.get(m.group(2), 1)
            lo = a if lo is None else min(lo, a)
            hi = a + n if hi is None else max(hi, a + n)
    return lo, hi


def report(path):
    lines, marks, free = parse(path)
    out = []
    for name, key, end in Regions:
        f = next((v for t, v, k in free if key and key in t), None)
        idx = [i for i, (a, n, s) in enumerate(marks)
               if s and s[-1] == {'The background\'s bank': 'BgBank', 'The cars\' bank': 'CarsBank',
                                  'The fourth bank': 'TraceBank', 'The objects\' bank': 'ObjBank',
                                  'Main RAM\'s code': 'MainCode', 'ANDY, over `&8000`-`&8FFF` (D15)': 'Andy'}.get(name, 'Shared')]
        if not idx:
            continue
        stop = end - f if f is not None else end
        parts = []
        for k, i in enumerate(idx):
            a = marks[i][0]
            b = marks[idx[k + 1]][0] if k + 1 < len(idx) else stop
            # a part in a nested section (FxData) runs to the next mark in its own section
            if b < a:
                b = next((m[0] for m in marks[i + 1:] if m[2] == marks[i][2] and m[0] >= a), stop)
            if b > a:
                parts.append(f'{marks[i][1]} {b - a:,}')
        out.append(f'| {name} | {", ".join(parts)} | {f if f is not None else "-"} |')
    for name, (lo, hi) in Vars.items():
        a, b = var_use(lines, name)
        if a is not None:
            out.append(f'| {name} (`&{a:04X}`-`&{b - 1:04X}`) | {b - a:,} bytes of labels | |')
    game = '\n'.join(lines[next(i for i, l in enumerate(lines) if l.startswith('SECTION BgFile')):])
    za = sorted({int(x, 16) for x in re.findall(r'= &([0-9A-F]{2}) \[auto\]', game)})   # (not !BOOT's)
    if za:
        out.append(f'| Zero page, the pool | used to `&{za[-1]:02X}` | |')
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(ROOT, 'build/sprint.lst')
    rows = ['| Region | Parts, bytes (by source file) | Free |', '|---|---|---|'] + report(path)
    if '--write' in sys.argv:
        text = ['# Memory map', '',
                'GENERATED by `tools/memmap.py --write` from `build/sprint.lst` of the play build (`make beeb '
                'TRACE=play`: track 1, three players). Never edit it by hand. Other tracks: `docs/brief-room-2026-11-02.md`.',
                ''] + rows
        open(os.path.join(ROOT, 'docs/memory-map.md'), 'w').write('\n'.join(text) + '\n')
    print('\n'.join(rows))
