# Phase 3: the renderer test

A BBC program that draws the ST's own race: the four cars' positions, frames and levels, recorded from the
original every frame, erased and drawn at 50 fps on a Master 128 in MODE 1, double-buffered in shadow RAM.
Every frame it draws is checked byte for byte against a model made from the ST's data. Started 2026-11-01.

## What it is

- **The race**: the ST's attract-mode race on track 6 (index 5: bridges, an overpass and a jump), 1,144
  frames, recorded in Hatari by `tools/st_trace_cars.py` (at each flip: the draw order, and per car its
  pixel x and y, facing and flags). The demo draws every car in its player colours, so the frame is
  car × 16 + facing.
- **The disc** (`make beeb`, `build/sprint.ssd`): `!BOOT` checks for a Master (OSBYTE 0), finds 3 banks of
  sideways RAM that take a write and that the ROM type table doesn't list (D4), copies SPRINTA, SPRINTB
  and SPRINTC into them and runs SPRINT. SPRINT's loader claims NMIs (OSBYTE 143), hooks IRQ1V, copies
  main RAM's code to `&0E00`, makes the tables, and starts the vsync interrupt. It leaves the OS's memory
  alone (D7). The frame loop then plays the race over and over.
- **The screen**: MODE 1, 26 rows from `&3F00` (R6 = 26, R7 = 31, R12/R13 = `&07E0`), the HUD's row
  and the 25-row play area from `&4180`. One screen in main RAM, one in shadow RAM. The
  vsync IRQ (the System VIA's CA1, its only interrupt) flips ACCCON's D bit when the main loop asks; the
  main loop then flips X, so it draws into the screen not shown. All the code and variables that run
  during a frame are below `&3000` or in a bank, so X never hides them.
- **The check** (`make check`, `tools/render_check.mjs`): headless jsbeeb's Master 128, the real IRQ. At
  each frame's end the screen just drawn (main or shadow RAM, by X: the HUD's row and the play area) is
  compared with
  `tools/render_model.py`'s frame: the clean background, then each car in the ST's order, its ST frame
  mapped through the car's colours (convert.py), drawn where the ST frame isn't colour 8 and, for a car on
  the ground, where mask C isn't 0. The model shares nothing with the BBC's data path (trimming, shifts,
  the key colour, the priority cells). Its HUD row is drawn from the ST's scores and laps by
  `tools/hud.py`'s layout and `tools/font.py`'s glyphs, brought up to date by the same rule as the 6502's.
  Broken on purpose, it fails: with priority off, 282 frames are wrong; with one car's erase skipped, 96 of
  the first 100; with two players' HUD colours swapped, 18 of the first 20.

## How it draws

- **Car frames**: each of the 64 frames (cars 0-3 × 16 facings) is stored at each of the 4 pixel shifts,
  trimmed to the bytes and rows its pixels cover, a column's rows together, each frame-shift wholly in a
  page and 7 bytes or more in (`tools/gendata.py`). 9,956 bytes of frames, 10,615 placed.
- **Transparency without a mask**: every car's frames use black, white and at most one body colour, so the
  fourth colour is the key. Frames store 2-bit values: 0 black, 1 the body, 2 transparent, 3 white. Two
  256-byte tables do the rest: `MaskTab` (the key's pixels: the screen's to keep) and a data table (the
  pixels, the key cleared, 1 drawn green, yellow or white). The yellow car's yellow is stored as 1. A byte
  is `(screen AND MaskTab) OR Data`. The drone-driven cars (frames 64-127) share one set of shapes between
  all three player cars, the stripes as value 1, so a fourth table (1 white) covers them.
- **The plot**: a character row (a band) at a time. In a band a column's lines are consecutive on the
  screen and in the frame, so Y, the line in the cell, indexes every column alike. The loop draws one line
  of every column a pass, its five column blocks unrolled (`LDX frame,Y : LDA screen,Y : AND MaskTab,X :
  ORA Data,X : STA screen,Y`, 21 cycles a byte); the operands' low bytes are patched once a band, the
  loop's branch back by the car's width.
- **Priority**: a car on the ground (not elevated or airborne) goes under mask C. Each 8 x 8 cell with hidden
  pixels has its 8 bytes of 1-bit mask and a class byte saying, for each 4-pixel half, whether none, all or
  some of it is hidden (333 cells on track 6: 2,664 + 333 bytes). A map gives each cell's number in its
  row; it's stored a row's span at a time, from 2 cells before the row's first such cell to 2 after its
  last (643 bytes rather than 1,000), with the first and last, so a band outside the span skips the map.
  In a band with such cells, each of the car's columns is classed by its half-cell: none hidden, it stays
  in the fast loop; all hidden, its block's screen operands point at an 8-byte Junk area instead, so it
  draws nothing; some hidden, the same, and then it goes on its own through a slow loop that keeps the
  screen where the bits are set as well as where the key is (about 52 cycles a byte).
