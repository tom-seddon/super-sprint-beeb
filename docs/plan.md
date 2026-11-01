# Super Sprint for the BBC Master: plan

A port of the Atari ST version of *Super Sprint* (State of the Art / Electric Dreams, 1987; `orig/st`) to the
BBC Master 128, written in Baron. It could be a multiload from disc. What's known about the ST version so far
comes from its file headers and from the longplay video (`orig/*.mp4`, 836 s, 1280×720 at 25 fps). Every
cycle and byte count below is an estimate until Phase 1 or 2 measures it.

## Verdict

**Feasible on a Master 128 in MODE 1 at 25 fps, double-buffered in shadow RAM.** Colour is the hard part, not
speed.

- The ST runs at 320×200 in low res. MODE 1 is 320 pixels across, so the art converts pixel for pixel. The
  play area is 25 MODE 1 rows (200 lines). The scores go in one row of plain 8-pixel text above it (D6).
  That makes 26 rows, 16,640 bytes. Main RAM holds one screen and shadow RAM the other, both at
  `&3F00`-`&7FFF`.
- The track is a still picture. Each frame only redraws a few small sprites (4 cars, plus pickups and
  hazards) and changed HUD digits. The estimate below is about 36,000 cycles per frame against 80,000 at
  25 fps.
- The ST draws with up to 16 colours on screen; MODE 1 has 4. The track alone needs black, grey, green,
  yellow and white, and the cars need three player colours that differ from each other and from the track.
  Something has to give: see Colours.

## The ST version

### Files

| File | Bytes | What it seems to be |
|---|---|---|
| `AUTO/SUPER.PRG` | 74,355 | GEMDOS program: text 72,908, data 1,314, BSS 11,124, no symbols. Not packed. Compiled C (`LINK`/`UNLK` frames), starting with a 101-entry `JMP` table (`&0`-`&25D` in the text segment; entry 0 is the start-up code at `&25E`). |
| `SUPER.DAT` | 212,650 | Starts with interleaved bitplane data: probably track backgrounds and screens. zlib -9 packs it to 80,520. Eight raw 32,000-byte screens would be 256,000, so not all of it is whole screens. |
| `SUPER1.DAT` | 17,024 | Records starting with small 16-bit sizes (`0009 0009 ...`): probably the sprites. |
| `INIT.DAT` | 5,139 | Tables of 16-bit values: probably per-track data (positions, paths). |
| `SSPRINT.HSC` | 295 | The high-score table. |

### What the video shows

- **Screens:** car and controls select (F2-F4 choose joystick 0, joystick 1 or keyboard for each car), "Prepare
  to race", the race, the upgrade screen (super traction, higher top speed, turbo acceleration, increase score,
  levels 1-5), "Winner's Circle" results with lap times, and a dot-pattern wipe between screens.
- **Race screen:** the whole track on one screen, no scrolling. The HUD is the top line (each car's score and
  lap, in its colour) and the bottom line ("TRACK n", "DRONE LAP n").
- **Tracks:** numbered, at least 7 (the frame used for the mock-ups is track 7). Hazards seen: oil, gates,
  traffic cones, tornadoes, wrench pickups, an overpass and a ramp.
- **Cars:** about 15×8 pixels at 320×200, in blue, red and yellow for players and grey for drones. Up to 4 on
  the track at once (to confirm in Phase 1).
- **Art:** the road is dark grey, about (95, 95, 94), with darker shading lines. There are two greens of grass
  plus a grey-green, light grey and white kerbs, yellow and black hazard stripes, and trees.

## Display (MODE 1, 26 rows)

- **Layout, top to bottom:** 1 HUD row, then 25 rows of play area. That is 26 × 640 = 16,640 bytes a screen,
  at `&3F00`-`&7FFF`, with 208 lines shown and 24 blank lines above and below. The ST picture maps 1:1 to the
  play area and keeps its aspect ratio.
