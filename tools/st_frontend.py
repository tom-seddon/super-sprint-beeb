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


def select_panels(mem, playing):
    """F_019FB6 and F_01A062: the select screen's panels, above its tracks (playing: which cars 0-2 are)."""
    c = Canvas(mem)
    for car in range(3):
        l2, col = 15 + 0x6B * car, car + 1
        if playing[car]:
            c.big(c.text(0x1F680), col, l2, 3)
            c.big(c.text(0x1F688), col, l2, 0x14)
        else:
            for a, x, y in ((0x1F690, 0x18, 3), (0x1F696, 9, 0xF), (0x1F6A2, 0x12, 0x1B)):
                c.small(c.text(a), l2 + x, y, 0, col)
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


def upgrade_boxes(c):
    """F_016AF2, F_016A6C, F_016A44: the top left box, in the plane it's drawn in, then F_016B76 and F_016BB8, which mirror it into the
    other three planes: each box a colour of its own, 1, 2, 4 and 8, so a palette entry lights it."""
    p = np.zeros((200, 320), np.uint8)
    for x, y, n in ((6, 0x3F, 0x35), (0x96, 0x3F, 0x1E)):
        p[y:y + n, x:x + 3] = 1
    for x, y, n in ((6, 0x3F, 0x93), (6, 0x71, 0x79)):
        p[y:y + 3, x:x + n] = 1
    for line in range(25):
        for g in range(3):
            w = c.d[0x3140 + (line * 3 + g) * 2] << 8 | c.d[0x3140 + (line * 3 + g) * 2 + 1]
            for j in range(16):
                p[91 + line, 112 + g * 16 + j] = w >> (15 - j) & 1
    p[63:116, 160:] = p[63:116, :160][:, ::-1] * 2
    p[126:179] = p[63:116][::-1] * 4
    return p


UpgradeText = ((0x1F6E4, 14, 74), (0x1F6EA, 14, 89), (0x1F6F4, 206, 74), (0x1F6FC, 206, 89), (0x1F706, 14, 137), (0x1F70C, 14, 152),
               (0x1F71A, 206, 137), (0x1F724, 206, 152))
UpgradeLevels = ((14, 105), (206, 105), (14, 168))      # traction, top speed, turbo: F_01A99E's "level" and its digits


