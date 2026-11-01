"""The HUD row's text (D6), as the 6502 lays it out: what render_model.py draws, and gendata.py's events.

40 characters: from column 1, each player's score and laps in their car's colour, "999,999 L4" (the score's 6
digits, the comma blank while the thousands are, then the laps completed, as the ST shows them), 11
columns apart; then "T6" (the track) at column 34 and "D4" (the drone's laps) at 37, in white. A blank is the
space glyph in colour 0.
"""
from font import Comma, LetterL, LetterT, LetterD, Space

Width = 40
PlayerCol = (1, 12, 23)
PlayerColour = (3, 1, 2)            # the cars' body colours in option B: white, green, yellow
TrackCol, DroneCol = 34, 37
White = 3
Blank = (Space, 0)


def score_digits(hexscore):
    """The ST's 6 score bytes (one BCD digit each, &80 a leading blank) -> 6 glyph codes."""
    return [Space if b & 0x80 else b for b in bytes.fromhex(hexscore)]


def text(laps, scores, track):
    """laps: 4 cars' laps completed; scores: the ST's hex score strings; track 0-7 -> 40 (code, colour)."""
    out = [Blank] * Width
    for car in range(3):
        c, col = PlayerColour[car], PlayerCol[car]
        d = score_digits(scores[car])
        for i, g in enumerate(d[:3] + [Comma if d[2] != Space else Space] + d[3:]):
            out[col + i] = (g, c)
        out[col + 8] = (LetterL, c)
        out[col + 9] = (laps[car], c)
    out[TrackCol] = (LetterT, White)
    out[TrackCol + 1] = (track + 1, White)
    out[DroneCol] = (LetterD, White)
    out[DroneCol + 1] = (laps[3], White)
    return [Blank if g == Space else (g, c) for g, c in out]
