"""A copy of build/game.ssd for trying what comes after a race by hand, reaching it quickly: for a look on a real machine, not for the checks.

- Every game starts with N wrenches, whatever the dial says, so the upgrades come up after the first race a player survives.
- A race is 1 lap.
- Last place earns 100 points, so a player who's knocked out has a score, and the high score table is low, 1,500 down to 50, 50 an entry, so that
  score gets in: a player knocked out enters initials at the next prepare to race, in a place that depends on how they did. The drones' scores are
  blanked after the circle as ever, so nobody else does. A score that's beaten is pushed down as usual.

Also OUT's ADFS L copy, OUT with .adl (build/cheat.adl), made from it by tools/adfs_disc.py as build/game.adl is.

Made as build/game.ssd is, by tools/make_game.py, the files patched before the boot's are packed (each pattern must be
in exactly one file, once).

Usage: cheat_disc.py [N] [OUT]   (N default 8, OUT default build/cheat.ssd; after make game)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adfs_disc
import make_game


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


class Files:
    """The disc's files' bytes, raw, patched in place: once() finds a pattern, writes go to its file."""
    def __init__(self, files):
        self.files = files
        self.data = {k: bytearray(f.data) for k, f in files.items()}

    def once(self, pattern, what):
        places = [(k, m.start()) for k, d in self.data.items() for m in re.finditer(pattern, bytes(d), re.DOTALL)]
        assert len(places) == 1, f'{what}: found {len(places)} times'
        return places[0]

    def done(self):
        for k, d in self.data.items():
            if bytes(d) != self.files[k].data:
                self.files[k].replace(d)


def cheat(files, n, syms):
    addr = lambda name: (lambda a: bytes([a & 255, a >> 8]))(symbol(syms, name))
    f = Files(files)

    # the select's end: LDA GsDial:LSR A:LSR A:LDX #2:STA RcWrench,X, its first 5 bytes made LDA #n and 3 NOPs
    k, at = f.once(re.escape(b'\xAD' + addr('GsDial') + b'\x4A\x4A\xA2\x02\x9D' + addr('RcWrench')), 'the wrenches')
    f.data[k][at:at + 5] = bytes([0xA9, int(n), 0xEA, 0xEA, 0xEA])

    # the race's end: CMP #4:BNE:LDA RcFinished, and the others held back from it: LDA RcLaps,X:CMP #4:BNE:LDA #3:STA RcLaps,X
    k, at = f.once(b'\xC9\x04\xD0.\xA5' + re.escape(addr('RcFinished')[:1]), 'the race\'s end')
    f.data[k][at + 1] = 1
    k, at = f.once(re.escape(b'\xBD' + addr('RcLaps')) + b'\xC9\x04\xD0.\xA9\x03\x9D' + re.escape(addr('RcLaps')), 'the cars after the win')
    f.data[k][at + 4] = 1
    f.data[k][at + 8] = 0

    # last place's points: PlacePtsLo's 1,000, 500, 250, 0
    k, at = f.once(b'\xE8\xF4\xFA\x00\x03\x01\x00\x00', 'the places\' points')
    f.data[k][at + 3] = 100

    # the table: 31 entries of 6 digits, the first unused
    table = open('orig/st/SSPRINT.HSC', 'rb').read()[:186]
    k, at = f.once(re.escape(table), 'the high scores')
    for e in range(1, 31):
        f.data[k][at + e * 6:at + e * 6 + 6] = bytes(int(d) for d in f'{(31 - e) * 50:06}')
    f.done()


def main(n=8, out='build/cheat.ssd'):
    syms = json.load(open('build/tracks/t0.json'))
    make_game.main('build/tracks', 'build/zx02', out, patch=lambda files: cheat(files, n, syms))
    print(f'{out}: {n} wrenches a game, 1 lap a race, a low table')
    adfs_disc.main(out, os.path.splitext(out)[0] + '.adl')


if __name__ == '__main__':
    main(*sys.argv[1:])
