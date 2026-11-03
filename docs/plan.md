# Super Sprint for the BBC Master: plan

A port of the Atari ST version of *Super Sprint* (State of the Art / Electric Dreams, 1987; `orig/st`) to the
BBC Master 128, written in Baron. Phases 1 and 2 are done (2026-11-01): the original is specified in
`docs/st-graphics.md` and `docs/st-logic.md`, and its graphics converted to MODE 1 in `docs/colours.md`.
Figures marked as estimates stay so until Phase 3 measures them. Decisions are in `docs/decisions.md`, work
done in `JOURNAL.md`.

## Verdict

**Feasible on a Master 128 in MODE 1, double-buffered in shadow RAM. The goal is 50 fps, as the ST (D2),
which is tight: the estimate is about 5% over.** Colour works out (D1). Memory and speed are the tight
resources.

- The ST runs at 320×200 in low res. MODE 1 is 320 pixels across, so the art converts pixel for pixel. The
  play area is 25 MODE 1 rows (200 lines), with one row of 8-pixel text above it for the HUD (D6): 26 rows,
  16,640 bytes. Main RAM holds one screen and shadow RAM the other, both at `&3F00`-`&7FFF`. Checked on
  jsbeeb's Master 128 (`docs/img/jsbeeb-option-a2-track1.png`).
- The ST runs its race at **50 fps**, logic and drawing, with no time compensation: every speed and timer is
  per frame. The BBC aims for the same, so every constant stays as the ST has it: 40,000 cycles a frame,
  against an estimate of about 42,000 (D2; Speed, below). A frame that overruns runs the logic twice next
  time, so the game keeps its speed.
- Four colours are enough with the right mapping: option B, a grey checkerboard road on black, green, yellow
  and white (D1, decided; `docs/colours.md`).
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
- **The HUD** (D6) is one row of 8 × 8 text, ` 999,999 L3 999,999 L3 999,999 L3 T6 D3`: each player's
  score (all 6 of the ST's digits fit) and laps completed, then the track and the drone's laps. Each
  player's text is in their car's colour, which is in the play area's palette, so **no palette split is
  needed**. A changed character is 16 bytes, written into both screens, at most 4 a frame each
  (`docs/renderer.md`).
- **The ST's own HUD text** in the map's bottom row ("TRACK n", "DRONE LAP") stays as it is (Tom,
  2026-11-02: "Don't worry about the track number or DRONE LAP embedded in the track").
- **Double-buffering in shadow RAM:** ACCCON (`&FE34`) bit 0 picks the screen shown, bit 2 sends the CPU's
  `&3000`-`&7FFF` accesses to shadow. Code that draws, and the data it reads, live outside `&3000`-`&7FFF`.
- **Erasing:** from a clean copy of the track, each buffer keeping its own list (as the ST does). Or, to save
  16K, from the converted tiles: a sprite's erase touches at most 3 × 3 cells.
- **Priority:** cars on the ground are hidden where the priority mask is 0; cars on the bridge level and
  airborne ones are drawn last and on top (`docs/st-logic.md` §3). Only tracks 2, 4, 6 and 8 have bridges.

## Colours (D1)

Phase 2 converted all 8 tracks and the cars in six options (`docs/colours.md`, pictures in `docs/img/`,
bootable viewer discs from `make viewer`). **Decided: B** (Tom, 2026-11-01, after the viewer on a real BBC
and a CRT: the checkerboard reads as grey and isn't too busy).
- MODE 1 in black, green, yellow and white. The road is a black/white checkerboard, fixed to the screen;
  the ST's shadows and underpasses are black on it, so the bridges keep their depth. Grass green, dark greens
  as green/black checkerboards, kerbs white, stripes yellow and black.
- Players' cars white, green and yellow (for the ST's blue, red and yellow), with the ST's black outlines and
  wheels. Car 3 and drone-driven cars have black bodies; a drone-driven player's car keeps its colour as
  stripes.

## Memory (Master 128, the OS taken over)

| Range | Size | Use |
|---|---|---|
| `&0000`-`&00FF` | 256 | Zero page; `&90`-`&FF` swapped with a copy around a load (D7) |
| `&0100`-`&03FF` | 768 | Stack; the OS's vectors and variables (the game hooks IRQ1V and BRKV only) |
| `&0400`-`&07FF` | 1,024 | The game's (the language's workspace) |
| `&0800`-`&0DFF` | 1,536 | The OS's: sound, buffers, the NMI handler |
| `&0E00`-`&2FFF` | 8,704 | IRQ, main loop, game logic, state |
| `&3000`-`&3EFF` main | 3,840 | The main screen's own variables (ScreenVars: its erase list, the HUD text it shows); tables, a copy in each, always readable (Tom's idea) |
| `&3F00`-`&7FFF` main | 16,640 | Screen A |
| `&3000`-`&3EFF` shadow | 3,840 | The shadow screen's: the same layout, ACCCON's X picking the screen being drawn's |
| `&3F00`-`&7FFF` shadow | 16,640 | Screen B |
| `&8000`-`&8FFF` ANDY | 4K | Mask B and the logic's state, paged in with the fourth bank while the logic runs (D15) |
| `&8000`-`&BFFF` banks 4-7 | 64K | Data, and the code that reads it: the renderer, unrolled loops |
| `&C000`-`&DFFF` HAZEL | 8K | The OS's: the filing systems' workspace (D7) |

