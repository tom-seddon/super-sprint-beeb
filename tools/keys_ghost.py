"""Keyboard ghosting on paper (D12): which keys a set of held keys makes the BBC's matrix read as held too.

Usage: keys_ghost.py   (checks the default three-player layout, and the model against a known ghost)

Exit status 1 if any of the layout's keys held can ghost another of them. The game's other keys it reads (Escape, f0,
f1, f5, and the options' f2-f4 and f9) are listed with the smallest sets that ghost them; Tom took the defaults'
Escape and F1 (2026-11-09, D12).

The matrix has no diodes: a key joins its column line to its row line (internal key number: column bits
0-3, row bits 4-6). Reading a key asks whether its column and row are connected, so with keys held, any key
whose column and row are joined through a chain of held keys reads as held: three keys at three corners of
a rectangle make the fourth (the simplest chain). So: rows and columns are nodes, held keys edges, and a key
ghosts if its row and column are in one component.

The model is checked against a ghost seen on a real BBC: Paradroid's Z, X, K, M and L held together fired
C (beeb-port-kit lib/keydown.6502). Key numbers are measured (the kit's docs/hardware-facts.md section 7;
COMMA 102 and PERIOD 103 measured with jsbeeb-mcp 4.3.0's key_down on a Master, 2026-11-02; CAPS, CTRL, A and
the keypad's against jsbeeb 2.18.0's table, tools/keys_check.mjs).
"""
import itertools, sys

Keys = {'Q': 16, 'W': 33, 'E': 34, 'SHIFT': 0, 'Z': 97, 'X': 66, 'V': 99, 'B': 100, 'N': 85, 'COMMA': 102, 'PERIOD': 103, 'SLASH': 104,
        'K': 70, 'M': 101, 'L': 86, 'C': 82, 'RETURN': 73, 'CAPS': 64, 'CTRL': 1, 'A': 65, 'PAD 5': 123, 'PAD 6': 26,
        'PAD DEL': 75}
Others = {'ESCAPE': 112, 'F0': 32, 'F1': 113, 'F5': 116, 'F2': 114, 'F3': 115, 'F4': 20, 'F9': 119}   # (keyboard.6502)

# the default layout (Tom, 2026-11-09): each player's left, right and accelerate
Layout = [('CAPS', 'CTRL', 'A'), ('COMMA', 'PERIOD', 'SLASH'), ('PAD 5', 'PAD 6', 'PAD DEL')]


def reads_held(held, key):
    """Whether key reads as held with the keys held (key numbers)."""
    parent = {}
    find = lambda n: n if parent.setdefault(n, n) == n else find(parent[n])
    for k in held:
        parent[find(('c', k & 15))] = find(('r', k >> 4))
    return find(('c', key & 15)) == find(('r', key >> 4))


def main():
    held = [Keys[k] for k in ('Z', 'X', 'K', 'M', 'L')]
    ghosts = [n for n, k in Keys.items() if k not in held and reads_held(held, k)]
    assert ghosts == ['C'], ghosts
    print('the model: Z, X, K, M and L held ghost', ghosts, '(as Paradroid saw on hardware)')

    keys = [k for p in Layout for k in p]
    cols = [Keys[k] & 15 for k in keys]
    print('the layout:', '; '.join(f'player {i + 1}: left {p[0]}, right {p[1]}, accelerate {p[2]}' for i, p in enumerate(Layout)))
    print('its columns:', dict(zip(keys, cols)))
    bad = 0
    for n in range(1, len(keys) + 1):
        for held in itertools.combinations(keys, n):
            g = [k for k in keys if k not in held and reads_held([Keys[h] for h in held], Keys[k])]
            if g:
                bad += 1
                if bad <= 5:
                    print('  held', held, 'ghost', g)
    print(f'{2 ** len(keys) - 1} combinations of its keys held: {bad} ghost another of its keys')
    for name, k in Others.items():
        sets = [held for n in range(1, len(keys) + 1) for held in itertools.combinations(keys, n)
                if reads_held([Keys[h] for h in held], k)]
        if sets:
            least = min(map(len, sets))
            print(f'  {name}: ghosted by {len(sets)} combinations, the least', [h for h in sets if len(h) == least])
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
