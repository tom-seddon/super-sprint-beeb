"""The front end's pictures and tables for the game (Phase 5, step 8): build/gen/front.6502, the screens' palettes and
wipe masks, and each picture, as NAME.bin (the screen's 16,000 bytes) and NAME.zx02. A screen's look is Looks below:
change it and rebuild.

The wipe (F_014E34): G_01DD82's diamond, 8 pixels across and 8 lines down, closing over 8 steps. 8 pixels is 2 bytes
in MODE 1 and in MODE 2, and 8 lines a cell, so a level is 16 byte masks: the left byte's 8 lines, then the right's.

Usage: screens.py OUTDIR ZX02
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs
import numpy as np
import st_frontend as F
import st_screens as SS
import stgfx
import st_tracks as T
import screen_options as O
from convert import PHYS, mode1_bytes

# G_01DD82's levels: a mask of 8 pixels a line, 8 lines. (Its first two are all set, and its last two clear)
Levels = [[0xFF] * 8, [0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E], [0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C],
          [0x18, 0x3C, 0x7E, 0xFF, 0xFF, 0x7E, 0x3C, 0x18], [0, 0x18, 0x3C, 0x7E, 0x7E, 0x3C, 0x18, 0],
          [0, 0, 0x18, 0x3C, 0x3C, 0x18, 0, 0], [0, 0, 0, 0x18, 0x18, 0, 0, 0], [0] * 8]
Looks = {'title': dict(mode=2, table=O.TitleChecked, over=O.title_line),    # (Tom, 2026-11-04: option 7, MODE 2 checked; he may change his mind)
         'credits': dict(mode=1, pal='KRYC', table=O.CreditsFlat('C')),
         'scores': dict(mode=1, pal='KBMY', table=O.ScoresFlat('M', 'Y'), blank=F.scores_frame),
         # (the high scores' frame but for the heading's cell rows, so only those are packed)
         'records': dict(mode=1, pal='KBMY', table=O.ScoresFlat('M', 'Y'), blank=F.records_frame, rows=(3, 5))}
Prepare = dict(pal='KGYW', colours='WGY', checks='GKKG')    # (Tom, 2026-11-05: the race's palette, a dim green checker)
Options = (b'white', b'green', b'yellow')    # (the cars as the BBC has them)
OptionsOn, OptionsOff = b'f9 sound on   f0 exit   ', b'f9 sound off  f0 exit   '
SelectRows = 4                          # the select screen's cell rows of panels
SelectLevels = (0x1F5EC, 0x1F600, 0x1F614, 0x1F628)    # G_01D09C's strings
PanelRows = 6                           # prepare's cell rows of panels
Glyphs = 39                             # the small font's, as the tables use them: the digits, the letters, a space


def mask1(n):
    """MODE 1: 4 pixels of a nibble, each a bit in both halves of the byte."""
    return n << 4 | n


def mask2(n):
    """MODE 2: 2 pixels, each 2 of the ST's, kept if both are: left bits 7, 5, 3, 1, right 6, 4, 2, 0."""
    return (0xAA if n >> 2 == 3 else 0) | (0x55 if n & 3 == 3 else 0)


def table(mask):
    out = []
    for lv in Levels:
        out += [mask(b >> 4) for b in lv] + [mask(b & 15) for b in lv]
    return out


def bytes_of(idx, look):
    if look['mode'] == 2:
        return O.mode2_bytes(look['over'](O.mapped(idx, look['table'])))
    return mode1_bytes(O.render(idx, look['table'], look['pal']))


def picture(name):
    """(The screen as it's shown, what's packed: without what the game draws over it.)"""
    look = Looks[name]
    idx = O.Screens[name](F.dat())[0]
    shown = bytes_of(idx, look)
    raw = bytes_of(look['blank'](F.first_dump()), look) if 'blank' in look else shown
    if 'rows' in look:
        a, b = (r * 640 for r in look['rows'])
        other = picture('scores')[1]
        assert raw[:a] == other[:a] and raw[b:] == other[b:], f'{name}: the frame differs outside its rows'
        raw = raw[a:b]
    return shown, raw


