# Brief - Phase 5, the game: the first steps

> **Status: AGREED (2026-11-03), nothing built.** Branch `phase5`, off `c6f9495` (main, Phase 4 closed).
> D18-D24 below are this brief's proposals. Tom, 2026-11-03: D18, D19, D20 and D22 decided as proposed;
> D21 withdrawn (the play build already has every object, §2); D23, D24 and D25 (the display) decided too: none left open.
>
> Figures say **MEASURED** (a tool run, named), **COUNTED** (off the source, the ST's disassembly or a listing)
> or **PROJECTED** (arithmetic on top).
>
> *Read first: `docs/st-logic.md` §9 (the game's sequence), §6 (the race's rules), §8 (the front end's tunes);
> `docs/st-graphics.md` "Track backgrounds" and "`SUPER.DAT`"; `docs/plan.md` Phase 5; D3, D7, D9, D11, D15,
> D16.*

**Resume point: step 2, room** (`beeb-ram-hunt`). Every decision is taken; step 1 (this brief) is the only
one done.

## 0. The proposal in one paragraph

Phase 4 left one race, on one track, with every track's data baked into the build by its generators. Phase 5
turns that into the game: one disc, the race's code resident, each race's data loaded through OSFILE (D3, D7),
and the ST's front end around it. The order: first **one build that races every track**, the track's data in
files loaded per race (the loader, the packer, the per-track constants made variables), proved by the Phase 4
oracles on all eight tracks from the one disc; then **the game's rules between races** (select, prepare,
winner's circle, elimination, upgrades, next track, game over, the demo race), bit-exact with the ST (D9
extended, D19) and checked against Hatari traces of the sequence; then **the screens** (title, high scores,
lap records, credits, select, prepare to race, winner's circle, upgrades, initials, options) converted to
MODE 1 as Phase 2 did the tracks, with the dot wipe between them; then the high scores saved, and the disc
tried on each filing system. Main RAM has 103 bytes free, so none of this goes in main RAM: the front end
lives in the fourth bank's first 4K (free outside the logic since D16) and, between races, in the
background's bank, whose 16K is reloaded for every race anyway; the load's code runs from the screen it
blanks.

## 1. What the original does - measured

The sequence is in `docs/st-logic.md` §9: an attract loop (title, high scores, lap records, a demo race,
credits, each 250 VBLs or so, the dot wipe between), and a game (select, prepare to race, race, winner's
circle, upgrades, prepare again, next track) until cars 0-2 are all drones.

**Where each screen's picture comes from** (COUNTED, `build/super.s`, for this brief; Phase 1 had left them
"not decoded"):

| Screen | Function | Picture | Bytes |
|---|---|---|---|
| Title | `F_013F68`, `F_015A24(8)` | map 8 of the 11 tile maps (`SUPER.DAT`+`&CD60`), palette `G_01DD62` | in the maps and tiles |
| High-score table | `F_0172EA` | `SUPER.DAT`+`&0000` (`G_01F234`), the table's frame and two cars, text drawn on it | 3,488 |
| Lap records | `F_01BF34` | the same block as the high scores | (the same) |
| Credits | `F_014196` -> `F_014E0A` | `SUPER.DAT`+`&2E9F6` (`G_01F218`), palette `G_01DD42` | 8,000 (one plane of 320 x 200, PROJECTED from the size) |
| Select (the dial) | `F_0198B6`, `F_015A24(10)` | map 10, and `SUPER.DAT`+`&3140`+`&96` (`G_01F22C`): the dial's pieces, PROJECTED | 7,190 (with upgrades') |
| Prepare to race | `F_018776` | `SUPER.DAT`+`&0DA0` (`G_01F230`) | 9,120 |
| Winner's circle | `F_01AC1C`, `F_015A24(9)` | map 9 | in the maps and tiles |
| Upgrades | `F_01A0D6` | `SUPER.DAT`+`&3140` (`G_01F22C`) | (the same as select's) |
| Initials entry, options (F1) | `F_017A42`, `F_0192A6` | not traced | |

So three screens are tile maps, which `tools/st_tracks.py` already decodes (Phase 2 converted maps 0-7; maps
8-10 use other palettes). `SUPER1.DAT` (17,024 bytes) is loaded by `F_0108B4` into `G_01F238`, the masks'
space, before any track is built there; what reads it is not traced yet (step 7). The blocks' formats are
not decoded: they're what step 7 does, in Hatari, as Phase 1 did the tracks.

**Pictures already captured** in Phase 1 (`build/logic/seq_*.png`, from Hatari): the title (`seq_p14056`), the
high scores (`seq_p14076`), the lap records (`seq_p14096`), the credits (`seq_p140D8`), prepare to race
(`seq_t11000`), the winner's circle (`seq_t10200`), the wipe part way (`seq_t10600`, `seq_v3000`). Not
captured: the select screen's dial, upgrades, initials entry, options.

**The front end's tunes** (st-logic §8): the select tune (12 s, also the upgrades'), prepare to race (7.7 s),
a join jingle, five winner's-circle tunes (10-13 s each), a "ding" per upgrade bought. D11 converts tunes as
captured streams; their sizes are not measured (step 9).

