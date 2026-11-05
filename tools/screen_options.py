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


# MODE 2: 160 pixels across, all 8 colours. Each pair of the ST's pixels is averaged, then:
Bayer = np.array([[0, 2], [3, 1]]) / 4 - 0.375
Order = 'KRGYBMCW'                      # (a logical colour is its physical one, the OS's default)


def mode2(idx, colours, how):
    """(200, 160) colours 0-7. how: 'solid', the nearest colour; 'ordered', a 2 x 2 threshold on each channel, as 1-bit
    RGB is; 'pick', the pair's commoner ST colour taken to the nearest colour, keeping edges hard."""
    pairs = colours[idx].reshape(200, 160, 2, 3)
    avg = pairs.mean(2)
    rgb = np.array([BBC[c] for c in Order], float)
    if how == 'ordered':
        yy, xx = np.mgrid[0:200, 0:160]
        t = (0.5 + Bayer[yy & 1, xx & 1] * Strength)[:, :, None]
        bits = (avg / 255 > t).astype(int)
        return np.array([Order.index(next(c for c in Order if tuple(int(v > 0) for v in BBC[c]) == tuple(b))) for b in bits.reshape(-1, 3)], np.uint8).reshape(200, 160)
    src = avg if how == 'solid' else pairs[:, :, 0, :]
    return np.argmin(((src[:, :, None, :] - rgb) ** 2).sum(3), axis=2).astype(np.uint8)


Strength = 1.0


def mapped(idx, table):
    """(200, 160): each pair of the ST's pixels by a table of ST colour -> a letter, or two for a checkerboard. Of a pair
    that differs, the brighter table entry's kept, as thin light lines would otherwise go."""
    l, r = idx[:, 0::2], idx[:, 1::2]
    yy, xx = np.mgrid[0:200, 0:160]
    ph = (xx + yy) & 1
    light = np.array([sum(BBC[table[c][0]]) for c in range(16)])
    src = np.where(light[l] >= light[r], l, r)
    out = np.zeros((200, 160), np.uint8)
    for c in range(16):
        tile = table[c]
        m = src == c
        out[m & (ph == 0)] = Order.index(tile[0])
        out[m & (ph == 1)] = Order.index(tile[-1])
    return out


# The title in MODE 2, by hand: sky cyan, reds red, the oranges flat or checked red and yellow, yellows yellow, blues blue
TitleFlat = {0: 'K', 1: 'W', 2: 'R', 3: 'R', 4: 'R', 5: 'Y', 6: 'C', 7: 'R', 8: 'Y', 9: 'Y', 10: 'B', 11: 'B', 12: 'C', 13: 'B', 14: 'R', 15: 'W'}
# In MODE 1, black, red, yellow, blue, by hand (Tom's): sky blue, white yellow, the tyres' blues darker. Tiles of four
TitleKRYB = {0: 'KKKK', 1: 'YYYY', 2: 'RRRR', 3: 'RRRY', 4: 'RYYR', 5: 'YYYY', 6: 'BBBB', 7: 'RRRK', 8: 'YYYY', 9: 'YYYY',
             10: 'BKKB', 11: 'BKKB', 12: 'BBBB', 13: 'BBBK', 14: 'RRRR', 15: 'YYYY'}
TitleChecked = {**TitleFlat, 3: 'RY', 4: 'RY', 5: 'YR', 2: 'RK', 7: 'RK', 11: 'BC', 6: 'CB'}


# The title's last line, redrawn (Tom, 2026-11-05: option C). The ST's letters are 5 pixels wide and MODE 2 has half its
# pixels across, so they fill in even in solid yellow: 3 x 5 letters here (the M and the (c) 5 across), their rows 1 and 3
# doubled, as a MODE 2 pixel is twice as wide as it's tall.
LineFont = {'c': ('.###.', '#.#.#', '##..#', '#.#.#', '.###.'), '1': ('.#.', '##.', '.#.', '.#.', '###'),
            '9': ('###', '#.#', '###', '..#', '###'), '8': ('###', '#.#', '###', '#.#', '###'), '6': ('###', '#..', '###', '#.#', '###'),
            'A': ('###', '#.#', '###', '#.#', '#.#'), 'T': ('###', '.#.', '.#.', '.#.', '.#.'), 'R': ('##.', '#.#', '##.', '#.#', '#.#'),
            'I': ('###', '.#.', '.#.', '.#.', '###'), 'G': ('###', '#..', '#.#', '#.#', '###'), 'M': ('#...#', '##.##', '#.#.#', '#...#', '#...#'),
            'E': ('###', '#..', '##.', '#..', '###'), 'S': ('###', '#..', '###', '..#', '###'), ' ': ('..',) * 5}