**The data, as measured or estimated:**

| Item | Bytes | Notes |
|---|---|---|
| Clean background, current track | 16,000 | Or tiles for the erase: about 7K a track (estimate) |
| Wall mask and priority mask, current track | 16,000 | 1 bit a pixel, as the ST. Rebuildable from 3,000 bytes of wall vectors and 526 of priority rectangles for all 8 tracks |
| Attribute map, current track | 1,000 | From 1,688 bytes of runs for all 8 |
| All 8 tracks' art, packed | 20,754 | ZX02, option B; about 2.6K a track |
| All 8 tracks' masks, packed | 9,670 | If not rebuilt from the vectors |
| Car sprites | 6,000-30,000 | 8 sets (4 cars, and 4 drone-driven) × 16 directions, 16 × 12: 6K unshifted, 30K pre-shifted to 4 positions |
| Object sprites | ~6,000 | Estimate: explosion, pickups, tornado, gates, barriers, helicopter |
| Drone paths | 7,100 | All 8 tracks, as the ST; about half as bytes |
| Sound | ~12,000 | The ST's sequences and instruments, before transcoding |

All of it at once is about 90K with unshifted sprites; the banks hold 64K. So:
- **Load one track's data per race (D3, decided):** its art (about 2.6K packed), wall vectors, priority
  rectangles, attribute runs and drone path, unpacked or rebuilt into the current track's buffers. The load
  goes through OSFILE, so it works on any filing system (DFS, MMFS, ADFS, Econet). The game leaves the OS's
  memory alone, HAZEL included, so a load needs only zero page swapped and the vectors put back (D7). The
  front-end screens load the same way.
- **Shift the car sprites while drawing** (256-byte shift tables) rather than store 4 copies, unless the
  timings say otherwise.
- **Transcode the sound** at build time into a compact SN76489 form.

## Speed (estimate; the budget is 40,000 cycles a frame at 50 fps, D2)

| Work, per frame | Cycles |
|---|---|
| 4 cars drawn: 16 × 12 pixels is 5 bytes × 12 lines once shifted, colour 0 transparent through a mask table, ~30 cycles a byte | 7,200 |
| 4 cars erased, ~12 cycles a byte | 2,900 |
| Priority masking under bridges (tracks 2, 4, 6, 8, cars near bridges only) | 2,000 |
| Smaller sprites (pickups, cones, tornado, helicopter, sparks), drawn and erased | 8,000 |
| Car logic, wall probes, attribute probes, car-to-car tests: 4 cars, one tick | 16,000 |
| HUD digits, input (keys and ADC), sound, IRQ | 6,000 |
| **Total** | **~42,000** |

About 5% over, before any optimisation, and every line is an estimate. The logic figure is the least certain:
the ST's wall test ANDs each car's shape with the wall mask every frame, and the drones' path following
divides. `docs/st-logic.md` §12 suggests the cheaper forms (a fixed shape per direction, a reciprocal table
per divisor). Other savings to look at: HUD digits drawn only when they change (into both screens), the
smaller sprites only when on screen, unrolled plotters in the banks. With double buffering at 50 fps, each
screen is erased where it was drawn two frames before.

