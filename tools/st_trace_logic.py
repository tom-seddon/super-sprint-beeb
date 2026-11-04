"""Record a real race's logic on the ST, frame by frame, for the BBC's logic oracle (D9, docs/brief-phase4.md).

Usage: st_trace_logic.py TRACK RACE SCRIPT OUT.json [FORCE]   (`make logictrace`; TRACK 0-7; RACE the race counter
G_01EBC2; SCRIPT a JSON list of [when, keys]: from the flip at which `when` comes true, the blue car's keyboard
holds `keys`, any of "L" (A), "R" (D) and "A" (left shift), until the next entry's `when`; or `keys` by car,
{"1": "LA", "2": "R"}: the cars the first entry names join the game (car 0 by the keyboard, 1 and 2 by the
joysticks' bytes), the rest are drones. `when` is a frame
counter G_01D30E (a number), or a comparison of car 0's pixel x, pixel y or facing with a number, "x<60",
"y>150", "f=8": an autopilot, each entry's breakpoint armed by the one before. An entry's third item, if any,
[[car, x, y, facing], ...]: those cars put there, stopped, at that flip (the logic's only: not for
tools/st_trace_objects.py; tools/disc_races.mjs does the same to the BBC). SCRIPT "-": accelerate held from
the attract mode on, as tools/st_trace_objects.py drives a race without one, so the two record the same race.
FORCE: "tornado", "cones" or both, joined by commas: their coin flips forced, as st_trace_objects.py's)

A game is started from the attract mode as st_trace_objects.py does (the blue car on the keyboard, the others
as the script says),
the real race F_00C592's track and race counter poked at its entry. Logged:
- at each flip (&14D9C): the frame counter, the coasting phase G_01D178, every per-car variable
  (G_01E2A0-G_01E437), the scores G_01DFA8, the pickups' state G_01EB54-G_01EB6F, the sparks G_01E070-
  G_01E0BF, the helicopter G_01EB28-G_01EB35 and the banner G_01EB88-G_01EB8D;
- each human car's input, as F_010CF2 returned it to F_00DC4C (at &DC64: d0, and the car at a6 + 8);
- each XBIOS Random result F_00ADB8 draws (at &ADC4: d0), and F_00ADB8's n (a6 + 8);
- the track's hazards: G_01EB36-G_01EBC1 whole (the oil-type hazards' places, the pickups, the gates, the banner,
  the barriers, the tornado, the cones), and each gate's and pop-up barrier's box of mask B (&63A76 on: 6 bytes x
  16 lines, 2 x 8), which they write as they move;
- the attribute map (&678F6), which the hazards, cones and pickups change.
The script's key changes are one-shot breakpoints on the flip, each one's file setting the next (Hatari 2.6.1
aborts with 16 breakpoints set).

The output: {"track", "race", "script", "frames": [{"frame", "phase", "mem": {addr: byte}, "inputs":
[[car, bits], ...], "random": [[n, value], ...]}, ...]}. A frame's inputs and random numbers are those drawn
before its flip, so they pair with the state dumped at that flip.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.environ.get('TRACEDIR') or os.path.join(ROOT, 'build', 'trace')    # (Hatari's scripts and log: one each, to run several at once)
RaceEntryStack = 0x21780                # a7 at F_00C592's entry in this run (as st_trace_objects.py)
FlipPc, InputPc, RandomPc = 0x14D9C, 0xDC64, 0xADC4
Frame = 0x1D30E
AttrMap = 0x678F6                       # the attribute map (G_01EB20's), 40 x 25
Dumps = [(Frame, 2), (0x1D178, 2), (0x1E2A0, 0x198), (0x1DFA8, 24), (0x1EB36, 0x8C), (0x1E070, 0x50), (0x1EB28, 0xE),
         (AttrMap, 1000)]
MaskB = 0x63A76                         # mask B (G_01F238 + &1F40): 40 bytes a line


def boxes(track):
    """The track's gates' and barriers' boxes of mask B: [(address, bytes)], a line each."""
    import logic_maps as M
    ng, gp = M.words(M.tb(0x1ED88)), M.words(M.tb(0x1ED98), False)
    bp = M.words(M.tb(0x1EC00), False)
    out = []
    for off, w, h in [(gp[track + i], 6, 16) for i in range(ng[track])] + [(bp[track * 3 + i], 2, 8) for i in range(3)]:
        out += [(MaskB + off // 4 + 40 * r, w) for r in range(h)]
    return out
Keys = {'L': 0x1DFF2, 'R': 0x1DFF4, 'A': 0x1DFFE}
Joy = {1: 0x1DFD2, 2: 0x1DFD3}          # cars 1 and 2: joystick 0 and 1's bytes (G_01DFCC's devices 2 and 3)


def humans(script):
    """The cars a script drives: its first entry's, if its keys are by car; else car 0."""
    return sorted(map(int, script[0][1])) if script and isinstance(script[0][1], dict) else [0]


def press(keys):
    """An entry's keys as Hatari's writes: a string, car 0's; or by car, {"0": "LA", "2": "R"}."""
    out = ''
    for car, k in ({'0': keys} if isinstance(keys, str) else keys).items():
        if car == '0':
            out += ''.join(f'w ${a:X} {3 if c in k else 0}\n' for c, a in Keys.items())
        else:
            out += f'w ${Joy[int(car)]:X} {4 * ("L" in k) + 8 * ("R" in k) + 128 * ("A" in k)}\n'
    return out


def join(script):
    """The attract mode's pokes: the copy protection off, and fire held by each car that's to join."""
    who = humans(script)
    return ('w $1F200 0 0\n' + ('w $1DFFE 3\n' if 0 in who else '')
            + ''.join(f'w ${Joy[c]:X} 128\n' for c in who if c) + 'c\n')


def release(script):
    """At the race's entry: every key the script drives up."""
    return press({str(c): '' for c in humans(script)}) if script else ''


Car0 = {'x': 0x1E42C, 'y': 0x1E424, 'f': 0x1E41C}


def place(cars):
    """An entry's third item as Hatari's writes: each [car, x, y, facing], stopped there."""
    out = ''
    for c, x, y, f in cars:
        for a, v in ((0x1E42C, x), (0x1E424, y), (0x1E3FC, x * 8), (0x1E3F4, y * 8), (0x1E41C, f), (0x1E414, f), (0x1E404, 0)):
            out += f'w ${a + 2 * c:X} {v >> 8} {v & 255}\n'
    return out


def condition(when):
    if isinstance(when, int):
        return f'(${Frame:X}).w = ${when:X}'
    m = re.fullmatch(r'([xyf])([<>=])(\d+)', when)
    return f'(${Car0[m.group(1)]:X}).w {m.group(2)} ${int(m.group(3)):X}'


def record(track, race, script, vbls, force=()):
    ev = lambda k: os.path.join(D, f'lev{k}.ini')
    def arm(k):
        if k >= len(script):
            return ''
        return f'b pc = ${FlipPc:X} && {condition(script[k][0])} :once :file {ev(k)}\n'
    import st_trace_objects as O
    force = sorted(force, key=('tornado', 'cones').index)
    setbp = lambda f: f'b pc = ${O.Force[f][0]:X} :once :file {D}/lf_{f}.ini\n'
    ini = {'l0.ini': f'b VBL = 2000 :once :file {D}/l1.ini\nb pc = $C592 :once :file {D}/l2.ini\n',
           'l1.ini': join(script),
           'l2.ini': (f'w ${RaceEntryStack + 4:X} 0 {track}\nw $1EBC2 0 {race}\n'
                      + release(script)
                      + (setbp(force[0]) if force else '')
                      + f'b pc = ${FlipPc:X} :quiet :file {D}/lflip.ini\n'
                      f'b pc = ${InputPc:X} :quiet :file {D}/linput.ini\n'
                      f'b pc = ${RandomPc:X} :quiet :file {D}/lrandom.ini\n'
                      + arm(0) + 'c\n'),
           'lflip.ini': ''.join(f'm ${a:X} {n}\n' for a, n in Dumps + boxes(track)) + 'c\n',
           'linput.ini': 'r\nm a6 10\nc\n',
           'lrandom.ini': 'r\nm a6 10\nc\n'}
    for k, entry in enumerate(script):
        ini[f'lev{k}.ini'] = press(entry[1]) + (place(entry[2]) if len(entry) > 2 else '') + arm(k + 1) + 'c\n'
    for f, after in zip(force, force[1:] + [None]):
        a, reg, v = O.Force[f]
        ini[f'lf_{f}.ini'] = f'r {reg}={v}\n{setbp(after) if after else ""}c\n'
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
    """The race: the first run of consecutive frame counters over 100 frames, the race the poke started (a
    run long enough for its race to end goes on into the game's next track's: track 1's race 17, 1,852 frames,
    in 9,000 VBLs, its next race longer; the longest run, as this took before, was that one)."""
    runs = [[frames[0]]]
    for f in frames[1:]:
        if f['frame'] == runs[-1][-1]['frame'] + 1:
            runs[-1].append(f)
        else:
            runs.append([f])
    return next(r for r in runs if len(r) > 100)


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
    track, race_no, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[4]
    script = [] if sys.argv[3] == '-' else json.load(open(sys.argv[3]))
    force = sys.argv[5].split(',') if len(sys.argv) > 5 else []
    os.makedirs(D, exist_ok=True)
    frames = race(parse(record(track, race_no, script, int(os.environ.get('VBLS', 6000)), force)))
    values = [v for f in frames for n, v in f['random']]
    json.dump({'track': track, 'race': race_no, 'script': script, 'force': force, 'seed': seed(values),
               'frames': [{'frame': f['frame'], 'phase': f['phase'], 'inputs': f['inputs'], 'random': f['random'],
                           'mem': {str(k): v for k, v in f['mem'].items()}} for f in frames]}, open(path, 'w'))
    print(f'{len(frames)} frames, {frames[0]["frame"]} to {frames[-1]["frame"]};',
          sum(len(f['inputs']) for f in frames), 'inputs;', len(values), 'random numbers, one run of TOS\'s generator')
