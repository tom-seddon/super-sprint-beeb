"""Record a whole game on the ST, screen by screen, for the game's rules on the BBC (Phase 5, step 5; D19).

Usage: st_trace_game.py SCRIPT OUT.json   (SCRIPT: tools/game_scripts/NAME.json, made by tools/game_scripts.py)

The game is started from the attract mode and played by the script: a list of steps, one after another, each
{"when": W, "keys": {car: keys}, "poke": [[address, byte, ...], ...]}, any of the last two left out. W is:
- ["vbl", N]: the VBL counter reaches N (only the first step);
- ["pc", A]: the program reaches address A;
- ["vsync", N]: the Nth XBIOS Vsync after the last step: every front-end wait goes through xbios_01194C;
- ["flip", N]: the Nth flip after the last step (xbios_014D9C): the race's frames, the wipes', the celebration's.
Keys are held until a later step changes them, as st_trace_logic.py's press(). A race needn't be driven: its loop
only tests a car's laps for 4, so a step can end it with the result it wants (the races are checked on their own:
tools/disc_races.sh). Each screen is then a function from the state before it and its inputs to the state after.

Logged, in order, as "events":
- {"kind": "point", "name", "vbl", "mem": hex}: at the game's start, on each return to F_0141B0 and at the initials'
  entry (Points), all of the data and BSS (Region, the high scores and lap records with them): what a screen
  changed is the difference between two of these;
- {"kind": "race", "vbl", "track"}: the race's entry, and its track;
- {"kind": "step", "index", "vbl"}: a script step taken;
- {"kind": "random", "vbl", "n", "value"}: each number F_00ADB8 draws;
- {"kind": "input", "from", "device", "value"}: each read of a player's input (F_010CF2): where it was called from, the
  device (0 the keyboard, 2 and 3 the joysticks) and what it gave. tools/game_check.mjs replays these read by read.
Hatari's breakpoints fire markers: `m` of an address that says which, as the "CPU=" headers can't be trusted.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import st_trace_logic as L

ROOT = L.ROOT
D = os.environ.get('TRACEDIR') or os.path.join(ROOT, 'build', 'trace')
Vbl = 0x466                             # TOS's VBL counter, a long: each event's time
Vsync, Flip = 0x1194C, 0x14D9C
Region = (0x1C722, 0x1F400 - 0x1C722)   # the data and BSS
Points = {0x141B0: 'start', 0x141D0: 'select', 0x141E8: 'prepare', 0x141F6: 'race', 0x14210: 'circle', 0x1421E: 'upgrades',
          0x1422C: 'prepare again', 0x14232: 'restored', 0x14282: 'over', 0x17A42: 'initials'}
RacePc = 0xC592
InputEnd = 0x10DA8                      # F_010CF2's rts: d0 the input
PointMark, RaceMark, RandomMark, InputMark, StepMark = 0x700, 0x6F0, 0x6F1, 0x6F2, 0x600


def poke(entries):
    return ''.join(f'w ${a:X} {" ".join(map(str, bs))}\n' for a, *bs in entries)


def trigger(when, file):
    kind, n = when
    cond = {'vbl': f'VBL = {n}', 'pc': f'pc = ${n:X}', 'vsync': f'pc = ${Vsync:X}', 'flip': f'pc = ${Flip:X}'}[kind]
    count = f' :{n}' if kind in ('vsync', 'flip') and n > 1 else ''
    return f'b {cond}{count} :once :file {file}\n'


def record(steps, vbls, points):
    f = lambda name: os.path.join(D, name)
    stamp = f'm ${Vbl:X} 4\n'
    ini = {'g0.ini': ''.join(f'b pc = ${a:X} :quiet :file {f(f"gp{i}.ini")}\n' for i, a in enumerate(points))
           + f'b pc = ${RacePc:X} :quiet :file {f("grace.ini")}\n'
           + f'b pc = ${L.RandomPc:X} :quiet :file {f("grandom.ini")}\n'
           + f'b pc = ${InputEnd:X} :quiet :file {f("ginput.ini")}\n'
           + trigger(steps[0]['when'], f('gs0.ini')),
           'grace.ini': f'm ${RaceMark:X} 1\n{stamp}m a7 8\nc\n',
           'grandom.ini': f'm ${RandomMark:X} 1\n{stamp}r\nm a6 10\nc\n',
           'ginput.ini': f'm ${InputMark:X} 1\nr\nm a7 6\nc\n'}
    for i in range(len(points)):
        ini[f'gp{i}.ini'] = f'm ${PointMark + i:X} 1\n{stamp}m ${Region[0]:X} {Region[1]}\nc\n'
    for k, s in enumerate(steps):
        nxt = trigger(steps[k + 1]['when'], f(f'gs{k + 1}.ini')) if k + 1 < len(steps) else ''
        ini[f'gs{k}.ini'] = (f'm ${StepMark + k:X} 1\n{stamp}' + (L.press(s['keys']) if 'keys' in s else '')
                             + poke(s.get('poke', [])) + nxt + 'c\n')
    for name, text in ini.items():
        open(f(name), 'w').write(text)
    log = f('hatari_game.log')
    with open(log, 'w') as out:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '1800', '--parse', f('g0.ini'), '--run-vbls', str(vbls)],
                       cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, check=True)
    return log


def parse(log, points):
    names, events, cur, d0 = list(points.values()), [], None, None
    def close():
        if cur is None:
            return
        if 'mem' in cur:
            cur['mem'] = bytes(cur['mem']).hex()
        cur.pop('a6', None)
        cur.pop('a7', None)
        events.append(cur)
    for line in open(log, errors='replace'):
        r = re.search(r'\bD0 ([0-9A-F]{8})', line)
        if r:
            d0 = int(r.group(1), 16)
        r = re.search(r'\bA6 ([0-9A-F]{8})', line)
        if r and cur and cur['kind'] == 'random':
            cur['a6'] = int(r.group(1), 16)
        r = re.search(r'\bA7 ([0-9A-F]{8})', line)
        if r and cur and cur['kind'] == 'input':
            cur['a7'], cur['value'] = int(r.group(1), 16), d0 & 0xFF
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a, bs = int(m.group(1), 16), [int(x, 16) for x in m.group(2).split()]
        mark = None
        if PointMark <= a < PointMark + len(names):
            mark = {'kind': 'point', 'name': names[a - PointMark], 'mem': []}
        elif a == RaceMark:
            mark = {'kind': 'race'}
        elif a == RandomMark:
            mark = {'kind': 'random'}
        elif a == InputMark:
            mark = {'kind': 'input'}
        elif StepMark <= a < StepMark + 0xF0:
            mark = {'kind': 'step', 'index': a - StepMark}
        if mark:
            close()
            cur = mark
        elif cur is None:
            continue
        elif a == Vbl:
            cur['vbl'] = int.from_bytes(bytes(bs[:4]), 'big')
        elif cur['kind'] == 'point' and Region[0] <= a < Region[0] + Region[1]:
            cur['mem'] += bs
        elif cur['kind'] == 'race' and 'track' not in cur:
            cur['track'] = bs[4] << 8 | bs[5]
        elif cur['kind'] == 'random' and a == cur.get('a6'):
            cur['n'], cur['value'] = bs[8] << 8 | bs[9], d0
        elif cur['kind'] == 'input' and a == cur.get('a7'):
            cur['from'], cur['device'] = int.from_bytes(bytes(bs[:4]), 'big'), bs[4] << 8 | bs[5]
    close()
    return events


def main(script, out):
    s = json.load(open(script))
    points = {int(a): n for a, n in s['points'].items()} if 'points' in s else Points
    events = parse(record(s['steps'], s.get('vbls', 30000), points), points)
    json.dump({'script': s, 'events': events}, open(out, 'w'))
    pts = [e for e in events if e['kind'] == 'point']
    print(f'{len(pts)} points: ' + ' '.join(e['name'] for e in pts))
    done = max((e['index'] for e in events if e['kind'] == 'step'), default=-1)
    print(f'steps {done + 1} of {len(s["steps"])}; {sum(e["kind"] == "random" for e in events)} random numbers; '
          f'races on {[e.get("track") for e in events if e["kind"] == "race"]}; '
          f'last VBL {max(e.get("vbl", 0) for e in events)}')
    if done + 1 != len(s['steps']):
        sys.exit('the script never finished')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
