# Super Sprint for the BBC Master: plan

A port of the Atari ST version of *Super Sprint* (State of the Art / Electric Dreams, 1987; `orig/st`) to the
BBC Master 128 and Compact, written in Baron. Phases 1 to 5 are done (2026-11-01 to 11-08): the original specified (`docs/st-graphics.md`,
`docs/st-logic.md`), its graphics converted to MODE 1 (`docs/colours.md`), the renderer
(`docs/renderer.md`), one race, its logic bit-exact with the ST's (`docs/brief-phase4.md`), and the whole game around
it on two discs, DFS and ADFS (`docs/brief-phase5.md`). What's left is under "After Phase 5"; Phase 6 is Tom's to
choose from it. The Verdict and Speed sections are the plan's estimates from before Phase 3, kept as made. Decisions are in `docs/decisions.md`, work
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
- **The ST's own HUD text** in the map's bottom row ("TRACK n", "DRONE LAP") stayed at first (Tom, 2026-11-02:
  "Don't worry about the track number or DRONE LAP embedded in the track"). Taken out 2026-11-09 (Tom: "the tracks
  still say `DRONE LAP` at the bottom", then "I'd like to see the re-dump from Hatari approach"): the text's cells
  are replaced in the ST's map before it builds the track, so its trees are drawn over clean ground
  (`tools/st_text_cells.py`, `st_dump_tracks.py --clean`). On Tom's Master: "Looks good, though I didn't play every
  track."
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
| `&0800`-`&08FF` | 256 | The OS's: sound, the printer buffer |
| `&0900`-`&0AFF` | 512 | The game's (D26): the MOS's serial and cassette buffers, unused; kept across loads |
| `&0B00`-`&0DFF` | 768 | The OS's: soft keys, the font, the NMI handler |
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
  left/centre/right, fire buttons on system VIA PB4/PB5); the Compact's are read differently (Tom, D33). Each
  player needs only left, right and accelerate.
- **Keyboard ghosting**: the nine keys chosen are each in a matrix column of their own, so none can ghost
  another (D12); none seen on Tom's Master either (2026-11-08).
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

### Phase 4: one race (done, 2026-11-03: `docs/brief-phase4.md`, `docs/report-phase4-start-2026-11-02.md`)
- Done: the ST's race logic on the BBC, bit-exact with the ST on every frame (D9): the humans' cars, walls
  (mask B as its mixed cells, D13, in ANDY with the logic's state, D15), the track's cells, drones,
  car-to-car, wrecks, pickups, points, laps and the race's end, and the hazards (tornado, barriers, gates,
  cones). Every track's race 17 traced from the ST, replayed through the BBC's logic and drawn from it,
  every frame matching (`tools/tracks_check.sh`, 48 checks; `tools/suite.sh`, 19).
- Done too: three players on the keys (Q W E, V B N, , . /: no ghosting on paper, D12), sound captured from
  the ST's YM and converted for the SN76489 with the engines live (D11, agreed by ear), the helicopter not
  drawn but cued (D16), and a frame shown in the blank after the display, not at the vsync (D17, seen on a
  real Master 128 with no tearing). `build/play.ssd` (`make play`) plays track 1, restarting at the race's
  end.
- Speed, four rounds and D14-D17: the hazard race's (track 5, race 17) fields repeating a frame 734 -> 5
  of 2,240; over the nine races drawn from the logic, 42. The logic run
  a frame ahead (about 9, simulated) was closed, not built: lower latency is better.
- Left open at its close, not urgent (Tom, 2026-11-03): the joysticks (D5), the three-person playtest (D12),
  D16's chop: carried to "After Phase 5".
- Phase 3's budget for the logic (the cycles the renderer left a frame by track, and the memory) is in
  `docs/brief-phase4.md` §9, kept as the record.

