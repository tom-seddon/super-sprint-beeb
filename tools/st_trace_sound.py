"""Record a race's sound on the ST (Phase 4, step 10, D11): every YM register write, the frames, the sound driver's
channel priorities, and each sound starter's call, for tools/sound_gen.py to cut the effects from.

Usage: st_trace_sound.py TRACK RACE OUT.json [FORCE] [SCRIPT]   (as tools/st_trace_objects.py: FORCE "tornado",
"cones", "oil", joined by commas, or "-"; SCRIPT an autopilot from tools/logic_scripts, else accelerate held)

"oil" puts oil (&05) in a column of the attribute map across track 1's start straight (cells 15, 3-7) with
the autopilot's first keys, so the cars drive over it: none of the traced races' cars ever met the oil
patches, and the skid's sound is only its sequence's.

Hatari's `--trace psg_write` logs each YM write as "ym write data reg=R val=V video_cyc=C ..."; a quiet
breakpoint on the flip (&14D9C) dumps the frame counter and the driver's three channel priorities between
them, so each frame's register state is the writes up to its flip; a breakpoint on each starter dumps its
address (a marker) and the stack (its argument: the channel, car MOD 3, or for F_012C74 and F_012D38 the
first of two). The driver's tables are malloc'd at start-up: their addresses are the same every run from
the same start (checked at the race's entry against these).
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import st_trace_logic as L
import st_trace_objects as O

ROOT = L.ROOT
D = L.D
Prio = 0x703DC                          # G_01F25C's target: each channel's priority, a word
PrioPtr = 0x1F25C
Frame = 0x1D30E
Starters = {0x0130A0: 'bounce', 0x013032: 'bump', 0x012F4A: 'slow', 0x012FB8: 'skid', 0x012E00: 'wrench',
            0x012EDC: 'bonus', 0x012E6E: 'tornado', 0x012C74: 'wreck', 0x012D38: 'heli_gone'}
VblPc = 0xFC06C0                        # TOS 1.04's VBL routine: addq.l #1, _frclock
FrClock = 0x466
# each starter's priority threshold: it starts only if the channel's priority is under it (None: always)
Threshold = {'bounce': 1, 'bump': 2, 'slow': 1, 'skid': 1, 'wrench': 4, 'bonus': 4, 'tornado': 3}


def record(track, race, force, script, vbls):
    def arm(k):
        if not script or k >= len(script):
            return ''
        return f'b pc = ${L.FlipPc:X} && {L.condition(script[k][0])} :once :file {D}/sev{k}.ini\n'
    oil = 'oil' in force
    force = sorted([f for f in force if f != 'oil'], key=lambda f: ('tornado', 'cones').index(f))
    def setbp(f):
        return f'b pc = ${O.Force[f][0]:X} :once :file {D}/sf_{f}.ini\n'
    ini = {'s0.ini': f'b VBL = 2000 :once :file {D}/s1.ini\nb pc = $C592 :once :file {D}/s2.ini\n',
           's1.ini': 'w $1F200 0 0\nw $1DFFE 3\nc\n',
           's2.ini': (f'w ${O.RaceEntryStack + 4:X} 0 {track}\nw $1EBC2 0 {race}\nm ${PrioPtr:X} 4\n'
                      + (''.join(f'w ${a:X} 0\n' for a in L.Keys.values()) + arm(0) if script else '')
                      + f'b pc = ${VblPc:X} :quiet :file {D}/svbl.ini\n'
                      + ''.join(f'b pc = ${a:X} :quiet :file {D}/s_{n}.ini\n' for a, n in Starters.items())
                      + (setbp(force[0]) if force else '') + 'c\n'),
           'svbl.ini': f'm ${FrClock:X} 4\nm ${Frame:X} 2\nm ${Prio:X} 6\nc\n'}
    for a, n in Starters.items():
        ini[f's_{n}.ini'] = f'm ${a:X} 2\nm a7 6\nm ${Prio:X} 6\nm ${Frame:X} 2\nc\n'
    for k, (frame, keys) in enumerate(script or []):
        ini[f'sev{k}.ini'] = (''.join(f'w ${a:X} {3 if c in keys else 0}\n' for c, a in L.Keys.items())
                              + (''.join(f'w ${0x678F6 + y * 40 + 15:X} 5\n' for y in range(3, 8)) if oil and k == 0 else '')
                              + arm(k + 1) + 'c\n')
    for f, after in zip(force, force[1:] + [None]):
        a, reg, v = O.Force[f]
        ini[f'sf_{f}.ini'] = f'r {reg}={v}\n{setbp(after) if after else ""}c\n'
    for name, text in ini.items():
        open(os.path.join(D, name), 'w').write(text)
    log = os.path.join(D, f'hatari_sound_t{track}_r{race}.log')
    with open(log, 'w') as f:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '900', '--parse', f'{D}/s0.ini',
                        '--run-vbls', str(vbls), '--trace', 'psg_write'], cwd=ROOT, stdout=f,
                       stderr=subprocess.STDOUT, check=True)
    return log


def parse(log):
    """-> (fields, starts). A field: TOS's VBL count, the race's frame counter, the YM's 16 registers at its
    VBL, the channels' priorities there, and the last R13 write (the envelope's restart) as (field index,
    video cycle). A start: the field it came before, the starter, its channel argument, and the priorities
    it found."""
    regs, frames, starts, pending, env, prio_ok = [0] * 16, [], [], None, None, None
    cur, start = {}, None
    for line in open(log, errors='replace'):
        w = re.match(r'^ym write data reg=0x([0-9a-f]+) val=0x([0-9a-f]+) video_cyc=(\d+)', line)
        if w:
            r, v = int(w.group(1), 16), int(w.group(2), 16)
            if r < 16:
                regs[r] = v
                if r == 13:
                    env = (len(frames), int(w.group(3)))
            continue
        m = re.match(r'^(?:> )?([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a = int(m.group(1), 16)
        bs = [int(x, 16) for x in m.group(2).split()]
        if a == PrioPtr:
            prio_ok = (bs[0] << 24 | bs[1] << 16 | bs[2] << 8 | bs[3]) == Prio
        elif a in Starters and len(bs) == 2:
            pending = Starters[a]
        elif pending and start is None:
            start = {'index': len(frames), 'name': pending, 'channel': bs[4] << 8 | bs[5]}
        elif pending and a == Prio:      # the priorities at the call
            start['prio'] = [bs[0] << 8 | bs[1], bs[2] << 8 | bs[3], bs[4] << 8 | bs[5]]
        elif pending and a == Frame:     # and the race's frame
            start['frame'] = bs[0] << 8 | bs[1]
            starts.append(start)
            pending, start = None, None
        elif a == FrClock:
            cur = {'vbl': bs[0] << 24 | bs[1] << 16 | bs[2] << 8 | bs[3], 'regs': list(regs), 'env': env}
        elif a == Frame:
            cur['frame'] = bs[0] << 8 | bs[1]
        elif a == Prio:
            cur['prio'] = [bs[0] << 8 | bs[1], bs[2] << 8 | bs[3], bs[4] << 8 | bs[5]]
            frames.append(cur)
    assert prio_ok, "the driver's priorities aren't where they were: a different start"
    return frames, starts


if __name__ == '__main__':
    track, race, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    force = sys.argv[4].split(',') if len(sys.argv) > 4 and sys.argv[4] != '-' else []
    script = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
    os.makedirs(D, exist_ok=True)
    frames, starts = parse(record(track, race, force, script, int(os.environ.get('VBLS', 6000))))
    # the race: the longest run of fields from a fall of the frame counter (the set-up's reset: a VBL sees
    # it at 1, the reset and the first flip between two) over which it never falls again (it stands still in
    # the pauses; at the end the ST sets it back to the winner's finish)
    best = (0, 0)
    for i in range(1, len(frames)):
        if frames[i]['frame'] < frames[i - 1]['frame']:
            j = i
            while j + 1 < len(frames) and frames[j + 1]['frame'] >= frames[j]['frame']:
                j += 1
            best = max(best, (j - i, i))
    lo, hi = best[1], best[1] + best[0]
    out = {'track': track, 'race': race, 'frames': frames[lo:hi + 1],
           'starts': [dict(s, index=s['index'] - lo) for s in starts if lo <= s['index'] <= hi + 1]}
    json.dump(out, open(path, 'w'))
    from collections import Counter
    print(f'{hi - lo + 1} fields, frames {frames[lo]["frame"]} to {frames[hi]["frame"]}; starters called:',
          dict(Counter(s['name'] for s in out['starts'])))