- **The HUD is one row of plain 8×8 text above the play area** (D6), not the ST's large masked digits drawn
  over the track. Terse is fine:

  ```
  99,999 L1 99,999 L1 99,999 L1  T8 D1
  ```

  - Each car's score and lap in 9 characters, three of them in car order, then the track number and the
    drone's lap: 35 of the 40 columns.
  - A character is 2 bytes × 8 lines. When a score changes, only its changed digits are written: 16 bytes
    each, into both screens.
  - Nothing in the HUD overlaps a sprite or the track, so it never needs erasing or masking. All 200 lines
    of the ST's track art show, including the parts its HUD covered.
- **Double-buffering in shadow RAM:** ACCCON (`&FE34`) bit 0 picks which screen is shown, and bit 2 sends the
  CPU's `&3000`-`&7FFF` accesses to shadow. So the code that draws, and the sprite data it reads, must live
  outside `&3000`-`&7FFF`.
- **Erasing:** keep a clean copy of the track (16,000 bytes, one sideways RAM bank) and copy the old sprite
  rectangles back from it. Each buffer keeps its own list of what to erase, since it was last drawn two frames
  ago.
- **Overpass and ramp:** cars go under the bridge. After drawing a car, redraw the parts of any overpass it
  overlaps from a masked copy kept per track. Phase 1 finds out how the ST does it.

## Colours

ST low res has 16 colours from 512. MODE 1 has 4 logical colours from the BBC's 8 physical colours. Each ST
colour becomes either one BBC colour or a 2-colour checkerboard. The pattern is fixed to the screen for the
background and to the sprite for sprites. Each ST palette entry gets its own mapping, so this is a per-track
table at build time, tuned by hand.

**The mock-ups** (`docs/img/palette-mockups.png`, close-up in `palette-mockups-zoom.png`) start from one
video frame at 4m50s on track 7. Its pixels were sampled back to 320×200 and grouped into 12 ST colours, then
mapped by hand. The video is blurred and compressed, so these are only rough.

| Option | Palette | Result |
|---|---|---|
| A | black, green, yellow, white; black road | Clearest. Cars and kerbs stand out. The road's shading is lost, apart from what thin lines can keep. |
| B | as A; grey road (black/white checkerboard) | Closest to the ST, but busy. On an RGB monitor the checkerboard stays sharp and cars get lost in it. |
| C | black, red, green, white; grey road | Red kerbs in place of yellow. Same problem as B. |
| D | black, blue, green, white; blue/black road | Distinctive, but blue is too dark for anything else. |
| E | MODE 2, 160 wide, 8 colours | Every colour available, but the cars are 7-8 pixels wide and lose their shape. Rejected. |

**Proposed: option A, plus a palette split for the HUD.**
- **Track:** solid colours wherever possible. The road is black, with its shading kept as sparse white or
  green dots. The two dark greens use green/black, and the grey-greens green/white.
- **Cars:** the three player cars need 3 different body colours out of the 4. Use yellow, white and green,
  each with black detail. Drones use a black/white checkerboard, which reads as grey on a black road, like the
  ST's drones. Green cars on green grass is acceptable, since cars are off the road only briefly.
