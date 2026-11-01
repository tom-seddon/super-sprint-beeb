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
  (blank for now) and the 25-row play area from `&4180`. One screen in main RAM, one in shadow RAM. The
  vsync IRQ (the System VIA's CA1, its only interrupt) flips ACCCON's D bit when the main loop asks; the
  main loop then flips X, so it draws into the screen not shown. All the code and variables that run
  during a frame are below `&3000` or in a bank, so X never hides them.
- **The check** (`make check`, `tools/render_check.mjs`): headless jsbeeb's Master 128, the real IRQ. At
  each frame's end the play area just drawn (main or shadow RAM, by X) is compared with
  `tools/render_model.py`'s frame: the clean background, then each car in the ST's order, its ST frame
  mapped through the car's colours (convert.py), drawn where the ST frame isn't colour 8 and, for a car on
  the ground, where mask C isn't 0. The model shares nothing with the BBC's data path (trimming, shifts,
  the key colour, the priority cells). Broken on purpose, it fails: with priority off, 282 frames are
  wrong; with one car's erase skipped, 96 of the first 100.

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
- **Priority**: a car on the ground (not elevated or airborne) goes under mask C. A map of the 8 × 8 cells
  (1,000 bytes) gives each cell with hidden pixels its 8 bytes of 1-bit mask (333 cells, 2,664 bytes on
  track 6). A band whose cells have any goes column by column through a slow loop that keeps the screen
  where those bits are set, as well as where the key is (about 52 cycles a byte).
- **The erase**: the box each car drew, two frames before in the same screen, copied back from the clean
  background, a band at a time with the same unrolled blocks (9 cycles a byte). The background lives
  `&4000` above the screen, at `&8180`-`&BFFF` in its bank.

## Measurements

jsbeeb, Master 128, the whole race (1,144 frames), cycles a frame from the screen chosen to the last car
drawn, with any IRQ that lands in it. The budget is 39,936 (one TV frame).

| Version | Erase | Trace read | Plot | Total: mean | 90% | 99% | Max |
|---|---|---|---|---|---|---|---|
| First (a loop a column, a pass a byte) | 5,213 | 211 | 10,094 | 15,518 | 17,720 | 20,376 | 21,251 |
| Columns unrolled, frames in pages | 3,682 | 211 | 8,418 | 12,311 | 15,564 | 20,033 | 20,822 |

Every frame was drawn within the TV frame it started in (1,143 of 1,143 swaps after one vsync).

With priority turned off the plot averages 6,744 (max 8,497), so priority costs about 1,670 a frame on
average and up to about 8,300 in the worst frames. Over the race a frame plots on average 131 bytes by the
fast loop and 22 by the slow one; 14 of those 22 really overlap hidden pixels, so a finer map would save
little. The slow loop itself is the cost.

Against the plan's estimate (D2: about 42,000 cycles a frame, with 10,100 for drawing and erasing 4 cars):
the cars measure 12,100 on average and 20,600 at worst. With the plan's other items (logic 16,000; HUD,
input, sound and IRQ 6,000) the average frame would be about 34,300 and the worst about 42,800, so the
worst frames would drop to 25 fps for a moment until the plot or the logic is faster.

## Memory

| Region | Used | Free |
|---|---|---|
| Background's bank | 16,000 background, 290 erase | 94 |
| Cars' bank | 10,615 frames (659 of it page padding), 1,000 priority map, 2,664 priority cells, 1,152 frame tables, 732 plotter, 164 alignment | 57 |
| Trace's bank (test only) | 13,728 | 2,656 |
| Main RAM | 289 code at `&0E00`; tables at `&0400`-`&07FF` (MaskTab, 3 data tables) and `&2C00`-`&2DFF` (the priority expansions); 42 bytes of variables at `&2E00` | |
| Zero page | `&00`-`&1E` | |

A race needs one set of 64 car frames: the human players' cars and car 3, plus the drone-driven set if any
player car is a drone (it shares one set of shapes, so at most 64 + 16). So the sprite storage is settled
as pre-shifted, trimmed frames, about 10.6K a race; the cars' bank is then full with the priority data.

## Next

- **Speed**, worst frames first: the slow loop unrolled across columns as the fast one is (about 41 cycles
  a byte, no per-column overhead, but about 150 bytes the cars' bank doesn't have); or the priority cells
  stored as screen masks (16 bytes a cell, double the space) so the slow loop needs no expansion table;
  patching only the car's own columns; checking a ground car's cells once rather than each band.
- **Memory**: the cars' bank is full. Room could come from the 164 bytes of alignment (the frames first, at
  the bank's start), the frame tables (1,152 bytes, packable), or moving the plotter to main RAM.
- **The HUD row**: blank so far.
- **Objects** (pickups, cones, tornado, helicopter, sparks) and the remaining tracks.
