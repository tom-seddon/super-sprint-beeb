"""The build's version, for the options screen's bottom right corner (Tom, 2026-11-09): the commit's first 5 hex
digits, and an "m" after them if the tree had changes (the small font has no "+"), in green.

Usage: version.py OUT VERSION   (the Makefile's VERSION: git's, or given, as tools/suite_remote.sh gives it; empty
                                 with no git, and nothing is shown)

Writes OUT/version.6502 (VersionGlyphs, the small font's glyphs ending in 255, VersionX, the first one's pixel
across, and VersionAscii, the version's characters ending in 0, for the crash handler's MODE 7 screen) and OUT/options_version.bin (the status line's 640 bytes with only the version drawn, as options.6502 draws
it: the glyphs ORed in white, then the bytes from VersionX's to the line's end ANDed with &0F, green), each only if
it's changed, so a build that doesn't change the version doesn't remake what reads them.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import st_frontend as F
from screens import text_on
from convert import mode1_bytes

Right = 314                             # the last glyph's end: a glyph's blank column, then the screen's edge


def write(path, data):
    if not os.path.exists(path) or open(path, 'rb').read() != data:
        open(path, 'wb').write(data)


def main(out, version):
    assert all(ch in '0123456789abcdefghijklmnopqrstuvwxyz' for ch in version), version
    canvas = F.Canvas(F.first_dump())
    codes = [canvas.code(ord(ch)) for ch in version]
    x = Right - 6 * len(version) if version else 320   # (320: none, and options.6502 draws nothing)
    lidx = np.zeros((200, 320), np.uint8)
    text_on(lidx, version.encode(), x, 192, colour=1)
    os.makedirs(out, exist_ok=True)
    write(f'{out}/version.6502', (f'\\\\ version.6502 - the build\'s version, "{version}" (tools/version.py)\n'
                                  f'VersionGlyphs = {{{", ".join(map(str, codes + [255]))}}}\n'
                                  f'VersionX = {x}\n'
                                  f'VersionAscii = {{{", ".join(str(ord(ch)) for ch in version + chr(0))}}}\n').encode())
    write(f'{out}/options_version.bin', mode1_bytes(lidx)[24 * 640:])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '')
