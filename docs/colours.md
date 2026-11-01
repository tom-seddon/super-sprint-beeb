# Phase 2: converting the graphics to MODE 1

The ST's 8 tracks and its cars, converted to BBC MODE 1 in six palette options, so the palette (D1) can be
chosen on the real art. Done 2026-11-01. Everything here is made by the scripts in `tools/` from `orig/st`;
generated files go to `build/` and the comparison pictures to `docs/img/`.

## The pipeline

1. `tools/st_dump_tracks.py` runs the original in Hatari and saves each track's finished background (tiles plus
   trees) and its three masks (solid, road, priority) the moment the track set-up returns. Decoding the tile
   maps alone (`tools/st_tracks.py`) gives the same picture without the trees.
2. `tools/convert.py build/conv` maps each ST colour to one MODE 1 logical colour, a checkerboard of two, or a
   2 × 2 pattern. The pattern is fixed to the screen for the background and to the sprite for sprites. Each car
   has its own map, so its body colour can differ while its outline and windows stay shared. It writes each
   track as 16,000 bytes in the BBC's character-cell order (`build/conv/<option>_t<n>_bg.bin`), the same with
   five sample cars drawn in (`<option>_t<n>.bin`), and PNGs. The cars are drawn behind the priority mask, as on
   the ST.
3. `tools/compare_sheets.py` makes the pictures in `docs/img/`.
4. `tools/make_viewer.py` builds a bootable disc per option with Baron (`build/viewer/disc<option>.ssd`;
   `make viewer`). SHIFT+BREAK on a Master: its `!BOOT` types a BASIC viewer in and runs it. The viewer sets
   MODE 1, prints a sample HUD row, then sets the CRTC to 26 rows (R6 = 26, R7 = 31) from `&3F00` (R12 = `&07`,
   R13 = `&E0`) and loads the tracks to `&4180` one at a time: any key shows the next.
   `docs/img/jsbeeb-option-a2-track1.png` is jsbeeb's Master 128 showing option A2's disc: the layout, the
   HUD row and the converted bytes are right, and it looks the same as the PNG (compared by eye, not pixel by
   pixel).

## The ST's colours

The race uses one 16-colour palette for every track. Over the 8 tracks, 56% of pixels are the road's grey
(`333`), 15% grass green (`153`), 6.5% the dark grey of shadows and the road's shading (`222`), 4.2% dark
green, and the rest whites, greys and yellows. The players' cars are blue `147`, red (pink `703`) and yellow
`773` (also the hazard stripes); car 3, always a drone, is green `153` (the grass's colour). A player's car
that a drone drives is grey `444` with its colour as stripes. They share black outlines and wheels, and white
and grey highlights. Full table in `docs/st-graphics.md`.

## The options

| Option | Palette | Road | Cars: blue, red, yellow; car 3 and drone-driven cars | Pictures |
|---|---|---|---|---|
| A | black, green, yellow, white | black | white, green, yellow; grey checkerboard | `option-a-tracks.png` |
| A2 | as A | black | as A, but every car's black pixels drawn as a grey checkerboard; car 3 and drones hollow (black inside the grey outline) | `option-a2-tracks.png` |
| B | black, green, yellow, white | grey checkerboard, shadows black | white, green, yellow; black | `option-b-tracks.png` |
| B2 | as B | one white pixel in four, shadows black | as B | `option-b2-tracks.png` |
| C | black, red, green, white | grey checkerboard, stripes red | white, red, green; black | `option-c-tracks.png` |
| D | black, blue, green, white | blue/black checkerboard | blue, green, white; black | `option-d-tracks.png` |

`track4-options.png` and `track6-options.png` put every option side by side on one track, with the ST's
original. `cars-options.png` shows the cars in four directions on each option's road, 4 × size: blue, red,
yellow, car 3, and the blue car driven by a drone.

## What they show

- **A** gives the cleanest tracks: the yellow and black stripes, white kerbs and green grass read well. But
  the road's shading goes, so bridges and underpasses show only by their kerbs (track 6's central crossing is
  hard to read). And the cars' black outlines and wheels vanish into the road: each car is only its body
  colour, and the drones' checkerboard breaks up into dots.
- **A2** keeps A's tracks and fixes the cars: with their outlines drawn grey, every car is clear in every
  direction, and the drones are distinctive hollow outlines. The white car's grey outline blends into its
  body more than the others'. The bridges are still drawn only by their kerbs.
- **B** and **C** keep the ST's look and its shading: underpasses and the shadows by the walls are black on a
  grey road. Cars stand out by their black outlines. But the checkerboard covers 56% of the screen, and at 320
  pixels across it shows as a fine pattern on an RGB monitor, behind everything. C's red kerbs look like
  racing kerbs, but its yellow car has to become green.
- **B2**'s road is darker and closer to the ST's, but the dots read as a pattern too, and the black drone
  gets lost among them.
- **D**'s blue road is distinctive, but the blue car is weak on it.

**Recommendation: A2.** Clean tracks, and cars that are easy to tell apart, which is what the game needs. Its
weakness is the bridges. If that matters more, B is the alternative: it keeps the depth, at the cost of a busy
road. **Your call (D1).**

Smaller points, whichever is chosen:
- The cars' colours can't follow the ST's (blue, red, yellow, and a green car 3): no palette with a readable
  road and green grass has room for them. A2's players are white, green and yellow, and every drone is a
  hollow grey outline (a drone-driven player's car keeps its colour as stripes).
- The HUD row's colours match the cars, so for every option it uses the play area's palette, and **no palette
  split is needed** (the plan expected one). The drone's lap is printed in white.
- The ST map's "TRACK n" and "DRONE LAP" text, in the bottom row of tiles, and the top rows' grandstands under
  the ST's HUD, convert as they are. With the HUD in its own row (D6) the text cells need repainting with
  grass at build time.

## Sizes

ZX02 (Baron's transform, `rich/teddyboy/src/zx02.6502`) on each track's 16,000 bytes, without cars:

| Option | Tracks 1-8 (bytes) | Total |
|---|---|---|
| A | 2,744, 2,339, 2,365, 2,698, 2,141, 2,511, 2,446, 2,018 | 19,262 |
| B | 2,815, 2,584, 2,476, 2,855, 2,360, 2,729, 2,691, 2,244 | 20,754 |
| C | 2,812, 2,575, 2,469, 2,845, 2,360, 2,729, 2,691, 2,243 | 20,724 |
| D | 2,904, 2,558, 2,520, 2,863, 2,357, 2,687, 2,664, 2,210 | 20,763 |

The ST's 1-bit masks, 8,000 bytes each, pack to 507-811 bytes (road, 5,525 for all 8) and 358-778 bytes
(priority, 4,145 for all 8).

So all 8 tracks' art and masks come to about 30K packed. That would fit in the Master's 64K of sideways RAM on
its own, but with the cars, objects, attribute maps, drone paths, code and sound the race needs about 90K
(`docs/plan.md`), so the plan loads one track's data per race (D3).
