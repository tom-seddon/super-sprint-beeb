"""Record the front end's tunes on the ST (Phase 5, step 9, D11): each one played whole, from the attract mode's title,
every YM register write logged, and the YM's state at each VBL kept, for tools/tune_gen.py to convert.

Usage: st_trace_tunes.py OUT.json [NAME ...]   (default every tune in Tunes)

On the ST each tune is started by a function that points the sequencer's track 0 at its sequence (st-logic §8):
F_0134FA the select's (&1E64), F_01353E prepare's (&A14), F_013362 one of the circle's five, F_013252 the join's
(&150), F_0131DE the upgrades' ding (&110). The first three are the same code but for the sequence's offset, and set
the noise period to 5 (F_0132EE) first. So a tune is started by sending the program to its starter as it calls
xbios_01194C for a Vsync in the title's wait: the starter returns to that call's caller, which pops its arguments as
usual, one Vsync short. The circle's five and prepare's go through F_0134FA with its LEA's offset patched (the word
at &13520). The title's wait and the screens after it start no sound, and the demo's race is minutes away, so the
tune plays alone to its end. A field is the YM's state at TOS's VBL (its registers as the writes before it left
them), as tools/st_trace_sound.py's.
"""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import st_trace_logic as L

ROOT = L.ROOT
D = L.D
Vsync = 0x1194C                         # xbios_01194C: every front-end wait's Vsync
VblPc = 0xFC06C0                        # TOS 1.04's VBL routine: addq.l #1, _frclock
FrClock = 0x466
Select, Patch = 0x0134FA, 0x013520      # F_0134FA and its LEA's offset
Title = 0x014056                        # the title's picture drawn: the attract mode's quiet stretch begins (title, high
Titles = int(os.environ.get('TITLES', 1))   # scores, lap records: 750 VBLs of waits, the wipes between); the nth
# the sound driver's other entries (st-logic §8), each logged when called: a tune is only what played before any of them
Watch = {0x013284: 'F_013284 silence', 0x013306: 'F_013306 fade', 0x013582: 'F_013582 engine', 0x0136C4: 'F_0136C4 set-up',
         0x0131A8: 'F_0131A8 race start', 0x01353E: 'F_01353E prepare', 0x013362: 'F_013362 circle',
         0x013252: 'F_013252 join', 0x0131DE: 'F_0131DE ding', Select: 'F_0134FA select'}
WatchMark = 0x700
# name: (the starter, the sequence's offset to patch in or None, its length in the driver's ticks: logic_snd.py)
Tunes = {'select': (Select, None, 1002), 'prepare': (Select, 0xA14, 640), 'join': (0x013252, None, 233),
         'ding': (0x0131DE, None, 91),
         **{f'circle{k}': (Select, o, t) for k, (o, t) in enumerate([(0xD46, 1089), (0x1188, 880), (0x14B6, 826),
                                                                    (0x171C, 1113), (0x1A8A, 1082)])}}
TickHz = 749.3 / 9
Fields = 800                            # fields recorded from the start: the longest tune's 706 and some


def record(name):
    starter, offset, ticks = Tunes[name]
    f = lambda n: os.path.join(D, f'tune_{name}_{n}')
    vbls = 6000
    count = f' :{Titles}' if Titles > 1 else ''
    ini = {'0.ini': f'b pc = ${Title:X}{count} :once :file {f("1.ini")}\nb pc = ${VblPc:X} :quiet :file {f("vbl.ini")}\n'
           + ''.join(f'b pc = ${a:X} :quiet :file {f(f"w{i}.ini")}\n' for i, a in enumerate(Watch)),
           '1.ini': f'w $1F200 0 0\nb pc = ${Vsync:X} :once :file {f("2.ini")}\nc\n',
           '2.ini': (f'w ${Patch:X} ${offset >> 8:02X} ${offset & 255:02X}\n' if offset is not None else '')
           + f'm $6F0 1\nr pc=${starter:X}\nb pc = ${VblPc:X} :{Fields} :once :file {f("q.ini")}\nc\n',
           'q.ini': 'quit\n',
           'vbl.ini': f'm ${FrClock:X} 4\nc\n',
           **{f'w{i}.ini': f'm ${WatchMark + i:X} 1\nc\n' for i in range(len(Watch))}}
    for n, text in ini.items():
        open(f(n), 'w').write(text)
    log = f('hatari.log')
    with open(log, 'w') as out:
        subprocess.run([os.path.join(ROOT, 'tools', 'hatari.sh'), '600', '--parse', f('0.ini'), '--run-vbls', str(vbls),
                        '--trace', 'psg_write'], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, check=True)
    return log


def parse(log):
    """-> (the fields from the tune's start: TOS's VBL count, the YM's 16 registers at it, and the last R13 write (the
    envelope's restart) as (field index, video cycle); the sound driver's entries called after the start, each
    (field index, name))."""
    regs, fields, env, started, calls = [0] * 16, [], None, False, []
    for line in open(log, errors='replace'):
        w = re.match(r'^ym write data reg=0x([0-9a-f]+) val=0x([0-9a-f]+) video_cyc=(\d+)', line)
        if w:
            r, v = int(w.group(1), 16), int(w.group(2), 16)
            if r < 16:
                regs[r] = v
                if r == 13:
                    env = (len(fields), int(w.group(3)))
            continue
        m = re.match(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', line)
        if not m:
            continue
        a, bs = int(m.group(1), 16), [int(x, 16) for x in m.group(2).split()]
        if a == 0x6F0:                  # the starter's run: fields from here
            started, fields, env, calls = True, [], None, []
        elif WatchMark <= a < WatchMark + len(Watch) and started:
            calls.append((len(fields), list(Watch.values())[a - WatchMark]))
        elif a == FrClock and started:
            fields.append({'vbl': bs[0] << 24 | bs[1] << 16 | bs[2] << 8 | bs[3], 'regs': list(regs), 'env': env})
    return fields, calls


def main(out, names):
    os.makedirs(D, exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        logs = dict(zip(names, pool.map(record, names)))
    tunes = {}
    for name in names:
        fields, calls = parse(logs[name])
        if not fields:
            sys.exit(f'{name}: the starter never ran')
        others = calls
        if others:
            print(f'{name}: {others[0][1]} called at field {others[0][0]}: cut there')
            fields = fields[:others[0][0]]
        tunes[name] = fields
        loud = [i for i, fd in enumerate(fields) if any(fd['regs'][8 + c] & 31 for c in range(3))]
        print(f'{name}: {len(fields)} fields, sound in {loud[0] if loud else "-"} to {loud[-1] if loud else "-"} '
              f'(its sequence {Tunes[name][2] / TickHz:.2f} s, {Tunes[name][2] / TickHz * 50:.0f} fields)')
    json.dump(tunes, open(out, 'w'))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2:] or list(Tunes))
