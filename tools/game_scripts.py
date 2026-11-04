"""The whole games tools/st_trace_game.py plays, written to tools/game_scripts/NAME.json. Usage: game_scripts.py"""
import json, os

Laps, Check, Stripes, Times, Wrench, Score = 0x1E354, 0x1E38C, 0x1E394, 0x1E32C, 0x1E324, 0x1DFA8
Fire0 = 0x1DFFE                         # car 0's accelerate, held in the attract mode to start a game


def w(address, value):
    return [address, value >> 8, value & 255]


def result(laps, check=None, stripes=None, times=None, wrenches=None, scores=None):
    """Pokes for a race's result: each list by car. A car's laps of 4 ends the race, the car the winner."""
    out = [w(Laps + 2 * c, v) for c, v in enumerate(laps)]
    out += [w(Check + 2 * c, v) for c, v in enumerate(check or [])]
    out += [w(Stripes + 2 * c, v) for c, v in enumerate(stripes or [])]
    for c, t in enumerate(times or []):
        out += [w(Times + 8 * c + 2 * i, v) for i, v in enumerate(t)]
    out += [w(Wrench + 2 * c, v) for c, v in enumerate(wrenches or [])]
    for c, s in enumerate(scores or []):
        if s is not None:
            out.append([Score + 6 * c, *s])
    return out


def tap(car, key, hold=6, gap=20):
    """A press and a release, gap Vsyncs from the last step."""
    return [{'when': ['vsync', gap], 'keys': {car: key}}, {'when': ['vsync', hold], 'keys': {car: ''}}]


Start = [{'when': ['vbl', 2000], 'poke': [[0x1F200, 0, 0], [Fire0, 3]]},   # the disc check off, car 0's fire
         {'when': ['pc', 0x198B6], 'poke': [[Fire0, 0]]}]
Keys = 0x1DFD4                          # G_01DFD4: a byte a scan code
Esc, F5, F10 = Keys + 1, Keys + 0x3F, Keys + 0x44
Race, Upgrade, Initials, Over = 0xC592, 0x1A130, 0x17A42, 0x14282
Loop = 160                              # Vsyncs from a screen's entry to its loop, past its set-up and wipe


def at(pc):
    return [{'when': ['pc', pc]}]


def key(address, gap):
    """A function key: F_010DAA clears the byte when it reads it."""
    return [{'when': ['vsync', gap], 'poke': [[address, 1]]}]


def finish(result_pokes, flips=150, up=None):
    """A race ended when it's been running a while; up: a car whose key's let go at its start."""
    return [{'when': ['pc', Race], **({'keys': {up: ''}} if up else {})}, {'when': ['flip', flips], 'poke': result_pokes}]


def initials(car, keys):
    """Each of keys a tap, the first when the entry's loop has started; the last only pressed, as the entry may end on
    it, with no Vsync to count to its release: the next step lets it go."""
    out = []
    for i, k in enumerate(keys):
        out += tap(car, k, gap=Loop if i == 0 else 20)
    return out[:-1]


Scripts = {
    # Three players: the dial moved to track 3 (1 wrench each), car 1 joins at the select, car 2 at prepare. Race 1:
    # car 0 wins, car 1 second, the drone third, car 2 last, so eliminated, with a score for the table; car 0 buys
    # an upgrade, and car 2 enters its initials. Race 2: a drone wins, both humans are eliminated, both with scores
    # for the table, and the game's over.
    'three': {'vbls': 12000, 'steps': Start
              + tap('0', 'R', gap=Loop) + tap('0', 'R') + tap('1', 'A') + tap('0', 'A')
              + at(0x18776) + tap('2', 'A', gap=60)
              + finish(result([4, 3, 2, 3], check=[1, 4, 2, 3], stripes=[0, 30, 10, 20],
                              times=[[300, 620, 930, 1250], [340, 700, 1040, 0], [420, 900, 0, 0], [360, 720, 0, 0]],
                              wrenches=[5, 2, 9, 0], scores=[None, None, [0x80, 7, 2, 3, 4, 0]]))
              + at(Upgrade) + tap('0', 'R', gap=80) + tap('0', 'A', gap=40)
              + at(Initials) + initials('2', ['R', 'A', 'R', 'A', 'L', 'A'])
              + finish(result([3, 2, 1, 4], check=[3, 2, 1, 1], stripes=[9, 8, 7, 0],
                              times=[[300, 620, 930, 0], [340, 700, 0, 0], [420, 0, 0, 0], [280, 560, 840, 1120]],
                              scores=[[0x80, 9, 0, 0, 0, 0], [0x80, 3, 0, 0, 0, 0]]), up='2')
              + at(Initials) + tap('0', 'A', gap=Loop) + tap('0', 'A') + tap('0', 'A')
              + initials('1', ['L', 'A', 'A', 'A'])
              + [{'when': ['pc', Over], 'keys': {'1': ''}}]},
    # One player: the dial left to track 8 (3 wrenches), the select's countdown left to run out; Esc ends prepare. Race
    # 1: car 0 wins with a lap record, F5 shortens the celebration (read once, before it starts: the byte waits), and
    # its upgrade's time runs out, which buys what the dial's on. Race 2: second behind a drone: eliminated, and the
    # game's over with no score for the table.
    'alone': {'vbls': 12000, 'steps': Start + tap('0', 'L', gap=Loop)
              + at(0x18776) + key(Esc, 200)
              + finish(result([4, 3, 2, 3], check=[1, 3, 2, 3], stripes=[0, 30, 10, 20],
                              times=[[200, 420, 640, 860], [340, 700, 1040, 0], [420, 900, 0, 0], [360, 720, 0, 0]],
                              wrenches=[4, 0, 0, 0]))
              + [{'when': ['pc', 0x1AC1C], 'poke': [[F5, 1]]}]
              + at(Upgrade)
              + finish(result([3, 2, 1, 4], check=[3, 2, 1, 1], stripes=[9, 8, 7, 0],
                              times=[[300, 620, 930, 0], [340, 700, 0, 0], [420, 0, 0, 0], [280, 560, 840, 1120]]))
              + at(Over)},
    # Two players: both eliminated by a drone's win, car 1 joins again at the last prepare, so the game goes on; F10
    # abandons race 2, back to the attract mode.
    'rejoin': {'vbls': 12000, 'steps': Start + tap('1', 'A', gap=Loop) + tap('0', 'A')
               + finish(result([3, 2, 1, 4], check=[3, 2, 1, 1], stripes=[9, 8, 7, 0],
                               times=[[300, 620, 930, 0], [340, 700, 0, 0], [420, 0, 0, 0], [280, 560, 840, 1120]]))
               + at(0x18776) + tap('1', 'A', gap=80)
               + at(Race) + [{'when': ['flip', 150], 'poke': [[F10, 1]]}]
               + at(Over)},
}

# The attract mode left alone, the order and times of its screens from its dumps' VBLs (tools/attract_check.mjs).
Scripts['attract'] = {'vbls': 22000, 'steps': [{'when': ['vbl', 1000]}],
                      'points': {0x13F68: 'title', 0x172EA: 'high scores', 0x1BF34: 'lap records', 0xD1FA: 'demo', 0x14196: 'credits',
                                 0x140F0: 'wait'}}

if __name__ == '__main__':
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_scripts')
    for name, s in Scripts.items():
        json.dump(s, open(os.path.join(here, f'{name}.json'), 'w'), indent=0)