**The wipe** (`F_014E34`): 8 steps out and 8 in, the patterns from `G_01DD82`, 3 to 5 VBLs a step on the ST
(st-logic §1, MEASURED in Phase 1).

## 2. What the port is now - counted

Every track's data is assembled into the build by `tools/gendata.py` and `tools/gen_logic.py`, one track
per build (`TRACK=n`). For the game, what differs between races has to come off the disc instead. What differs
between tracks (COUNTED: `gen_logic.py` run for tracks 1 and 8 and its files compared, for this brief; the
renderer's from `src/sprint.6502` and `docs/renderer.md`):

| Item | Region | Bytes | Differs by |
|---|---|---|---|
| The clean background | the background's bank | 16,000 (about 2.6K packed, `docs/colours.md`) | track |
| The priority map, cells and classes | the cars' bank | about 3,640 (track 6's, `docs/renderer.md`) | track |
| The cars' frames | the cars' bank | 5,331 (one human) to 10,615 (three) | which cars are human (D20) |
| Mask B | ANDY | 2,168 to 3,427 | track |
| The attribute map, slots, probes (`lgen/cells`) | the fourth bank | 1,195 | track |
| The drone path (`lgen/path`) | Shared | 616 to 994 | track |
| The hazards' boxes (`lgen/hazards`) | Shared | about 285 | track |
| The background objects' variants and tables (`objdata`) | the objects' bank | 3,589 | track (its gates, barriers' kinds, banner) |
| `TrackGates`, the banner's place, `LgTrack`, `LgRace` | assembled constants | | track, race |

Same on every track: the probes and their pre-shifted shapes, `lgen/tables`, the tornado's compiled code,
the font, the sound's effects.

Two things in that table aren't just data moving:
- **The cars' frames depend on who's human.** A race stores the human cars' own sets and, if any of cars 0-2
  is a drone, the drone-driven set: 64 + 16 frames at most (`docs/renderer.md`). In the game that changes
  between races (joining, elimination), and the demo race draws all four cars in their own colours.
- **The objects are already complete per track.** In the play build `tools/gendata.py --logic` makes every
  gate and barrier frame the track has, from the ST's tables (`logic_objects`), all 22 slot sprites, and
  every moving object's frames (explosion, sparks, the track's banner); only the renderer test's builds
  pick variants from a traced race (`frames_used`). So a track's objects need no new work, only moving into
  its file. (COUNTED, `tools/gendata.py`;
  the first draft of this brief had it the other way, D21 withdrawn.)

## 3. The ledger

From `docs/memory-map.md` (the play build, track 1, MEASURED 2026-11-03) and `tools/all_tracks.sh`
(MEASURED for this brief, §8). The game wants (PROJECTED, every figure to be measured by the step that builds
it):