def font():
    """The small font (G_01D43C): 6 lines a glyph, of its 8 bytes."""
    mem = F.first_dump()
    return [mem[0x1D43C - F.Region + g * 8 + line] for g in range(Glyphs) for line in range(6)]


def prepare(out, zx02):
    """Prepare to race: the picture from cell row PanelRows on as prepare.zx02, and each car's panel, its part of the rows above,
    a cell row after another, playing and not: prepare_0-2 and prepare_3-5. prepare_all and prepare_none.bin are the screen
    with all three playing and none, for tools/game_check.mjs."""
    mem = F.first_dump()
    full = [mode1_bytes(O.prepare(F.prepare(mem, (p, p, p)), **Prepare)) for p in (1, 0)]
    assert full[0][PanelRows * 640:] == full[1][PanelRows * 640:], 'prepare: the panels reach below their rows'
    open(f'{out}/prepare_all.bin', 'wb').write(full[0])
    open(f'{out}/prepare_none.bin', 'wb').write(full[1])
    streams = [('prepare', full[0][PanelRows * 640:])]
    for state, screen in enumerate(full):
        for car in range(3):
            a, b = O.PanelX[car] * 2, O.PanelX[car + 1] * 2
            streams.append((f'prepare_{state * 3 + car}', b''.join(screen[r * 640 + a:r * 640 + b] for r in range(PanelRows))))
    for name, raw in streams:
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')


# The options' keys of the main keyboard, numbers measured (tools/options_check.mjs): (number, name), the name a character,
# a word from OptWords's list, or None if it can't be taken: the game's own keys.
# The Master's keypad's numbers are Tom's, 2026-11-06.
Pad = {0x7A: 'PAD 4', 0x7B: 'PAD 5', 0x7C: 'PAD 2', 0x6A: 'PAD 0', 0x6B: 'PAD 1', 0x6C: 'PAD 3', 0x5A: 'PAD #', 0x5B: 'PAD *', 0x5C: 'PAD ,', 0x4A: 'PAD /',
       0x4B: 'PAD DEL', 0x4C: 'PAD .', 0x3A: 'PAD +', 0x3B: 'PAD -', 0x3C: 'PAD RET', 0x2A: 'PAD 8', 0x2B: 'PAD 9', 0x1A: 'PAD 6', 0x1B: 'PAD 7'}
Words = ('SHIFT', 'CTRL', 'CAPS', 'LOCK', 'RETURN', 'DELETE', 'TAB', 'SPACE', 'COPY') + tuple(Pad.values())
Matrix = (('SHIFT', 'CTRL'),
          ('Q', '3', '4', '5', None, '8', None, '-', '^', 136),
          (None, 'W', 'E', 'T', '7', 'I', '9', '0', '_', 138),
          ('1', '2', 'D', 'R', '6', 'U', 'O', 'P', '[', 139),
          ('CAPS', 'A', 'X', 'F', 'Y', 'J', 'K', '@', ':', 'RETURN'),
          ('LOCK', 'S', 'C', 'G', 'H', 'N', 'L', ';', ']', 'DELETE'),
          ('TAB', 'Z', 'SPACE', 'V', 'B', 'M', ',', '.', '/', 'COPY'),
          (None, None, None, None, None, None, None, None, '\\', 137))


def option_keys():
    """[(number, its name's byte)]: a character, a word's number, or 0."""
    code = lambda n: 0 if n is None else n if isinstance(n, int) else Words.index(n) + 1 if n in Words else ord(n)
    return [(row * 16 + col, code(n)) for row, names in enumerate(Matrix) for col, n in enumerate(names)] + [(k, code(n)) for k, n in Pad.items()]


def lines_of(screen, y, n):
    """Lines y on of the screen's bytes, each its 80 bytes across."""
    return bytes(screen[(l >> 3) * 640 + c * 8 + (l & 7)] for l in range(y, y + n) for c in range(80))