- **HUD:** the HUD row is separate from the play area, so it can have its own palette: set at vsync, and
  switched to the play area's by a timer interrupt at the bottom of the row. With black and the same three
  car colours there, each score matches its car on the track; the track and drone's lap use one of the three.
  The switch happens on a blank line of the text (the font uses 7 of a character's 8 lines), so its timing
  has a line's slack.
- Changing the mid-screen palette doesn't help the playfield, because cars go everywhere.

The ST's player colours (blue, red, yellow) can't all appear on the track alongside green grass and a readable
road. Matching player colours to the ST matters less than cars that are easy to tell apart. **This is your
call (decision D1).** Phase 2 renders the real ST tracks every way on a real Master screen (jsbeeb) before
deciding.

## Memory (Master 128, the OS taken over)

| Range | Size | Use |
|---|---|---|
| `&0000`-`&2FFF` | ~12K | Zero page, stack, IRQ, sound, game logic, and the drawing code (which must stay outside `&3000`-`&7FFF`) |
| `&3000`-`&3EFF` main | 3,840 | Variables and tables (read when the CPU is not mapped to shadow) |
| `&3F00`-`&7FFF` main | 16,640 | Screen A: HUD row, then the play area |
| `&3000`-`&3EFF` shadow | 3,840 | Tables used only while drawing to shadow (awkward: data for screen B only) |
| `&3F00`-`&7FFF` shadow | 16,640 | Screen B |
| `&8000`-`&8FFF` ANDY | 4K | Code (paged with ROMSEL bit 7; hides the first 4K of the sideways bank) |
| `&8000`-`&BFFF` banks 4-7 | 64K | Clean track copy (16,000), sprites, per-track data, the front end |
| `&C000`-`&DFFF` HAZEL | 8K | Drawing code, independent of sideways paging. The DFS uses it, so the loader has to allow for it. |

That is about 95K besides the screens, against an ST program of 72K of 68000 code plus 230K of data. The
68000's C compiles large, and 6502 versions will be smaller, but the data has to be cut down.

**Multiload** helps most with the data, not the code: one track's art, map and paths at a time (~6-8K packed
each, to be measured), and the front-end screens loaded when needed. Proposed: own 1770 sector loader (WD1770
on the Master at `&FE24`/`&FE28`-`&FE2B`), so the MOS and DFS can stay dead and HAZEL stays ours. A load
between races takes well under a second. Decision D3 waits until Phase 1 measures the packed sizes, and could
be "everything in sideways RAM" if it fits.

## Speed (estimate; the budget at 25 fps is 80,000 cycles a frame)

| Work, per frame | Cycles |
|---|---|
| 4 cars drawn: 16 × 16 pixels is 5 bytes × 16 lines with a 4-position shift, colour 0 transparent through a 256-byte mask table, ~30 cycles a byte | 9,600 |
| 4 cars erased from the clean copy, ~12 cycles a byte | 3,800 |
| ~6 smaller sprites (oil, wrenches, cones, tornado), both together | 8,000 |
| Physics, track collisions and car-to-car collisions for 4 cars; drone steering | 12,000 |
| HUD digits (8×8 text outside the play area), input, sound, IRQ | 3,000 |
| **Total** | **~36,000** |

25 fps looks comfortable. 50 fps (40,000 a frame, less the IRQ) might just fit, but nothing is planned around
it. Phase 1 measures the ST's own frame rate (its VBL count per game loop) and the ST's real sprite sizes and
counts.