| Region | Free now (track 1) | Phase 5 wants | Where it comes from |
|---|---|---|---|
| Main RAM's code (`&0E00`-`&29FF`) | 103 | the game's sequence glue: paging the front end in and out, ~100 | the room hunt (`docs/brief-ram-2026-11-03.md`): 780 free after it |
| GameVars (`&2E00`-`&2FFF`) | 174 (338 of 512 used) | the state that outlives a race: scores 24, devices 3, wrenches and upgrades (already in the logic's state, which ANDY keeps), race count, track, the attract's place: ~60 | itself |
| The fourth bank's first 4K (`&8000`-`&8FFF`, under ANDY while the logic runs) | 4,096 (D16) | the game's rules between races, the loader's code (copied out to run), the high-score and lap-record tables (295) | itself |
| The background's bank | 177 in a race | between races: the front end's code, font, the screen's picture packed, its tune | itself: reloaded for the next race |
| Both screens (`&3F00`-`&7FFF`) and shadow's `&3000` area | | during a load: the file lands packed in main's screen (~15.9K below `&8000` after the HUD row, D7), the load's code beside it | itself |
| The fourth bank (`&9000`-`&BFFF`) | 1,828 on every track (§8) | the per-track constants as variables, a little | |
| The cars' bank | 2,245 (track 1, three humans); 422 on track 6 (§8) | the frames for every combination of humans | D20 |
| Zero page | `&5A`-`&7B` free (used to `&59`) | the loader's pointers, borrowed | |
| The disc | play disc 67,840 bytes (MEASURED, `build/play.ssd`) | 8 tracks' files, the car sets, ~10 screens, the tunes: PROJECTED 150-200K | D22 |

**Main RAM is the binding region, and the plan is not to put anything there.** The levers, to cost in a
`beeb-ram-hunt` before the loader is written (step 2):
1. Code and tables only the logic reads, into the logic's bank, and read-only data into Shared: built in
   `docs/brief-ram-2026-11-03.md` (main RAM 103 -> 780). (First proposed here: `gen/objects`' "1,600 bytes
   of tables" into the objects' bank. There were none: the memory map credited `objects.6502`'s own code to
   the constants file it includes, fixed in `tools/memmap.py`.)
2. The loader's code (the zero-page swap, the vectors, OSFILE, the unpacker) kept in the fourth bank's first
   4K and copied into the main screen to run: the display shows only the HUD row during a load (D7), and code
   calling OSFILE can't sit in `&8000`-`&BFFF` (the filing system's ROM is paged in there). Main RAM keeps a
   few bytes to copy it out and call it.
3. The front end's code in the fourth bank's first 4K and the background's bank, never main RAM.
4. If a fourth is needed: D7's HAZEL, swapped through a bank, as decided would be considered first.

## 4. The loads

D3 and D7 decided the mechanism; what's left is what goes in each file, and the disc.

- **A track's file**: the background, the priority data, mask B, the attribute map, the path, the hazards'
  boxes, the objects' variants and their tables, the track's constants, each part ZX02-packed (Baron's
  transform, as `docs/colours.md` measured), unpacked in place into its bank. PROJECTED 6-9K a track packed:
  2.6K of background, the rest at an assumed 2:1.
- **The cars' frames** (D20): (a) one file per combination of humans (the 7 non-empty subsets of cars 0-2,
  plus the demo's four own colours: 8 files of up to ~10.6K raw), or (b) a file per car colour and one for
  the drone-driven set, their frame tables rebuilt at the load. (a) is the generator as it is, run 8 times;
  (b) costs code and the page padding the plotter's frames need (659 bytes, `docs/renderer.md`).
