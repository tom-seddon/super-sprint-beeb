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


# The moving objects, drawn into the screen being drawn each frame over everything before them, colour 8
# transparent (the sparks', banner's and explosion's routines; the tornado's colour 0). Their frames' planes
# are stored 0, 2, 1, 3, as the cars' are, but for the sparks', which are bytes in the screen's order.

def _words_frame(dat, off, rows, order=(0, 2, 1, 3)):
    out = []
    for r in range(rows):
        w = words(dat, off + r * 8, 4)
        out.append([sum(((w[k] >> (15 - x)) & 1) << order[k] for k in range(4)) for x in range(16)])
    return np.array(out, np.uint8)


def banner(dat, frame):
    """F_0148BE's frames (the banners): 16 x 8."""
    return _words_frame(dat, Objects + 0x1BC0 + frame * 64, 8)


def tornado(dat, frame):
    """F_0147A0's frames (the tornado, 3 of them): 16 x 16, colour 0 transparent, drawn at any pixel. (The
    routine sign-extends each plane word before shifting it, which would smear a set leftmost pixel; none
    of the frames has one.)"""
    base = Objects + frame * 128
    assert not any(w & 0x8000 for w in words(dat, base, 64))
    return _words_frame(dat, base, 16)


def explosion(dat, frame):
    """F_0152E0's frames: 16 x 14, at the wrecked car's place."""
    return _words_frame(dat, Objects + 0x5BC0 + frame * 0x70, 14)


def spark(dat, frame):
    """F_014B1C's frames: 8 x 8, bytes in the screen's plane order."""
    base = Objects + 0x1240 + frame * 32
    return np.array([[sum(((dat[base + r * 4 + p] >> (7 - x)) & 1) << p for p in range(4)) for x in range(8)]
                     for r in range(8)], np.uint8)


def spark_state(extra, i):
    """A spark's frame and place, from the state logged with its call (G_01E090, G_01E0A0): (frame, x, y), x
    on an 8-pixel boundary; or None if it isn't out."""
    w = lambda a: extra.get(str(a), 0) << 8 | extra.get(str(a + 1), 0)
    x, y = w(0x1E0A0 + 4 * i), w(0x1E0A0 + 4 * i + 2)
    if x == 0:
        return None
    return w(0x1E090 + 2 * i), x & ~7, y


def draw(screen, sprite, x, y):
    """A sprite into an image of ST colours, colour 8 transparent, clipped to the screen."""
    h, w = sprite.shape
    for r in range(h):
        if 0 <= y + r < screen.shape[0]:
            for c in range(w):
                if sprite[r, c] != 8 and 0 <= x + c < screen.shape[1]:
                    screen[y + r, x + c] = sprite[r, c]


def heli_compose(dat, variant, colour, frame):
    """F_0146DA: a helicopter frame composed for the wreck, its pixels with plane 0 set and planes 1 and 2 clear
    recoloured by colour (the routine's second argument): below 2 into plane 1, 2 into plane 2, above 2 into
    planes 0 and 2. The vertical variants (0, 1): 36 rows of 32 pixels, each row two groups of 4 plane
    words, then the mask's two words (set: the screen kept). The sideways ones (2, 3), drawn by F_0144AA:
    26 rows of 64 pixels, each row two such units, left then right. -> (colours, mask), 36 x 32 or
    26 x 64."""
    rows, size, base = (52, 0x410, Objects + 0x24C0 + 0x1680) if variant & 2 else (36, 0x2D0, Objects + 0x24C0)
    base += ((variant & 1) * 4 + frame) * size
    col, mask = [], []
    for r in range(rows):
        w = list(words(dat, base + r * 20, 10))
        for g in range(2):
            p0, p1, p2, p3 = w[4 * g:4 * g + 4]
            m = p0 & ~p1 & ~p2 & 0xFFFF
            p0 &= ~m
            if colour < 2:
                p1 |= m
            elif colour == 2:
                p2 |= m
            else:
                p0 |= m
                p2 |= m
            w[4 * g:4 * g + 4] = [p0 & 0xFFFF, p1, p2, p3]
        col.append(sum((planes_to_indices(w[4 * g:4 * g + 4]) for g in range(2)), []))
        mask.append(bits(w[8]) + bits(w[9]))
    col, mask = np.array(col, np.uint8), np.array(mask, np.uint8)
    if variant & 2:
        col, mask = col.reshape(26, 64), mask.reshape(26, 64)
    return col, mask


def draw_masked(screen, col, mask, x, y):
    """A sprite with its own mask (set: the screen kept), clipped to the screen."""
    h, w = col.shape
    for r in range(h):
        if 0 <= y + r < screen.shape[0]:
            for c in range(w):
                if not mask[r, c] and 0 <= x + c < screen.shape[1]:
                    screen[y + r, x + c] = col[r, c]