def text_on(lidx, s, x, y, colour=3):
    """The small font's text on logical colours, as front_glyph ORs it."""
    c = F.Canvas(F.first_dump())
    for ch in s:
        off = 0x1D43C - F.Region + c.code(ch) * 8
        for line in range(6):
            for j in range(6):
                if c.mem[off + line] >> (7 - j) & 1:
                    lidx[y + line, x + j] = colour
        x += 6


def mirror(raw):
    """A dial's position, each line's 16 bytes the other way round, and the pixels in each."""
    flip = lambda n: int(f'{n:04b}'[::-1], 2)
    rev = lambda b: flip(b >> 4) << 4 | flip(b & 15)
    return b''.join(bytes(rev(b) for b in raw[l * 16:l * 16 + 16][::-1]) for l in range(44))


def dial_files(out, zx02, name, top, mirrored=False):
    """The dial's 16 positions at line top, 16 bytes across from byte 32, each its own stream but for 5-8, which the game turns upside
    down, and if mirrored, 9-15, which it turns round: NAME.zx02s, and NAME.bin for the checks. Returns (each position's offset, the
    positions unpacked)."""
    d, event, pal = F.dat(), F.shot('select1')[1], Prepare['pal']
    base5 = 0x3140 + 0x96
    stored = [stgfx.planar_to_indices(d[base5 + i * 0x580:base5 + (i + 1) * 0x580], 64, 44) for i in range(5)]
    positions = stored + [stored[3 - i][::-1] for i in range(4)]
    positions = positions + [positions[7 - i][:, ::-1] for i in range(7)]
    idx = F.shot('select1')[0]
    dial, offsets, packed, frames = b'', [], b'', []
    for p, f in enumerate(positions):
        px = idx.copy()
        px[97:141, 128:192] = f
        rgb = SS.rgb(px, event)[97:141, 128:192]
        lidx = np.zeros((200, 320), np.uint8)
        lidx[top:top + 44, 128:192] = O.tiled(rgb, pal, top)
        screen = mode1_bytes(lidx)
        raw = bytes(screen[(l >> 3) * 640 + c * 8 + (l & 7)] for l in range(top, top + 44) for c in range(32, 48))
        if 5 <= p <= 8:                 # (upside down, by the game)
            offsets.append(offsets[8 - p])
            raw = b''.join(frames[8 - p][l * 16:l * 16 + 16] for l in range(43, -1, -1))
        elif mirrored and p > 8:
            offsets.append(offsets[16 - p])
            raw = mirror(frames[16 - p])
        else:
            offsets.append(len(packed))
            packed += dfs.compress(raw, exe=zx02, name=f'dial {p}')
        frames.append(raw)
        dial += raw
    open(f'{out}/{name}.bin', 'wb').write(dial)
    open(f'{out}/{name}.zx02s', 'wb').write(packed)
    print(f'{name}: {len(packed):,} bytes packed')
    return offsets, frames


