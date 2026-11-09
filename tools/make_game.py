"""The game's disc (Phase 5, 3b): track 1's play build as it boots, and a file for each track, TRACK1 to TRACK8,
holding that track's slots (tools/track_slots.py: the only bytes the tracks' builds differ in), each part ZX02
packed, for src/load.6502 to load between races.

Usage: make_game.py DIR ZX02 OUT.ssd   (DIR: tools/all_tracks.sh's build/tracks, t0.ssd .. t7.ssd and their
listings; ZX02: the compressor, built from the beeb-port-kit's source). Also writes OUT_slots.json, every
track's slots as its build has them, for tools/load_check.mjs.

A track's file: a byte, the parts' count; 6 bytes a part (where: 0-3 the bank, as bankbg on, | &80 ANDY, or
&40 Shared; its address, low and high; its stream's offset in the file, low and high; 0); then the streams.
Each stream is round-tripped through the kit's zx02.py before it's written, and the file must fit below the load's code.

A bank's file that ends in a slot (SPRINTA in the background, SPRINTB in the priority cells) ends where the slot
starts instead: every race loads its track's file first, and until then nothing reads it (game_go's code goes over
SPRINTA's at the boot, prepare's file is parked in SPRINTB's). The boot copies the whole 16K regardless.
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import track_slots as T
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs                                      # the kit's .ssd reader and writer, and its compress (used in place)

FileAddr = 0x4200                               # load.6502's TrackFileAddr
CodeOrg = 0x7C00                                # and LoadCodeOrg: a file must end below it
Where = {'BgBank': 0, 'CarsBank': 1, 'TraceBank': 2, 'ObjBank': 3, 'Andy': 0x80 | 2, 'Shared': 0x40}


def slots(d, n):
    """Track n's slots: [(name, section, address, bytes)]."""
    files = dfs.read_image(f'{d}/t{n}.ssd').files
    _, at = T.listing(f'{d}/t{n}.lst')
    out = []
    for name, (sec, a) in sorted(at.items(), key=lambda kv: kv[1][1]):
        if not name.endswith('Slot') or name + 'End' not in at:
            continue
        e = at[name + 'End'][1]
        if sec in ('BgBank', 'CarsBank', 'TraceBank', 'ObjBank'):
            f, off = {v: k for k, v in T.Files.items()}[sec], a - 0x8000
        elif sec == 'Shared':
            f, off = 'SPRINT', a - 0x3000
        elif sec == 'Andy':
            f, off = 'SPRINT', at['andy_image'][1] - 0x3000 + a - 0x8000
        else:
            sys.exit(f'{name}: a slot in {sec}, which the loader can\'t reach')
        out.append((name, sec, a, files[f].data[off:off + e - a]))
    return out


def cut(files, parts):
    """files' banks' files that end in a slot cut where it starts (each slot's end the file's end, latest first)."""
    bank = {v: k for k, v in T.Files.items()}
    for name, sec, a, raw in sorted(parts, key=lambda p: -p[2]):
        f = bank.get(sec)
        if f and a - 0x8000 + len(raw) == len(files[f].data):
            print(f'{f}: {len(files[f].data):,} bytes cut to {a - 0x8000:,}, at {name} (a track file\'s)')
            files[f].replace(files[f].data[:a - 0x8000])


def track_file(d, n, zx02):
    parts = slots(d, n)
    streams = [dfs.compress(raw, exe=zx02, name=f'track {n + 1} {name}') for name, _, _, raw in parts]
    head = bytearray([len(parts)])
    off = 1 + 6 * len(parts)
    for (name, sec, a, raw), s in zip(parts, streams):
        head += bytes([Where[sec], a & 255, a >> 8, off & 255, off >> 8, 0])
        off += len(s)
    data = bytes(head) + b''.join(streams)
    if FileAddr + len(data) > CodeOrg:
        sys.exit(f'TRACK{n + 1}: {len(data)} bytes, over the load\'s code at &{CodeOrg:04X}')
    return data, [(name, len(raw), len(s)) for (name, _, _, raw), s in zip(parts, streams)]


def main(d, zx02, out):
    img = dfs.read_image(f'{d}/t0.ssd')
    files = dict(img.files)
    want = [[{'name': name, 'section': sec, 'address': a, 'bytes': raw.hex()} for name, sec, a, raw in slots(d, n)]
            for n in range(8)]
    json.dump(want, open(os.path.splitext(out)[0] + '_slots.json', 'w'))   # (tools/load_check.mjs's answers)
    cut(files, slots(d, 0))
    for n in range(8):
        data, sizes = track_file(d, n, zx02)
        files[f'TRACK{n + 1}'] = dfs.Entry(f'TRACK{n + 1}', data, 0xFF0000 | FileAddr, 0xFF0000, '$', False)
        print(f'TRACK{n + 1}: {len(data):,} bytes ({sum(r for _, r, _ in sizes):,} unpacked): '
              + ', '.join(f'{k} {r}/{p}' for k, r, p in sizes))
    # the files read between races first, next to the catalogue, as DFS goes back to it for each: those read together as a race ends, then the tracks
    first = ['TRACKP', 'TRACKU', 'TRACKC'] + [f'TRACK{n + 1}' for n in range(8)]
    disc = dfs.build_image(files, layout=first + [f for f in img.files if f not in first], title=img.title, cycle=img.cycle, opt=img.opt)
    open(out, 'wb').write(disc)
    used = sum((len(f.data) + 255) // 256 for f in files.values())
    print(f'{out}: {len(files)} files of 31, {used} sectors of {dfs.TOTAL_SECTORS} '
          f'({used * 256:,} bytes), sha256 {hashlib.sha256(disc).hexdigest()[:16]}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
