"""A copy of build/game.ssd for trying what comes after a race by hand, reaching it quickly: for a look on a real machine, not for the checks.

- Every game starts with N wrenches, whatever the dial says, so the upgrades come up after the first race a player survives.
- A race is 1 lap.
- Last place earns 100 points, so a player who's knocked out has a score, and the high score table is low, 1,500 down to 50, 50 an entry, so that
  score gets in: a player knocked out enters initials at the next prepare to race, in a place that depends on how they did. The drones' scores are
  blanked after the circle as ever, so nobody else does. A score that's beaten is pushed down as usual.

Also OUT's ADFS L copy, OUT with .adl (build/cheat.adl), made from it by tools/adfs_disc.py as build/game.adl is.

Usage: cheat_disc.py [N] [OUT]   (N default 8, OUT default build/cheat.ssd; after make game)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adfs_disc


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


def once(disc, pattern, what):
    """The one place pattern, a regex of bytes, is on the disc."""
    places = [m.start() for m in re.finditer(pattern, bytes(disc), re.DOTALL)]
    assert len(places) == 1, f'{what}: found {len(places)} times'
    return places[0]


def main(n=8, out='build/cheat.ssd'):
    syms = json.load(open('build/tracks/t0.json'))
    addr = lambda name: (lambda a: bytes([a & 255, a >> 8]))(symbol(syms, name))
    disc = bytearray(open('build/game.ssd', 'rb').read())

    # the select's end: LDA GsDial:LSR A:LSR A:LDX #2:STA RcWrench,X, its first 5 bytes made LDA #n and 3 NOPs
    at = once(disc, re.escape(b'\xAD' + addr('GsDial') + b'\x4A\x4A\xA2\x02\x9D' + addr('RcWrench')), 'the wrenches')
    disc[at:at + 5] = bytes([0xA9, int(n), 0xEA, 0xEA, 0xEA])

    # the race's end: CMP #4:BNE:LDA RcFinished, and the others held back from it: LDA RcLaps,X:CMP #4:BNE:LDA #3:STA RcLaps,X
    at = once(disc, b'\xC9\x04\xD0.\xA5' + re.escape(addr('RcFinished')[:1]), 'the race\'s end')
    disc[at + 1] = 1
    at = once(disc, re.escape(b'\xBD' + addr('RcLaps')) + b'\xC9\x04\xD0.\xA9\x03\x9D' + re.escape(addr('RcLaps')), 'the cars after the win')
    disc[at + 4] = 1
    disc[at + 8] = 0

    # last place's points: PlacePtsLo's 1,000, 500, 250, 0
    at = once(disc, b'\xE8\xF4\xFA\x00\x03\x01\x00\x00', 'the places\' points')
    disc[at + 3] = 100

    # the table: 31 entries of 6 digits, the first unused
    table = open('orig/st/SSPRINT.HSC', 'rb').read()[:186]
    at = once(disc, re.escape(table), 'the high scores')
    for e in range(1, 31):
        disc[at + e * 6:at + e * 6 + 6] = bytes(int(d) for d in f'{(31 - e) * 50:06}')

    open(out, 'wb').write(disc)
    print(f'{out}: {n} wrenches a game, 1 lap a race, a low table')
    adfs_disc.main(out, os.path.splitext(out)[0] + '.adl')


if __name__ == '__main__':
    main(*sys.argv[1:])