The other sprite decision: store each car colour pre-shifted (4 shifts × D directions × 80 bytes; with D = 16
that's 5K per colour, 20K for 4), or store one set and shift and recolour through 256-byte tables while
drawing (about +10 cycles a byte, ~1.3K per set). Decided once D is known.

## Input and sound

- **Three players**, as on the ST: two analogue joysticks (the Master 128's ADC, read as left/centre/right,
  with the fire buttons on system VIA PB4/PB5) and the keyboard. Or more players on the keyboard. Each player
  needs left, right and accelerate.
- **Keyboard ghosting** with several keys held at once must be tested on a real Master before the key sets are
  fixed. The keys are read directly through the system VIA (`&FE4F`, bit 7), but the matrix may still show
  phantom keys.
- **ADC:** its conversions are slow (about 10 ms a channel), and its interrupts upset timed palette splits.
  Read it by polling in the frame IRQ, not by interrupt.
- **Sound:** the SN76489 has 3 tone channels plus noise, the same count as the ST's YM2149. Engine tones for
  the human players, with effects taking channels by priority. Phase 1 reads the ST's sound driver.

## How the port gets checked

- Tools in `tools/`, in Python (`.venv`: pillow, numpy, capstone). Data made from `orig/st` goes in `build/`.
- A 68000 disassembler that applies `SUPER.PRG`'s relocation table, finds code by recursive descent from the
  entry and the `JMP` table, and labels GEMDOS/XBIOS calls and hardware addresses (`&FF8240` palette, `&FF8800`
  YM, and so on).
- Extractors that turn the ST's data into PNGs to compare with the video, before anything is converted.
- jsbeeb (the MCP server) as a Master 128 for screenshots and timing. Each renderer is timed over a recorded
  race before the game is built on it.
- An ST emulator (Hatari) would make it possible to run the original and see its memory. It isn't installed,
  and may be needed if the code proves hard to read statically.

## Phases

### Phase 0: housekeeping
- Project `CLAUDE.md` rules (emulator use, commits), a `Makefile`, `docs/decisions.md`, `JOURNAL.md`.

### Phase 1: understand the ST version
- The disassembler. Find `main`, the game loop, the VBL handler and the frame rate.
- File formats: track backgrounds, palettes, sprites, collision or attribute maps, drone paths, the front-end
  screens. Extract them all to PNG and check them against the video.
- Specs in `docs/st-*.md`: car physics (directions, speed, grip, the upgrades), collisions, drone driving,
  hazards and their timing, laps and scoring, difficulty, the sequence of screens. Don't transliterate the C:
  write the spec, then write the 6502 that suits the 6502.
- Measure: number of directions, sprite sizes and counts, how big each track's data is once converted and
  packed (Baron's `zx02` transform).

### Phase 2: graphics and colour
- The conversion pipeline: ST colour → BBC colour or checkerboard, per track, in MODE 1 byte order.
- Render every track in options A-D on jsbeeb. Decide D1.

### Phase 3: renderer
- Boot, take over the OS, set up MODE 1 with 26 rows, shadow double-buffering, the HUD text and its palette
  split.
- Car and sprite plotting, erasing, the overpass. Time 4 cars driven from a recorded input stream. Decide the
  frame rate (D2) and the sprite storage.

### Phase 4: one race
- Physics, collisions, drones, laps, scoring, HUD, input for 3 players, sound. One track, played start to
  finish.

### Phase 5: the game
- All the tracks, hazards, upgrades, the front end, the results and high-score screens, the screen wipe, the
  disc and the loader (D3).

## Decisions to make

| | Question | Proposed |
|---|---|---|
| D1 | Palette and dithering | Option A (black, green, yellow, white; black road), HUD palette split |
| D2 | Frame rate | 25 fps, double-buffered, unless the ST runs slower |
| D3 | Multiload or all in memory | Own 1770 loader, one track at a time, unless everything fits packed |
| D4 | Machines | Master 128 only (shadow RAM, ANDY, HAZEL, 64K sideways RAM). A BBC B with sideways RAM would lose the double-buffering. |
| D5 | Controls | Two joysticks and keyboard, as on the ST, once ghosting has been tested |
| D6 | HUD | **Decided** (Tom, 2026-11-01): "it might be worth showing the scores and lap indicators as simple 8-pixel text, outside the main 320x200 play area, rather than the large, masked text that the ST version uses." Then (same day): "I reckon one row would be enough. `99,999 L1` (for example) is 9 chars; now there's room for 3 of those in 1 line, and still space for the drone's lap and the track number. It doesn't matter if it's a little cryptic." One row above the play area. |

## Risks

- **Colour.** Four colours may not be enough to make the tracks and cars readable at the same time. Phase 2
  settles it with real data before any game code depends on it.
- **The data may be harder to decode than it looks.** If the ST version builds its tracks or sprites in code
  (rotating cars at run time, for example), Phase 1 takes longer, and Hatari becomes worth installing.
- **Keyboard ghosting** may limit how many players can share the keyboard.
- **Code size.** 72K of 68000 C must fit in ~30K of 6502 with the data, so the spec has to be the logic, not
  the C.
