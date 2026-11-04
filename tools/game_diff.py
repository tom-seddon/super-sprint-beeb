"""What each screen of a game changes (Phase 5, step 5): from tools/st_trace_game.py's traces, for each screen the
runs of bytes that differ between the state before it and after it, in any of the traces, named where they're known.

Usage: game_diff.py TRACE.json ...
"""
import json, os, re, sys
from collections import defaultdict

Region = 0x1C722
Known = {  # (first, last + 1): name
    (0x1C724, 0x1C730): 'scratch (a screen\'s text)', (0x1CF2E, 0x1CF32): 'G_01CF2E/30 celebration speed',
    (0x1D30E, 0x1D310): 'frame counter G_01D30E', (0x1D178, 0x1D17A): 'coasting phase', (0x1D314, 0x1D324): 'lap records',
    (0x1D324, 0x1D382): 'high scores\' initials', (0x1D382, 0x1D43C): 'high scores', (0x1DA74, 0x1DAA4): 'G_01DA74',
    (0x1DB44, 0x1DB46): 'difficulty G_01DB44', (0x1DF90, 0x1DFA8): 'G_01DF90 (saved scores?)', (0x1DFA8, 0x1DFC0): 'scores',
    (0x1DFC0, 0x1DFC8): 'G_01DFC0', (0x1E2AC, 0x1E2B4): 'upgrades (a car\'s word each: this car\'s)', (0x1E324, 0x1E32C): 'wrenches',
    (0x1E32C, 0x1E34C): 'lap times', (0x1E34C, 0x1E354): 'drone flags', (0x1E354, 0x1E35C): 'laps', (0x1EBC2, 0x1EBC4): 'race counter',
}


def name(a):
    for (lo, hi), n in Known.items():
        if lo <= a < hi:
            return n
    return None


def main(paths):
    seen = defaultdict(set)
    for p in paths:
        pts = [e for e in json.load(open(p))['events'] if e['kind'] == 'point']
        for x, y in zip(pts, pts[1:]):
            a, b = bytes.fromhex(x['mem']), bytes.fromhex(y['mem'])
            seen[y['name']] |= {Region + i for i in range(len(a)) if a[i] != b[i]}
    for screen, addrs in seen.items():
        runs = []
        for a in sorted(addrs):
            if runs and a - runs[-1][1] <= 2:
                runs[-1][1] = a
            else:
                runs.append([a, a])
        print(f'{screen}: {len(addrs)} bytes')
        named = defaultdict(int)
        rest = []
        for lo, hi in runs:
            for a in range(lo, hi + 1):
                n = name(a)
                if n:
                    named[n] += 1
            if not name(lo):
                rest.append(f'{lo:05X}+{hi - lo + 1}')
        print('   ' + ', '.join(f'{k} ({v})' for k, v in named.items()))
        print('   others: ' + ' '.join(rest))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1:])