- **The erase**: the box each car drew, two frames before in the same screen, copied back from the clean
  background, a band at a time with the same five unrolled column blocks (`LDA bg,X : STA screen,X`, 9
  cycles a byte). The background lives `&4000` above the screen, at `&8180`-`&BFFF` in its bank. X runs
  from the band's first cell's low byte plus the line, and each block's operand is 8n into the page, so
  only the operands' high bytes are patched a band, and a page crossed among the cells is carried by the
  indexing. (The plot can't do the same: its blocks need X for the table lookups.)

- **The HUD** (D6, `src/hud.6502`, in main RAM): one row of 40 characters, 8 x 8. From column 1, each
  player's score and laps completed in their car's colour (white, green, yellow), `999,999 L3`, 11 columns
  apart; then `T6` (the track) and `D3` (the drone's laps) in white. The score shows all 6 of the ST's
  digits (D6's example had 5; 6 fit), its comma blank while the thousands are; the laps are laps completed,
  as the ST shows them. The text wanted is 40 bytes, a glyph and colour each; each screen keeps what it
  shows. After a change, the screen being drawn has the columns that differ redrawn, at most 4 a frame, the
  screens taking turns until both have caught up, so a score rolling over can't cost a frame (the ST
  spreads its HUD the same way, a player's panel every other frame). A character is its glyph's 8 lines,
  each split into two bytes of 4 pixels through the priority mask's nibble tables and ANDed with the
  colour's bits: about 350 cycles. The glyphs are 15 (the digits, `,`, `L`, `T`, `D`, a space), 120
  bytes, from `tools/font.py`. In the test the changes come from the ST's race (its scores and laps,
  recorded with the cars): 78 of them, 782 bytes in the trace's bank.

- **Background objects** (under way): gates, pop-up barriers and the pickups and hazards in the track's
  slots. The ST draws one into the screen being drawn and the clean background when it changes, and again
  the frame after for its other screen; gates and barriers also write mask C, so the cars' priority around
  them changes as they move (a gate frame hides up to 392 of its 768 pixels). On the BBC
  (`src/objects.6502`, in main RAM): each change's bytes are copied from a fourth bank, the objects' (48
  variants, 4,864 bytes: the slots' 22 sprites, the gates' 5 frames and the barriers' 8, each for an even
  and an odd top line, the patterns' phase), written into the clean background and both screens (a
  barrier over what's there, its colour 0 kept), and a gate's or barrier's priority bits written into its
  cells, which `tools/gendata.py` reserves in the map with class "some hidden", so the plotter goes by the
  bits. The ST's second call is left out of the trace.
- **The test race for objects**: a real race recorded in Hatari (`tools/st_trace_objects.py`,
  `tools/st_race.py`): track 5, as the 17th race of a game (barriers, oil-type hazards; the tornado and
  cones are coin flips that didn't come up), one player on the keyboard accelerating with no steering, so
  car 0 is wrecked at frame 80. Every call of the car plotter and the object routines is logged with its
  arguments. Its first 857 frames fit the trace's bank. Cars 1 and 2 are players' cars driven by drones,
  drawn from the shared second set of frames (3 sets in the cars' bank: car 0's, car 3's, the
  drone-driven). `tools/objects.py` applies the calls to the ST's background and mask C; checked against
  a dump of the ST's own at the race's frame 300, it matches to the bit below the ST's HUD strip.

## Measurements

jsbeeb, Master 128, the whole race (1,144 frames), cycles a frame from the screen chosen to the last car
drawn, with any IRQ that lands in it. The budget is 39,936 (one TV frame).

| Version | Erase | Trace read | Plot | Total: mean | 90% | 99% | Max |
|---|---|---|---|---|---|---|---|
| First (a loop a column, a pass a byte) | 5,213 | 211 | 10,094 | 15,518 | 17,720 | 20,376 | 21,251 |
| Columns unrolled, frames in pages | 3,682 | 211 | 8,418 | 12,311 | 15,564 | 20,033 | 20,822 |
| Hidden half-cells not drawn, the slow loop only for the mixed | 3,682 | 211 | 7,748 | 11,641 | 12,945 | 15,552 | 16,689 |
| The erase indexed by X from the cell's low byte; the data table patched only when it changes | 3,134 | 211 | 7,725 | 11,071 | 12,368 | 14,957 | 16,259 |

Every frame was drawn within the TV frame it started in (1,143 of 1,143 swaps after one vsync).

With the HUD (fifth version, the same erase and plot): 11,219 a frame on average, 15,305 at 99%, 18,125
at worst (the race's first frame, which sets every field: its 4 changes cost 1,741 to put in the text and
1,676 to start drawing). The HUD costs 98 a frame on average; every 64 frames, when each player's score
goes up by 10, 1,842 in each of two frames (3 characters and the scan of 40 columns); 2,076 at most.

With priority turned off the second version's plot averaged 6,744 (max 8,497), so priority cost about 1,670
a frame on average and up to about 8,300 in the worst frames. In those frames every car was under a bridge,
and the slow loop and its per-column set-up took 13,900 of 20,223 cycles. But of the bytes it drew, most
were in cell lines wholly hidden (100 a frame in the worst 20 frames, 12 on average) or not hidden at all
(40 and 8); only 16 (2 on average) were partly hidden. The third version draws nothing for the first, the
fast loop for the second, and the slow loop only for the third.

Where the fourth version's cycles go (`tools/render_profile.mjs`, cycles a frame):

| Region | Mean | The worst 20 frames |
|---|---|---|
| Erase: the copy loop | 1,680 | 1,643 |
| Erase: per car and per band | 1,439 | 1,452 |
| Plot: per car | 1,222 | 1,220 |
| Plot: per band (patching the blocks, the priority checks) | 2,496 | 2,867 |
| Plot: the fast loop | 3,274 | 2,682 |
| Plot: classifying columns | 377 | 2,233 |
| Plot: the slow loop | 113 | 986 |
| Plot: the slow loop's columns | 238 | 1,904 |
| The frame loop (main RAM) | 235 | 235 |

The set-up around the loops is spread thin: about 300 cycles a car, 250 a band for the plot and 150 for
the erase, and in the worst frames the columns under bridges. What was weighed and left:
- Patching only the car's own columns (3.9 of the 5 on average): it saves about what arranging it costs.
- The plot's screen indexed by X like the erase's: the table lookups need X; moving them into patched
  operands costs 8 cycles a byte to save about 60 a band.
- Compiled sprites (the frame's bytes as immediates, 13 cycles a byte): about 100K of code.
- The slow columns drawn from the classification directly, with the cell already found: perhaps 500
  cycles in the worst frames.

Against the plan's estimate (D2: about 42,000 cycles a frame, with 10,100 for drawing and erasing 4 cars):
the cars measure 10,860 on average and 16,000 at worst. With the plan's other items (logic 16,000; HUD,
input, sound and IRQ 6,000) the average frame would be about 33,100 and the worst about 38,300, inside the
39,936 of a TV frame, but only just, and the logic's figure is the least certain.

The real race on track 5 (857 frames), background objects included: every frame matches the model. But
the object events cost 4,770 cycles a frame on average and up to 112,820 (the race's first frame, which
sets up 7 objects); 47 frames run over a TV frame. A gate's step is 192 bytes, written through general
loops at about 80 cycles a byte, plus its priority cells. Next: the bytes written by unrolled column
blocks patched once a band, as the plotter's, and the ST's two calls kept (the first writing the
background and the screen being drawn, the second only copying the background into the other screen).

## Memory

| Region | Used | Free |
|---|---|---|
| Background's bank | 207 erase, then 16,000 background from `&8180` | 177 |
| Cars' bank | 10,615 frames (659 of it page padding), 643 priority map, 2,664 priority cells, 333 classes, 1,138 tables, 863 plotter | 154 |
| Trace's bank (test only) | 13,728 trace, 782 HUD events | 1,874 |
| Main RAM | 754 code at `&0E00` (the HUD 394 of it, with its font); tables at `&0400`-`&07FF` (MaskTab, 3 data tables) and `&2C00`-`&2DFF` (the priority expansions, which the HUD uses too); 180 bytes of variables at `&2E00` | |
| Zero page | `&00`-`&1E` | |

A race needs one set of 64 car frames: the human players' cars and car 3, plus the drone-driven set if any
player car is a drone (it shares one set of shapes, so at most 64 + 16). So the sprite storage is settled
as pre-shifted, trimmed frames, about 10.6K a race; the cars' bank is then all but full with the priority data.

## Next

- **Speed**: the set-up around the loops (per band and per car) is now the biggest part. The worst frames
  are the ones with every car near a bridge (classifying columns, the slow loop's columns).
- **Memory**: the cars' bank has 154 bytes left. The frames' page padding (659 bytes, about 375 more than
  a perfect packing) and the frame tables (1,138 bytes) are where room could come from.
- **Objects** (pickups, cones, tornado, helicopter, sparks) and the remaining tracks.