LineText = 'c 1986  ATARI  GAMES'
LineLeft, LineTop, LineRight = 96, 192, 152      # (the ST's own line starts at MODE 2's pixel 98: only the S's tail is left of it)


def title_line(lidx):
    """(200, 160) colours, the ST's line taken out and this one drawn, in yellow."""
    out = lidx.copy()
    out[LineTop:, LineLeft:] = 0
    x = LineRight - sum(len(LineFont[c][0]) + 1 for c in LineText) + 1
    for c in LineText:
        glyph = LineFont[c]
        for y, row in enumerate((0, 1, 1, 2, 3, 3, 4)):
            for i, bit in enumerate(glyph[row]):
                if bit == '#':
                    out[LineTop + y, x + i] = Order.index('Y')
        x += len(glyph[0]) + 1
    return out


def CreditsFlat(c):
    """The credits in MODE 1: red and yellow as they are, everything blue or white the one colour. Checks on the darkest
    blue were tried: the letters are a pixel wide, and they break up."""
    return {0: 'KKKK', 8: 'RRRR', 9: 'YYYY', **{i: c * 4 for i in (6, 10, 11, 12, 15)}}


def ScoresFlat(band, gold):
    """The high scores' frame in MODE 1, flat: the background blue, band the magenta bands and the car's reds, gold the
    edges, the car's yellows and greys and the white text, which is logical 3 (the game draws the table over the frame)."""
    return {0: 'KKKK', 1: 'BBBB', **{i: band * 4 for i in (3, 5, 8, 9, 14)}, **{i: gold * 4 for i in (2, 4, 6, 7, 11, 13, 15)}}


# Prepare to race (Tom, 2026-11-05: MODE 1, the race's palette): each car's ST colours by part. The three are one drawing, but
# not one colouring (docs/brief-phase5.md, step 8), and the middle panel is the bottom car's.
PrepareCars = ((dict(solid=(6, 4), shade=(3, 5)), (slice(52, 112), slice(0, 160))),
               (dict(solid=(6, 4, 10), shade=(3, 5, 9)), (slice(112, 200), slice(0, 320))),
               (dict(solid=(1, 2, 10), shade=(9,)), (slice(52, 112), slice(160, 320))))
PanelX = (0, 108, 216, 320)             # (panels by a byte's 4 pixels)


def prepare(px, pal, colours, checks):
    """px, F.prepare's picture, in logical colours: colours the cars', players 1-3, checks the checker's lighter squares."""
    table = {i: 'KKKK' for i in range(16)}
    table.update({12: checks, 15: 'WWWW', 7: 'WKKW'})
    out = render(px, table, pal)
    for (parts, area), c in zip(PrepareCars, colours):
        car = {**table, **{i: c * 4 for i in parts['solid']}, **{i: c + 'KK' + c for i in parts['shade']}}
        out[area] = render(px, car, pal)[area]
    for i, c in enumerate(colours):
        xs = slice(PanelX[i], PanelX[i + 1])
        out[:52, xs] = render(px, {**table, i + 1: c * 4}, pal)[:52, xs]
    return out


def mode2_bytes(lidx):
    """(200, 160) colours 0-7 -> 16,000 bytes: 2 pixels a byte, the left's bits 7, 5, 3, 1, the right's 6, 4, 2, 0."""
    a = lidx.astype(np.uint8)
    l, r = a[:, 0::2], a[:, 1::2]
    spread = lambda v: (v >> 3 & 1) << 6 | (v >> 2 & 1) << 4 | (v >> 1 & 1) << 2 | (v & 1)
    px = (spread(l) << 1 | spread(r)).astype(np.uint8)
    return px.reshape(25, 8, 80).transpose(0, 2, 1).tobytes()


