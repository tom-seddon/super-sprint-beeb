"""Record a real race on the ST with its objects: each frame's cars (as st_trace_cars.py) and every call of the
object drawing routines, with their arguments, for the renderer's objects.

Usage: st_trace_objects.py TRACK RACE OUT.json   (TRACK 0-7; RACE the race counter G_01EBC2, which decides the
hazards: barriers when (RACE + 1) % 3 == 0, oil-type hazards from race 6, the tornado from race 4 half the
time, cones from race 16 half the time)

A one-player game is started from the attract mode (the pokes in docs/st-logic.md section 0: the blue car on
the keyboard, accelerate held, no steering), the real race F_00C592's track argument and the race counter
poked at its entry. Each call of a drawing routine is logged by a breakpoint at its first instruction that
dumps 2 bytes at the routine's address (a marker) and the stack: the return address, then the arguments as
words. The sparks' state is dumped with their calls.
"""
import json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'build', 'trace')
RaceEntryStack = 0x21780                # a7 at F_00C592's entry in this run (deterministic): the track at +4
Routines = {0x1519C: 'car', 0x149B4: 'slot', 0x14A04: 'gate', 0x14A80: 'barrier', 0x147A0: 'tornado', 0x148BE: 'small',
            0x14B1C: 'spark', 0x146DA: 'heli', 0x152E0: 'explosion', 0x1440E: 'heli2', 0x144AA: 'heli3'}
Flip = [(0x1D30E, 2), (0x1E2CC, 8), (0x1E3A4, 8), (0x1E41C, 8), (0x1E424, 16), (0x1E354, 8), (0x1DFA8, 24),
        (0x1E3D4, 8), (0x1E37C, 8), (0x1E34C, 8)]
SparkState = [(0x1E090, 16), (0x1E0A0, 32)]


def record(track, race, vbls):
    ini = {'o0.ini': f'b VBL = 2000 :once :file {D}/o1.ini\nb pc = $C592 :once :file {D}/o2.ini\n',
           'o1.ini': 'w $1F200 0 0\nw $1DFFE 3\nc\n',
           'o2.ini': (f'w ${RaceEntryStack + 4:X} 00 {track:02x}\nw $1EBC2 00 {race:02x}\n'
                      f'b pc = $14D9C :quiet :file {D}/oflip.ini\n'
                      + ''.join(f'b pc = ${a:X} :quiet :file {D}/o_{n}.ini\n' for a, n in Routines.items())
                      + 'c\n'),
           'oflip.ini': ''.join(f'm ${a:X} {n}\n' for a, n in Flip) + 'c\n'}
    for a, n in Routines.items():
        extra = ''.join(f'm ${x:X} {k}\n' for x, k in SparkState) if n == 'spark' else ''
        ini[f'o_{n}.ini'] = f'm ${a:X} 2\nm a7 12\n{extra}c\n'
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    log = os.path.join(D, f'hatari_obj_t{track}_r{race}.log')
    with open(log, 'w') as f:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '600', '--parse', f'{D}/o0.ini',
                        '--run-vbls', str(vbls)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    return log


def parse(log):
    """-> frames, each {"mem": {addr: byte}, "calls": [(name, [args...], extra mem)]}, split at the flips."""
    frames, cur, pending = [], {'mem': {}, 'calls': []}, None
    for line in open(log, errors='replace'):
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a = int(m.group(1), 16)
        bs = [int(x, 16) for x in m.group(2).split()]
        if a in Routines and len(bs) == 2:
            pending = Routines[a]
            continue
        if pending:
            words = [bs[i] << 8 | bs[i + 1] for i in range(4, len(bs) - 1, 2)]
            cur['calls'].append([pending, words, {}])
            pending = None
            continue
        if a == Flip[0][0]:
            frames.append(cur)
            cur = {'mem': {}, 'calls': []}
        target = cur['calls'][-1][2] if cur['calls'] and a in (x for x, _ in SparkState) else cur['mem']
        for i, b in enumerate(bs):
            target[a + i] = b
    return frames


if __name__ == '__main__':
    track, race, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    os.makedirs(D, exist_ok=True)
    frames = parse(record(track, race, 7000))
    json.dump([{'mem': {str(k): v for k, v in f['mem'].items()},
                'calls': [[n, w, {str(k): v for k, v in e.items()}] for n, w, e in f['calls']]} for f in frames],
              open(path, 'w'))
    from collections import Counter
    print(len(frames), 'flips;', Counter(n for f in frames for n, _, _ in f['calls']))
