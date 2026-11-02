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
  during a frame are below `&3000` or in a bank, so X never hides them, but for each screen's own
  variables (ScreenVars, `&3000`): its erase list and the HUD's text it shows, main RAM's and shadow RAM's
  copies, so X picks the screen being drawn's (Tom's idea).
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
  The ST's tornado never comes near the top or bottom in the recorded race, so `tools/tornado_sweep.py`
  makes a race with its place swept, y from -17 to 201 and x across the screen (`make check TRACE=sweep
  TRACEFILE=...`): every frame matches; with a clipped line's place in its cell off by one, 180 fail.

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
  screen and in the frame, so Y indexes every column alike. The loop draws one line of every column a
  pass, its five column blocks unrolled (`LDX frame,Y : LDA screen,Y : AND MaskTab,X : ORA Data,X : STA
  screen,Y`, 21 cycles a byte); the loop's branch back is patched by the car's width. Y is 8 * the band +
  the line in the cell (since speed's third round, Phase 4), so it runs on through the car's rows as the
  frame's do: the frame's operands are patched once a car, the screen's (less 8 * the band) once a band.
- **Priority**: a car on the ground (not elevated or airborne) goes under mask C. Each 8 x 8 cell with hidden
  pixels has its 8 bytes of 1-bit mask and a class byte saying, for each 4-pixel half, whether none, all or
  some of it is hidden (333 cells on track 6: 2,664 + 333 bytes). A map gives each cell's number in its
  row; it's stored a row's span at a time, from 2 cells before the row's first such cell to 2 after its
  last (643 bytes rather than 1,000), with the first and last, so a band outside the span skips the map.
  In a band with such cells, each of the car's columns is classed by its half-cell: none hidden, it stays
  in the fast loop; all hidden, its block's screen operands point at a Junk area instead (the tornado's), so it
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

- **Background objects**: gates, pop-up barriers and the pickups and hazards in the track's slots. The ST
  draws one into the screen being drawn and the clean background when it changes, and again into its other
  screen the frame after; gates and barriers also write mask C, so the cars' priority around them changes as
  they move (a gate frame hides up to 392 of its 768 pixels). On the BBC (`src/objects.6502`, in main RAM,
  paging three banks), each call writes the variant from a fourth bank, the objects' (the
  slots' 22 sprites, and the gates' and barriers' frames the race uses, of 5 and 12 (a barrier's 3 kinds of
  4: a track's are of one or two), each for an even and an odd top line, the patterns' phase; each variant's bytes column by column, wholly in a page), into the screen being drawn
  (a barrier over what's there, its colour 0 kept), through unrolled column blocks (up to 12, a gate's
  width), their operands patched once a band: the screen indexed by X from the cell's low byte and the
  line, column n's operand 8n into the cell's page, so only its high byte is patched and a page crossed
  among the cells is carried by the indexing (as the erase does), the variant by Y, its line (the masked
  barriers' pass, 4 columns, keeps Y for both and a path for a crossed page). The
  second call then copies the screen into the background: the background is a frame behind the screens
  between the calls, which is safe because each frame's erase comes before its objects, so whatever it
  restores is drawn over. The first call also writes a gate's or barrier's priority: the race's gates and
  barriers are numbered by place (per track, Tom's suggestion), and `tools/gendata.py` works out, for each
  one and each of its frames, the finished bits of the cells it covers (the track's own, the frame's over
  the lines it covers). Their cells are reserved in the map with class "some hidden", and sit together in
  the cars' bank, a run of 48 bytes a cell row for a gate. A gate or barrier only ever steps to a
  neighbouring frame, so each call's event gives an entry, its transition (the instance, from one frame to
  another, or its first draw), whose variant and runs (up to 3) are worked out at build time: a first
  draw's every cell, a step's only each cell row's span of cells that change (48 to 80 of a gate's 144
  bytes). A change is a copy of those runs through a buffer in main RAM, 4 bytes a loop pass.
