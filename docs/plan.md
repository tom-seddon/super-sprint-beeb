# Super Sprint for the BBC Master: plan

A port of the Atari ST version of *Super Sprint* (State of the Art / Electric Dreams, 1987; `orig/st`) to the
BBC Master 128, written in Baron. Phases 1 and 2 are done (2026-11-01): the original is specified in
`docs/st-graphics.md` and `docs/st-logic.md`, and its graphics converted to MODE 1 in `docs/colours.md`.
Figures marked as estimates stay so until Phase 3 measures them. Decisions are in `docs/decisions.md`, work
done in `JOURNAL.md`.

## Verdict

**Feasible on a Master 128 in MODE 1, double-buffered in shadow RAM, drawing at 25 fps with the game logic at
50 Hz.** Colour works out (D1). Memory is now the tightest resource, then speed.

- The ST runs at 320×200 in low res. MODE 1 is 320 pixels across, so the art converts pixel for pixel. The
  play area is 25 MODE 1 rows (200 lines), with one row of 8-pixel text above it for the HUD (D6): 26 rows,
  16,640 bytes. Main RAM holds one screen and shadow RAM the other, both at `&3F00`-`&7FFF`. Checked on
  jsbeeb's Master 128 (`docs/img/jsbeeb-option-a2-track1.png`).
- The ST runs its race at **50 fps**, logic and drawing, with no time compensation: every speed and timer is
  per frame. On the BBC, draw at 25 fps and run the logic twice per drawn frame, so every constant stays as the
  ST has it (D2). Estimated 58,000 of the 80,000 cycles a drawn frame (Speed, below).
- Four colours are enough with the right mapping: proposed option A2, a black road with grey-outlined cars
  (D1, `docs/colours.md`).
- Everything for the race is about 90K before any cleverness, against about 64K of sideways RAM, so the data
  needs work: one track's data at a time (a multiload, D3), the masks rebuilt from the ST's vector and
  rectangle lists, or the background restored from tiles (Memory, below).

## The ST version

In short (the details, with addresses, are in the two specs):
- **Program:** Megamax C, 283 functions, 70,696 bytes of code. `SUPER.DAT` (212,650 bytes) is fixed blocks: car
  sprites, tile maps and tiles, object sprites, wall vectors, drone paths, sound. `INIT.DAT` (5,139 bytes) is
  43 tables: grid positions, pickups, direction vectors, collision probes, priority rectangles, attribute runs,
  trees. `SUPER1.DAT` is front-end data.
- **Tracks:** 8, each a 40 × 25 map of 8 × 8 tiles plus trees, played in the order 0, 2, 6, 5, 1, 4, 7, 3. One
  16-colour palette for all.
- **Cars:** always 4. Cars 0-2 are blue, red and yellow, each a human or a drone; car 3 is always a drone,
  green. 16 × 12 sprites in 16 directions; positions in 1/8 pixel; speed 0 to 135.
- **Collisions:** three 1-bit masks per track built at set-up: walls (from line lists, flood-filled), priority
  (what scenery hides cars: bridges, trees) and one from the background's colours. Cars hit walls by ANDing
  their sprite's shape with the wall mask and probing it. A 40 × 25 attribute map holds laps, checkpoints,
  bridge levels, ramps and pickups.
- **Drones:** straight-segment paths per track, with lane choice; difficulty is their top speed only.
- **Race:** 4 laps, 10 points per car every 64 frames, pickups 100-250, place and lap-time bonuses; hazards
  (oil, water, cones, tornado, pop-up barriers) grow with the race count.
- **Sound:** the YM2149 driven by the game's own 749 Hz timer interrupt: a 3-track sequencer at 83 Hz, one
  engine channel per human car, effects by priority.
- **Input:** joystick 0, joystick 1 and the keyboard (A/Z/L left, D/X/' right, Shift or Alternate
  accelerate). Up and down are never used.
- **CPU:** the race uses about 112,000 of the 68000's 160,000 cycles a frame; the car plotter alone is 15%.

## Display (MODE 1, 26 rows)

- **Layout:** 1 HUD row, then 25 rows of play area. CRTC R6 = 26, R7 = 31, start `&3F00` (R12 = `&07`, R13 =
  `&E0`); 208 lines shown, 24 blank above and below.
- **The HUD** (D6) is one row of 8 × 8 text, `99,999 L1 99,999 L1 99,999 L1  T8 D1`: each player's score and
  lap, then the track and the drone's lap. Each player's text is in their car's colour, which is in the play
  area's palette, so **no palette split is needed**. A changed digit is 16 bytes, written into both screens.
- **The ST's own HUD text** in the map's bottom row ("TRACK n", "DRONE LAP") is repainted with grass at build
  time.