def select_files(out, zx02):
    """The select screen: select.zx02 the picture; select_0-2 and 3-5 the panels, playing and not; select_dial.zx02s the dial's 16
    positions, each its own stream; and what tools/game_check.mjs compares: select.bin, select_all, select_none, select_dial.bin,
    select_text.bin (\"SELECT TRACK\", then the seconds 0-5) and select_level.bin. Returns the tables' lines for front.6502."""
    mem, pal = F.first_dump(), Prepare['pal']
    d, event = F.dat(), F.shot('select1')[1]
    frame = O.select_frame(SS.rgb(T.decode_map(d, 10), event), pal)
    text_on(frame, b'select track', 0x7C, O.SelectText)
    base = mode1_bytes(frame)
    open(f'{out}/select.bin', 'wb').write(base)
    streams = [('select', base)]
    colours = [pal.index(c) for c in Prepare['colours']]
    tops = []
    for playing in ((1, 1, 1), (0, 0, 0)):
        px, lidx = F.select_panels(mem, playing), np.zeros((200, 320), np.uint8)
        for car in range(3):
            lidx[px == car + 1] = colours[car]
        tops.append(mode1_bytes(lidx))
    for state, screen in enumerate(tops):
        for car in range(3):
            a, b = O.PanelX[car] * 2, O.PanelX[car + 1] * 2
            streams.append((f'select_{state * 3 + car}', b''.join(screen[r * 640 + a:r * 640 + b] for r in range(SelectRows))))
    open(f'{out}/select_all.bin', 'wb').write(tops[0][:SelectRows * 640])
    open(f'{out}/select_none.bin', 'wb').write(tops[1][:SelectRows * 640])
    for name, raw in streams:
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')
    offsets = dial_files(out, zx02, 'select_dial', O.SelectDial)[0]
    c = F.Canvas(mem)
    levels = [bytes(mem[a - F.Region:mem.index(0, a - F.Region)]) for a in SelectLevels]
    text, at, glyph = b'', [], []
    for s in levels:
        lidx = np.zeros((200, 320), np.uint8)
        text_on(lidx, s, 106, O.SelectLevel)
        text += lines_of(mode1_bytes(lidx), O.SelectLevel, 6)
        at.append(len(glyph))
        glyph += [c.code(ch) for ch in s] + [255]
    open(f'{out}/select_level.bin', 'wb').write(text)
    band = b''
    for s, x in [(b'select track', 0x7C)] + [(str(n).encode(), 0x9D) for n in range(6)]:
        lidx = np.zeros((200, 320), np.uint8)
        text_on(lidx, s, x, O.SelectText)
        band += lines_of(mode1_bytes(lidx), O.SelectText, 6)
    open(f'{out}/select_text.bin', 'wb').write(band)
    return ['SelDialOffsets = {' + ', '.join(map(str, offsets)) + '}', 'SelLevelOffsets = {' + ', '.join(map(str, at)) + '}',
            'SelLevelGlyphs = {' + ', '.join(map(str, glyph)) + '}']


UpDial = 99                             # the dial's first line, the ST's
UpRows = 8                              # the cell rows of a car's heading stream: the labels and the heading
UpPanelX = (0, 108, 216)                # each panel's first pixel
UpLapX = 86                             # "LAP", into a panel
UpMaxRun = 31                           # a rectangle's bytes across: Y, 8 a byte


def upgrade_font(mem):
    """The ST's HUD digits (`G_01DF4E`'s first set), a byte a line: their ink, 8 pixels wide, moved left a pixel; then its comma (`F_01603C`
    ORs one into a digit's mask, measured off the capture) and the wrench, as two 6-pixel halves (the sprites at `G_01EBDC` + &6F00)."""
    d = F.dat()
    out = []
    for g in range(10):
        for line in range(11):
            v = d[0x286BE + g * 0x2C + line * 4] << 8 | d[0x286BE + g * 0x2C + line * 4 + 1]
            assert v & 0x807F == 0, f'digit {g}: its ink past 8 pixels'
            out.append(v >> 7 & 255)
    out += [0] * 7 + [0xC0, 0xC0, 0x40, 0x80]
    idx = F.shot('upgrade0')[0]
    wrench = [[int(idx[y, x] not in (0, 13)) for x in range(51, 63)] for y in range(5)]
    for half in (0, 6):
        out += [sum(b << (7 - i) for i, b in enumerate(row[half:half + 6])) for row in wrench] + [0] * 6
    return out + [0] * 11               # (a blank, for a figure that wasn't there)


def box_rects(box):
    """The top left box's bytes as rectangles of one mask: [(first byte across, bytes, line, lines, mask)]. The game holds only these:
    the other three boxes are their mirrors."""
    nib = {}
    for y, x in zip(*np.nonzero(box)):
        nib[(y, x >> 2)] = nib.get((y, x >> 2), 0) | 8 >> (x & 3)
    runs = []
    for (y, col) in sorted(nib):
        last = runs[-1] if runs else None
        if last and last[2] == y and last[0] + last[1] == col and last[4] == nib[(y, col)] and last[1] < UpMaxRun:
            last[1] += 1
        else:
            runs.append([col, 1, y, 1, nib[(y, col)]])
    rects = []
    for r in runs:
        for q in rects:
            if q[0] == r[0] and q[1] == r[1] and q[4] == r[4] and q[2] + q[3] == r[2]:
                q[3] += 1
                break
        else:
            rects.append(r)
    return [(*r[:4], r[4] * 0x11) for r in rects]


