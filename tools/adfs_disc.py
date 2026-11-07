"""build/game.ssd's files as an ADFS M disc, build/game.adf, for a load's time on ADFS and step 11's trials: 320K on one side, so sectors are in order in
the image, the files in the root in the order the DFS disc has them, !BOOT run by SHIFT-BREAK (*OPT 4,2). The game's loads go through OSFILE and name no
filing system, so nothing else differs.

Usage: adfs_disc.py [IN] [OUT]   (default build/game.ssd, build/game.adf)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs

Sectors = 1280                          # 80 tracks of 16 sectors
Root = 2                                # the root directory: 5 sectors
First = 7


def checksum(sector):
    """An old map sector's last byte."""
    total = 255
    for b in reversed(sector[:255]):
        if total > 255:
            total = (total & 255) + 1
        total += b
    return total & 255


def address(a):
    """A catalogue's 18 bits to ADFS's 32."""
    return a | 0xFFFC0000 if a >> 16 & 3 == 3 else a


def main(src='build/game.ssd', out='build/game.adf'):
    img = dfs.read_image(src)
    disc = bytearray(Sectors * 256)
    at, entries = First, []
    for name, f in img.files.items():
        entries.append((name, f, at))
        n = (len(f.data) + 255) // 256
        disc[at * 256:at * 256 + len(f.data)] = f.data
        at += n
    assert len(entries) <= 47 and at < Sectors
    # the free space map: one run, from the end of the files
    disc[0:3] = at.to_bytes(3, 'little')
    disc[0xFC:0xFF] = Sectors.to_bytes(3, 'little')
    disc[0x100:0x103] = (Sectors - at).to_bytes(3, 'little')
    disc[0x1FB:0x1FD] = (0x5350).to_bytes(2, 'little')  # the disc's id
    disc[0x1FD] = 2                                     # *OPT 4,2
    disc[0x1FE] = 3                                     # one run: the list's end
    disc[0xFF] = checksum(disc[0:256])
    disc[0x1FF] = checksum(disc[256:512])
    # the root: "Hugo", 26 bytes an entry in name order, then its tail
    d = bytearray(1280)
    d[1:5] = b'Hugo'
    for i, (name, f, start) in enumerate(sorted(entries, key=lambda e: e[0].upper())):
        e = 5 + i * 26
        raw = name.encode().ljust(10, b'\r')[:10]
        d[e:e + 10] = raw
        d[e] |= 0x80                    # readable,
        d[e + 1] |= 0x80                # writable
        d[e + 10:e + 14] = address(f.load).to_bytes(4, 'little')
        d[e + 14:e + 18] = address(f.exec_addr if hasattr(f, 'exec_addr') else f.exec).to_bytes(4, 'little')
        d[e + 18:e + 22] = len(f.data).to_bytes(4, 'little')
        d[e + 22:e + 25] = start.to_bytes(3, 'little')
    d[0x4CC:0x4CD] = b'$'
    d[0x4CD:0x4D6] = b'\r' * 9
    d[0x4D6:0x4D9] = Root.to_bytes(3, 'little')
    d[0x4D9:0x4E5] = b'Super Sprint'
    d[0x4FB:0x4FF] = b'Hugo'
    disc[Root * 256:Root * 256 + 1280] = d
    open(out, 'wb').write(disc)
    print(f'{out}: {len(entries)} files, {at} sectors of {Sectors}')


if __name__ == '__main__':
    main(*sys.argv[1:])