- **Double-buffering in shadow RAM:** ACCCON (`&FE34`) bit 0 picks the screen shown, bit 2 sends the CPU's
  `&3000`-`&7FFF` accesses to shadow. Code that draws, and the data it reads, live outside `&3000`-`&7FFF`.
- **Erasing:** from a clean copy of the track, each buffer keeping its own list (as the ST does). Or, to save
  16K, from the converted tiles: a sprite's erase touches at most 3 × 3 cells.
- **Priority:** cars on the ground are hidden where the priority mask is 0; cars on the bridge level and
  airborne ones are drawn last and on top (`docs/st-logic.md` §3). Only tracks 2, 4, 6 and 8 have bridges.

## Colours (D1)

Phase 2 converted all 8 tracks and the cars in six options (`docs/colours.md`, pictures in `docs/img/`,
bootable viewer discs from `make viewer`). **Proposed: A2.**
- MODE 1 in black, green, yellow and white; a black road; grass green, dark greens as green/black
  checkerboards, kerbs white, stripes yellow and black.
- Players' cars white, green and yellow (for the ST's blue, red and yellow), with their black outlines drawn
  as a grey checkerboard so they show on the black road. Every drone, car 3 and drone-driven players alike, is
  a hollow grey outline; a drone-driven player's car keeps its colour as stripes.
- Its weakness: the road's shading is lost, so bridges show only by their kerbs. Option B (a grey
  checkerboard road) keeps the shading but the road is busy.

## Memory (Master 128, the OS taken over)

| Range | Size | Use |
|---|---|---|
| `&0000`-`&2FFF` | ~12K | Zero page, stack, IRQ, sound, game logic, the drawing code |
| `&3000`-`&3EFF` main | 3,840 | Variables and tables (read when the CPU is not mapped to shadow) |
| `&3F00`-`&7FFF` main | 16,640 | Screen A |
| `&3000`-`&3EFF` shadow | 3,840 | Data read only while drawing into shadow (awkward) |
| `&3F00`-`&7FFF` shadow | 16,640 | Screen B |
| `&8000`-`&8FFF` ANDY | 4K | Code (hides the first 4K of the paged bank while in) |
| `&8000`-`&BFFF` banks 4-7 | 64K | Data |
| `&C000`-`&DFFF` HAZEL | 8K | Code, independent of sideways paging (the DFS's while the OS lives) |

**The data, as measured or estimated:**

| Item | Bytes | Notes |
|---|---|---|
| Clean background, current track | 16,000 | Or tiles for the erase: about 7K a track (estimate) |
| Wall mask and priority mask, current track | 16,000 | 1 bit a pixel, as the ST. Rebuildable from 3,000 bytes of wall vectors and 526 of priority rectangles for all 8 tracks |
| Attribute map, current track | 1,000 | From 1,688 bytes of runs for all 8 |
| All 8 tracks' art, packed | 19,262 | ZX02, option A; about 2.4K a track |
| All 8 tracks' masks, packed | 9,670 | If not rebuilt from the vectors |
| Car sprites | 6,000-30,000 | 8 sets (4 cars, and 4 drone-driven) × 16 directions, 16 × 12: 6K unshifted, 30K pre-shifted to 4 positions |
| Object sprites | ~6,000 | Estimate: explosion, pickups, tornado, gates, barriers, helicopter |
| Drone paths | 7,100 | All 8 tracks, as the ST; about half as bytes |
| Sound | ~12,000 | The ST's sequences and instruments, before transcoding |

All of it at once is about 90K with unshifted sprites; the banks hold 64K. So:
- **Load one track's data per race (D3):** its art (about 2.4K packed), wall vectors, priority rectangles,
  attribute runs and drone path, unpacked or rebuilt into the current track's buffers. A 1770 sector loader
  (WD1770 at `&FE24`, `&FE28`-`&FE2B`) keeps the MOS and DFS dead and HAZEL ours; a load between races is well
  under a second. The front-end screens load the same way.
- **Shift the car sprites while drawing** (256-byte shift tables) rather than store 4 copies, unless the
  timings say otherwise.
- **Transcode the sound** at build time into a compact SN76489 form.

## Speed (estimate; the budget is 80,000 cycles a drawn frame at 25 fps)

| Work, per drawn frame | Cycles |
|---|---|
| 4 cars drawn: 16 × 12 pixels is 5 bytes × 12 lines once shifted, colour 0 transparent through a mask table, ~30 cycles a byte | 7,200 |
| 4 cars erased, ~12 cycles a byte | 2,900 |
| Priority masking under bridges (tracks 2, 4, 6, 8, cars near bridges only) | 2,000 |
| Smaller sprites (pickups, cones, tornado, helicopter, sparks), drawn and erased | 8,000 |
| Car logic, wall probes, attribute probes, car-to-car tests: 4 cars × 2 ticks | 32,000 |
| HUD digits, input (keys and ADC), sound, IRQ | 6,000 |
| **Total** | **~58,000** |

The logic figure is the least certain: the ST's wall test ANDs each car's shape with the wall mask every frame,
and the drones' path following divides. `docs/st-logic.md` §12 suggests the cheaper forms (a fixed shape per
direction, a reciprocal table per divisor). 50 fps drawing would need everything in 40,000 cycles: not
planned, but Phase 3's timings will show how far off it is.