def upgrades_files(out, zx02):
    """The upgrades (F_01A130): upgrades.zx02 the screen below the heading, upgrades_h0-2 each car's rows above it, the dial's positions,
    and what tools/upgrades_model.mjs builds on: upgrades_all.bin, each car's whole screen with no levels, upgrades_box.bin the
    boxes' pixels, 4 screens of byte masks, and upgrades_font.bin, the small font then the digits. Returns the tables' lines for front.6502."""
    mem, pal = F.first_dump(), Prepare['pal']
    choose = F.c_text(mem, 0x1F6C8)
    box = F.upgrade_boxes(F.Canvas(mem))
    offsets, frames = dial_files(out, zx02, 'upgrades_dial', UpDial, mirrored=True)
    lit = [[c for c in range(16) if any(f[l * 16 + c] for f in frames)] for l in range(44)]
    span = [list(range(s[0], s[-1] + 1)) if s else [] for s in lit]
    screens = []
    for car, name in enumerate(Options):
        lidx = O.upgrades(F.upgrades(mem, ((name + b' car', 30), (choose, 45)), colour=6, bars=True), pal, Prepare['checks'], car)
        for panel in range(3):
            text_on(lidx, b'lap', UpPanelX[panel] + UpLapX, 0, pal.index('WGY'[panel]))
        screens.append(bytearray(mode1_bytes(lidx)))
    for l, cols in enumerate(span):     # the dial's ground: black, so 16 frames can do for every picture, and none reach a box
        for c in cols:
            at = ((UpDial + l) >> 3) * 640 + (32 + c) * 8 + ((UpDial + l) & 7)
            assert not box[UpDial + l, 128 + c * 4:132 + c * 4].any(), 'the dial reaches a box'
            for s in screens:
                s[at] = 0
    assert all(s[UpRows * 640:] == screens[0][UpRows * 640:] for s in screens), 'upgrades: the cars differ below the heading'
    streams = [('upgrades', bytes(screens[0][UpRows * 640:]))] + [(f'upgrades_h{car}', bytes(screens[car][:UpRows * 640])) for car in range(3)]
    for name, raw in streams:
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')
    open(f'{out}/upgrades_all.bin', 'wb').write(b''.join(map(bytes, screens)))
    masks = b''
    for n in (2, 8, 4, 1):              # in the dial's order, G_01D02E's
        lidx = np.where(box == n, 3, 0).astype(np.uint8)
        masks += mode1_bytes(lidx)
    open(f'{out}/upgrades_box.bin', 'wb').write(masks)
    font_bytes = upgrade_font(mem)
    open(f'{out}/upgrades_font.bin', 'wb').write(bytes(font() + font_bytes))
    rects = box_rects(box == 1)
    print(f'the box: {len(rects)} rectangles')
    assert len(rects) < 256
    c = F.Canvas(mem)
    code = lambda s: [c.code(ch) for ch in s] + [255]
    names = [code(n + b' car') for n in Options] + [code(b'drone')]
    at, text = [], []
    for n in names:
        at.append(len(text))
        text += n
    taken = len(text)
    text += code(c.text(0x1F730))
    return ['UpDialOffsets = {' + ', '.join(map(str, offsets)) + '}',
            'UpDialFirst = {' + ', '.join(str(s[0] if s else 0) for s in span) + '}', 'UpDialBytes = {' + ', '.join(str(len(s)) for s in span) + '}',
            'UpFont = {' + ', '.join(map(str, font_bytes)) + '}',
            'UpNameAt = {' + ', '.join(map(str, at)) + '}', f'UpTaken = {taken}', 'UpTextGlyphs = {' + ', '.join(map(str, text)) + '}',
            f'UpRectCount = {len(rects)}'] + [f'UpRect{n} = {{' + ', '.join(str(r[i]) for r in rects) + '}'
                                              for i, n in enumerate(('Col', 'Bytes', 'Line', 'Lines', 'Nibble'))]