def mode2_rgb(lidx):
    return np.array([BBC[c] for c in Order], np.uint8)[lidx].repeat(2, axis=1)


Screens = {'title': lambda d: (T.decode_map(d, 8), F.shot('title')[1]['palette']),
           'credits': lambda d: (stgfx.planar_to_indices(F.unrle(d, 0x2E9F6)[0], 320, 200), F.shot('credits')[1]['palette']),
           'scores': lambda d: (F.scores(F.first_dump()), F.shot('scores')[1]['palette']),
           'records': lambda d: (F.records(F.first_dump()), F.shot('records')[1]['palette'])}


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
20 N={n}:DIM P(N,4),N$(N)
30 FOR I=0 TO N-1:READ N$(I),P(I,4),P(I,0),P(I,1),P(I,2),P(I,3):NEXT
40 T=0
50 MODE P(T,4):VDU 23,1,0;0;0;0;
60 VDU 23,0,6,26;0;0;0;23,0,7,31;0;0;0;23,0,12,7;0;0;0;23,0,13,&E0;0;0;0;
70 IF P(T,4)=1 THEN VDU 19,0,P(T,0);0;19,1,P(T,1);0;19,2,P(T,2);0;19,3,P(T,3);0;
80 COLOUR 7-4*(P(T,4)=1):PRINT TAB(0,6);T+1;"/";N;" ";N$(T);
90 OSCLI "LOAD O"+STR$T+" 4180"
100 A=GET:T=(T+1) MOD N:GOTO 50
{data}'''


def viewer(name, options):
    """options: [(label, mode, palette, the screen's 16,000 bytes)] -> build/viewer/NAME.ssd."""
    os.makedirs('build/viewer', exist_ok=True)
    data = '\n'.join(f'{110 + 10 * i} DATA {label},{mode},' + ','.join(str(PHYS[c]) for c in pal.ljust(4, 'K'))
                     for i, (label, mode, pal, _) in enumerate(options))
    text = Viewer.format(name=name, n=len(options), data=data)
    boot = '*BASIC\r' + text.replace('\n', '\r') + '\rRUN\r'
    src = [f'\\\\ Viewer disc for {name} (tools/screen_options.py)', 'SECTION Boot, filename = "!BOOT", org = 0',
           '    EQUS ' + ', '.join(str(ord(c)) for c in boot), 'ENDSECTION']
    for i, (_, _, _, raw) in enumerate(options):
        open(f'build/viewer/{name}_{i}.bin', 'wb').write(raw)
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
    options = [(f'MODE 1 {p}', 1, p, mode1_bytes(render(idx, next(r[2] for r in ranked if r[1] == p), p))) for p in chosen]
    if want == 'title':
        options[5:5] = [(f'MODE 2 {n}', 2, '', mode2_bytes(mapped(idx, tab))) for n, tab in (('flat', TitleFlat), ('checked', TitleChecked))]
    if want == 'title':
        options.insert(7, ('MODE 1 KRYB by hand', 1, 'KRYB', mode1_bytes(render(idx, TitleKRYB, 'KRYB'))))
    if want == 'credits':               # (by hand: the ranking goes by area, and it's the text that matters)
        options = [(f'MODE 1 K R Y {c}', 1, 'KRY' + c, mode1_bytes(render(idx, CreditsFlat(c), 'KRY' + c))) for c in 'CWMG']
    if want == 'scores':                # (by hand: the text and the frame's edges want one colour, the bands another)
        options = [(f'MODE 1 K B {b} {g}', 1, 'KB' + b + g, mode1_bytes(render(idx, ScoresFlat(b, g), 'KB' + b + g)))
                   for b, g in ('MY', 'MW', 'RY', 'RW')]
    viewer(want, options)
    sheet = Image.new('RGB', (3 * 648, 2 * 424), (60, 60, 60))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (e, pal, table) in enumerate(ranked[:6]):
        im = Image.fromarray(to_rgb(render(idx, table, pal), pal)).resize((640, 400), Image.NEAREST)
        x, y = (i % 3) * 648, (i // 3) * 424
        sheet.paste(im, (x, y + 20))
        d.text((x + 4, y + 4), f'{pal}  error {e:.0f}', fill=(255, 255, 0))
    sheet.save(f'build/st_screens/opt_{want}.png')