### Phase 5: the game (done, 2026-11-08: `docs/brief-phase5.md`)
- Done: one build for every track, each race's data a file loaded through the OS between races (D3, D7), the
  race count's hazards real; the game around the race bit-exact with the ST's (D19), attract mode to game over,
  traced in Hatari and checked read by read; all ten screens converted (D18) and drawn by the game with the
  ST's dot wipe, in the race's 26 rows (D25): title, credits, high scores, lap records, select, prepare to race,
  the winner's circle, upgrades, initials and options (keys and sound, D24); the front end's ten tunes from the
  ST's (D11); the high scores, lap records, keys and sound saved as `SCORES` (D23). Two discs from one build,
  `build/game.ssd` (DFS, D22) and `build/game.adl` (ADFS L, D32), for the Master 128 and the Compact (D33).
- Departures from the ST at Tom's word, for a home computer: the upgrades, the winner's circle and the
  initials wait with no time limit (D27-D29); the initials act on a key's press at once (D30). One load after a
  race and one into a game (D31).
- Checked: `tools/suite.sh`, 38 verdicts, all passing (2026-11-08): 72 traced races exact on the disc, state and
  screen; three whole games exact on both discs; each screen against its model; the tunes at the chip; the
  save; every track's load on both discs. On real hardware (Tom): his Master 128 (DFS and ADFS L) and a Master
  Compact; MMFS and a hard disc (installed by `*COPY`) in b2; BeebLink.
