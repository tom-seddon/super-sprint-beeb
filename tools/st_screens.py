"""The ST's screens as PNGs (Phase 5, step 7): tools/st_trace_game.py's "shot" steps, each the screen the Shifter was
showing, in its palettes: the front end's screens change palette down the screen (xbios_010070). Usage: st_screens.py TRACE.json DIR   (DIR: where the .bin files are, and the PNGs go)
"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import stgfx
import st_trace_game as G


def shots(path, d):
    t = json.load(open(path))
    for e in t['events']:
        if e['kind'] != 'step' or 'shot' not in t['script']['steps'][e['index']]:
            continue
        name = t['script']['steps'][e['index']]['shot']
        which = G.Screens.index(e['base']) if e['base'] in G.Screens else None
        if which is None:
            print(f'{name}: base &{e["base"]:X}: neither screen')
            continue
        yield name, e, open(f'{d}/{name}_{which}.bin', 'rb').read()


def bands(e):
    """[(first line, 16 palette words)]: xbios_010070's raster, if it's on: a palette, and at each line count (2 lines
    a count, Timer B) the next, until a count of &FF; else the palette in the Shifter."""
    if not e.get('rasterOn'):
        return [(0, e['palette'])]
    base, tab = G.Palettes[0], bytes(e['tables'])
    word = lambda a: tab[a - base] << 8 | tab[a - base + 1]
    pal, lines = e['raster']
    out, y = [], 0
    for k in range(8):
        out.append((y, [word(pal + 32 * k + 2 * i) for i in range(16)]))
        n = word(lines + 2 * k)
        if n >= 0xFF:
            break
        y += 2 * n
    return out


def rgb(idx, e):
    """A screen's indices as the Shifter shows them: (200, 320, 3)."""
    out = np.zeros(idx.shape + (3,), np.uint8)
    b = bands(e)
    for k, (y, words) in enumerate(b):
        end = b[k + 1][0] if k + 1 < len(b) else 200
        out[y:end] = np.array(stgfx.palette_from_words(words), np.uint8)[idx[y:end]]
    return out


def main(path, d):
    for name, e, raw in shots(path, d):
        idx = stgfx.planar_to_indices(raw, 320, 200)
        Image.fromarray(rgb(idx, e)).resize((640, 400), Image.NEAREST).save(f'{d}/{name}.png')
        print(f'{name}: vbl {e["vbl"]}, base &{e["base"]:X}, raster {"on" if e.get("rasterOn") else "off"}, bands from {[y for y, w in bands(e)]}')


if __name__ == '__main__':
    main(*sys.argv[1:])