def glyphs(s):
    c = F.Canvas(F.first_dump())
    return ', '.join(str(c.code(ch)) for ch in s) + ', 255'


def string(a):
    """The string at a, as the small font's glyphs, ended by a byte with its top bit set."""
    c = F.Canvas(F.first_dump())
    return ', '.join(str(c.code(ch)) for ch in c.text(a)) + ', 255'


CircleHud = 22                          # the winner's circle: lines the panels have, black
CircleFig = (40, 144, 12, 32)           # the figure's first byte across, line, bytes and lines
CircleKinds = (3, 3, 3, 7)              # frames of each kind: 3 * kind + frame on the ST, the last with 7
CircleChunk = 1296                      # FrontBuf: the most of a car's masks at once
CircleSplit = 13                        # the picture's first stream's cell rows: each must fit under ANDY, to be unpacked into the shadow screen


def cells(raw, col, cols, y, lines):
    """cols bytes from byte col across, on lines lines from y, a line at a time, out of a screen's cell order."""
    return b''.join(bytes(raw[(l >> 3) * 640 + c * 8 + (l & 7)] for c in range(col, col + cols)) for l in range(y, y + lines))


def nibbles(row):
    """8 pixels of 0 or 1: the two bytes of a mask."""
    n = [sum(int(b) << (3 - i) for i, b in enumerate(row[h:h + 4])) * 17 for h in (0, 4)]
    return n


