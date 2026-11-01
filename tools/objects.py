"""The ST's background objects: pickups and hazards in the track's slots, gates and pop-up barriers, as the
ST draws them into the screen being drawn and the clean background (docs/st-logic.md section 3), from their
routines' calls as tools/st_trace_objects.py logs them.

- slot (F_0149B4: sprite, x cell, y cell): 16 x 8, opaque, at (x cell * 8, y cell * 8). Sprites at
  G_01EBDC + &CC0, 64 bytes each, in the screen's plane order.
- gate (F_014A04: frame, screen offset): 48 x 16, opaque; a row is 3 groups of 4 plane words, then 3 words
  of mask C and 3 of mask B, written over the masks' own. Frames at + &180, &240 bytes each.
- barrier (F_014A80: frame, screen offset): 16 x 8, drawn over what's there with colour 0 transparent; a
  row is 4 plane words, a word of mask C (written over the mask's) and one of mask B. Frames at + &1740, 96
  bytes each.
A screen offset is y * 160 + x DIV 16 * 8: x is on a 16-pixel boundary. In mask C a set bit lets a car on
the ground show; a clear one hides it.
"""
import struct
import numpy as np

Objects = 0x205D6                       # G_01EBDC: the object sprites' block in SUPER.DAT


def words(dat, off, n):
    return struct.unpack(f'>{n}H', dat[off:off + 2 * n])


def planes_to_indices(ws):
    """4 plane words (planes 0-3) -> 16 colour indices."""
    return [sum(((ws[p] >> (15 - x)) & 1) << p for p in range(4)) for x in range(16)]


def bits(w):
    return [(w >> (15 - x)) & 1 for x in range(16)]


def slot(dat, sprite):
    base = Objects + 0xCC0 + sprite * 64
    return np.array([planes_to_indices(words(dat, base + r * 8, 4)) for r in range(8)], np.uint8)


def gate(dat, frame):
    """-> colours (16 x 48), mask C (16 x 48, 1: a car shows)."""
    base = Objects + 0x180 + frame * 0x240
    col, mc = [], []
    for r in range(16):
        w = words(dat, base + r * 36, 18)
        col.append(sum((planes_to_indices(w[4 * g:4 * g + 4]) for g in range(3)), []))
        mc.append(sum((bits(x) for x in w[12:15]), []))
    return np.array(col, np.uint8), np.array(mc, np.uint8)


def barrier(dat, frame):
    """-> colours (8 x 16), mask C (8 x 16)."""
    base = Objects + 0x1740 + frame * 96
    col, mc = [], []
    for r in range(8):
        w = words(dat, base + r * 12, 6)
        col.append(planes_to_indices(w[0:4]))
        mc.append(bits(w[4]))
    return np.array(col, np.uint8), np.array(mc, np.uint8)


def place(kind, args):
    """A call -> (x, y) of its top-left pixel."""
    if kind == 'slot':
        return args[1] * 8, args[2] * 8
    off = args[1]
    return (off % 160) // 8 * 16, off // 160


def apply(dat, kind, args, bg, maskc):
    """A call's effect on the clean background (ST colours) and mask C, as the ST has it."""
    x, y = place(kind, args)
    if kind == 'slot':
        bg[y:y + 8, x:x + 16] = slot(dat, args[0])
    elif kind == 'gate':
        col, mc = gate(dat, args[0])
        bg[y:y + 16, x:x + 48] = col
        maskc[y:y + 16, x:x + 48] = mc
    elif kind == 'barrier':
        col, mc = barrier(dat, args[0])
        region = bg[y:y + 8, x:x + 16]
        region[col != 0] = col[col != 0]
        maskc[y:y + 8, x:x + 16] = mc


Background = ('slot', 'gate', 'barrier')
