"""The front end's pictures and tables for the game (Phase 5, step 8): build/gen/front.6502, the screens' modes, palettes and
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

# G_01DD82's levels: a mask of 8 pixels a line, 8 lines. (Its first two are all set, and its last two clear)
Levels = [[0xFF] * 8, [0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E], [0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C],
          [0x18, 0x3C, 0x7E, 0xFF, 0xFF, 0x7E, 0x3C, 0x18], [0, 0x18, 0x3C, 0x7E, 0x7E, 0x3C, 0x18, 0],
          [0, 0, 0x18, 0x3C, 0x3C, 0x18, 0, 0], [0, 0, 0, 0x18, 0x18, 0, 0, 0], [0] * 8]
Looks = {'title': dict(mode=2, table=O.TitleChecked)}    # (Tom, 2026-11-04: option 7, MODE 2 checked; he may change his mind)


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


def picture(name):
    look = Looks[name]
    idx = T.decode_map(F.dat(), 8)
    assert look['mode'] == 2
    return O.mode2_bytes(O.mapped(idx, look['table']))


def main(out, zx02):
    lines = ['\\\\ front.6502 - the front end\'s tables (tools/screens.py)', 'Mode1Wipe = {' + ', '.join(map(str, table(mask1))) + '}',
             'Mode2Wipe = {' + ', '.join(map(str, table(mask2))) + '}']
    for name in Looks:
        raw = picture(name)
        open(f'{out}/{name}.bin', 'wb').write(raw)
        packed = dfs.compress(raw, exe=zx02, name=name)
        open(f'{out}/{name}.zx02', 'wb').write(packed)
        print(f'{name}: {len(packed):,} bytes packed')
    open(f'{out}/front.6502', 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(*sys.argv[1:])
