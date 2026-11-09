"""The memory map, from a build's listing (beeb-ram-hunt): each region's parts by source file, its free bytes, and
the variables' sections' use. Figures off the build, never a doc.

Usage: memmap.py [LISTING] [--write]   (LISTING build/sprint.lst; --write: docs/memory-map.md, from the play build:
make beeb TRACE=play)

A part's size is from its INCLUDE to the next INCLUDE or the region's end in the same section; a file that only
includes others shows as 0 and is left out. A file of constants only (every line `Name = ...`: the generators'
lists) emits nothing and isn't a mark, so the file that includes it keeps the bytes after it. A region's end is its PRINTed free figure where it has one. The
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
    ('LowFree\'s code, `&0AC0`-`&0AFF`', 'LowFree\'s code', 0x0B00),
]
AtEnd = {'TunesFixed'}                 # data placed at its region's end: the free bytes are before it, not after
Labels = ['FxImage', 'LogicInputs', 'TraceData', 'HudEvents', 'TunesFixed']   # data INCBINned, not INCLUDEd: marked by label
Vars = {'Tables': (0x0400, 0x0800), 'LowFree': (0x0900, 0x0AC0), 'ObjBuf': (0x2A00, 0x2B00),
        'BlackTable': (0x2B00, 0x2C00), 'MoreTables': (0x2C00, 0x2E00), 'GameVars': (0x2E00, 0x3000), 'ScreenVars': (0x3000, 0x3070), 'LogicVars': (0x8E00, 0x9000),
        'FxData': (0x3000, 0x3F00), 'LogicZp': (0x00, 0x100)}


def constants_only(name, listing):
    """True if an INCLUDEd file (as the listing names it, relative to src/) has nothing but assignments."""
    f = os.path.normpath(os.path.join(os.path.dirname(listing), '..', 'src', name))
    try:
        text = open(f, errors='replace').read()
    except OSError:
        return False
    body = [l.split(';')[0].strip() for l in text.split('\n')]
    body = [l for l in body if l and not l.startswith('\\\\')]
    return all(re.match(r'^\w+\s*=', l) for l in body)


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
            if not constants_only(m.group(2), path):
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
        m = re.match(r'^  ([0-9A-F]{4})\s+SKIP (.+?)\s*(;.*)?$', l)
        if m:
            a = int(m.group(1), 16)
            try:                        # a number, a constant, or arithmetic on them (SKIP 4 * MaxObjEvents)
                n = int(eval(re.sub(r'&([0-9A-Fa-f]+)', r'0x\1', m.group(2)), {'__builtins__': {}}, consts))
            except Exception:
                n = 1
            lo = a if lo is None else min(lo, a)
            hi = a + n if hi is None else max(hi, a + n)
    return lo, hi


def report(path):
    lines, marks, free = parse(path)
    out = []
    for name, key, end in Regions:
        f = next((v for t, v, k in free if t == key), None)     # (the whole label: "ANDY" isn't "... under ANDY")
        idx = [i for i, (a, n, s) in enumerate(marks)
               if s and s[-1] == {'The background\'s bank': 'BgBank', 'The cars\' bank': 'CarsBank',
                                  'The fourth bank': 'TraceBank', 'The objects\' bank': 'ObjBank',
                                  'Main RAM\'s code': 'MainCode', 'ANDY, over `&8000`-`&8FFF` (D15)': 'Andy',
                                  'LowFree\'s code, `&0AC0`-`&0AFF`': 'LowCode'}.get(name, 'Shared')]
        if not idx:
            continue
        stop = end - f if f is not None else end
        last = marks[idx[-1]][1] in AtEnd and f is not None
        parts = []
        for k, i in enumerate(idx):
            a = marks[i][0]
            b = marks[idx[k + 1]][0] if k + 1 < len(idx) else stop
            if last and k == len(idx) - 2:
                b -= f                  # (the free bytes: between this part and the one at the end)
            elif last and k == len(idx) - 1:
                b = end
            # a part in a nested section (FxData) runs to the next mark in its own section
            if b < a:
                b = next((m[0] for m in marks[i + 1:] if m[2] == marks[i][2] and m[0] >= a), stop)
            if b > a:
                parts.append(f'{marks[i][1]} {b - a:,}')
        out.append(f'| {name} | {", ".join(parts)} | {f if f is not None else "-"} |')
    for name, (lo, hi) in Vars.items():
        a, b = var_use(lines, name)
        if a is not None:
            out.append(f'| {name} (`&{a:04X}`-`&{b - 1:04X}`) | {b - a:,} bytes of labels | {hi - b} |')
        elif any(re.match(r'^SECTION %s\b' % name, l) for l in lines):
            out.append(f'| {name} (`&{lo:04X}`-`&{hi - 1:04X}`) | nothing yet | {hi - lo} |')
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
