"""build/game.ssd's files as the game's ADFS disc, build/game.adl (D32), the files in the root, !BOOT run by SHIFT-BREAK
(*OPT 4,2). The game's loads go through OSFILE and name no filing system or directory, so nothing else differs.

ADFS L, 640K on two sides (Tom: double-sided drives can be assumed). ADFS numbers side 0's sectors first, tracks 0 to 79, then side 1's
(seen in jsbeeb: logical sector 22 read from side 0's track 1), so files end to end would fill side 0's first 44
tracks. Here they're split between the sides instead, each side's from its track 0, so the head travels about half
as far: side 1 has the attract mode's and options' pictures, then the boot's files, read only once; side 0 the
rest. jsbeeb's .adl image keeps the two sides' tracks interleaved, track 0 of side 0, then of side 1, and so on.
A *COPY to another disc puts the files end to end again: it works, but the layout's gone (*BACKUP keeps it).

Usage: adfs_disc.py [IN] [OUT]   (default build/game.ssd, build/game.adl; `make game` runs it)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs

Track = 16                              # sectors a track
SideSectors = 80 * Track                # a side's: 80 tracks
Root = 2                                # the root directory: 5 sectors
First = 7
Side1 = ['TRACKF', 'TRACKS', 'TRACKO', '!BOOT', 'SPRINT', 'SPRINTA', 'SPRINTB', 'SPRINTC', 'SPRINTD']   # side 1's, in order


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


def main(src='build/game.ssd', out='build/game.adl'):
    sides = 2
    sectors = sides * SideSectors
    img = dfs.read_image(src)
    logical = bytearray(sectors * 256)
    runs = [[First, SideSectors], [SideSectors, 2 * SideSectors]]   # each side's next free sector and its end
    names = [n for n in img.files if n not in Side1] + [n for n in Side1 if n in img.files]
    entries = []
    for name in names:
        f = img.files[name]
        run = runs[1 if name in Side1 else 0]
        at = run[0]
        logical[at * 256:at * 256 + len(f.data)] = f.data
        run[0] += (len(f.data) + 255) // 256
        assert run[0] <= run[1], f'{name}: no room'
        entries.append((name, f, at))
    assert len(entries) <= 47
    # the free space map: a run from the end of each side's files
    for i, (at, end) in enumerate(runs):
        logical[i * 3:i * 3 + 3] = at.to_bytes(3, 'little')
        logical[0x100 + i * 3:0x103 + i * 3] = (end - at).to_bytes(3, 'little')
    logical[0xFC:0xFF] = sectors.to_bytes(3, 'little')
    logical[0x1FB:0x1FD] = (0x5350).to_bytes(2, 'little')  # the disc's id
    logical[0x1FD] = 2                                     # *OPT 4,2
    logical[0x1FE] = 3 * len(runs)                         # the list's end
    logical[0xFF] = checksum(logical[0:256])
    logical[0x1FF] = checksum(logical[256:512])
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
    logical[Root * 256:Root * 256 + 1280] = d
    # the image: the sides' tracks interleaved, as jsbeeb's .adl
    disc = bytearray(len(logical))
    for n in range(sectors):
        side, rest = divmod(n, SideSectors)
        track, sector = divmod(rest, Track)
        p = (track * sides + side) * Track + sector
        disc[p * 256:p * 256 + 256] = logical[n * 256:n * 256 + 256]
    open(out, 'wb').write(disc)
    used = ', '.join(f'side {i} to track {(at - i * SideSectors - 1) // Track}' for i, (at, _) in enumerate(runs))
    print(f'{out}: {len(entries)} files, {used}')


if __name__ == '__main__':
    main(*sys.argv[1:])
