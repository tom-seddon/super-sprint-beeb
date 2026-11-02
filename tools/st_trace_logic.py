"""Record a real race's logic on the ST, frame by frame, for the BBC's logic oracle (D9, docs/brief-phase4.md).

Usage: st_trace_logic.py TRACK RACE SCRIPT OUT.json   (`make logictrace`; TRACK 0-7; RACE the race counter G_01EBC2; SCRIPT a
JSON list of [when, keys]: from the flip at which `when` comes true, the blue car's keyboard holds `keys`,
any of "L" (A), "R" (D) and "A" (left shift), until the next entry's `when`. `when` is a frame counter
G_01D30E (a number), or a comparison of car 0's pixel x, pixel y or facing with a number, "x<60", "y>150",
"f=8": an autopilot, each entry's breakpoint armed by the one before)

A one-player game is started from the attract mode as st_trace_objects.py does (the blue car on the keyboard),
the real race F_00C592's track and race counter poked at its entry. Logged:
- at each flip (&14D9C): the frame counter, the coasting phase G_01D178, every per-car variable
  (G_01E2A0-G_01E437), the scores G_01DFA8, and the pickups' state G_01EB54-G_01EB6F;
- each human car's input, as F_010CF2 returned it to F_00DC4C (at &DC64: d0, and the car at a6 + 8);
- each XBIOS Random result F_00ADB8 draws (at &ADC4: d0), and F_00ADB8's n (a6 + 8).
The script's key changes are one-shot breakpoints on the flip, each one's file setting the next (Hatari 2.6.1
aborts with 16 breakpoints set).

The output: {"track", "race", "script", "frames": [{"frame", "phase", "mem": {addr: byte}, "inputs":
[[car, bits], ...], "random": [[n, value], ...]}, ...]}. A frame's inputs and random numbers are those drawn
before its flip, so they pair with the state dumped at that flip.
"""
import json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'build', 'trace')
RaceEntryStack = 0x21780                # a7 at F_00C592's entry in this run (as st_trace_objects.py)
FlipPc, InputPc, RandomPc = 0x14D9C, 0xDC64, 0xADC4
Frame = 0x1D30E
Dumps = [(Frame, 2), (0x1D178, 2), (0x1E2A0, 0x198), (0x1DFA8, 24), (0x1EB54, 0x1C)]
Keys = {'L': 0x1DFF2, 'R': 0x1DFF4, 'A': 0x1DFFE}


Car0 = {'x': 0x1E42C, 'y': 0x1E424, 'f': 0x1E41C}


def condition(when):
    if isinstance(when, int):
        return f'(${Frame:X}).w = ${when:X}'
    m = re.fullmatch(r'([xyf])([<>=])(\d+)', when)
    return f'(${Car0[m.group(1)]:X}).w {m.group(2)} ${int(m.group(3)):X}'


def record(track, race, script, vbls):
    ev = lambda k: os.path.join(D, f'lev{k}.ini')
    def arm(k):
        if k >= len(script):
            return ''
        return f'b pc = ${FlipPc:X} && {condition(script[k][0])} :once :file {ev(k)}\n'
    ini = {'l0.ini': f'b VBL = 2000 :once :file {D}/l1.ini\nb pc = $C592 :once :file {D}/l2.ini\n',
           'l1.ini': 'w $1F200 0 0\nw $1DFFE 3\nc\n',
           'l2.ini': (f'w ${RaceEntryStack + 4:X} 0 {track}\nw $1EBC2 0 {race}\n'
                      + ''.join(f'w ${a:X} 0\n' for a in Keys.values())
                      + f'b pc = ${FlipPc:X} :quiet :file {D}/lflip.ini\n'
                      f'b pc = ${InputPc:X} :quiet :file {D}/linput.ini\n'
                      f'b pc = ${RandomPc:X} :quiet :file {D}/lrandom.ini\n'
                      + arm(0) + 'c\n'),
           'lflip.ini': ''.join(f'm ${a:X} {n}\n' for a, n in Dumps) + 'c\n',
           'linput.ini': 'r\nm a6 10\nc\n',
           'lrandom.ini': 'r\nm a6 10\nc\n'}
    for k, (frame, keys) in enumerate(script):
        ini[f'lev{k}.ini'] = (''.join(f'w ${a:X} {3 if c in keys else 0}\n' for c, a in Keys.items())
                              + arm(k + 1) + 'c\n')
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    log = os.path.join(D, f'hatari_logic_t{track}_r{race}.log')
    with open(log, 'w') as f:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '900', '--parse', f'{D}/l0.ini',
                        '--run-vbls', str(vbls)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    return log