def upgrades(mem, heading=(), levels=(0, 0, 0), colour=6, bars=False):
    """F_01A130's picture but for the HUD and the dial: heading the (text, y) lines in colour, levels each upgrade's; bars puts each
    level's line on a bar of colour 13 (the BBC's: small coloured text is lost on the checks)."""
    c = Canvas(mem)
    c.fill(13, 0, 0, 20, 0x29)
    c.fill(13, 0, 0xB5, 20, 0x13)
    c.px[:] = np.where(upgrade_boxes(c) > 0, upgrade_boxes(c), c.px)
    for (x, y), level in zip(UpgradeLevels, levels):
        ground = 13 if bars else 0
        if bars:
            c.px[y:y + 6, x:x + 90] = 13
        c.small(c.text(0x1F72A), x, y, ground, 15)
        for n in range(1, 6):
            c.glyph(n, x + 24 + n * 12, y, ground, 15 if n > level else colour)
        if level == 5:
            c.small(c.text(0x1F730), x + 30, y - 38, 0, colour)
    checker(c)
    for s, y in heading:
        c.big(s, colour, (320 - len(s) * 11) // 2 if y == 30 else 12, y)
    for a, x, y in UpgradeText:
        c.big(c.text(a), 15, x, y)
    return c.px


CircleBelow = 44                        # the capture's third car's best lap, less than 0: tenths, found by trying them
CircleBands = (18, 74, 140)             # the winner's circle's bands' first lines
CirclePlaces = ((1, 7), (2, 7), (2, 10), (3, 7))    # each place's band and first of its three palette entries (G_01CFAE, G_01CFB6)


def circle_parts(idx):
    """(place, part), both (200, 320): which place's car a pixel of map 9 is in, -1 none, and which of its three entries: 1 the sides and
    front spoiler, 2 the edges and heading, 3 the bodywork and rear spoiler."""
    y = np.arange(200)[:, None] * np.ones((1, 320), int)
    band = sum((y >= b).astype(int) for b in CircleBands)
    place, part = np.full((200, 320), -1), np.zeros((200, 320), int)
    for p, (b, e) in enumerate(CirclePlaces):
        for k in range(3):
            m = (band == b) & (idx == e + k)
            place[m], part[m] = p, k + 1
    return place, part


def circle_frame(d, n):
    """The figure's frame n (F_01BC36): (32, 48) indices."""
    return stgfx.planar_to_indices(d[0x29C4E + n * 0x300:0x29C4E + (n + 1) * 0x300], 48, 32)


def circle_sparkle(d, n):
    """A sparkle's frame n (F_01BDCE): (8, 8) indices, and what's kept of what's under it, 1 kept."""
    px, keep = np.zeros((8, 8), np.uint8), np.zeros((8, 8), np.uint8)
    for line in range(8):
        row = d[0x2CC5A + n * 80 + line * 10:][:10]
        for j in range(8):
            px[line, j] = sum((row[p * 2] >> (7 - j) & 1) << p for p in range(4))
            keep[line, j] = row[8] >> (7 - j) & 1
    return px, keep


def circle(mem, frame, figures, times):
    """The winner's circle as F_01AC1C draws it over map 9, but for the HUD and the sparkles. frame: the figure's. figures: each place's three bonuses
    so far; times: each place's average and best laps in tenths of a second, F_01BC74's value."""
    import st_tracks as T
    word = lambda a, n: [int.from_bytes(mem[a - Region + i * 2:a - Region + i * 2 + 2], 'big', signed=True) for i in range(n)]
    px = T.decode_map(dat(), 9).copy()
    px[144:176, 160:208] = circle_frame(dat(), frame)
    c = canvas_on(px)
    ground = word(0x1CFBE, 4)
    rows = ((0x1CFCE, 0x1CFC6), (0x1CFDE, 0x1CFD6), (0x1CFEE, 0x1CFE6))
    for place in range(4):
        for (ax, ay), v in zip(rows, figures[place]):      # F_01BD40: 3 figures, no leading 0s; and the last 0
            x, y = word(ax, 4)[place], word(ay, 4)[place]
            on = 0
            for i, d in enumerate((v // 1000, v // 100 % 10, v // 10 % 10)):
                on += d
                if on:
                    c.glyph(d, x + i * 6, y, ground[place], 0)
            c.glyph(0, x + 18, y, ground[place], 0)
        for (ax, ay), v in zip(((0x1CFFE, 0x1CFF6), (0x1D00E, 0x1D006)), times[place]):     # F_01BC74
            x, y = word(ax, 4)[place], word(ay, 4)[place]
            v = min(v, 999)
            if v > 99:
                c.glyph(v // 100, x, y, ground[place], 0)
            trunc = lambda a, b: abs(a) // b * (1 if a >= 0 else -1)
            c.glyph(trunc(v, 10) % 10 if v >= 0 else -(abs(v) // 10 % 10), x + 6, y, ground[place], 0)
            c.glyph(10, x + 12, y, ground[place], 0)
            c.glyph(v % 10 if v >= 0 else -(abs(v) % 10), x + 18, y, ground[place], 0)
    return px


def first_dump():
    t = json.load(open(os.path.join(ROOT, 'build/st_screens/screens.json')))
    return bytes.fromhex(next(e for e in t['events'] if e['kind'] == 'point')['mem'])


def c_text(mem, a):
    return Canvas(mem).text(a)


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
    # the circle (F_01AC1C), but for the HUD and the sparkles, which are the game's. The figures and times are read off the capture: the third's best
    # lap was below 0, which the ST's digits show from past the font.
    word = lambda a, n: [int.from_bytes(mem[a - Region + i * 2:a - Region + i * 2 + 2], 'big', signed=True) for i in range(n)]
    for shot_name, frame, figures in (('circle0', 3, ((410, 410, 410), (410, 410, 410), (250, 410, 410), (0, 400, 410))),
                                      ('circle1', 4, ((1000, 530, 550), (500, 500, 510), (250, 850, 1570), (0, 400, 430)))):
        want, e = shot(shot_name)
        idx = circle(mem, frame, figures, ((62, 60), (69, 68), (0, -CircleBelow), (90, 84)))
        idx[:22] = want[:22]
        for x, y in zip(word(0x1CEBE, 16), word(0x1CE9E, 16)):
            idx[y:y + 8, x * 8:x * 8 + 8] = want[y:y + 8, x * 8:x * 8 + 8]
        n, where = diff(idx, want)
        bad += n > 0
        print(f'{shot_name}: {n} pixels differ{f" in {where}" if n else ""} outside the HUD and sparkles{": WRONG" if n else ""}')
    # the upgrades (F_01A130), but for the HUD, the dial and the seconds, which are the game's: the boxes in the planes they're drawn in
    for shot_name in ('upgrade0', 'upgrade1', 'upgrade2'):
        want, e = shot(shot_name)
        idx = upgrades(mem, ((b'blue car', 30), (c_text(mem, 0x1F6C8), 45)))
        idx[:41] = want[:41]
        idx[99:143, 128:192] = want[99:143, 128:192]
        idx[184:195, 155:171] = want[184:195, 155:171]
        n, where = diff(idx, want)
        Image.fromarray(S.rgb(idx, e)).resize((640, 400), Image.NEAREST).save(os.path.join(ROOT, f'build/st_screens/dec_{shot_name}.png'))
        bad += n > 0
        print(f'{shot_name}: {n} pixels differ{f" in {where}" if n else ""}{"" if not n else ": WRONG"}')
    print(f'{bad} wrong' if bad else 'every picture as the ST drew it')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
