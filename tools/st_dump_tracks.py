"""Dump each track's finished background and masks from the ST original running in Hatari.

Usage: st_dump_tracks.py   (writes build/gfx/bg_t<n>.bin, .npy and mask<k>_t<n>.npy for tracks 0-7)

The attract-mode race calls the race function F_00D1FA at VBL 2001 with the track as its argument, at &217A4.
A breakpoint there patches in the track wanted; another at &D20A, where the track set-up F_015FD6 returns,
saves the background (&59E36, 32,000 bytes) and the three 1-bit masks after it (3 x 8,000).
"""
import os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from stgfx import planar_to_indices

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'build', 'gfx')


def dump(t):
    ini = {f'tb{t}.ini': f'b pc = $D1FA :once :file {D}/set{t}.ini\nb pc = $D20A :once :file {D}/dumpbg{t}.ini\n',
           f'set{t}.ini': f'w $217A4 00 {t:02x}\nc\n',
           f'dumpbg{t}.ini': f'savebin {D}/bg_t{t}.bin $59E36 56000\nc\n'}
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '60', '--parse', f'{D}/tb{t}.ini',
                    '--run-vbls', '2150'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    b = open(f'{D}/bg_t{t}.bin', 'rb').read()
    np.save(f'{D}/bg_t{t}.npy', planar_to_indices(b[:32000], 320, 200))
    for k in range(3):
        m = np.unpackbits(np.frombuffer(b[32000 + 8000 * k:40000 + 8000 * k], np.uint8)).reshape(200, 320)
        np.save(f'{D}/mask{k}_t{t}.npy', m)


if __name__ == '__main__':
    os.makedirs(D, exist_ok=True)
    for t in range(8):
        dump(t)
        print('track', t + 1)