The main loop counts vsyncs (as Critical Mass does) and runs the logic once for each, so an overrun drops one
frame and the game keeps its speed. Phase 3 timed the renderer with 4 cars from a recorded ST trace
(`docs/renderer.md`: 11,071 cycles a frame on average for erasing and drawing them, 16,259 at worst); Phase 4
adds the logic.

## Input and sound

- **Three players**, each on the keyboard or a joystick (D5): joysticks weren't common on the BBC, so all
  three can be on the keyboard. Joysticks are the Master 128's two analogue ones (the ADC, read as
  left/centre/right, fire buttons on system VIA PB4/PB5). Each player needs only left, right and accelerate.
- **Keyboard ghosting** with several keys held decides which keys each player gets; left until later (D5).
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

### Phase 2: graphics and colour (done)
- The conversion pipeline, six options on all 8 tracks, checked on jsbeeb's Master 128. Packed sizes.

### Phase 3: renderer (done, 2026-11-01: `docs/renderer.md`)
- Done: boot, the OS's memory left alone (D7), MODE 1 with 26 rows, shadow double-buffering at 50 fps; the
  four cars erased, drawn and put under the priority mask, from the ST's race on track 6, every frame
  checked against a model; timed (11,071 cycles a frame on average, 16,259 at worst). Sprite storage:
  pre-shifted, trimmed frames, about 10.6K a race.
- Done too: the HUD row, from the ST's scores and laps, checked with the rest.
- Done too: the objects (gates, barriers, pickups, oil-type hazards, cones, the explosion, banner, sparks,
  tornado and helicopter), from a real ST race on track 5, checked with the rest. The tornado's frames are
  compiled (about 3.5K). With all of them a frame averages about 21,000 cycles (`docs/renderer.md`).
- The helicopter is in the fourth bank, all 4 variants (5K), each checked in a race, leaving the objects'
  bank 2.2K and the fourth about 11.1K for the race's data and some logic (Tom: the logic can be squeezed
  in there).
- All 8 tracks checked, frame by frame, each a real ST race with every hazard: everything fits on each,
  the cars' bank tightest (504 bytes free with three human players on track 6), and only track 5's gates
  take a frame over 40,000 cycles (`docs/renderer.md`).
- The gates' steps made cheaper (about 13,600 cycles over their two frames to 10,500): the priority
  bits only for the cells that change, the screen copies indexed as the erase's. No frame of any track
  goes over 40,000 cycles but the race's set-up.

### Phase 4: one race
- Physics, collisions, drones, laps, scoring, HUD, input for 3 players, sound. One track, played start to
  finish, checked against Hatari traces.
- **Started 2026-11-02** (`docs/brief-phase4.md`): bit-exact with the ST (D9), on track 1 first (D10), sound as
  captured register streams (D11, which replaces the sequencer plan under "Input and sound"), keys proposed
  and checked for ghosting (D12), mask B as its mixed cells (D13, decided). The tracer and the oracle come first.
