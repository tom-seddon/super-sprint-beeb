"""Turn st_trace_objects.py's log of a real race into frames for the renderer test, as st_trace_cars.py's.

Usage: st_race.py RAW.json OUT.json

Each frame: "frame" (the ST's counter), "order" (the cars the car plotter drew, in order), "cars" ([x, y,
facing, flags] per car, at the flip), "drone" (each car's drone flag: a player's car driven by a drone is
drawn from the second set of frames), "laps", "scores", and "calls": the car plotter and object routines
called that frame, in order, each [name, args] (and the sparks' state with theirs). A frame's calls come before its flip and its state is dumped at the flip, so
calls_k pairs with the state dumped at flip k.
"""
import json, sys

Flip = 0x1D30E


def word(m, a):
    return m.get(str(a), 0) << 8 | m.get(str(a + 1), 0)


def main(raw, out):
    log = json.load(open(raw))
    flips = [(log[k]['calls'], log[k + 1]['mem']) for k in range(len(log) - 1)]
    frames = []
    for calls, m in flips:
        frames.append({'frame': word(m, Flip),
                       'order': [w[0] for n, w, e in calls if n == 'car'],
                       'cars': [[word(m, 0x1E42C + 2 * c), word(m, 0x1E424 + 2 * c), word(m, 0x1E41C + 2 * c),
                                 word(m, 0x1E3A4 + 2 * c)] for c in range(4)],
                       'drone': [word(m, 0x1E34C + 2 * c) for c in range(4)],
                       'laps': [word(m, 0x1E354 + 2 * c) for c in range(4)],
                       'scores': [bytes(m.get(str(0x1DFA8 + 6 * c + i), 0) for i in range(6)).hex() for c in range(4)],
                       'calls': [[n, w] + ([e] if e else []) for n, w, e in calls]})
    runs, run = [], [frames[0]]
    for f in frames[1:]:
        if f['frame'] == run[-1]['frame'] + 1:
            run.append(f)
        else:
            runs.append(run)
            run = [f]
    runs.append(run)
    race = max(runs, key=len)
    json.dump(race, open(out, 'w'))
    print(f'{len(race)} frames, {race[0]["frame"]} to {race[-1]["frame"]}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
