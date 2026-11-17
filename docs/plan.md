# Super Sprint for the BBC Master: plan

A port of the Atari ST version of *Super Sprint* (State of the Art / Electric Dreams, 1987; `orig/st`) to the
BBC Master 128 and Compact, written in Baron. Phases 1 to 5 are done (2026-11-01 to 11-08): the original specified (`docs/st-graphics.md`,
`docs/st-logic.md`), its graphics converted to MODE 1 (`docs/colours.md`), the renderer
(`docs/renderer.md`), one race, its logic bit-exact with the ST's (`docs/brief-phase4.md`), and the whole game around
it on two discs, DFS and ADFS (`docs/brief-phase5.md`). Then a time attack version from the same source, on two
discs of its own (`make ta`; `docs/brief-timeattack-2026-11-10.md`), done and merged 2026-11-12. What's left is under
"After Phase 5"; Phase 6 is Tom's to choose from it. The Verdict and Speed sections are the plan's estimates from before Phase 3, kept as made. Decisions are in `docs/decisions.md`, work
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

- `make all` (see `Makefile`; `make` alone makes the discs, 2026-11-16): the disassembly (`tools/st_disasm.py`), track dumps from Hatari
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
- ~~The three-person playtest~~: done 2026-11-15 (Tom: "There were some frame drops noticeable, but they weren't too bothersome in practice."). The sparks that repeat up to 4.1% of fields with three
  humans driving at random (put aside for it, Tom, 2026-11-04; `docs/brief-phase5.md` step 4): left as they are. If
  they're ever wanted fewer, the brief's first fix stands: the sparks a plotter of their own, exact (roughly 40 repeats
  for the 93, ESTIMATED), before dropping sparks when frames run late. The keys' ghosting is done: none on Tom's
  Master, "using the keypress indicators, and no clashes noted" (2026-11-08, D12).
