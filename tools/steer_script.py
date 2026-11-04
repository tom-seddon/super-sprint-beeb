"""A script for tools/st_trace_logic.py that drives several cars at once, at random, for the wall probes' sake
(D9): accelerate mostly held and left, right or neither for a few frames at a time, so each car runs into the
walls at every facing it can.

Usage: steer_script.py CARS SEED OUT.json [FRAMES]   (CARS: the cars driven, as "012" or "12"; FRAMES default 8000)
"""
import json, random, sys


def car_times(rnd, frames):
    """One car's driving: [(frame, keys)]."""
    out, t = [], 2
    while t < frames:
        turn = rnd.choice(('', '', 'L', 'R'))
        out.append((t, turn + ('' if rnd.random() < 0.1 else 'A')))
        t += rnd.randint(3, 25) if turn else rnd.randint(10, 60)
    return out


def main(cars, seed, path, frames=8000):
    rnd = random.Random(int(seed))
    times = {c: dict(car_times(rnd, int(frames))) for c in cars}
    held, script = {c: '' for c in cars}, []
    for t in sorted({t for v in times.values() for t in v}):
        for c in cars:
            held[c] = times[c].get(t, held[c])
        script.append([t, dict(held)])
    json.dump(script, open(path, 'w'))
    print(f'{len(script)} changes for cars {cars}')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
