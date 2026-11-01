"""Make a 720K Atari ST floppy image (.st) holding the original game's files.

Usage: mkst.py <source dir> <out.st>

Copies every file in <source dir> to the root, and every subdirectory (AUTO) one level deep, as a
FAT12 disc in the ST's own 720K format: 80 tracks, 2 sides, 9 sectors, 2 sectors a cluster, 5 sectors
a FAT, 112 root entries. TOS 1.02 reads it directly, unlike Hatari's GEMDOS directory emulation.
"""
import struct, sys, time
from pathlib import Path

BPS, SPC, RES, NFATS, NDIRS, NSECTS, MEDIA, SPF, SPT, NSIDES = 512, 2, 1, 2, 112, 1440, 0xF9, 5, 9, 2
CLUSTER = BPS * SPC
ROOT_SECTORS = NDIRS * 32 // BPS
DATA_START = RES + NFATS * SPF + ROOT_SECTORS


def dos_name(name):
    stem, _, ext = name.upper().partition('.')
    assert len(stem) <= 8 and len(ext) <= 3, name
    return stem.ljust(8).encode('ascii') + ext.ljust(3).encode('ascii')


def dos_time(t):
    tm = time.localtime(t)
    return (tm.tm_hour << 11 | tm.tm_min << 5 | tm.tm_sec // 2,
            (tm.tm_year - 1980) << 9 | tm.tm_mon << 5 | tm.tm_mday)


def entry(raw_name, attr, cluster, size, mtime):
    t, d = dos_time(mtime)
    return raw_name + struct.pack('<B10xHHHI', attr, t, d, cluster, size)


class Disc:
    def __init__(self):
        self.img = bytearray(NSECTS * BPS)
        self.fat = [0] * (NSECTS // SPC)
        self.fat[0], self.fat[1] = 0xF00 | MEDIA, 0xFFF
        self.next = 2

    def alloc(self, data):
        """Store data in a run of clusters; return the first (0 for an empty file)."""
        if not data:
            return 0
        n = -(-len(data) // CLUSTER)
        first = self.next
        assert DATA_START + (first + n - 2) * SPC <= NSECTS, 'disc full'
        for c in range(first, first + n):
            self.fat[c] = c + 1 if c < first + n - 1 else 0xFFF
        off = (DATA_START + (first - 2) * SPC) * BPS
        self.img[off:off + len(data)] = data
        self.next += n
        return first

    def finish(self, root):
        b = self.img
        b[0:2] = b'\x60\x38'                    # BRA.S over the BPB, as TOS formats it
        b[2:8] = b'Loader'
        b[8:11] = b'\x12\x34\x56'               # serial
        struct.pack_into('<HBHBHHBHHHH', b, 11, BPS, SPC, RES, NFATS, NDIRS, NSECTS, MEDIA, SPF, SPT,
                         NSIDES, 0)
        fat = bytearray(SPF * BPS)
        for i in range(0, len(self.fat) - 1, 2):
            v = self.fat[i] | self.fat[i + 1] << 12
            fat[i * 3 // 2:i * 3 // 2 + 3] = v.to_bytes(3, 'little')
        for f in range(NFATS):
            off = (RES + f * SPF) * BPS
            b[off:off + len(fat)] = fat
        off = (RES + NFATS * SPF) * BPS
        assert len(root) <= ROOT_SECTORS * BPS
        b[off:off + len(root)] = root


def main(src, out):
    src = Path(src)
    disc = Disc()
    root = bytearray()
    for p in sorted(src.iterdir()):
        if p.name.startswith('.'):
            continue
        mtime = p.stat().st_mtime
        if p.is_dir():
            files = [q for q in sorted(p.iterdir()) if q.is_file() and not q.name.startswith('.')]
            # Place the directory's cluster first, then fill it in once its files have clusters.
            dir_cluster = disc.alloc(bytes(CLUSTER))
            body = entry(b'.          ', 0x10, dir_cluster, 0, mtime)
            body += entry(b'..         ', 0x10, 0, 0, mtime)
            for q in files:
                data = q.read_bytes()
                body += entry(dos_name(q.name), 0, disc.alloc(data), len(data), q.stat().st_mtime)
            assert len(body) <= CLUSTER
            off = (DATA_START + (dir_cluster - 2) * SPC) * BPS
            disc.img[off:off + len(body)] = body
            root += entry(dos_name(p.name), 0x10, dir_cluster, 0, mtime)
        else:
            data = p.read_bytes()
            root += entry(dos_name(p.name), 0, disc.alloc(data), len(data), mtime)
    disc.finish(root)
    Path(out).write_bytes(disc.img)
    used = (disc.next - 2) * CLUSTER
    print(f'{out}: {used} of {(NSECTS - DATA_START) * BPS} bytes used')


if __name__ == '__main__':
    main(*sys.argv[1:])