- ~~The bank probe on real hardware, beyond the default layout~~: closed 2026-11-15. Tom tried it in b2, sideways
  RAM in banks 0, 1, 2, 4 and 5 and ROM in 6 and 7: "I'm happy enough with this, I think." And too little, RAM in
  banks 0-2 alone (48K): the error, "needs 64K", "so I think this is working". Not tried: a real Master with
  cartridge RAM, a Compact. What it was (Tom, 2026-11-09: "Please add the bank probe testing
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
- Build from a fresh clone by hand, on Linux and on macOS (Tom, 2026-11-12): "I would like to try this by hand, to
  ensure the instructions cover everything. I'd like this to be straightforward for a person to do by hand without
  needing agent assistance." Tom does it, following the README alone; what he finds missing or awkward is dealt with
  then (in a future session). README.md's building section is vague on purpose till then (Tom, 2026-11-15: "I'm being
  deliberately a bit vague about the build stuff in README.md until I've had a chance to try it from a fresh
  clone"); what it might mention, for Tom to word:
  - Linux done, 2026-11-16, on the branch `fresh-clone-linux`: Tom's first clone on his Linux PC (Mint 22.3, an AMD
    2990WX) wanted `python3.14`, which Mint hasn't, and a Hatari of 2.5.0 or later, where apt's is 2.4.1. So now
    `python3` (checked for 3.12 or later), Hatari 2.6.1 as the submodule `extern/hatari` built by make (as Baron),
    `tools/hatari.sh` saying why it stops, and `game` and `ta` making every ST file first under make's `-j`. Then
    (Tom): a fresh clone of the branch made a working `game.ssd`; `make -j64 game && make -j64 ta` about 5 minutes
    from the clone (about 11 before the last change), and about 2 min 13 s again straight after (every track built
    again: `tools/all_tracks.sh`, the later version's item). macOS not tried, and broken till it's given `PYTHON3`
    and `HATARI` or Homebrew's `sdl2` (Tom: "I don't mind temporarily breaking the Mac build for now"; he may not
    want Hatari built there, "since installing dependencies can be a pain"). Then `make` alone makes all four discs
    (`make discs`: `make game`, then `make ta`), Tom's clone of it checked ("Looks good"), and README.md's building
    section his (`bab1f32`).
  - Next, in a session on the Mac (Tom, 2026-11-16), on the branch `fresh-clone-linux`, not yet merged: macOS's
    build (above), and **GitHub's build, not yet run since it changed**. Done there so far (2026-11-17): on macOS
    make doesn't build Hatari, and `HATARI` is required when a file wants it (Tom: "don't build it in the Mac case.
    Require the user to have it installed somewhere, or build it themselves, and require them to specify the path";
    "It's OK if it's a second-class citizen"; "just testing it at the Makefile level will be good enough"):
    `docs/st-traces.md`. Still to go through with Tom, one by one: `gh`, not on the Mac either (the Actions tab, or
    MacPorts' `gh`); the Mac's `python3`, Apple's 3.9.6 (`PYTHON3=python3.14`, MacPorts'); its packages, MacPorts'
    not Homebrew's; then a fresh clone built. GitHub's build (`074e8a2`: Hatari from `extern/hatari` by
    `make hatari`, no tarball or SHA-256; the local OS doesn't matter, it runs on GitHub). To check it:
    1. Start it. `gh workflow run build.yml --ref fresh-clone-linux` (or the Actions tab, "Run workflow", the
       branch picked) runs the branch's workflow without touching `ci-build`; `main`'s copy has
       `workflow_dispatch`, which GitHub needs. Either way it publishes a release named after the commit, as every
       run does (Tom deleted the test ones before): Tom's call whether a branch commit gets one, or whether to wait
       till it's merged and push `ci-build` as usual (`git branch -f ci-build main && git push origin ci-build`).
    2. The first run misses the cache (its key is now `hatari-<extern/hatari's commit>-Linux-ubuntu-24.04`): the
       "Build Hatari" step runs `make hatari` (about 2 minutes on 2 CPUs, ESTIMATED from the old step's 2 min 11 s)
       and copies the binary to the cache's folder; "Make the ST's files" prints "Hatari v2.6.1"; "Check them
       against the Mac's" passes (`docs/stfiles-sha256.txt`); the discs, time attack's and the release follow. The
       old cache, `hatari-2.6.1-Linux-ubuntu-24.04`, is unused now and can be deleted (`gh cache list`,
       `gh cache delete`), or left to expire.
    3. Run it again (same commit, or the next): a cache hit, "Build Hatari" skipped, and no `cmake -S extern/hatari`
       in "Build the discs" or later (`HATARI` is set for every step from the first, through `GITHUB_ENV`, so make
       doesn't build its own).
    4. Compare the release's notes (the five files' SHA-256 and the zip's) with `make release`'s `dist/` built
       locally at the same commit, as was done for fd53abd: the discs carry the commit, so only the same commit
       compares (`make` then `make release`, once the Mac builds).
    Checked here first (2026-11-16): a depth-1 fetch of `extern/hatari`'s pinned commit works (the workflow fetches
    its submodules `--depth 1`), Hatari's build leaves the submodule's tree clean (the workflow fails if the tree has
    changes, as the version would end in `m`), and the YAML parses. Not run: `gh` isn't on Tom's Linux PC.
  - The prerequisites, in README.md till 2026-11-15 and gone from it now (`CLAUDE.md` still sends a reader there):
    make, a C compiler (`cc`), CMake 3.21 or later and Ninja (Baron and the ZX02 compressor are built from the
    submodules); Python 3.12 or later as `python3` (the build makes `.venv` from `requirements.txt`, stopping first
    if it's older; another with `make PYTHON3=...`; on Ubuntu apt's `python3.12-venv`; a Mac's own `python3` is too
    old); Hatari is the submodule `extern/hatari` (v2.6.1), built by make as Baron is, so SDL2's and zlib's headers
    (`libsdl2-dev`, `zlib1g-dev` on Ubuntu; on a Mac, not built: `HATARI` set to an app of 2.5.0 or later, below),
    and perl; Node 22 for the checks. On Ubuntu 24.04 or Mint 22 and later (CMake 3.21 for Baron, Python 3.12;
    the packages as apt names them, 2026-11-16; `libreadline-dev` as GitHub's build has it, optional to Hatari;
    pip fetches the three Python packages from PyPI):
    `sudo apt-get install build-essential cmake ninja-build perl python3 python3-venv libsdl2-dev zlib1g-dev
    libreadline-dev` (git taken as there: Tom, "we can also assume `git` is always installed in practice"). Disk: about 1.1 GB for `build/` (MEASURED on the Mac, a fresh clone).
    About 16 minutes from nothing one job at a time, most of it the ST's traces in Hatari, made once and kept in
    `build/` (about 5 minutes at `-j64` on Tom's Linux PC); where Hatari
    doesn't run, `docs/st-traces.md` (`make stfiles`, `build/stfiles.tar.gz`). Linux (Mint 22.3) and macOS; not
    Windows.
  - Time attack: `make ta` makes its discs, `build/ta.ssd` and `build/ta.adl` (from its tracks' builds in
    `build/tracks_ta`), after `make game` as a second make (they share `build/sprint.*`: README.md's `make game &&
    make ta`). `make discs`, or `make` alone (its default), does both, one after the other, `-j` passed on (Tom, 2026-11-16: "a make target that
    does `make game` then `make ta`, so the user can build everything in one command"; `make -j64 discs` MEASURED,
    the inner makes running the missing traces side by side); `tools/ta_checks.sh OUT` checks them (MERGE's `tools/ta_merge_check.mjs`, DFS and `--adfs`, among
    them), and `tools/suite.sh` runs that too.
  - The submodules' own submodules: Baron's build needs `rich/baron/extern/richc` (building `main` in a fresh
    worktree failed at CMake's configure until it was fetched, 2026-11-12). README.md's `git clone
    --recurse-submodules` does it; in a clone made without it, `git submodule update --init --recursive`.
  - The release: `make release` (after `make game` and `make ta`) makes `dist/` as the GitHub build does, the four
    discs named as the release names them, the zip's `README.txt` and the zip. The READMEs are templates
    (`tools/disc_readme.py`): `{{version}}` (as the options screen), `{{commit}}`, `{{date}}` (the commit's, UTC,
    "2026-11-14 11:03"), `{{link}}` (README.md at the commit; without it, it's added at the end after a blank
    line), and the release zip's discs, `{{game_ssd}}`, `{{game_adl}}`, `{{ta_ssd}}`, `{{ta_adl}}`;
    `tools/disc_readme.py --check` (in the suite) fails on an unknown name, and the discs' line lengths are checked
    by eye.
- ~~A GitHub Actions build~~: closed 2026-11-16 (Tom: "Yes, close it"), after the run at fd53abd below. What it was
  (Tom, 2026-11-10): "a GitHub Actions setup that builds the game and creates a zip file with the .adl and .ssd files
  in it. The zip file and disk images inside it should be named with commit time and
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
  Also still to do (Tom, 2026-11-12: "the GitHub CI setup should build a time attack disk image as well"): `make ta`
  after `make game` in the workflow, and time attack's discs (`build/ta.ssd`, `build/ta.adl`) in the release. Open:
  whether they go in the same zip or one of their own, and their names (`super-sprint-ta-…`, say). It reads the same
  ST files, so no more Hatari time; its tracks take about as long as the game's.
  Both built 2026-11-14 on the branch `ci-zip` (Tom: "Please put all disk images in the same archive, and the disk's
  README as well"): `make ta` after `make game` (two makes: they share `build/sprint.*`), and one zip holding
  `super-sprint-WHEN.ssd`/`.adl`, `super-sprint-ta-WHEN.ssd`/`.adl` and `README.txt` (`tools/disc_readme.py --pc`:
  the disc's text with CR LF line ends), the release's notes each one's SHA-256. The zip step and the notes run here
  on a clean tree as the workflow has them: the five files as named. Run on GitHub 2026-11-14 (run 43589334755, at
  42aae0e, 8 min 10 s with Hatari from the cache): the release `super-sprint-20261114-1103-42aae`, its zip 343,789
  bytes, and all five files' SHA-256 in its notes the same as 42aae0e's built here.
  Later perhaps (Tom, 2026-11-14): "I wonder whether perhaps the zip should have a different README from the disk, as
  it's intended for reading on a PC rather than the BBC's tiny screen - but that shouldn't be too hard to sort out
  later." Built 2026-11-15 on the branch `pc-readme` (Tom: "The PC README"): `tools/disc_readme.py --pc` reads
  `disc/README-pc.txt`, Tom's text (a placeholder till he writes it), adds the same link to `README.md`, and writes
  it in UTF-8 with CR LF; the disc's README the same byte for byte. Merged into `main` (Tom, 2026-11-15:
  "Yes, merge").
  Then (Tom, 2026-11-15: "Maybe it's going to need some kind of basic templating, so that the disk images' actual
  names can be inserted into the README as well"), on the branch `readme-template`: both READMEs are templates
  (`tools/disc_readme.py`: `{{version}}`, `{{commit}}`, `{{date}}`, `{{link}}`, `{{game_ssd}}`, `{{game_adl}}`,
  `{{ta_ssd}}`, `{{ta_adl}}`; an unknown name stops the build; without `{{link}}` the link line goes after the text,
  a blank line between; `--check` in the suite, an unknown name failing it, the discs' line lengths Tom's to check by
  eye), the release's names made in one place, and `make release` (`tools/release.py`) makes `dist/` and the zip as
  the workflow does, which now runs it. Then three READMEs (Tom, 2026-11-15: "I think maybe it could do with 3
  versions of the README actually"): `disc/README-game.txt`, `disc/README-ta.txt` and `disc/README-pc.txt`, Tom's
  first drafts in `b2c26dd`; merged into `main` (Tom: "Please merge into main").
  Run on GitHub 2026-11-16 (run 43778634091, at fd53abd, 6 min 43 s with Hatari from the cache): the release
  `super-sprint-20261115-2353-fd53a`, its zip 349,786 bytes, and all six SHA-256s in its notes (the five files and
  the zip) the same as `make release`'s at fd53abd here (MEASURED: the notes' lines diffed against `dist/`'s).
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
- ~~A time attack version~~: done, merged into `main` 2026-11-12 (Tom, 2026-11-10): one player, endless laps, a ghost of the best lap, a table and the ghost
  saved per track, a track menu for a front end; its own disc from the same source:
  `docs/brief-timeattack-2026-11-10.md` (built on the branch `timeattack`, merged into `main` 2026-11-12), its questions answered (D36-D50). The ghost's room is the
  cars' bank's three unused car sets (about 8K, ESTIMATED: the green set alone, drawn white for the player and black
  for the ghost, D37). Steps 1 to 3 done (`make ta`: `build/ta.ssd`, `build/ta.adl`; one car, endless laps, Escape out; the lap's time,
  the best and the ghost's on the HUD; the dead code out, the fourth bank 1,931 bytes free); step 4, the ghost, recorded and drawn; step 5, each track's ghost and the table saved and loaded; step 6 in pieces (6a room; 6b a plain menu, tried by Tom, then the drones and the demo's code out and the table loaded once; 6c the menu in 32 rows, tried by Tom; then the tunes out, SCORES the keys and sound, Shared kept in the fourth bank, D55, tried by Tom; 6d the menu's picture, the logo and the maps, tried by Tom; then accelerate opens a track and the highlight goes round the cells, tried by Tom; 6e the track's screen, its 10 entries, tried by Tom; then the numbers open a track's screen too, tried by Tom; 6f the upgrades picked on the track's screen, then his changes to it, tried by Tom; 6g the name typed and saved, tried by Tom; 6i the options, tried by Tom; 6h the title's file kept, Escape loading nothing, tried by Tom); step 7, the close: `tools/ta_checks.sh` in the suite, the game's discs the same as `main`'s, tried by Tom and merged into `main` (2026-11-12); D51-D55.
- ~~The game's loads' two screen faults~~: done 2026-11-14, merged into `main` (Tom, 2026-11-14: "Tested in my Master. Looks good. Please merge it into main."). Found in time attack (2026-11-12) and fixed there only, under `IF GenTimeAttack`
  in `src/loadcode.6502`. For once time attack's merged into one branch (Tom, 2026-11-12: "Please leave the game alone
  for now, but make notes for later, as it'll be worth fixing once everything is merged back into one branch."):
  - The first load's "Loading" redrawn too soon: `load_track.again` clears and redraws the HUD's row from OSBYTE 19's
    vsync, 64 lines before the row's shown, and the redraw takes 72. Time attack's disc ended it about 4 lines late,
    so the g's last line was cleared for one field (Tom saw it on his Master). The game's ends it at line 0 in jsbeeb,
    about 6 lines to spare, but where it ends hangs on the OS's interrupts around the vsync. Time attack's fix: 90
    lines' wait after the vsync (`.past`, 9 bytes), so the redraw runs from about line 32 to 94.
  - The display switched off mid-row: `rows_back` writes R8 &F0 whenever a load ends, so about 8 lines in 312 (1 load
    in 40) a field shows the row's first lines alone. Time attack's fix: from a vsync, CA1's flag polled (`.edge`,
    interrupts off at both calls).
  To do: drop the two `IF GenTimeAttack`s so the game has both (the game's build then differs: LoadCode 20 bytes
  more, every load up to a field longer), then the game's suite, `boot_check` (DFS and ADFS), `flash_check` and
  `load_check` the ones that watch it. `boot_check` caught both in time attack (`--ta`, `--ta --adfs`); the game's
  passes only because its loads happen to end elsewhere, so a fault test is to move one by a few lines.
  Built 2026-11-14 on the branch `game-load-faults` (an unattended job: `docs/brief-load-faults-2026-11-14.md`,
  `docs/report-load-faults-2026-11-14.md`): both fixes the game's too, time attack's discs the same; the fault test
  failing the old code and passing the new; the whole suite passing (40 min 32 s here). On Tom's Master: "Looks good."
- ~~Time attack's scores and ghosts merged~~: done 2026-11-15, MERGE (D57), merged into `main`. (Tom, 2026-11-12): a program that merges a player's tables and ghosts
  with another set, so the disc ends up with the best 10 per track across both sets (`TIMES`) and the ghosts that go
  with them (`GHOST1`-`GHOST8`). "That's the basic idea, anyway. I need to think a bit more about the UX though so
  that it works ok across all filing systems." Designed 2026-11-15 (D57, `docs/brief-merge-2026-11-15.md`): `MERGE`
  on time attack's discs, a `*` prompt before the read and the write, the best 10 of both, the faster ghost. Branch
  `ta-merge`: all built 2026-11-15 and each step tried (Tom's Master, DFS to BeebLink; step 4 in b2,
  DFS to DFS: "Looks good"); the READMEs' wording a reminder for Tom (below). Merged into `main` (Tom,
  2026-11-15: "Yes, merge").

- ~~The select screen's dial frozen after a join~~: done 2026-11-15, merged into `main` (Tom, 2026-11-15: "I've tried
  this on my Master and it looks good. Please merge into main"). (Tom, 2026-11-14, on his Master at DC7D9: "the selected track does
  change, but the highlight doesn't move"): the joining car's panel (`front_block`) left `fshadow` on the shadow
  screen, so the dial, rectangle and seconds went to the screen not shown. The ST turns the dial by the starter's
  controller alone, joins or not, as here. Fixed 2026-11-14 on the branch `select-join-dial` (`front_block` keeps
  `fshadow`); `select_check` goes round the dial again after a join, failing the old build; the whole suite
  passing.

- ~~Time attack's menu: a line of key hints~~: done 2026-11-14, merged into `main` (Tom, 2026-11-14: "Tried it.
  Please merge into main"). (Tom, 2026-11-12, at 6d: "A line of keys perhaps later, maybe squeezed in around the
  logo"; at 6i: "we can think about the hints later".) Designed 2026-11-14 (D56): `F1 OPTIONS` in white at the
  screen's top left, on the menu alone. Built on the branch `ta-menu-hint` (`docs/img/timeattack-menu-hint.png`).
- ~~Time attack's menu: each track's best shows its time but not its name or upgrades~~: done 2026-11-13, merged into `main` (Tom, 2026-11-13: "there's no
  name/upgrades display on the time attack main menu. The record lap is shown, but not the corresponding name or
  upgrade details."). Planned and dropped: D47 gives each cell four lines of the small font, the track, the best time,
  the name and the upgrades (`docs/img/timeattack-menu.png`); 6d drew the first two, noting "No name or upgrades yet
  (6f, 6g)", and 6f and 6g built them on the track's screen alone. What's there: `tagame.6502`'s `tg_row` draws
  `TRACK n` (line 9 of the cell) and the time (19); `timeattack.6502`'s `ta_track_best` already copies the entry's
  name into `TaName` and its upgrades into `TaUp`, which the track's screen draws as a row's name (white) and
  `S2 A1 T2` (green). So the name and upgrades on lines 29 and 39 as the mock-up, nothing for a track with no best;
  `ta_picture_check`'s model of the menu to match. Built 2026-11-13 on the branch `ta-menu-names`, as that
  (`docs/img/timeattack-menu-names.png`, bests poked); Tom, 2026-11-13: "Track names on the main menu look good."
- `!BOOT` above a Model B's PAGE: done 2026-11-16 on the branch `suite-boot`, merged into `main` (an unattended job,
  `docs/report-suite-boot-2026-11-16.md`), `BootOrg` `&2000`, `tools/modelb_check.mjs` in the suite; a Model B with ADFS
  only refused it in b2 (Tom, 2026-11-16: "Tried on b2 with BBC B+ADFS - got the expected error."); the refusal now "Super Sprint needs a BBC
  Master", on one row. Merged without the Master's try (Tom: "This can always be fixed if I'm proven wrong."). What it was (Tom, 2026-11-15: "Note it in the plan as a possible future improvement - I don't fancy waiting for
  the tests right now"): the game's `!BOOT` loads at `&1200` (`boot.6502`'s `BootOrg`), below a Model B's PAGE (&1900
  with DFS 1.2, &1F00 with jsbeeb's 1770 model, DFS and ADFS both), over the DFS's workspace, as MERGE did before it
  moved to `&2000`. In jsbeeb (2026-11-15) both Model Bs still show "Super Sprint needs a Master 128 or Compact" from
  SHIFT-BREAK on `build/game.ssd` and `build/ta.ssd`, then stop in the MOS (PC `&DC5D`: the error comes before any
  language is entered; BREAK to go on). Tom: "It might end up a problem with a BBC B with ADFS only? But that'll be a
  very rare case." The change: `BootOrg` at `&2000` or so (above any PAGE, under `&3000` where the files land); it
  changes the game's discs, so the whole suite. A check: the boot on Model Bs (DFS 1.2, 1770) refused, PAGE read
  against `!BOOT`'s load address, as `ta_merge_check` does for MERGE.
- The suite's wall time: done 2026-11-16, both halves. The laptop's on the branch `suite-boot`, merged
  (`docs/report-suite-boot-2026-11-16.md`): the disc's jobs in the background in their own copy, and longest first,
  2,637 s to about 2,465 (MEASURED, one run each); `MACHINES=2` no better (dropped). agentbox's on the branch
  `ghost-split`, merged (`docs/report-ghost-split-2026-11-16.md`): time attack's ghost checks in two pieces each
  (`GHOSTS=2`, `tools/suite_remote.sh`'s default), the suite there 214-222 s to 179-182 (MEASURED, three runs each);
  4 and 8 no better. On the way the time attack autopilot fixed (Tom: "Yes, fix the autopilot"): it wedged on tracks
  5 and 8, so the ghost check never saw a ghost there; now every track laps and the check wants a ghost on each. The
  report's note on what agentbox's suite still waits on is now an item for a later version, below. What it was (Tom, 2026-11-13: "potentially useful, but still a lot
  of wall clock time either way. So not worth it immediately"); the laptop's measurements, `JOURNAL.md`, 2026-11-13,
  "the checks' times on Tom's laptop".
- For Tom to do: `README.md`, his file (`CLAUDE.md`): reminders only, of what it might usefully mention, kept up as
  things are built (noted 2026-11-12; Tom, 2026-11-15: "I will continue to word the README.md myself, as its contents
  are primarily for human consumption (barring the short note at the bottom for agent use, pointing them at CLAUDE.md
  and so on). But please do continue to maintain the list of things that might usefully need mentioning, as it is
  useful."). The discs' and the zip's READMEs (`disc/README-game.txt`, `disc/README-ta.txt`,
  `disc/README-pc.txt`) have Tom's first drafts (`b2c26dd`, 2026-11-15), and anything they're missing goes in
  `README.md` instead (Tom, 2026-11-15: "I think the zip README is fine as it stands. Any missing README items will be
  added to the README.md in the repo (since it's Markdown and can therefore include images and stuff)."). Its building
  section's notes are in the fresh-clone build item, above.
  Nothing outstanding (2026-11-15): README.md, as Tom wrote it that day, covers playing (the machines and 64 KB of
  sideways RAM, the keys, the options, the sound, the version), time attack and MERGE. Not needed (Tom, 2026-11-15: "I
  don't think points 1 or 3 need documenting"): time attack's name typed on the keyboard; MERGE's ESCAPE, an entry
  on both discs kept once, and its summary before the Y. What's saved to the disc isn't spelt out (Tom: "I have
  modified README.md so it doesn't specify what gets saved to the disk"). MERGE's 32K of sideways RAM dropped: a
  machine that runs time attack has the game's 64K.

#### For a possible later version

Worth noting, not needed for a first release (Tom, 2026-11-16).

- Joysticks (D5): left open, not urgent (Tom, 2026-11-03). The Master 128's two analogue ones, and the
  Compact's, read differently (D33); a choice beside the keys in the options, saved with them.
- Speculative: time attack with its tracks in a second processor's RAM (Tom, 2026-11-13). "the second processor doesn't
  actually get used for anything. Tracks are loaded into second processor RAM initially, then the game runs on the host
  as normal. But instead of loading tracks from disk, they're read from the second processor using one of the Tube
  remote peek operations. Scores are saved to disk as normal." "In principle, this could be made to work with any
  second processor, but start with the 6502 one as I have the hardware to test on." So a Master 128 with a Master
  Turbo or an external 6502 second processor (the Compact has no Tube). Not designed. What's known:
  - The room: time attack's eight track files, packed, are 51,818 bytes on `build/ta.ssd` (COUNTED, 5,882 to 6,875
    each), against a 6502 second processor's 64K less its client ROM and low pages: they fit as they are, with some
    room spare.
  - The game's OSFILE blocks already give host addresses (`&FFFF0000 +`: `boot.6502`, `entry.6502`), so with a Tube
    on, its loads and saves still go to the host. The tracks could be loaded across at the boot by OSFILE with a
    parasite address (the filing system doing the transfer), the boot a few seconds longer on DFS (ESTIMATED).
  - To check, all from memory, none measured: the Master's MOS puts its Tube host code at `&0400`-`&06FF` when a
    second processor is on, which is the game's (the memory table above); reading the parasite's memory from the host
    is a type 0 transfer (parasite to host) through that code's entry at `&0406`, a byte at a time from R3, or the
    game's own few bytes of the same protocol, so the MOS's copy isn't needed; the parasite's client code answers
    with nothing of the game's running there; no Tube interrupts arrive while the parasite's idle, so the game's
    IRQ1V needs nothing for it; the zero page the host code uses. The other second processors take the same
    transfers, with their own addresses.
  - Answered (Tom, 2026-11-13): "ideally, it'd be the existing disk, reusing most of the existing files", so time
    attack's disc, using the second processor when it finds one (OSBYTE &EA, say) and the disc otherwise. "ghost files
    get saved to disk. But if there'd be space to cache them in the 2nd processor RAM as well, great": so whether the
    eight ghosts fit beside the tracks is to be measured (a ghost's size depends on its lap). The load's time "can be
    measured when actually starting on this".
  - Emulators: Tom, "jsbeeb does offer a Master Turbo option but I don't know whether it's accessible in the headless
    version" (`tools/jsbeeb.mjs`, the jsbeeb MCP's `create_machine`): to check. b2 has a Master with a 6502 second
    processor, from memory.
- For later (Tom, 2026-11-08): Econet. "I don't have an Econet setup, so that will definitely have to wait for later."
  What's known: D26's check on ANFS in jsbeeb (the logon refused, LowFree untouched); the loads and the save go through
  OSFILE with no filing system named, so nothing is expected to differ, but nothing has run on a network.
- `make sheets` leaving files in the tree (Tom, 2026-11-16: "`make sheets` should really not leave files lying
  around"; it's in `make all`, the default till 2026-11-16). `tools/compare_sheets.py` writes straight into
  `docs/img` (its `OUT`): `st-tracks.png`, `option-KEY-tracks.png` for each option, `track1-options.png` to
  `track8-options.png` and `cars-options.png`. Ten of them are tracked, Phase 2's comparisons (`docs/colours.md`):
  `st-tracks.png`, `option-a`, `a2`, `b`, `b2`, `c` and `d-tracks.png`, `track4-` and `track6-options.png`,
  `cars-options.png`; so a run shows as changes wherever a picture comes out differently, and leaves the six other
  tracks' sheets (and any other option's) untracked. The likely fix: write to `build/sheets`, and copy one into
  `docs/img` by hand when a doc wants it. Not looked at further.

- The suite on agentbox faster still (Tom, 2026-11-16: "I think at this stage maybe it isn't quite worth it for 2
  minutes. Please add this to the list of things for consideration for a future update, as it'd help with the
  iteration time when making the changes."). MEASURED, `tools/suite_remote.sh` at 8972c9b, `GHOSTS=2`, 179 s: the
  game's 8 track builds one at a time, 0-39 s; its disc, 39-42; the disc's checks in the background, 42-147 (their
  longest, one batch of races, 105 s alone); meanwhile 5 builds and 18 short checks one at a time, 42-105; time
  attack's 8 track builds and disc one at a time, 105-137; its checks 142-179, the last. They're one at a time because
  every build writes `build/sprint.*` and `build/gen` (the Makefile names `build/` in 104 places, no setting to move
  it); the disc's checks escaped by running in their own copy (`OUT/disc_races/tree`). Three changes, each in copies
  the same way, ESTIMATED, none tried:
  1. Time attack built and checked in its own copy (`OUT/ta/tree`, the source copied, the ST's traces, `.venv`, Baron
     and the ZX02 compressor linked) from the start: done by about 85-90 s, inside the disc's checks, so the suite
     about 150 s. `modelb_check`, reading both discs, moved to the end.
  2. The short checks beside each other: each build's outputs copied to a folder of its own, its checks run there in
     the background, the builds (1-2 s each) still one at a time. Little alone once (1) is done; needed if (3)
     shortens the disc's checks' wait.
  3. The track builds 8 at a time, each in its own copy (`tools/all_tracks.sh`, the game's and time attack's), its
     disc and listing gathered as now, the slots check unchanged: the disc made at about 12 s, not 42, so the suite
     about the disc's start and its longest batch of races, about 120 s against 179. It would help the build
     itself too, on a machine of many slow cores: Tom's Linux PC (an AMD 2990WX, 2018), building a fresh clone with
     `make -j64 game && make -j64 ta` (2026-11-16), sat on `tools/all_tracks.sh`, one core busy, where agentbox (an
     M4 Max, much faster a core) doesn't notice. Here at `-j32`, `make game` 2 min 6 s and `make ta` 1 min 5 s
     (MEASURED, 2026-11-16), most of it the 8 track builds one after another. And each of those is `-j1` too: the
     script runs `make beeb` from a plain recipe, so make passes it no jobserver ("jobserver unavailable: using -j1.
     Add '+' to parent make rule.", in every `build/all_tracks_t*.log`); `+tools/all_tracks.sh` in the `game` and
     `ta` rules would pass `-j` on. What that saves isn't measured (likely little: much of a track's build is Baron
     alone). Tom, 2026-11-16: nothing needs doing for now.
  Below that, the 105 s batch of races split. On the laptop (2 cores) nothing spare: a setting `tools/suite_remote.sh`
  turns on for agentbox, as `GHOSTS`, `tools/suite.sh` alone as it is. Each kept only if every check passes and the
  suite is clearly faster, three runs each.

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
| D5 | Controls | Decided in part (Tom, 2026-11-01): any player on the keyboard, all three included; joysticks optional, left open, not urgent (Tom, 2026-11-03); three on the keys played, the playtest done (Tom, 2026-11-15: frame drops noticeable, not too bothersome) |
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
| D36 | Time attack's gates | Decided (Tom, 2026-11-10): the ST's schedule, kept; closed after play (Tom, 2026-11-16) |
| D37 | Time attack's ghost | Decided (Tom, 2026-11-10): a black car, solid, no flicker; the green set alone, the player through `DataWhite`, the ghost `DataBlack`; closed after play (Tom, 2026-11-16) |
| D38 | Time attack's first lap | Decided (Tom, 2026-11-10): a standing start, timed; the ghost shown from the race's start |
| D39 | Time attack's names | Decided (Tom, 2026-11-10): up to 10 characters, typed on the keyboard |
| D40 | Time attack's table | Decided (Tom, 2026-11-10): one table, 10 entries a track, resident; the menu every track's best, a screen a track's 10 |
| D41 | What a time attack race enters | Decided (Tom, 2026-11-10): its best lap only, one entry a race; names may repeat |
| D42 | Time attack's hazards | Decided (Tom, 2026-11-10): the gates and wrecks, which a track always has, kept; patches, cones, barriers and tornado gone |
| D43 | Time attack's ghost at the line | Decided (Tom, 2026-11-10): one that finishes first waits, still, at its lap's first frame until the player crosses |
| D44 | Time attack's menu maps | Decided (Tom, 2026-11-10): the select screen's mini maps beside each track's best; the layout open |
| D45 | Time attack's turnaround | Decided (Tom, 2026-11-10): as short as it can be but for the loads: no wipe, no prepare to race |
| D46 | Time attack's front end rows | Decided (Tom, 2026-11-10): the front end in 32 rows, the race in 26; Shared put back before each race, the table in a bank |
| D47 | Time attack's menu | Decided (Tom, 2026-11-10): all eight tracks at once, the ST's small font, the SUPER SPRINT logo in red and yellow, colour 1 changed below it |
| D48 | Time attack's track screen | Decided (Tom, 2026-11-10): the menu, Return on a track, its 10 entries; Return races, Escape back to the menu |
| D49 | Time attack's upgrades and names | Decided (Tom, 2026-11-10): the upgrades on the track's screen, the last race's at first; a name asked, empty, for every entry |
| D50 | Time attack after a race | Decided (Tom, 2026-11-10): back to the track's screen, the new entry lit |
| D51 | Time attack's attract mode | Decided (Tom, 2026-11-11): none, so no demo race; the menu screens alone; the drones and the demo's code go at step 6 |
| D52 | Picking a track on time attack's menu | Decided (Tom, 2026-11-11): the driving keys move the highlight, 1-8 pick, Return opens; a number or Return wins over a driving key |
| D53 | Time attack's driving keys | Decided (Tom, 2026-11-11): any of the three players' sets drives the car |
| D54 | Time attack's options | Decided (Tom, 2026-11-11): its own simplified screen, mostly text with the logo; keys and sound as the game's |
| D55 | Time attack's tunes and SCORES | Decided (Tom, 2026-11-12): no tunes, room kept for front-end sound effects; SCORES the keys and sound alone |

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