- **Moving objects** (`src/movers.6502` in the objects' bank, `src/heli.6502` in the fourth): a wrecked car's explosion (26 frames, drawn
  in the car's place in the draw order), the banner (36 frames, 16 x 8, at a place fixed per track), the
  tornado (3 frames, 16 x 16, at any pixel, colour 0 its transparent one), the
  sparks (8 x 8 on 8-pixel steps) and the helicopter (4 frames, 32 x 36 flying in from below or above, or
  64 x 26 from either side, clipped at the screen's sides by whole 16-pixel groups as the ST does it,
  each piece of a sideways frame within a group, so the trace leaves out the pieces off the side; on
  16-pixel steps, its carried
  car's pixels recoloured as the ST composes it). Each is erased and drawn every frame like a car, through
  the same key-colour scheme (every frame uses black, white and at most one of green and yellow) and a copy
  of the car plotter's fast loop, 8 columns wide, clipped to the play area's lines, with no priority (the
  ST draws them over everything). One shift each: the explosion snapped to 4-pixel steps (D8), the banner's
  frames shifted for its place, the sparks and helicopter aligned already. The plotter
  (`src/movplot.6502`) is included in each bank with moving objects, each copy in a scope of its own with
  its own variants' tables: the objects' bank's (`objmov`: the explosion, banner and sparks) and the fourth
  bank's (`helimov`: the helicopter, every variant, so any wreck can be shown; each variant's bytes once,
  the carried car's colour being its data table's, yellow or car 3's green). The frame loop (main RAM)
  calls the car plotter or the explosion car by car, then `mov_all` (main RAM), which pages in each moving
  object's bank and calls its plotter (the helicopter's, the tornado's, or the objects' bank's); the erase lists
  hold 16 boxes a screen and end at one of height 0. Each sprite is cut into pieces by `tools/gendata.py`:
  rectangles of neighbouring byte columns, each trimmed to the rows its columns cover, chosen to draw the
  fewest bytes with a piece costing 50 bytes more (a helicopter's columns run from 2 rows to 36; it comes
  to 1 to 3 pieces, 184 to 198 bytes rather than 272). Each piece is a record of its own, with its own erase
  box. The plotter carries each column's data address in full (a piece can be more than a page), and
  patches only the piece's own columns, its unrolled patching entered at column w - 1 through a table by
  width; so does the erase.
- **The tornado** has a plotter of its own (`mov_tornado`), as it's on screen all race when it comes up:
  each of its frame-shifts (3 frames at 4 shifts) is compiled by `tools/gendata.py`, column by column, an
  opaque byte `LDA #:STA (ts+2l),Y` (8 cycles; no `LDA` if A has the byte already), a mixed one
  `LDA (ts+2l),Y:AND #:ORA #:STA (ts+2l),Y` (15; no `ORA` of 0), an empty one nothing; Y is 8 times the
  byte column, set once a column. `ts` is 16 zero-page pointers, one a sprite line, to its line's cell in
  the box's first column: set each call from the last plus 1, or from a cell's line 7 the next row's line 0
  (about 230 cycles), so the character rows it crosses cost nothing in the drawing. A line outside the play
  area points at `TorJunk` instead (a slower loop, for a tornado partly above or below). Its frame-shifts
  draw 45 bytes each on average (of 64 in the box), in about 600 cycles. Its variants are numbered after the
  other moving objects', and `mov_all` sends them to it; its box goes in the erase list like the others'.
- **The test race for objects**: a real race recorded in Hatari (`tools/st_trace_objects.py`,
  `tools/st_race.py`): track 5 with the race counter 17, the 18th race of a game (barriers, oil-type
  hazards, and the tornado and cones, whose coin flips are forced: a breakpoint after each one's call of
  the random routine sets the register it's tested in), one player on the keyboard accelerating with no
  steering, so car 0 is wrecked at frame 81. Every call of the car plotter and the object routines is
  logged with its arguments. Its first 304 frames fit the trace's bank beside the helicopter (the tornado
  and the sparks are records every frame); in them the 4 cones are placed, and two are knocked over, at frames 19 and 242
  (each then drawn over with the road, the slots' sprite &15). Before that race the counter was poked
  as hex into Hatari's `w`, which reads decimal, so the race recorded as "the 17th" was really counter 11:
  no cones possible. The measurements of the background and moving objects below, before the tornado's,
  are from that race. Cars 1 and 2 are players' cars driven by drones,
  drawn from the shared second set of frames, and so is car 3: in a real race the ST draws every
  drone-driven car from it (only the attract race draws each car in its own), car 3's stripes black on
  the BBC, through a fourth data table. `tools/objects.py` applies the background calls to the ST's
  background and mask C, and draws the moving objects as the ST's routines do; checked against dumps of the
  ST's own background at frame 300 and screens at frames 190, 200 and 251, it matches to the bit, but for
  the ST's HUD strip and its drone-lap digit (in the BBC's HUD row instead, D6).

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

The real race on track 5 (846 frames), background objects included: every frame matches the model.

| Version | Objects: mean a frame | Max | Total: mean | 99% | Max | Frames over |
|---|---|---|---|---|---|---|
| General loops, both calls written in full | 6,809 | 142,317 | 17,485 | 57,868 | 151,083 | 122 |
| Both screens written by the first call; cells found once | 4,770 | 112,820 | 16,347 | 45,779 | 121,586 | 47 |
| Unrolled column passes; the ST's second call a copy | 1,865 | 53,654 | 13,421 | 27,101 | 62,420 | 1 |

The one frame over is the race's first, which sets up 7 objects (3 gates, 3 barriers, a pickup) at once;
in a game it comes before the race starts. A change, first call and second: a gate's step 12,542 and
3,626 cycles (the two copies 6,078, its 18 cells' priority bits 4,025, copying those bits out of the
objects' bank 2,010); a barrier's 4,503 and 1,763; a pickup's 2,257 and 1,396. Gates step every 6 frames
while they move.

With the moving objects too (the race's first 560 frames, all matching the model): 18,864 cycles a frame
on average, 38,023 at 99%, 64,328 at worst (the first frame); 2 frames over a TV frame.

| Region (`tools/render_profile.mjs`) | Mean | The worst 20 frames |
|---|---|---|
| Erase: the copy loop | 2,316 | 3,702 |
| Erase: per box and per band | 2,282 | 2,764 |
| Plot the cars: set-up, bands, fast loop | 6,647 | 6,226 |
| Plot the cars: priority (classify, slow loop and columns) | 1,819 | 1,565 |
| Moving objects: the fast loop | 1,520 | 4,717 |
| Moving objects: set-up, bands | 1,917 | 3,478 |
| Background objects (main RAM) | 1,534 | 13,741 |
| The frame loop, the trace, the HUD (main RAM) | 836 | 1,381 |

The worst frames are a gate's step with the helicopter in flight: with the plan's estimate for the logic
(16,000) they'd run over a TV frame and drop to 25 fps for a moment. The gate's step (12,542 on its first
call) and the helicopter (272 bytes drawn and erased, about 8,000 with its share of the erase) are where
the time would come from.

Then, the work of a change split between the ST's two calls and the priority precomputed per gate and
barrier (above): a gate's step 8,142 on the first call and 6,772 on the second (was 12,542 and 3,626), a
barrier's 3,477 and 3,166. The whole race: 18,751 cycles a frame on average (18,864 before), 33,738 at
99% (38,023); the worst 20 frames 33,760 (37,576): the gates 9,747 of it, the helicopter about 9,300,
the erase 6,553.

Then the moving objects in pieces, and the plotter and the erase patching only their boxes' own columns:
18,318 cycles a frame on average, 32,557 at 99%, the worst 20 frames 32,718 (33,760 before). The pieces
alone drew a third fewer of the helicopter's bytes but cost as much in set-up as they saved, until the
patching stopped doing all 8 columns for every piece. The helicopter's middle columns run its full height,
so what's left of its cost (about 7,000 drawn and erased) is mostly bytes it really draws.

With the tornado and cones, on the race with the counter 17 (463 frames, all matching the model; broken on
purpose, the tornado drawn without its shift in the model, 362 fail): 22,602 cycles a frame on average,
40,048 at 99%, 52,565 at worst; 5 frames over a TV frame. The same race with the tornado left out: 18,424
on average (541 frames), so the tornado costs about 4,200 a frame, about 2,900 drawn and 1,300 erased, all
race long. That's the general moving-object path's usual cost for a 64-byte piece over 3 bands (about 250
of set-up, 200 a band, 21 a byte drawn, 9 erased), not a fault. The cones cost nothing new: they're the
slots' sprite &14, drawn at the start, and the road sprite over each when it's hit.

| Region (`tools/render_profile.mjs`) | Mean | The worst 20 frames |
|---|---|---|
| Erase: the copy loop | 2,998 | 4,384 |
| Erase: per box and per band | 2,705 | 3,296 |
| Plot the cars: set-up, bands, fast loop | 6,548 | 5,948 |
| Plot the cars: priority (classify, slow loop and columns) | 2,098 | 4,784 |
| Moving objects: the fast loop | 2,966 | 6,195 |
| Moving objects: set-up, bands | 2,925 | 4,809 |
| Background objects (main RAM) | 1,445 | 8,859 |
| The frame loop, the trace, the HUD (main RAM) | 927 | 1,260 |

Then the tornado's own plotter, compiled (above): 20,994 cycles a frame on average (22,602 before), 38,262
at 99% (40,048), 50,781 at worst; the worst 20 frames 37,905 (39,541); 4 frames over a TV frame (5). The
plot fell by 1,609 a frame, about what was estimated (2,450 through the general path, 850 compiled); the
tornado now costs about 2,600 a frame, half of it the erase's (unchanged). In the profile the general
path's loop fell from 2,966 to 1,538, and "set-up, bands" (2,745) now includes the tornado's set-up and
its compiled code. The cost is memory: 3,561 bytes in the objects' bank (509 the routine, 3,052 its 12
frame-shifts), less the 736 its pieces took, so about 2.8K more; 1,346 bytes are left in the bank.

Then the helicopter moved to the fourth bank, all 4 variants (5,520 bytes with its plotter's copy, then
5,023 once the sideways frames were read right, below), the
objects' bank's moving objects paged from main RAM: over the first 304 frames (what now fits the trace's
bank; all match), 22,752 cycles a frame on average against 22,723 before, the paging's 29.

The helicopter's other variants: the ST picks the side it flies in from by where the car was wrecked
(`F_00BB4E`): from the farther side horizontally if the horizontal distance to it is more than twice the
vertical, else vertically (variant 0 from below, 1 from above, 2 and 3 from the sides). The recorded race's
wreck brings it from below, so `make check TRACE=heli1` (`heli2`, `heli3`) plays the same race with the
variant written over just after the ST chose it (`tools/st_trace_objects.py`'s `heliN`), the flight then
the ST's own. The sideways frames are 26 rows of 64 pixels (`F_0144AA`), not the 52 rows of 32 that
`tools/objects.py` first read them as; it flies in from x -39 or 319, 4 pixels a frame. All four races
match on every frame (303 to 325 frames each); with the plotter's x DIV 4 wrong for a negative x, the
helicopter from the left fails 9.

**All the tracks** (`make check TRACE=t0` to `t7`): the same race (the counter 17, the tornado and cones
forced, the blue car accelerating with no steering) recorded on each of the 8. Every frame of each matches
the model (313 to 332 frames each). The other tracks found three things track 4 (index) hadn't:
- Barriers come in 3 kinds of 4 frames (frames 0-11); only 8 were stored, and track 4's are kind 1. Now
  only the gates' and barriers' frames the race uses are stored: 1,952 bytes less on track 4 than all 12,
  and none of the gates' on the 5 tracks without one.
- Pop-up barriers 9 lines apart share a cell row (tracks 3, 5 and 7 by index). They move one at a time,
  the others at rest in their first frame, so each one's priority frames carry its sharers' lines at
  rest; `tools/gendata.py` checks that against the race.
- The car plotter's fast loop crossed a page with track 2's data before it: it's kept in a page now.

| Track (index) | Mean | 99% | Max | Over a TV frame | Cars' bank free (3 players) | Objects' bank free |
|---|---|---|---|---|---|---|
| 0 | 16,367 | 20,230 | 26,056 | 0 | 2,346 | 8,424 |
| 1 | 16,555 | 21,658 | 28,851 | 0 | 2,097 | 7,620 |
| 2 | 17,755 | 28,241 | 32,238 | 0 | 1,666 | 5,217 |
| 3 | 20,913 | 33,687 | 34,663 | 0 | 1,266 | 7,064 |
| 4 | 22,403 | 37,717 | 49,779 | 2 | 962 | 2,933 |
| 5 | 17,109 | 26,021 | 29,145 | 0 | 504 | 7,061 |
| 6 | 16,223 | 21,576 | 30,534 | 0 | 1,281 | 7,508 |
| 7 | 20,158 | 32,182 | 33,426 | 0 | 1,769 | 4,400 |

(After the gates' speed-up, below; before it track 4 (index) averaged 22,707, 40,312 at 99%, with 4
frames over.)

The races have one human car, so their cars' frames are 5,331 bytes (the blue car's and the drone-driven
set); a race with three human players needs 10,615 (three cars' own sets and the drone-driven set, car
3's), so the cars' bank's free bytes above are what the build prints less 5,284. The tightest is track 5
(index), the most priority cells (341): 504 bytes. Track 4 (index), with 3 gates, is the slowest; its 2
frames over a TV frame are the race's set-up (7 objects drawn at once, before a game's race starts).

The gates' speed, on track 4 (index), `tools/render_profile.mjs --list N` giving the worst frames region
by region. A gate's step was 7,546 cycles on its first call (the variant into the screen 3,047, its
priority runs about 4,500) and 6,080 on its second (two passes, 3,734 copying and 2,346 setting up
bands); the worst real frames, a step with the helicopter in flight and cars under a bridge, 42,089 and
40,312. Only the bytes that change could be drawn, but a step changes 47 to 105 of 192 bytes, inside a box
of 150 to 165, and at about 22 cycles a changed byte against 9 a byte copied, it comes out about even. The
priority runs did pay: trimmed to the cells that change, the first call's runs fell from about 4,500 to
about 2,000. Then the screen indexed by X in the copy passes: their band set-up fell from 1,180 to 974 a
pass on the first call and from 2,346 to 1,811 on the second. A step now costs 4,870 and 5,583 (13,626 in
all before, 10,453 now); the worst real frame 39,359.

## Memory

| Region | Used | Free |
|---|---|---|
| Background's bank | 207 erase, then 16,000 background from `&8180` | 177 |
| Cars' bank | 10,615 frames (659 of it page padding), 643 priority map, 2,664 priority cells, 333 classes, 1,138 tables, 863 plotter | 154 |
| Fourth bank (race 17, track 5) | 5,023 the helicopter (1,561 its plotter's copy and tables, 3,462 its 4 variants' bytes, 84 pieces); the rest the test's trace and HUD events | in the game, about 11.1K for the race's data and some logic |
| Objects' bank (race 17, track 5) | 8,345 the variants' bytes; 2,239 their tables, the background objects' and the moving objects' plotters; 3,561 the tornado's plotter (its compiled frame-shifts 3,052) | 2,239 |
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
- **Objects' speed**: in a race with everything (track 4, index) the average frame is about 22,400 before
  the logic's estimated 16,000: 38,400 of 39,936. What's left in a gate's step is mostly bytes copied
  (3 passes of 192); the helicopter (about 7,700 in flight) and the erase are the other big items.
- **Memory**: the objects' bank has 2,239 bytes left, with the tornado compiled and the helicopter in the
  fourth bank (Tom: the logic is less reliant on unrolled code or contiguous, page-aligned data, so some
  can be squeezed into what's left of that bank). The tornado's code is needed only in a race that has it
  (D3: a race's data is loaded per race).
