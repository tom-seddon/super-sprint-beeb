"""Run tools/logic_check.mjs on every stretch of the traced race where one car is free of what the BBC's logic
doesn't do yet, each from the ST's state at the frame before it (--from), so a part of the logic can be proved
over the whole race before the parts around it are built.

Usage: logic_stretches.py CAR [--until N] [-- logic_check options...]

A frame is free if, at its end in the ST, the car is racing (state 0), touches no other car (flags &000E
clear), wasn't just shoved (immunity not 25), and no car has finished (the race's end). A stretch starts the
frame after a free frame (its seed) and runs while frames are free. Exit status 1 if any stretch fails.
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def stretches(trace, car, until):
    fr = json.load(open(trace))['frames']
    w = lambda m, a: m[str(a)] << 8 | m[str(a + 1)]
    free = [k >= 1 and k <= until and w(f['mem'], 0x1E3D4 + 2 * car) == 0 and (w(f['mem'], 0x1E3A4 + 2 * car) & 0xE) == 0
            and w(f['mem'], 0x1E3AC + 2 * car) != 25 and all(w(f['mem'], 0x1E354 + 2 * c) < 4 for c in range(4))
            for k, f in enumerate(fr)]
    out, k = [], 1
    while k < len(fr):
        if free[k]:
            j = k
            while j + 1 < len(fr) and free[j + 1]:
                j += 1
            if j > k:
                out.append((max(2, k + 1), j))
            k = j + 1
        else:
            k += 1
    return out


def main():
    args = sys.argv[1:]
    extra = args[args.index('--') + 1:] if '--' in args else []
    args = args[:args.index('--')] if '--' in args else args
    car = int(args[0])
    until = int(args[args.index('--until') + 1]) if '--until' in args else 1 << 30
    trace = os.path.join(ROOT, 'build/trace/logic_t0_r0.json')
    failed, frames = 0, 0
    for a, b in stretches(trace, car, until):
        r = subprocess.run(['node', 'tools/logic_check.mjs', '--from', str(a), '--until', str(b), '--cars', str(car)] + extra,
                           cwd=ROOT, capture_output=True, text=True)
        last = [l for l in r.stdout.splitlines() if 'match' in l or 'wrong' in l or 'stopped' in l]
        print(f'{a}-{b}: {"; ".join(last)}')
        failed += r.returncode != 0
        frames += b - a + 1
    print(f'{frames} frames in stretches; {failed} stretches failed')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
