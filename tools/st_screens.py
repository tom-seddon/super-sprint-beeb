"""The ST's screens as PNGs (Phase 5, step 7): tools/st_trace_game.py's "shot" steps, each the screen the Shifter was
showing, in the palette it had. Usage: st_screens.py TRACE.json DIR   (DIR: where the .bin files are, and the PNGs go)
"""
import json, os, sys
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


def main(path, d):
    for name, e, raw in shots(path, d):
        idx = stgfx.planar_to_indices(raw, 320, 200)
        stgfx.indices_to_png(idx, stgfx.palette_from_words(e['palette']), f'{d}/{name}.png', scale=2)
        print(f'{name}: vbl {e["vbl"]}, base &{e["base"]:X}, {len(set(idx.ravel().tolist()))} colours')


if __name__ == '__main__':
    main(*sys.argv[1:])
