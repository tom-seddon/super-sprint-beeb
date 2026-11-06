"""The ST's front-end pictures from SUPER.DAT (Phase 5, step 7; docs/st-graphics.md "The front end").

Usage: st_frontend.py check   every decoder against tools/st_screens.py's captured screens, the differences counted
"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import st_screens as S
import stgfx

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
Base = 0x29500                          # where SUPER.DAT is loaded: a pointer less this is its offset


def dat():
    return open(os.path.join(ROOT, 'orig/st/SUPER.DAT'), 'rb').read()


def unrle(d, off):
    """F_014F9C: a screen, plane by plane. The first word's the escape: the escape, a word and a count is that word that
    many times; any other word is itself. -> (the 32,000 bytes, the bytes read)."""
    word = lambda i: d[off + 2 * i] << 8 | d[off + 2 * i + 1]
    esc, i = word(0), 1
    out = np.zeros(16000, dtype='>u2')
    for plane in range(4):
        n = 0
        while n < 4000:
            if word(i) == esc:
                v, c = word(i + 1), word(i + 2)
                i += 3
                out[n * 4 + plane:(n + c) * 4 + plane:4] = v
                n += c
            else:
                out[n * 4 + plane] = word(i)
                i += 1
                n += 1
    return out.tobytes(), 2 * i


def shot(name):
    """A captured screen: (the indices, its step's event: tools/st_screens.py's rgb() colours it)."""
    d = os.path.join(ROOT, 'build/st_screens')
    for f in ('screens.json', 'options.json'):
        t = json.load(open(f'{d}/{f}'))
        for e in t['events']:
            if e['kind'] == 'step' and t['script']['steps'][e['index']].get('shot') == name:
                which = (0xF8000, 0x21800).index(e['base'])
                return stgfx.planar_to_indices(open(f'{d}/{name}_{which}.bin', 'rb').read(), 320, 200), e
    raise KeyError(name)


def diff(a, b):
    """Differing pixels, and their box."""
    ys, xs = np.nonzero(a != b)
    return (len(ys), (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(ys) else None)


class Canvas:
    """A screen being drawn, as the ST's routines draw it, in colour indices. Groups are 16 pixels."""

    def __init__(self, mem):
        self.px = np.zeros((200, 320), np.uint8)
        self.mem = mem                  # the game's data and BSS, from a trace's dump: the fonts, the table
        self.d = dat()

    def fill(self, c, gx, y, gw, h):    # F_0169D4
        self.px[y:y + h, gx * 16:(gx + gw) * 16] = c

    def blit(self, off, gx, y, gw, h):  # F_0168CC: gw groups of 4 planes, h lines, from the block
        raw = self.d[off:off + gw * 8 * h]
        self.px[y:y + h, gx * 16:(gx + gw) * 16] = stgfx.planar_to_indices(raw, gw * 16, h)

    def mirror_car(self):               # F_016DCA: lines 65-108, the left 10 groups, flipped onto the right
        self.px[65:109, 160:320] = self.px[65:109, 0:160][:, ::-1]

    def tile(self, block, n, col, y):   # F_016E12: an 8 x 8 tile at block + &C60, a byte a plane a line
        off = block + 0xC60 + (n & 15) * 32
        for line in range(8):
            for j in range(8):
                self.px[y + line, col * 8 + j] = sum(((self.d[off + line * 4 + p] >> (7 - j)) & 1) << p for p in range(4))

    def tiles(self, block, n, col, y, dcol, dy, count):     # F_016E6C
        for _ in range(count):
            self.tile(block, n, col, y)
            col += dcol
            y += dy * 8

    def glyph(self, g, x, y, c0, c1):   # F_016C7A: 6 x 6, from G_01D43C, c1 where it's set, c0 where it's not
        off = 0x1D43C - Region + (g & 255) * 8
        for line in range(6):
            b = self.mem[off + line]
            for j in range(6):
                self.px[y + line, x + j] = c1 if b >> (7 - j) & 1 else c0

    def code(self, ch):                 # a character's glyph
        return (ch & 31) + 11 if ch > 0x40 else self.mem[0x1D118 - Region + (ch & 31)]

    def small(self, s, x, y, c0, c1):   # F_016BE8
        for ch in s:
            self.glyph(self.code(ch), x, y, c0, c1)
            x += 6

    def big(self, s, c, x, y):          # F_016F4E, F_016EB8: 12 lines of a mask word and a data word, 11 pixels on
        for ch in s:
            if ch != 0x20:
                off = 0x1D594 - Region + ((ch & 31) - 1) * 0x30
                for line in range(12):
                    m = self.mem[off + line * 4] << 8 | self.mem[off + line * 4 + 1]
                    v = self.mem[off + line * 4 + 2] << 8 | self.mem[off + line * 4 + 3]
                    for j in range(16):
                        if x + j < 320:
                            kept = self.px[y + line, x + j] if m >> (15 - j) & 1 else 0
                            self.px[y + line, x + j] = (kept | c) if v >> (15 - j) & 1 else kept
            x += 11

    def text(self, a):
        """The string at address a."""
        return bytes(self.mem[a - Region:self.mem.index(0, a - Region)])

    def entry(self, n, x, y, c0, c1):   # F_0171B6: a high score's line
        if n >= 10:
            self.glyph(n // 10, x, y, c0, c1)
        self.glyph(n % 10, x + 6, y, c0, c1)
        for i in range(6):
            self.glyph(self.mem[0x1D382 - Region + n * 6 + i], x + 17 + i * 6, y, c0, c1)
        for i in range(3):
            self.glyph(self.mem[0x1D324 - Region + n * 3 + i], x + 59 + i * 6, y, c0, c1)


Region = 0x1C722
Block = 0                               # G_01F234: 44 lines of 9 groups, the car, then 32-byte tiles from &C60


def frame(c, title, foot):
    """The high scores' and lap records' frame (F_0172EA, F_01BF34)."""
    c.fill(1, 0, 0, 20, 200)
    c.blit(Block, 0, 0x41, 9, 0x2C)
    c.mirror_car()
    for a in ((3, 0, 0x13, 20, 0x1E), (3, 7, 0x31, 6, 0x18), (3, 0, 0x70, 1, 0x58), (3, 0x13, 0x70, 1, 0x58), (3, 0, 0xC0, 20, 8)):
        c.fill(*a)
    c.big(c.text(title), 15, 0x1C, 0x1B)
    for a in ((0, 0, 0xB, 1, 0, 0x28), (0, 0, 0x31, 1, 0, 0xD), (0, 0xE, 0x49, 1, 0, 0xC), (0, 0x1B, 0x31, 1, 0, 0xD), (0, 3, 0xB8, 1, 0, 0x22),
              (1, 2, 0x70, 0, 1, 9), (1, 0x25, 0x70, 0, 1, 9), (1, 0xD, 0x39, 0, 1, 2), (1, 0x1A, 0x39, 0, 1, 2), (0, 0, 0x68, 1, 0, 2), (0, 0x26, 0x68, 1, 0, 2)):
        c.tiles(Block, *a)
    for a in ((2, 0xD, 0x31), (3, 0x1A, 0x31), (5, 0xD, 0x49), (4, 0x1A, 0x49), (7, 2, 0x68), (6, 0x25, 0x68), (8, 2, 0xB8), (9, 0x25, 0xB8)):
        c.tile(Block, *a)
    c.small(c.text(foot), 0x64, 0xC0, 3, 15)


def scores_frame(mem):
    """The high scores without the table."""
    c = Canvas(mem)
    frame(c, 0x1F344, 0x1F35E)
    return c.px


def scores(mem):
    c = Canvas(mem)
    c.px = scores_frame(mem)
    n = 1
    for i in range(3):
        c.entry(n, 0x7A, 0x33 + i * 7, 3, 15)
        n += 1
    for x in (0x1E, 0x7A, 0xD6):
        for i in range(9):
            c.entry(n, x, 0x76 + i * 7, 1, 15)
            n += 1
    return c.px


def records_frame(mem):
    """The lap records without the table."""
    c = Canvas(mem)
    frame(c, 0x1F736, 0x1F750)
    return c.px


def records(mem):
    c = Canvas(mem)
    c.px = records_frame(mem)
    c.small(c.text(0x1F766), 0x76, 0x3C, 3, 15)
    for n in range(8):
        x, y = n // 4 * 0x94 + 0x20, 0x86 + 12 * (n & 3)
        c.small(c.text(0x1F776), x, y, 1, 15)
        c.glyph(n + 1, x + 0x24, y, 1, 15)
        t = min((mem[0x1D314 - Region + 2 * n] << 8 | mem[0x1D315 - Region + 2 * n]) // 5, 999)
        if t > 99:
            c.glyph(t // 100, x + 0x36, y, 1, 15)
        c.glyph(t // 10 % 10, x + 0x36 + 6, y, 1, 15)
        c.glyph(10, x + 0x36 + 12, y, 1, 15)
        c.glyph(t % 10, x + 0x36 + 18, y, 1, 15)
        c.small(c.text(0x1F77C), x + 0x54, y, 1, 15)
    return c.px


def checker(c):                         # F_01AA88, F_016912: 16 x 7 squares of 20, only over colour 0
    for row in range(7):
        for col in range(16):
            k = (col + row & 1) + 11
            if (row in (0, 6) or col in (0, 15)) and k == 12:
                k = 13
            area = c.px[row * 20 + 41:row * 20 + 61, col * 20:col * 20 + 20]
            area[area == 0] = k


def prepare(mem, playing):
    """F_018776's picture: the cars, the bands, the checker, each panel (playing: which cars 0-2 are)."""
    c = Canvas(mem)
    c.px[:] = stgfx.planar_to_indices(unrle(c.d, 0x0DA0)[0], 320, 200)
    c.fill(13, 0, 0, 20, 0x29)
    c.fill(13, 0, 0xB5, 20, 0x13)
    checker(c)
    for car in range(3 if playing else 0):
        l2, col = 15 + 0x6B * car, car + 1
        if playing[car]:
            for a, x, y in ((0x1F422, 0x18, 3), (0x1F428, 9, 0xD), (0x1F434, 6, 0x17), (0x1F440, 0x24, 0x21)):
                c.small(c.text(a), l2 + x, y, 13, col)
            for a, x, y in ((0x1F442, 0, 2), (0x1F44A, 0x1B, 0x13), (0x1F44E, 0x10, 0x24)):
                c.big(c.text(a), col, l2 + x, y)
        else:
            c.small(c.text(0x1F454), l2 + 0x18, 3, 13, col)
            c.small(c.text(0x1F45A), l2 + 9, 0xD, 13, col)
            c.small(c.text(0x1F466), l2 + 6, 0x17, 13, col)
    return c.px


def canvas_on(px):
    """A canvas over a picture already made."""
    c = Canvas(first_dump())
    c.px = px
    return c


def options_frame(mem, names):
    """The options, as the BBC has them: prepare's picture, each car's name and its keys' labels, the function keys."""
    c = Canvas(mem)
    c.px = prepare(mem, None)
    for car, name in enumerate(names):
        x = (108 * car) + (107 - len(name) * 11) // 2
        c.big(name, car + 1, x, 2)
        for row, label in enumerate((b'left', b'right', b'accel')):
            c.small(label, 108 * car + 6, 17 + row * 8, 13, car + 1)
    c.small(b'f2 ' + names[0] + b' keys  f3 ' + names[1] + b' keys  f4 ' + names[2] + b' keys', 24, 184, 13, 15)
    return c.px


def first_dump():
    t = json.load(open(os.path.join(ROOT, 'build/st_screens/screens.json')))
    return bytes.fromhex(next(e for e in t['events'] if e['kind'] == 'point')['mem'])


def main():
    """Each picture against its captured screen. Exit status 1 if one that should be exact isn't, or anything else
    differs outside the parts that move."""
    import st_tracks as T
    d, mem, bad = dat(), first_dump(), 0
    credits = stgfx.planar_to_indices(unrle(d, 0x2E9F6)[0], 320, 200)
    for name, idx, against, limit, box in (
            ('title (map 8)', T.decode_map(d, 8), 'title', 0, None),
            ('credits', credits, 'credits', 0, None),
            ('high scores', scores(mem), 'scores', 0, None),
            ('lap records', records(mem), 'records', 0, None),
            # the cars' flickering pieces (F_01784A, F_017898, F_0178DE), which move
            ('prepare, two playing', prepare(mem, (1, 1, 0)), 'prepare0', 200, (0, 60, 319, 150)),
            ('prepare, three playing', prepare(mem, (1, 1, 1)), 'prepare1', 200, (0, 60, 319, 150)),
            # the text, the dial, the bonuses and the sparkles over the maps: step 8's to draw
            ('the circle (map 9)', T.decode_map(d, 9), 'circle1', 4000, None),
            ('the select (map 10)', T.decode_map(d, 10), 'select1', 3000, None)):
        want, e = shot(against)
        n, where = diff(idx, want)
        Image.fromarray(S.rgb(idx, e)).resize((640, 400), Image.NEAREST).save(os.path.join(ROOT, f'build/st_screens/dec_{against}.png'))
        ok = n <= limit and (box is None or where is None or (where[0] >= box[0] and where[1] >= box[1] and where[2] <= box[2] and where[3] <= box[3]))
        bad += not ok
        print(f'{name}: {n} pixels differ{f" in {where}" if n else ""}{"" if ok else ": WRONG"}')
    print(f'{bad} wrong' if bad else 'every picture as the ST drew it')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