- **The screens**: each picture packed in its own file, loaded into the background's bank with its code.
- **Timing**: not measured; a DFS reads a few K a second on a real Master (to be measured on Tom's), so a
  race's two files (track, cars) at ~15K packed are a few seconds. D7 blanks the display to the HUD row for a
  load so the file can land in the screen; showing a picture during it (the ST's "prepare to race" waits 8 s)
  would need the file to land in the screen not shown, which the OS's ACCCON handling has to allow: measured
  in step 3 (`beeb-measure-fact`), and until then a load shows "LOADING" in the HUD row.
- **The DFS's 31-file catalogue**: 8 tracks + 8 car sets + ~10 screens + tunes + the resident files is near
  it already, so screens and tunes share files where they're shown together.

## 5. Where these figures could be wrong

- The per-track file sizes assume 2:1 packing for the logic's data and the priority cells; nothing but the
  background has been packed.
- The tightest banks per track are the objects' (2,491 free on track 5) and the cars' (422 on track 6), with
  every object and three humans (§8); D20's demo set (all four cars' own frames) is the cars' bank's risk.
- The front end's code size isn't counted at all: the ST's front-end functions lie between `F_0172EA` and
  `F_01BF34` (19,530 bytes of 68000, COUNTED) with other code among them, much of it text drawing. If the
  fourth bank's 4K and the background's bank between races aren't enough, the front end is an overlay of
  its own, loaded per screen.
- Whether `SUPER1.DAT` is front-end art at all is not known.

## 6. The decisions

| # | Question | Options | Proposed |
|---|---|---|---|
| D18 | The front-end screens' colours | (a) each screen its own 4 of the BBC's 8 colours, dithered, converted as Phase 2 did the tracks, with option sheets and a viewer disc; (b) the race's palette for all | **Decided (Tom, 2026-11-03): (a)** |
| D19 | How exact the game around the race is | (a) D9 extended: the select dial, the joins, the bonuses, the elimination, the upgrades, the next track and race count, the demo race, all bit-exact with the ST, checked against Hatari traces of the sequence; the screens' layouts checked by eye against the ST's pictures; (b) the rules by the spec, not traced | **Decided (Tom, 2026-11-03): (a)** |
| D20 | The cars' frames per race | (a) a file per combination of humans (8); (b) a file per colour, the tables built at the load | **Decided (Tom, 2026-11-03): (a)**, unless the disc doesn't fit (D22) |
| D21 | (withdrawn) | The play build already makes every object a track can draw (§2) | |
| D22 | The disc | (a) one 80-track single-sided DFS disc (200K, 31 files), copied as it is to MMFS, ADFS or Econet; (b) double-sided, the second side as drive 2; (c) ADFS only | **Decided (Tom, 2026-11-03): (a)**, measured at step 3 |
| D23 | High scores and lap records | (a) saved to `SSPRINT.HSC`-style file as the ST does after each game, a failed save (write-protected disc, Econet without rights) said in the HUD row and ignored; (b) kept for the session only | **Decided (Tom, 2026-11-03): (a)** |
| D24 | The ST's keys | F1 options, F5 shortens the celebration, F8 pause, F10 abandons the race, Esc ends prepare to race, F9 sound on/off: on the BBC f1, f5, f8, f0 (no f10), Escape (read from the matrix, Escape itself is off, D7), f9 | **Decided (Tom, 2026-11-03): as stated**; the options screen offers each player keys or (later, D5) a joystick, and sound |

Also to settle, not urgent before step 2:
- **The display between races (D25)**: **Decided (Tom, 2026-11-03)**: the race's 26 rows for every screen,
  set up once; the pictures in the play area's 25 rows, the HUD row erased as each screen needs.
- **The wipe**: the ST's 16 patterns in MODE 1's pixels, exact. About 16K read and written a step, ~160,000
  cycles (PROJECTED), so 4 fields a step, close to the ST's 3 to 5.
- **The filing systems**: jsbeeb's Master has DFS and ADFS; MMFS and Econet need b2, b-em or a real machine
  (`beeb-cross-emulator`, Tom's hardware).

## 7. The steps

Each one commit with its measurement in the body; the suite (`tools/suite.sh`, `make check`) after each that
touches the build.

1. **This brief, D18-D24** - no code. (Done.)
2. **Room** (`beeb-ram-hunt`, `docs/brief-ram-2026-11-03.md`): §3's levers costed, the cheap ones built, the ledger regenerated. (Done: main RAM 103 -> 780, and `&0900`-`&0AFF` the game's, D26.) Proved by: the suite;
   the default disc byte-identical where nothing should change (`beeb-identical-build`).
3. **One build, every track**: the per-track constants made variables; the generators write a file per track
   (and per car combination, D20) instead of assembling one; the loader (D7's sequence, the ZX02 unpacker)
   loads track n's files before a race. The disc's size and catalogue measured (D22). Proved by: the Phase 4
   oracles, all eight tracks' race 17 replayed from the one disc, every frame exact (`tools/tracks_check.sh`
   driven through the loads); a load timed in jsbeeb and on Tom's Master.
   **Zero page around a load** (Tom asked, 2026-11-03; nothing of it built yet): in a race the game owns
   `&04`-`&FF` but `&FC`, over the MOS's NMI workspace `&A0`-`&A7`, the filing system's transient `&B0`-`&BF`
   and its persistent `&C0`-`&CF`. The takeover saves the OS's `&90`-`&FF` (112 bytes) before the game
   writes any of it (today it doesn't: `src/entry.6502`); a load swaps the game's out and the OS's in, and
   back after it, so every OS and filing-system call sees its own values, and whatever a filing system leaves
   in `&B0`-`&BF` is swapped out before the game resumes. `&00`-`&8F` is the language's, unused, never swapped.
   The two copies go in `&0900`-`&0AFF` (D26), which survives loads. The loader's own code uses no zero page
   at `&90`-`&FF` while the OS is back. Proved by: a sentinel in the OS's copy across a race (`beeb-bss-bugs`),
   and `*CAT` and a load working after it on DFS, ADFS and Econet.
4. **The race count's hazards on every track**: races traced with the barriers (every third race) and
   without, the tornado (after race 3) and without, on each track, through the one disc's loads. (D21's
   question withdrawn: the objects are already complete per track.)
5. **The sequence tracer**: Hatari traces of a whole game (select, two or three races, joins, an elimination,
   upgrades bought, a game over), the state between races at each screen. The demo race traced on each track.
6. **The game's rules** on the BBC, one screen's logic at a time, each checked against step 5's traces, with
   placeholder screens (text in the HUD row's font): select, prepare, winner's circle and its bonuses,
   elimination, upgrades, next track, game over, the demo race and the attract loop's order and timings.
7. **The ST's front-end data decoded**: `SUPER.DAT`'s first three blocks, the credits' plane, `SUPER1.DAT`,
   maps 8-10, initials entry and options captured; written up in `docs/st-graphics.md`.
8. **The screens converted** (D18): option sheets and a viewer disc for Tom; then drawn by the game, with the
   wipe.
9. **The front end's tunes** (D11's method): captured, converted, sized, heard against the ST's.
10. **High scores** (D23): initials entry and the tables; saving and loading them is lower priority (Tom,
    2026-11-03), dropped if the disc's catalogue or the room for its error handling runs short.
11. **The disc on every filing system**: DFS and ADFS in jsbeeb (`beeb-target-matrix`), MMFS and Econet on
    hardware or another emulator; the BRKV retry on a disc error tried.

## 8. What the all-tracks build says today

Each track's play build (three humans, race 17's objects), free bytes by region (MEASURED, `tools/all_tracks.sh`,
2026-11-03, from `c6f9495`):