def circle_files(out, zx02):
    """The winner's circle: circle_0 and circle_1.zx02 the picture, in two, the cars' colours left black; circle_streams.zx02s each car's masks in chunks FrontBuf
    can hold, then each kind's figure, its frames and their masks. A mask is the screen's bytes, its right half the bodywork and its left the sides.
    And what tools/circle_model.mjs builds on: circle.bin, circle_class.bin, circle_figure.bin, circle_figure_class.bin, circle_sparkle.bin, circle_junk.bin. Returns front.6502's lines."""
    mem, pal, d = F.first_dump(), Prepare['pal'], F.dat()
    idx, event = T.decode_map(d, 9), F.shot('circle1')[1]
    place, part = F.circle_parts(idx)
    lidx = O.circle(SS.rgb(idx, event), pal)
    lidx[place >= 0] = 0
    lidx[:CircleHud] = 0
    for panel in range(3):
        text_on(lidx, b'lap', UpPanelX[panel] + UpLapX, 0, pal.index('WGY'[panel]))
    word = lambda a, n: [int.from_bytes(mem[a - F.Region + i * 2:a - F.Region + i * 2 + 2], 'big', signed=True) for i in range(n)]
    px, py, ground = word(0x1CFCE, 4), word(0x1CFC6, 4), word(0x1CFBE, 4)
    assert word(0x1CFDE, 4) == px == word(0x1CFEE, 4) and word(0x1CFD6, 4) == [y + 8 for y in py] and word(0x1CFE6, 4) == [y + 16 for y in py]
    assert word(0x1CFFE, 4) == [x - 36 for x in px] == word(0x1D00E, 4)
    inks = []
    for p in range(4):                  # the figures are EOR'd, so what's under them has to be flat
        block = lidx[py[p]:py[p] + 22, px[p] - 36:px[p] + 24]
        words = [block[l:l + 6, x:x + 24] for l in (8, 16) for x in (0, 36)] + [block[0:6, 36:60]]
        flats = {int(w.flat[0]) for w in words}
        assert len(flats) == 1 and all((w == w.flat[0]).all() for w in words), f'circle: the ground under place {p}\'s figures'
        inks.append((0, 0x0F, 0xF0, 0xFF)[flats.pop()])
    picture_bytes = mode1_bytes(lidx)
    classes = np.where((place >= 0) & (part == 3), 1, np.where((place >= 0) & (part == 1), 2, 0)).astype(np.uint8)
    class_bytes = mode1_bytes(classes)
    open(f'{out}/circle.bin', 'wb').write(picture_bytes)
    open(f'{out}/circle_class.bin', 'wb').write(class_bytes)
    packed = [dfs.compress(raw, exe=zx02, name='circle') for raw in (picture_bytes[:CircleSplit * 640], picture_bytes[CircleSplit * 640:])]
    for n, stream in enumerate(packed):
        open(f'{out}/circle_{n}.zx02', 'wb').write(stream)
    print(f'circle: {" and ".join(f"{len(p):,}" for p in packed)} bytes packed')
    streams, chunks = [], []
    for p in range(4):
        ys, xs = np.nonzero((classes > 0) & (place == p))
        col, cols = xs.min() >> 2, (xs.max() >> 2) - (xs.min() >> 2) + 1
        y, end = ys.min(), ys.max() + 1
        each = -(-(end - y) // -(-(end - y) * cols // CircleChunk))
        while y < end:
            lines = min(each, end - y)
            streams.append(cells(class_bytes, col, cols, y, lines))
            chunks.append((p, col, cols, y, lines))
            y += lines
    bands = SS.bands(event)
    ink3 = np.array(stgfx.palette_from_words(bands[3][1]), np.uint8)
    col, y, cols, lines = CircleFig
    figure, figure_class, first = b'', b'', 0
    for kind, n in enumerate(CircleKinds):
        base, cls = b'', b''
        for f in range(first, first + n):
            frame = F.circle_frame(d, f)
            whole, parts = np.zeros((200, 320), np.uint8), np.zeros((200, 320), np.uint8)
            look = O.circle(ink3[frame], pal, y, col * 4)
            look[(frame >= 7) & (frame <= 9)] = 0
            whole[y:y + lines, col * 4:(col + cols) * 4] = look
            parts[y:y + lines, col * 4:(col + cols) * 4] = np.where(frame == 9, 1, np.where(frame == 7, 2, 0))
            base += cells(mode1_bytes(whole), col, cols, y, lines)
            cls += cells(mode1_bytes(parts), col, cols, y, lines)
        first += n
        streams += [base, cls]
        figure += base
        figure_class += cls
    open(f'{out}/circle_figure.bin', 'wb').write(figure)
    open(f'{out}/circle_figure_class.bin', 'wb').write(figure_class)
    joined, offsets = b'', []
    for n, raw in enumerate(streams):
        offsets.append(len(joined))
        joined += dfs.compress(raw, exe=zx02, name=f'circle stream {n}')
    open(f'{out}/circle_streams.zx02s', 'wb').write(joined)
    print(f'the circle\'s masks and figure: {len(joined):,} bytes packed, {len(chunks)} chunks')
    ink1 = np.array(stgfx.palette_from_words(bands[1][1]), np.uint8)
    sparkles = []
    for n in range(6):
        px8, keep = F.circle_sparkle(d, n)
        keep[px8 > 0] = 0               # (the ST ORs these with what's under them, which only its colours' numbers make sense of)
        for line in range(8):
            ink = [0 if c in (0, 8, 9) else pal.index(O.CircleTiles[tuple(int(v) for v in ink1[c])][0]) for c in px8[line]]
            lo = [v & 1 for v in ink]
            hi = [v >> 1 for v in ink]
            data = [(a & 0xF0) | (b & 0x0F) for a, b in zip(nibbles(hi), nibbles(lo))]
            sparkles += data + nibbles(keep[line]) + nibbles(px8[line] == 9)
    open(f'{out}/circle_sparkle.bin', 'wb').write(bytes(sparkles))
    junk = [b & 0xFC for k in range(1, 10) for b in mem[0x1D43C - F.Region + (256 - k) * 8:][:6]]
    open(f'{out}/circle_junk.bin', 'wb').write(bytes(junk))
    hold = [v for k in range(4) for v in word(0x1CEDE + 26 * k, 13)]
    steps = [v & 255 for k in range(4) for v in word(0x1CF46 + 26 * k, 13)]
    col_of = lambda i: ', '.join(str(c[i]) for c in chunks)
    lst = lambda v: ', '.join(map(str, v))
    return [ f'CircleSplit = {CircleSplit}', f'CirclePages0 = {(len(packed[0]) + 255) // 256}', f'CirclePages1 = {(len(packed[1]) + 255) // 256}', f'CircleStreams = {len(streams)}', f'CircleChunks = {len(chunks)}',
            'CircleOffsets = {' + lst(offsets) + '}', 'CircleChunkPlace = {' + col_of(0) + '}', 'CircleChunkCol = {' + col_of(1) + '}',
            'CircleChunkBytes = {' + col_of(2) + '}', 'CircleChunkLine = {' + col_of(3) + '}', 'CircleChunkLines = {' + col_of(4) + '}',
            'CircleInk = {' + lst(inks) + '}', 'CirclePlaceX = {' + lst(px) + '}', 'CirclePlaceY = {' + lst(py) + '}',
            'CircleSparkY = {' + lst(word(0x1CE9E, 16)) + '}', 'CircleSparkX = {' + lst(word(0x1CEBE, 16)) + '}',
            'CircleSparkles = {' + lst(sparkles) + '}', 'CircleHold = {' + lst(hold) + '}', 'CircleSteps = {' + lst(steps) + '}',
            'CircleJunk = {' + lst(junk) + '}', 'CircleKindFrames = {' + lst(CircleKinds) + '}']


def main(out, zx02):
    lines = ['\\\\ front.6502 - the front end\'s tables (tools/screens.py)', 'Mode1Wipe = {' + ', '.join(map(str, table(mask1))) + '}',
             'Mode2Wipe = {' + ', '.join(map(str, table(mask2))) + '}',
             'CreditsPhys = {' + ', '.join(str(PHYS[c]) for c in Looks['credits']['pal']) + '}',
             'ScoresPhys = {' + ', '.join(str(PHYS[c]) for c in Looks['scores']['pal']) + '}',
             'SmallFont = {' + ', '.join(map(str, font())) + '}',
             'OptKeyNumbers = {' + ', '.join(str(k) for k, _ in option_keys()) + '}',
             'OptKeyNames = {' + ', '.join(str(n) for _, n in option_keys()) + '}',
             'OptWordBytes = {0, ' + ', '.join(str(b) for w in Words for b in w.encode() + b'\0') + '}',
             'OptTextOn = {' + glyphs(OptionsOn) + '}', 'OptTextOff = {' + glyphs(OptionsOff) + '}',
             'OptTextClash = {' + glyphs(b'keys may clash') + '}', 'OptTextPrompt = {' + glyphs(b'press the new keys   escape to cancel') + '}',
             'OptTextUsed = {' + glyphs(b'that key is in use') + '}',
             'BestsGlyphs = {' + string(0x1F766) + '}', 'TrackGlyphs = {' + string(0x1F776) + '}', 'SecsGlyphs = {' + string(0x1F77C) + '}']
    for name in Looks:
        shown, raw = picture(name)
        open(f'{out}/{name}.bin', 'wb').write(shown)
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')
    lines += select_files(out, zx02)
    lines += upgrades_files(out, zx02)
    lines += circle_files(out, zx02)
    prepare(out, zx02)
    frame = mode1_bytes(O.prepare(F.options_frame(F.first_dump(), Options), **Prepare))
    open(f'{out}/options.bin', 'wb').write(frame)
    for name, line in (('on', OptionsOn), ('off', OptionsOff), ('clash', OptionsOn + b'keys may clash')):
        px = F.options_frame(F.first_dump(), Options)
        F.Canvas.small(F.canvas_on(px), line, 24, 192, 13, 15)
        open(f'{out}/options_{name}.bin', 'wb').write(mode1_bytes(O.prepare(px, **Prepare))[24 * 640:])
    packed = dfs.compress(frame, exe=zx02, name='options')
    open(f'{out}/options.zx02', 'wb').write(packed)
    print(f'options: {len(packed):,} bytes packed')
    open(f'{out}/front.6502', 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(*sys.argv[1:])
