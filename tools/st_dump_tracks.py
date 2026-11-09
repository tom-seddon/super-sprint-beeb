"""Dump each track's finished background and masks from the ST original running in Hatari.

Usage: st_dump_tracks.py [--clean]   (writes build/gfx/bg_t<n>.bin, .npy and mask<k>_t<n>.npy for tracks 0-7)

The attract-mode race calls the race function F_00D1FA at VBL 2001 with the track as its argument, at &217A4.
A breakpoint there patches in the track wanted; another at &D218 saves the background (&59E36, 32,000 bytes)
and the three 1-bit masks after it (3 x 8,000): after the track set-up F_015FD6 and F_01C3E4, which draws
tracks 5, 6 and 7's skid marks into the background, and before the ST's HUD panels (F_014C1C).

--clean: the same, with the map's "TRACK n" and "DRONE LAP" cells replaced first (st_text_cells.py's words,
written into SUPER.DAT's copy in memory, loaded at &29500, as the track's argument is patched), so the ST draws
its trees over clean ground: build/gfx/bgclean_t<n>.npy and maskclean<k>_t<n>.npy, the others left as they are.
The map's bottom row as it was before the writes goes in mapclean_t<n>.bin, to check the address.
"""
import os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from stgfx import planar_to_indices
from st_tracks import MAP_OFF
from st_text_cells import ROW, cells as text_cells

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'build', 'gfx')


DatAddr = 0x29500                       # SUPER.DAT, loaded (docs/st-graphics.md)


def dump(t, words=None):
    """words: {column: map word} for the bottom row, written before the set-up (--clean); else the map as it is."""
    tag = 'clean' if words else ''
    row = DatAddr + MAP_OFF + t * 2000 + ROW * 80
    pokes = ''.join(f'w ${row + 2 * c:X} ${w >> 8:02X} ${w & 0xFF:02X}\n' for c, w in (words or {}).items())
    check = f'savebin {D}/map{tag}_t{t}.bin ${row:X} 80\n' if words else ''
    ini = {f'tb{tag}{t}.ini': f'b pc = $D1FA :once :file {D}/set{tag}{t}.ini\nb pc = $D218 :once :file {D}/dumpbg{tag}{t}.ini\n',
           f'set{tag}{t}.ini': f'{check}w $217A4 00 {t:02x}\n{pokes}c\n',
           f'dumpbg{tag}{t}.ini': f'savebin {D}/bg{tag}_t{t}.bin $59E36 56000\nc\n'}
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '60', '--parse', f'{D}/tb{tag}{t}.ini',
                    '--run-vbls', '2150'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if words:
        dat = open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read()
        was = open(f'{D}/map{tag}_t{t}.bin', 'rb').read()
        if was != dat[row - DatAddr:row - DatAddr + 80]:
            raise SystemExit(f'track {t + 1}: the map in memory at &{row:X} isn\'t SUPER.DAT\'s')
    b = open(f'{D}/bg{tag}_t{t}.bin', 'rb').read()
    np.save(f'{D}/bg{tag}_t{t}.npy', planar_to_indices(b[:32000], 320, 200))
    for k in range(3):
        m = np.unpackbits(np.frombuffer(b[32000 + 8000 * k:40000 + 8000 * k], np.uint8)).reshape(200, 320)
        np.save(f'{D}/mask{tag}{k}_t{t}.npy', m)


if __name__ == '__main__':
    os.makedirs(D, exist_ok=True)
    clean = '--clean' in sys.argv
    if clean:
        table = text_cells(open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read())
    for t in range(8):
        dump(t, {c: w for c, (w, n, k) in table[t].items()} if clean else None)
        print('track', t + 1)