| Track (index) | 1 (0) | 2 (1) | 3 (2) | 4 (3) | 5 (4) | 6 (5) | 7 (6) | 8 (7) |
|---|---|---|---|---|---|---|---|---|
| Main RAM's code | 103 | 103 | 103 | 103 | 103 | 103 | 103 | 103 |
| The fourth bank | 1,828 | 1,828 | 1,828 | 1,828 | 1,828 | 1,828 | 1,828 | 1,828 |
| ANDY | 1,496 | 1,199 | 985 | 1,054 | 681 | 421 | 668 | 237 |
| Shared (`&3000` area) | 1,146 | 1,132 | 1,093 | 768 | 987 | 768 | 880 | 855 |
| The cars' bank | 2,245 | 1,973 | 1,605 | 1,137 | 848 | 422 | 1,128 | 1,687 |
| The objects' bank | 7,273 | 7,273 | 4,283 | 6,587 | 2,491 | 6,753 | 7,099 | 3,734 |

Every track assembles. In one build for every track each region has to hold the largest track's part, so
the fixed parts' room is the column minimum: ANDY 237, Shared 768, the cars' bank 422, the objects' bank
2,491. The fourth bank and main RAM are the same on every track: nothing per track lives in them but
`lgen/cells` (the same size on each). (Before the room hunt: see `docs/brief-ram-2026-11-03.md` for after.)
