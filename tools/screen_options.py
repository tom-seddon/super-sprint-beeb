"""Colour options for a front-end screen (Phase 5, step 8; D18): every set of 4 of the BBC's colours with black in it, each
ST colour taken to the nearest of the solid colours, checkerboards and 1-in-4 patterns the set can make, the sets
ranked by how near the picture comes. A pattern's in convert.py's form: four letters, a 2 x 2 tile.

Usage: screen_options.py NAME [PALETTES]   (the screens are Screens below): the ranking; a sheet of the best six as
build/st_screens/opt_NAME.png; and a disc of PALETTES (default those six), build/viewer/NAME.ssd, booting to each in
turn on a key, in the race's 26-row screen, named in the HUD's row.
"""
import itertools, os, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import st_frontend as F
import st_tracks as T
import stgfx
from convert import BBC, PHYS, mode1_bytes

Letters = 'RGYBMCW'


def patterns(pal):
    """{tile: its mean colour}: solid, checkerboard, one in four."""
    out = {}
    for a in pal:
        out[a * 4] = np.array(BBC[a], float)
    for a, b in itertools.permutations(pal, 2):
        if a < b:
            out[a + b + b + a] = (np.array(BBC[a], float) + BBC[b]) / 2
        out[a + a + a + b] = (3 * np.array(BBC[a], float) + BBC[b]) / 4
    return out


def fit(colours, counts, pal):
    """Each ST colour's tile, and the picture's total error. A solid colour is preferred when it's nearly as good."""
    pats = patterns(pal)
    names, means = list(pats), np.array(list(pats.values()))
    plain = np.array([0.0 if n == n[0] * 4 else 400.0 for n in names])
    table, err = {}, 0.0
    for i, (c, n) in enumerate(zip(colours, counts)):
        if n:
            d = ((means - c) ** 2).sum(1)
            k = int(np.argmin(d + plain))
            table[i] = names[k]
            err += d[k] * n
    return table, err


def render(idx, table, pal):
    """The picture in logical colours."""
    h, w = idx.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ph = (xx & 1) + 2 * (yy & 1)
    out = np.zeros((h, w), np.uint8)
    for c, tile in table.items():
        m = idx == c
        for k in range(4):
            out[m & (ph == k)] = pal.index(tile[k])
    return out


def to_rgb(lidx, pal):
    return np.array([BBC[p] for p in pal], np.uint8)[lidx]


Screens = {'title': lambda d: (T.decode_map(d, 8), F.shot('title')[1]['palette'])}


def main(name):
    idx, words = Screens[name](F.dat())
    colours = np.array(stgfx.palette_from_words(words), float)
    counts = np.bincount(idx.ravel(), minlength=16)
    ranked = []
    for rest in itertools.combinations(Letters, 3):
        pal = 'K' + ''.join(rest)
        table, err = fit(colours, counts, pal)
        ranked.append((err / idx.size, pal, table))
    ranked.sort(key=lambda r: r[0])
    for e, pal, table in ranked[:12]:
        print(f'{pal}: {e:7.0f}')
    return idx, ranked


Viewer = '''10 REM {name}: the options, a key each
20 N={n}:DIM P(N,3),N$(N)
30 FOR I=0 TO N-1:READ N$(I),P(I,0),P(I,1),P(I,2),P(I,3):NEXT
40 MODE 1:VDU 23,1,0;0;0;0;
50 VDU 23,0,6,26;0;0;0;23,0,7,31;0;0;0;23,0,12,7;0;0;0;23,0,13,&E0;0;0;0;
60 T=0
70 VDU 19,0,P(T,0);0;19,1,P(T,1);0;19,2,P(T,2);0;19,3,P(T,3);0;
80 COLOUR 3:PRINT TAB(0,6);"{name} ";T+1;" of ";N;": ";N$(T);"     ";
90 OSCLI "LOAD O"+STR$T+" 4180"
100 A=GET:T=(T+1) MOD N:GOTO 70
{data}'''


def viewer(name, options):
    """options: [(palette, logical picture)] -> build/viewer/NAME.ssd."""
    os.makedirs('build/viewer', exist_ok=True)
    data = '\n'.join(f'{110 + 10 * i} DATA {pal},' + ','.join(str(PHYS[c]) for c in pal) for i, (pal, _) in enumerate(options))
    text = Viewer.format(name=name, n=len(options), data=data)
    boot = '*BASIC\r' + text.replace('\n', '\r') + '\rRUN\r'
    src = [f'\\\\ Viewer disc for {name} (tools/screen_options.py)', 'SECTION Boot, filename = "!BOOT", org = 0',
           '    EQUS ' + ', '.join(str(ord(c)) for c in boot), 'ENDSECTION']
    for i, (pal, lidx) in enumerate(options):
        open(f'build/viewer/{name}_{i}.bin', 'wb').write(mode1_bytes(lidx))
        src += [f'SECTION Option{i}, filename = "O{i}", org = &4180', f'    INCBIN "{name}_{i}.bin"', 'ENDSECTION']
    path = f'build/viewer/{name}.6502'
    open(path, 'w').write('\n'.join(src) + '\n')
    subprocess.run(['baron', '--opt', '3', '--title', name.upper(), '-o', f'build/viewer/{name}.ssd', path], check=True)
    print(f'build/viewer/{name}.ssd')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    idx, ranked = main(sys.argv[1])
    want = sys.argv[1]
    chosen = sys.argv[2].split(',') if len(sys.argv) > 2 else [r[1] for r in ranked[:6]]
    viewer(want, [(p, render(idx, next(r[2] for r in ranked if r[1] == p), p)) for p in chosen])
    sheet = Image.new('RGB', (3 * 648, 2 * 424), (60, 60, 60))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (e, pal, table) in enumerate(ranked[:6]):
        im = Image.fromarray(to_rgb(render(idx, table, pal), pal)).resize((640, 400), Image.NEAREST)
        x, y = (i % 3) * 648, (i // 3) * 424
        sheet.paste(im, (x, y + 20))
        d.text((x + 4, y + 4), f'{pal}  error {e:.0f}', fill=(255, 255, 0))
    sheet.save(f'build/st_screens/opt_{want}.png')
