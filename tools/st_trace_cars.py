"""Record what the ST draws of the four cars each frame of an attract-mode race, for the renderer's tests.

Usage: st_trace_cars.py TRACK OUT.json   (TRACK 0-7; about 30 s)

The attract race F_00D1FA is entered at VBL 2001 with the track at &217A4 (as st_dump_tracks.py patches it).
A breakpoint on the flip (&14D9C) then dumps, each frame: the frame counter G_01D30E, the draw order G_01E2CC,
and per car the flags G_01E3A4, facing G_01E41C and pixel position G_01E42C/G_01E424 (the sprite box's
top-left). The demo draws every car in its player colours, so the sprite frame is car * 16 + facing.
The output is a list of frames, each {"frame", "order", "cars": [[x, y, facing, flags], ...]}.
"""
import json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'build', 'trace')
Dumps = [(0x1D30E, 2), (0x1E2CC, 8), (0x1E3A4, 8), (0x1E41C, 8), (0x1E424, 16), (0x1E354, 8), (0x1DFA8, 24)]


def record(track, vbls=5200):
    ini = {'tr.ini': f'b pc = $D1FA :once :file {D}/set.ini\n',
           'set.ini': f'w $217A4 00 {track:02x}\nb pc = $14D9C :quiet :file {D}/flip.ini\nc\n',
           'flip.ini': ''.join(f'm ${a:X} {n}\n' for a, n in Dumps) + 'c\n'}
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    log = os.path.join(D, f'hatari_t{track}.log')
    with open(log, 'w') as f:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '120', '--parse', f'{D}/tr.ini',
                        '--run-vbls', str(vbls)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    return log


def parse(log):
    frames, cur = [], None
    for line in open(log, errors='replace'):
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a = int(m.group(1), 16)
        bs = [int(x, 16) for x in m.group(2).split()]
        if a == Dumps[0][0]:
            cur = {}
            frames.append(cur)
        if cur is not None:
            for i, b in enumerate(bs):
                cur[a + i] = b
    word = lambda f, a: f[a] << 8 | f[a + 1]
    out = []
    for f in frames:
        if any(a + i not in f for a, n in Dumps for i in range(n)):
            continue
        out.append({'frame': word(f, 0x1D30E),
                    'order': [word(f, 0x1E2CC + 2 * i) for i in range(4)],
                    'cars': [[word(f, 0x1E42C + 2 * c), word(f, 0x1E424 + 2 * c), word(f, 0x1E41C + 2 * c),
                              word(f, 0x1E3A4 + 2 * c)] for c in range(4)],
                    'laps': [word(f, 0x1E354 + 2 * c) for c in range(4)],
                    'scores': [bytes(f[0x1DFA8 + 6 * c + i] for i in range(6)).hex() for c in range(4)]})
    # the race's own frames: the longest run of the counter counting up by one a flip
    runs, run = [], [out[0]]
    for f in out[1:]:
        if f['frame'] == run[-1]['frame'] + 1:
            run.append(f)
        else:
            runs.append(run)
            run = [f]
    runs.append(run)
    race = max(runs, key=len)
    return race


if __name__ == '__main__':
    track, path = int(sys.argv[1]), sys.argv[2]
    os.makedirs(D, exist_ok=True)
    race = parse(record(track))
    json.dump(race, open(path, 'w'))
    print(f'track {track + 1}: {len(race)} frames, {race[0]["frame"]} to {race[-1]["frame"]}')