def parse(log):
    """-> frames as in the module's doc. Each breakpoint's report starts "CPU=$pc"; "r" gives d0, and the
    input's and random number's "m a6" the routine's argument at a6 + 8, told apart by the "Next PC" line
    (the "CPU=" headers can't be trusted: one sometimes heads another breakpoint's dumps). The inputs and
    random numbers drawn since the last flip go with the next flip's dumps."""
    frames, kind, d0, a6, inputs, random = [], None, None, None, [], []
    for line in open(log, errors='replace'):
        r = re.search(r'\bD0 ([0-9A-F]{8})', line)
        if r:
            d0 = int(r.group(1), 16)
            continue
        r = re.search(r'\bA6 ([0-9A-F]{8})', line)
        if r:
            a6 = int(r.group(1), 16)
            continue
        n = re.match(r'^Next PC: ([0-9a-f]{8})', line)
        if n:
            kind = {InputPc + 4: 'input', RandomPc + 2: 'random'}.get(int(n.group(1), 16))
            continue
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a = int(m.group(1), 16)
        bs = [int(x, 16) for x in m.group(2).split()]
        if kind and a == a6:
            arg = bs[8] << 8 | bs[9]
            if kind == 'input':
                inputs.append([arg, d0 & 0xFF])
            else:
                random.append([arg, d0])
            kind = None
            continue
        if a == Frame:
            frames.append({'mem': {}, 'inputs': inputs, 'random': random})
            inputs, random = [], []
        if frames:
            for i, b in enumerate(bs):
                frames[-1]['mem'][a + i] = b
    for f in frames:
        f['frame'] = f['mem'][Frame] << 8 | f['mem'][Frame + 1]
        f['phase'] = f['mem'][0x1D178] << 8 | f['mem'][0x1D179]
    return frames


RandomMul = 3141592621                  # TOS's XBIOS Random: seed = seed * this + 1, the result (seed >> 8) & &FFFFFF


def race(frames):
    """The race: the longest run of consecutive frame counters."""
    runs = [[frames[0]]]
    for f in frames[1:]:
        if f['frame'] == runs[-1][-1]['frame'] + 1:
            runs[-1].append(f)
        else:
            runs.append([f])
    return max(runs, key=len)


def seed(values):
    """The generator's state before the first of `values`, checking every one follows from it."""
    inv = pow(RandomMul, -1, 1 << 32)
    for low in range(256):
        s = values[0] << 8 | low
        t = s
        for v in values[1:]:
            t = (t * RandomMul + 1) & 0xFFFFFFFF
            if (t >> 8) & 0xFFFFFF != v:
                break
        else:
            return ((s - 1) * inv) & 0xFFFFFFFF
    sys.exit('the random numbers are not one run of TOS\'s generator')


if __name__ == '__main__':
    track, race_no, script, path = int(sys.argv[1]), int(sys.argv[2]), json.load(open(sys.argv[3])), sys.argv[4]
    os.makedirs(D, exist_ok=True)
    frames = race(parse(record(track, race_no, script, int(os.environ.get('VBLS', 6000)))))
    values = [v for f in frames for n, v in f['random']]
    json.dump({'track': track, 'race': race_no, 'script': script, 'seed': seed(values),
               'frames': [{'frame': f['frame'], 'phase': f['phase'], 'inputs': f['inputs'], 'random': f['random'],
                           'mem': {str(k): v for k, v in f['mem'].items()}} for f in frames]}, open(path, 'w'))
    print(f'{len(frames)} frames, {frames[0]["frame"]} to {frames[-1]["frame"]};',
          sum(len(f['inputs']) for f in frames), 'inputs;', len(values), 'random numbers, one run of TOS\'s generator')