## Input and sound

- **Three players**, as on the ST: two analogue joysticks (the Master 128's ADC, read as left/centre/right, fire
  buttons on system VIA PB4/PB5) and the keyboard. Each player needs only left, right and accelerate.
- **Keyboard ghosting** with several keys held must be tested on a real Master before more than one keyboard
  player is offered (D5).
- **ADC:** slow conversions (about 10 ms a channel). Poll it from the frame IRQ, not by interrupt.
- **Sound:** the SN76489's 3 tones and noise against the YM's 3 channels: one engine tone per human car,
  effects taking channels by the ST's priorities, the noise parts on the shared noise channel. The ST's periods
  divide by 4 to fit 10 bits; envelopes and the sequencer run in the 50 Hz IRQ with timings scaled by 0.6, or
  on a VIA timer at 83 Hz. Plan in `docs/st-logic.md` §8.

## How the port gets checked

- `make` (see `Makefile`): the disassembly (`tools/st_disasm.py`), track dumps from Hatari
  (`tools/st_dump_tracks.py`), conversions (`tools/convert.py`), comparison sheets, viewer discs. Python in
  `.venv` (pillow, numpy, capstone); generated data in `build/`.
- **The original, running:** Hatari 2.6.1 headless (`tools/hatari.sh`, TOS 1.04). Breakpoints and pokes give
  any track, a real game with held keys, per-frame traces of the cars' variables, and RAM dumps
  (`docs/st-logic.md` §0). The BBC version's logic can be checked against these traces frame by frame.
- **The port:** jsbeeb (the MCP server) as a Master 128 for screenshots and timing. Each renderer is timed over
  a recorded race before the game is built on it.

## Phases

### Phase 0: housekeeping (done)
- `Makefile`, `docs/decisions.md`, `JOURNAL.md`.

### Phase 1: understand the ST version (done)
- The disassembler, the frame (50 fps), file formats, every track's art and masks, car and object sprites:
  `docs/st-graphics.md`.
- Car physics, collisions, drones, race rules, input, sound, the game sequence: `docs/st-logic.md`.
- Left for later phases: the front-end screens' data (`SUPER1.DAT`, the first three `SUPER.DAT` blocks) and the
  object sprites' exact formats.

### Phase 2: graphics and colour (done; D1 waits for Tom)
- The conversion pipeline, six options on all 8 tracks, checked on jsbeeb's Master 128. Packed sizes.

### Phase 3: renderer
- Boot, take over the OS, MODE 1 with 26 rows, shadow double-buffering, the HUD row.
- Car and sprite plotting, erasing, priority. Time 4 cars driven from a recorded ST trace (Hatari gives the
  positions and directions per frame). Decide D2 and the sprite storage.

### Phase 4: one race
- Physics, collisions, drones, laps, scoring, HUD, input for 3 players, sound. One track, played start to
  finish, checked against Hatari traces.

### Phase 5: the game
- All the tracks, hazards, upgrades, the front end, the results and high-score screens, the screen wipe, the
  disc and the loader (D3).

## Decisions

| | Question | State |
|---|---|---|
| D1 | Palette and dithering | Proposed: A2 (black road, grey-outlined cars); B the alternative |
| D2 | Frame rate | Proposed: draw at 25 fps, logic at 50 Hz (twice a drawn frame) |
| D3 | Multiload or all in memory | Proposed: a 1770 loader, one track's data per race |
| D4 | Machines | Proposed: Master 128 only |
| D5 | Controls | Proposed: two joysticks and the keyboard, as on the ST, once ghosting has been tested |
| D6 | HUD | Decided (Tom, 2026-11-01): one row of 8-pixel text above the play area |

## Risks

- **Memory.** The estimate above is over the banks by about a quarter before the savings listed. Phase 3
  measures the sprites and code.
- **The logic's cost at 50 Hz.** Four cars' wall probes and drone steering twice a drawn frame is the biggest
  item, and the least certain.
- **Keyboard ghosting** may limit how many players can share the keyboard.
- **Bridges in A2** show only by their kerbs. If that plays badly, B's grey road is the fallback.