- Room, the play build (MEASURED, `tools/all_tracks.sh`, 2026-11-08), free bytes: main RAM's code 222, the
  `&3000` area 267 (both after D16's sweep), the fourth bank's first 4K 52, the fourth bank 21, ANDY 237; the cars' bank 2,212 on track 1, 370
  at the least (track 6); the objects' bank 4,322 on track 1, 34 at the least (track 5). The screens' files have
  195 (prepare's) to 1,682 (the circle's) free, their parts under ANDY 45 to 357. `docs/memory-map.md` has the rest.

### After Phase 5: what's left
- Joysticks (D5): left open, not urgent (Tom, 2026-11-03). The Master 128's two analogue ones, and the
  Compact's, read differently (D33); a choice beside the keys in the options, saved with them.
- The three-person playtest: the sparks that repeat up to 4.1% of fields with three humans driving at random
  (put aside for it, Tom, 2026-11-04; `docs/brief-phase5.md` step 4). The keys' ghosting is done: none on Tom's
  Master, "using the keypress indicators, and no clashes noted" (2026-11-08, D12).
- The bank probe on real hardware, beyond the default layout (Tom, 2026-11-09: "Please add the bank probe testing
  to the "Needs people or hardware" section"). Tom's Master has run only its RAM in banks 4-7. In jsbeeb only: the
  RAM in banks 0-3, 1/3/5/7 and 0-7 (the game on the highest 4), and too few (2/5/6, the error in MODE 7). Wanted:
  a Master with cartridge RAM in banks 0-3 (D4: a machine whose 4-7 are ROM may still play), and one with too
  little, and a Compact.
- ~~The default keys less cramped~~ (Tom, 2026-11-08, D12: "I think it'd be worth updating the default key
  assignments, so that things are a bit less cramped"): done 2026-11-09, Tom's set: white Q, W, E ("playable out of
  the box in single player mode with the default keys on jsbeeb"); green `, . /`; yellow Pad 5, Pad 6, Pad Delete. No
  ghost of them or of any other key the game reads (D12). On Tom's Master: "Tested on Master."
- ~~The demo's car 3's green stripes~~: done 2026-11-09, black as in a race, through `DataBlack` (D20; Tom: "Yes, try it", then on his Master "Looks good"). Its own
  frames, 29 pixels different, would want a 2.6K file and a load path: left out.
- ~~D16's helicopter chop~~: done 2026-11-08, a rising sweep over the car's blink to its put-back (Tom: "Build C1 (sweep)", "Span the blink").
- ~~A palette split on prepare to race, so the cars are the right colours~~ (Tom's idea, 2026-11-05): dropped
  2026-11-10, Tom: "let's abandon that idea. Everything else in the game flow uses the same black/green/yellow/white
  in-game palette."
- ~~The score pickups' digits~~: done 2026-11-08, black on the yellow box (D34; Tom, after his CRT: "Good, commit").
- ~~"Loading" from the boot's start~~: done 2026-11-09, the boot's MODE 1 in shadow RAM while the files load (D35, Tom's
  idea; on his Master: "Looks much better").
- ~~Track 1's parts in the boot's files~~: done 2026-11-09 (Tom: "Yes, cut them"). SPRINTA ended in track 1's background
  (16,000 bytes) and SPRINTB in its priority cells (2,105), never read: `make_game.py` cuts them. The title's file in
  1.82 s sooner on DFS, 1.62 s on ADFS L; 68 sectors fewer. On Tom's Master: "it looks good".
- ~~The boot's files packed~~: done 2026-11-09 (Tom: "Yes, build it"). SPRINT and the banks' four ZX02 packed on the game's
  discs, 60,134 bytes to 29,147; the title's file in 1.98 s sooner again on DFS, 2.2 s on ADFS L; 121 sectors fewer. On Tom's
  Master: "Looks good", and an hour of the attract mode without problems.
- ~~A boot that printed "Loading", then characters 128-255, and hung~~ (Tom's Master, once, 2026-11-09): a BRK under
  the OS's BRKV between `!BOOT` and the title looks exactly like that. Not reproduced in 770 jsbeeb boots with junk
  RAM and the disc's timing moved (`tools/seed_check.mjs`). The likely cause, from Tom: the probe read an empty
  socket (bank 8) in MODE 7, where the floating bus is the video's last byte, and could take it for RAM. Done
  2026-11-09: banks 7 to 0 probed with the screen clear, a bank counted only if it reads back what's written (D4). On Tom's
  Master: "Looks good on my Master 128, though it has the default config of sideways RAM in banks 4-7 so it wasn't
  exercising every case."
- ~~A crash handler~~: done 2026-11-10 (`src/crash.6502`, `tools/crash_check.mjs`), as designed below; main RAM's
  code 1,183 to 1,019 bytes free. From `!BOOT`'s hand-over to the title (Tom, 2026-11-09: "Please add the crash handler to the open
  items list"). Between `.raw` putting the OS's BRKV back and the title, a BRK goes to the OS's handler: its message
  lands after "Loading" and the rest on rows not shown, so the machine looks hung and says nothing useful (the
  probe fault above). Between loads, while the game runs, a BRK goes to the OS's handler too (each load puts its
  BRKV back), and a wild jump into zeroed memory usually ends at one (BRK is &00). The design (2026-11-10), not built:
  - The game's own BRKV, in main RAM's code: set once the loader has copied that in, and put back after each load
    instead of the OS's, so it covers the loader, the screens and the race.
  - MODE 7, set from the hardware (the CRTC's registers, the Video ULA), not through the OS, whose VDU workspace in
    ANDY the game has taken; a teletext screen holds ASCII, so no font and no palette (Tom: "would it be cheaper
    overall to have it set Mode 7?"). About 100 bytes, estimated.
  - ACCCON set to show the screen the CPU writes (Tom: "It'll need to make sure that ACCCON is set to display the
    same bank that's mapped in to RAM").
  - It shows the build's version and the BRK's address, nothing else (Tom: "just print the address, and don't print
    the ROMSEL value at all. Do include the git commit in the version number screen. Then any investigation can be
    done offline."): by the time BRKV is called the MOS has paged in the language ROM (Tom), so ROMSEL is gone, and
    `&024A`, its copy of `&F4`, is only right where the game kept `&F4` in step (8 of its 47 ROMSEL writes).
  - Built as that, with the SN76489's volumes off too, so a crash doesn't leave a tone sounding. Merged untested on
    hardware (Tom: "this will get ongoing testing just through general use").
- ~~A README on the disc~~: off this list, 2026-11-10 (Tom: "Please remove the README from the open items list. I'll
  track this myself using GitHub issues."). What's built: `disc/README.txt` (his text), `tools/disc_readme.py`
  appending the link to README.md at the build's commit, `tools/make_game.py` putting it last on both discs.
- ~~Does the game build from a fresh clone?~~ (Tom, 2026-11-07): yes, done 2026-11-09. `git clone
  --recurse-submodules` then `make game`, nothing by hand: 15 min 14 s on this machine, every ST trace made again
  in Hatari, and the discs byte for byte this checkout's (`game.ssd` 37fd99f7f367a9ff1a9370dd66efd107df2d78a9,
  `game.adl` 3fc4c18e5d23e4964d9a9673818d35dcb1c76d88; every track's build the same). It took the `rich/teddyboy`
  submodule out (below; `--recurse-submodules` stopped there and left the kit empty), and two traces `make game`
  read but never asked for, now order-only prerequisites, made if missing and kept once made:
  `build/trace/logic_t0_r0.json` (`tools/all_tracks.sh` reads it before calling make) and
  `build/st_screens/screens.json` and `options.json` (`tools/screens.py`'s, made by `tools/game_traces.sh`).
  Then (Tom, 2026-11-09: "What about adding baron as a submodule, building it as part of the build, and having the
  build use the repo's copy?"): make builds `rich/baron` with CMake and Ninja into `build/baron` and assembles with
  that; a fresh clone with no `baron` on the PATH built the same discs here (15 min 18 s). `tools/hatari.sh` takes
  `HATARI`; the README says what the build needs. And where Hatari doesn't run (agentbox: Tom's copy there won't
  start over ssh), the build's ST files packed here (`make build/stfiles.tar.gz`, 2.5 MB) and unpacked in a fresh
  clone build the same discs, in 1 min 8 s, with `HATARI=/usr/bin/false`: `docs/st-traces.md`, which also lists
  every ST file, what makes it and what reads it. Not tried: Linux; Windows not supported for now (Tom).
- A GitHub Actions build (Tom, 2026-11-10): "a GitHub Actions setup that builds the game and creates a zip file
  with the .adl and .ssd files in it. The zip file and disk images inside it should be named with commit time and
  date (in UTC) as well as the part of the commit hash shown in-game, so that it's easier to check which is the
  newer version if you end up with multiple copies." Names like `super-sprint-20261110-1432-e6e28.zip` (Tom: "The
  name format is fine"). The build reads the ST's files Hatari makes (`docs/st-traces.md`), which aren't in the
  repository, so the runner makes them: Tom, "There's an apt-get package for hatari 2.41, so in principle it might be
  possible to run on the CI server and generate the files there" (about 12 minutes from nothing). Open: whether
  Hatari 2.4.1 makes the same files as the 2.6.1 they were made with here (compare its `stfiles` with these: a
  difference shows as a different disc, or checks failing); whether the suite runs there too. Not built. The
  experiments for an agent on Tom's Linux PC: `docs/brief-ci-hatari-2026-11-10.md`, against
  `docs/stfiles-sha256.txt` (the 120 files' hashes, made here). Run (2026-11-10, branch `ci-hatari-2026-11-10`):
  apt's Hatari 2.4.1 can't (its memory dumps break the race and sound tracers: 2.5.0 or later needed); 2.6.1
  built from source on Linux makes all 120 the same and the discs the same, and the whole suite passes there,
  with the tracers reading a dump after the debugger's prompt and running in parallel (`make -j16 stfiles` 45 s).
  Built 2026-11-10 (`.github/workflows/build.yml`). Tom: "Please create a new branch, that
  the CI builds from on push ... Let's not have a build on every push to `main`": it runs on a push to `ci-build`, or
  by hand. Hatari 2.6.1 built from source (cached between runs), `make -j2 stfiles` checked against
  `docs/stfiles-sha256.txt`, `make -j2 game`, the zip uploaded as it is (`archive: false`, so not zipped again).
  The suite isn't run there. Disk (MEASURED, a fresh clone on the Mac at `-j2`): 1.1 GB at most, 800 MB of it
  `build/trace`, against the runner's 14 GB; the ST's files 8 min 3 s, the discs 2 min 41 s.
  Run on GitHub, 2026-11-10: the third run passed (42824858951, at 3502c70; the first two failed on
  `hatari --version`'s exit 1 and Baron's own submodule, `extern/richc`, not fetched). 6 min 49 s with Hatari
  from the cache (the ST's files 4 min 11 s, all 120 the Mac's; the discs 2 min 9 s), and Hatari's build 2 min 11 s
  when it isn't. `super-sprint-20261110-1323-3502c.zip`, 216,135 bytes. A branch's first push that also brings the
  workflow to GitHub started no run; deleting `ci-build` there and pushing it again did.
  Then (Tom: "Please update the CI setup to make a release. Then it should be possible to download the results and
  check them that way"): each build a release named as its zip, the notes the commit and the SHA-256s, in place of
  the Actions artifact (which needs a sign-in to download).
  The first, `super-sprint-20261110-1429-cfe19` (run 42839432092), downloaded with no sign-in: both discs the same
  byte for byte as cfe192a's built here (`--depth 1`, the two submodules, `-j2`), the zip as its notes say.
  Tom, 2026-11-10: "Build tested on my Master, and looks good. I've deleted it for now, but will create another one
  when the game is ready for proper release."
  Still to do (Tom, 2026-11-10: "Putting the disk README into the zip should be part of the GitHub Actions item. Please
  move it there and leave the GitHub Actions item open."): the disc's README in the zip too, as `tools/disc_readme.py`
  makes it (Tom, earlier: "That same file should also be added to the zip somehow").
- For later (Tom, 2026-11-08): Econet. "I don't have an Econet setup, so that will definitely have to wait for later."
  What's known: D26's check on ANFS in jsbeeb (the logon refused, LowFree untouched); the loads and the save go through
  OSFILE with no filing system named, so nothing is expected to differ, but nothing has run on a network.
- ~~The build's version shown in the game~~ (Tom, 2026-11-08: "probably git commit?", "so it's easier to be
  confident about which build you're playing"): done 2026-11-09, on the options screen's status line, bottom right,
  in green, the small font: the commit's first 5 hex digits, "m" after them if the tree had changes (Tom: "the
  initial loading screen won't stick around for long enough", then "in the bottom right corner, in the small font",
  "in green"). `make version` prints it; `tools/version.py`. A rebuild of one commit gives the same disc; every
  commit changes it. Tom, after trying it: "Looks good."
- ~~The `rich/teddyboy` submodule out~~: done 2026-11-08 (Tom: "It should be removed from the repo"). Its
  repository has gone from GitHub, so `git clone --recurse-submodules` stopped there and left the submodules
  after it empty, the kit's among them. `CLAUDE.md`'s list of Rich's projects without it; the mentions in
  `docs/colours.md` and `docs/upstream-notes.md` stay as history. This machine's copy of its history is still in
  `.git/modules/rich/teddyboy`.
- ~~The suite's load on Tom's laptop~~ (Tom, 2026-11-08: "my laptop's fans are spinning up"): done 2026-11-09.
  Measured from this session's 13 runs: the laptop (a 2015 MacBook Pro, 4 threads) did about 5 minutes of builds and
  checks each run, and remade the races' 72 models whenever `tools/render_model.py` changed, 3 at a time (D34's run:
  `disc_races` 705 s against about 107, the checks beside it 2 to 3 times slower). Now `tools/suite_remote.sh OUT`
  runs the whole suite on agentbox: the tree and the ST's files copied there, OUT and the discs back. 3 min 22 s,
  1 s of the laptop's CPU; every verdict and log as D34's local run but the Baron command lines, and the discs
  37fd99f7f367a9ff1a9370dd66efd107df2d78a9 and 3fc4c18e5d23e4964d9a9673818d35dcb1c76d88. For anyone else
  `tools/suite.sh OUT` runs it all locally, now its default (Tom: "It must ultimately be possible to run
  everything locally"). Found on the way: a merge rewrote `tools/hatari.sh`, and make wanted every ST file traced
  again; the ST files' tools are now order-only prerequisites (made if missing, then kept).
- ~~Room~~ (Tom, 2026-11-09: "this is probably worth thinking about next, as it's a potential blocker for any further
  work"): a RAM hunt's batch 1 built 2026-11-09 (Tom: "Build batch 1"), `docs/brief-ram-2026-11-09.md`. Main RAM 222 to
  1,183 free, the fourth bank 21 to 95, its first 4K 47 to 181, at no cost in cycles (the hazard race's mean 32,903 to
  32,884); the dead restart path gone, `human.6502` into the fourth bank, `fill_screen` into the background's bank,
  `font_char` into LowFree's top. The brief lists batch 2 and the levers that cost cycles, for when something needs them.
  Now: the `&3000` area 267 free, ANDY 237, the front end's code 34, the objects' bank 34 (track 5). New code for
  between races goes in the screens' files, in `game.6502` (the first 4K) or main RAM.
- A time attack version (Tom, 2026-11-10): one player, endless laps, a ghost of the best lap, a table and the ghost
  saved per track, a track menu for a front end; its own disc from the same source. Proposed, not built:
  `docs/brief-timeattack-2026-11-10.md`, branch `timeattack`. The ghost's room is the cars' bank's three unused car
  sets (about 8K, ESTIMATED). Tom's notes on it, and its §7 questions, still to come.

### At the end of the project
- Go through `docs/upstream-notes.md` with Tom: which of the faults and gaps found here would be worthwhile
  issues or PRs for the beeb-port-kit, jsbeeb, Baron and the rest (Tom, 2026-11-04). Add to it as things turn up.
- With it, go through the Master reference manuals for anything relevant to the kit (Tom, 2026-11-09: "As part of
  doing the upstream PR list later, it'd be worth going through the reference manuals, to see if there'd be anything
  relevant for the port kit. Something for a future session as I expect this'll be a lot of tokens."). The kit's
  memory tables give the Model B's map in places (`&0B00`-`&0CFF`, `&0900`-`&0AFF`: `docs/upstream-notes.md`).

## Decisions

| | Question | State |
|---|---|---|
| D1 | Palette and dithering | Decided (Tom, 2026-11-01): option B, a grey checkerboard road |
| D2 | Frame rate | Decided (Tom, 2026-11-01): 50 fps the goal; logic once a frame, as the ST |
| D3 | Multiload or all in memory | Decided (Tom, 2026-11-01): one track's data per race, loaded through the OS |
| D4 | Machines | Decided (Tom, 2026-11-01): Master 128 only, CMOS opcodes allowed; 4 free banks of sideways RAM needed; the Compact too (D33, Tom, 2026-11-07) |
| D5 | Controls | Decided in part (Tom, 2026-11-01): any player on the keyboard, all three included; joysticks optional, left open, not urgent (Tom, 2026-11-03); three on the keys waits on a three-person playtest |
| D6 | HUD | Decided (Tom, 2026-11-01): one row of 8-pixel text above the play area |
| D8 | Object sprites | Decided (Tom, 2026-11-01): the explosion and helicopter snapped to 4-pixel steps |
| D7 | Bringing the OS back for a load | Decided (Tom, 2026-11-01): leave the OS's memory alone; HAZEL through a bank only if needed |
| D9 | Exactness of the race logic | Decided (Tom, 2026-11-02): bit-exact, checked frame by frame against Hatari |
| D10 | First track | Decided (Tom, 2026-11-02): track 1 (index 0) |
| D11 | Sound | Decided (Tom, 2026-11-02): 50 Hz IRQ; captured streams for effects and tunes; engines live |
| D12 | Keys | Decided in part (Tom, 2026-11-02): Q W E, V B N, , . /, no ghosting on paper or on Tom's Master (2026-11-08); since 2026-11-09 Tom's less cramped defaults, Q W E; , . /; Pad 5, Pad 6, Pad Delete, no ghosts; joysticks as an option |
| D13 | Mask B's storage | Decided (Tom, 2026-11-02): the mixed cells only, as the priority mask |
| D14 | The drones' dead accumulators | Decided (Tom, 2026-11-02): dropped (only dead ST code reads them) |
| D15 | ANDY for the logic's data | Decided (Tom, 2026-11-02): mask B and the logic's state in ANDY |
| D16 | The helicopter | Decided (Tom, 2026-11-02): not drawn, the car blinks where it comes back; its chop replaced by a sweep over the blink (2026-11-08) |
| D17 | The flip | Decided (Tom, 2026-11-03): in the blank after the display, by System VIA T1 and T2; seen on a real Master |
| D18 | Front-end colours | Decided (Tom, 2026-11-03): each screen its own 4 colours, from option sheets |
| D19 | The game around the race | Decided (Tom, 2026-11-03): bit-exact, traced against Hatari |
| D20 | Cars' frames per race | Decided (Tom, 2026-11-04, revised): all four sets resident for every race; the demo's car 3 drawn from the drone-driven set, black (2026-11-09), its own set left out |
| D22 | The disc | Decided (Tom, 2026-11-03): one 80-track single-sided DFS disc; an ADFS one as well (D32) |
| D23 | High scores | Decided (Tom, 2026-11-03): saved to disc, a failed save shown and ignored; built 2026-11-08 as `SCORES`, keys and sound with them |
| D24 | The ST's keys | Decided (Tom, 2026-11-03): f1, f5, f8, f0 (for F10), f9, Escape from the matrix |
| D26 | `&0900`-`&0AFF` | Decided (Tom, 2026-11-03): the game's, kept across loads (revises D7) |
| D25 | The display between races | Decided (Tom, 2026-11-03): the race's 26 rows for every screen, the HUD row erased as needed |
| D27 | The upgrades' time limit | Decided (Tom, 2026-11-06): none; they wait for fire |
| D28 | The winner's circle's end | Decided (Tom, 2026-11-06): waits for fire, no prompt |
| D29 | The initials' time limit | Decided (Tom, 2026-11-07): none |
| D30 | The initials' keys | Decided (Tom, 2026-11-07): a press acts at once, a held key repeating after 24 fields |
| D31 | Loads between races | Decided (Tom, 2026-11-07): one after a race (circle, upgrades, prepare) and one into a game (prepare, select) |
| D32 | An ADFS disc | Decided (Tom, 2026-11-07): `build/game.adl`, ADFS L, beside the DFS disc |
| D33 | The Master Compact | Decided (Tom, 2026-11-07): a target; tried by Tom 2026-11-08, works |
| D34 | The score pickups' digits | Agreed (Tom, 2026-11-08): black on the yellow box, seen on his CRT |
| D35 | "Loading" from the boot's start | Agreed (Tom's, 2026-11-09): the boot's shadow screen says it while the files load; on his Master, "Looks much better" |

## Risks

- **Speed at 50 fps.** Measured in Phase 4: logic and drawing fit a TV frame on most frames of every track;
  42 fields in the nine races repeat a frame (a gate stepping, cars under a bridge and against walls,
  together).
- **Keyboard ghosting**: none possible on paper with the chosen nine keys (each in its own column), and none
  seen on Tom's Master (2026-11-08, D12). A less cramped set, still to choose, needs the same checks.
- **Room**: main RAM has 1,019 bytes free (after the crash handler, 2026-11-10), the `&3000` area 267 and the fourth bank 95 (2026-11-09, after the RAM
  hunt's batch 1); its brief's batch 2 has more (`docs/brief-ram-2026-11-09.md`).
- **A filing system in sideways RAM** (MMFS is often loaded that way; Tom's MMFS run in b2 worked) leaves 3 banks; the game needs 4 free
  (D4), so such a machine is told so at boot.
- **Unpaged space** is about 13.5K with the OS's memory left alone (D7). If the IRQ, logic and state don't
  fit, HAZEL can be taken, with the OS's copy swapped through a bank (up to 8K); the low pages stay the OS's.
