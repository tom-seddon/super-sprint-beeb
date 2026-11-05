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
import st_frontend as F
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


def string(a):
    """The string at a, as the small font's glyphs, ended by a byte with its top bit set."""
    c = F.Canvas(F.first_dump())
    return ', '.join(str(c.code(ch)) for ch in c.text(a)) + ', 255'


def main(out, zx02):
    lines = ['\\\\ front.6502 - the front end\'s tables (tools/screens.py)', 'Mode1Wipe = {' + ', '.join(map(str, table(mask1))) + '}',
             'Mode2Wipe = {' + ', '.join(map(str, table(mask2))) + '}',
             'CreditsPhys = {' + ', '.join(str(PHYS[c]) for c in Looks['credits']['pal']) + '}',
             'ScoresPhys = {' + ', '.join(str(PHYS[c]) for c in Looks['scores']['pal']) + '}',
             'SmallFont = {' + ', '.join(map(str, font())) + '}',
             'BestsGlyphs = {' + string(0x1F766) + '}', 'TrackGlyphs = {' + string(0x1F776) + '}', 'SecsGlyphs = {' + string(0x1F77C) + '}']
    for name in Looks:
        shown, raw = picture(name)
        open(f'{out}/{name}.bin', 'wb').write(shown)
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')
    prepare(out, zx02)
    open(f'{out}/front.6502', 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(*sys.argv[1:])
