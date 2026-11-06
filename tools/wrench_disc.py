"""A copy of build/game.ssd for trying what comes after a race by hand: every game starts with N wrenches, whatever the dial says, so
the upgrades come up after the first race a player survives. For a look on a real machine, not for the checks: nothing else differs.

Usage: wrench_disc.py [N] [OUT]   (N default 8, OUT default build/wrenches.ssd; after make game)
"""
import json, re, sys


def symbol(tree, name):
    if isinstance(tree, dict):
        if name in tree and isinstance(tree[name], dict) and 'value' in tree[name]:
            return tree[name]['value']
        tree = tree.values()
    elif not isinstance(tree, list):
        return None
    for v in tree:
        found = symbol(v, name)
        if found is not None:
            return found


def main(n=8, out='build/wrenches.ssd'):
    syms = json.load(open('build/tracks/t0.json'))
    dial, wrench = symbol(syms, 'GsDial'), symbol(syms, 'RcWrench')
    disc = open('build/game.ssd', 'rb').read()
    # the select's end: LDA GsDial:LSR A:LSR A:LDX #2:STA RcWrench,X, its first 5 bytes made LDA #n and 3 NOPs
    code = bytes([0xAD, dial & 255, dial >> 8, 0x4A, 0x4A, 0xA2, 2, 0x9D, wrench & 255, wrench >> 8])
    places = [m.start() for m in re.finditer(re.escape(code), disc)]
    assert len(places) == 1, f'the wrenches\' code found {len(places)} times'
    at = places[0]
    open(out, 'wb').write(disc[:at] + bytes([0xA9, int(n), 0xEA, 0xEA, 0xEA]) + disc[at + 5:])
    print(f'{out}: {n} wrenches a game (the code at &{at:X} on the disc)')


if __name__ == '__main__':
    main(*sys.argv[1:])