- **The logic's cycles**, what the renderer leaves of a TV frame (39,936), measured over the first ~320
  frames of race 17 on each track with every hazard (`render_check.mjs --json`; the race's set-up and the
  test's own trace reading, about 600 a frame, left out):

  | Track (index) | Mean left | 90% of frames | 99% | Worst | Frames over with logic 12K / 16K / 20K |
  |---|---|---|---|---|---|
  | 0 | 24,180 | 22,064 | 20,580 | 15,045 | 0 / 1 / 1 of 329 |
  | 1 | 24,009 | 21,961 | 20,564 | 12,250 | 0 / 1 / 3 of 323 |
  | 2 | 22,812 | 19,292 | 13,390 | 8,951 | 1 / 12 / 47 of 330 |
  | 3 | 19,653 | 10,277 | 7,021 | 6,045 | 54 / 93 / 117 of 312 |
  | 4 | 18,227 | 9,521 | 3,132 | 1,291 | 52 / 107 / 160 of 315 |
  | 5 | 23,460 | 20,064 | 14,651 | 11,956 | 1 / 9 / 32 of 321 |
  | 6 | 24,340 | 22,168 | 19,576 | 10,567 | 1 / 1 / 5 of 330 |
  | 7 | 20,404 | 12,927 | 9,651 | 7,435 | 27 / 84 / 122 of 331 |

  The logic (4 cars, the IRQ's sound and ADC, input) has to fit in these. A frame over only drops the
  display to 25 fps for a moment (D2), but the busy tracks (3, 4, 7: bridges, gates, the helicopter) would
  do so a quarter to a third of the time at the plan's 16,000. Aim for about 10,000-12,000.
- **The logic's memory**: main RAM `&1813`-`&29FF` free (4,589 bytes) for code, about 300 bytes of
  `&2E00`-`&2FFF` for variables (the erase lists and the HUD's shown text moved to `&3000`), and
  `&3000`-`&3EFF` less the 104 bytes of each screen's own variables: about 3,700 bytes, in main and shadow
  RAM alike, so a table written into both copies is always readable, from a bank or the IRQ too (Tom's
  idea; rebuilt after each per-race load, which lands in screen memory, D7); zero page
  `&71`-`&FB`. The fourth bank has 11,361 bytes after the helicopter; the objects' bank 2,933 to 8,424 by
  track; the cars' bank 504 to 2,346 with three players. The race's own data: mask B (walls) 8,000 bytes at
  1 bit a pixel, the attribute map 1,000, a drone path about 900; sound about 12K for all, before
  transcoding. Mask B is the big one: stored only for the cells that aren't all road or all wall, as the
  priority mask is, it would be much less.

### Phase 5: the game
- All the tracks, hazards, upgrades, the front end, the results and high-score screens, the screen wipe, the
  disc, and the loads through the OS (D3, D7), tested on DFS, MMFS, ADFS and Econet.

## Decisions

| | Question | State |
|---|---|---|
| D1 | Palette and dithering | Decided (Tom, 2026-11-01): option B, a grey checkerboard road |
| D2 | Frame rate | Decided (Tom, 2026-11-01): 50 fps the goal; logic once a frame, as the ST |
| D3 | Multiload or all in memory | Decided (Tom, 2026-11-01): one track's data per race, loaded through the OS |
| D4 | Machines | Decided (Tom, 2026-11-01): Master 128 only, CMOS opcodes allowed; 4 free banks of sideways RAM needed |
| D5 | Controls | Decided in part (Tom, 2026-11-01): any player on the keyboard, all three included; joysticks optional, left open, not urgent (Tom, 2026-11-03); three on the keys waits on a three-person playtest |
| D6 | HUD | Decided (Tom, 2026-11-01): one row of 8-pixel text above the play area |
| D8 | Object sprites | Decided (Tom, 2026-11-01): the explosion and helicopter snapped to 4-pixel steps |
| D7 | Bringing the OS back for a load | Decided (Tom, 2026-11-01): leave the OS's memory alone; HAZEL through a bank only if needed |
| D9 | Exactness of the race logic | Decided (Tom, 2026-11-02): bit-exact, checked frame by frame against Hatari |
| D10 | First track | Decided (Tom, 2026-11-02): track 1 (index 0) |
| D11 | Sound | Decided (Tom, 2026-11-02): 50 Hz IRQ; captured streams for effects and tunes; engines live |
| D12 | Keys | Decided in part (Tom, 2026-11-02): layout Proposed (Q W E, V B N, , . /: no ghosting on paper), the real BBC's check deferred (Tom, 2026-11-03: another set if needed); joysticks as an option |
| D13 | Mask B's storage | Decided (Tom, 2026-11-02): the mixed cells only, as the priority mask |

## Risks

- **Memory.** The estimate above is over the banks by about a quarter before the savings listed. Phase 3
  measures the sprites and code.
- **Speed at 50 fps.** The estimate is about 42,000 cycles against 40,000. Four cars' wall probes and drone
  steering is the biggest item, and the least certain.
- **Keyboard ghosting** may limit which keys three keyboard players can have.
- **A filing system in sideways RAM** (MMFS is often loaded that way) leaves 3 banks; the game needs 4 free
  (D4), so such a machine is told so at boot.
- **Unpaged space** is about 13.5K with the OS's memory left alone (D7). If the IRQ, logic and state don't
  fit, HAZEL can be taken, with the OS's copy swapped through a bank (up to 8K); the low pages stay the OS's.
