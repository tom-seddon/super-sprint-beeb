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

**Resume point: step 5.** Every decision is taken; steps 1-4 are done.

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
| The cars' frames | the cars' bank | 10,275, the same for every race (D20, revised) | |
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
| GameVars (`&2E00`-`&2FFF`) | 174 (338 of 512 used) | the state that outlives a race: scores 24, devices 3, wrenches and upgrades (already in the logic's state, which ANDY keeps), track, the attract's place: ~60; but `clear_state` clears GameVars at each load, so step 4 put the race count, generator and drones in `LowFree` (`Gm`), and the rest will want the same | itself |
| The fourth bank's first 4K (`&8000`-`&8FFF`, under ANDY while the logic runs) | 4,096 (D16) | the game's rules between races, the loader's code (copied out to run), the high-score and lap-record tables (295) | itself |
| The background's bank | 177 in a race | between races: the front end's code, font, the screen's picture packed, its tune | itself: reloaded for the next race |
| Both screens (`&3F00`-`&7FFF`) and shadow's `&3000` area | | during a load: the file lands packed in main's screen (~15.9K below `&8000` after the HUD row, D7), the load's code beside it | itself |
| The fourth bank (`&9000`-`&BFFF`) | 1,828 on every track (§8) | the per-track constants as variables, a little | |
| The cars' bank | 2,245 (track 1, three humans); 422 on track 6 (§8) | nothing: every race's frames are resident (D20, revised) | |
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
- **The cars' frames** (D20, revised 2026-11-04): first proposed as a file per combination of humans. Building it
  found every real race needs only cars 0-2's own sets and the drone-driven set, one 10,275-byte block: all
  resident, no files. The demo alone needs car 3's own set, one small file (step 6).
- **The screens**: each picture packed in its own file, loaded into the background's bank with its code.
- **Timing**: not measured; a DFS reads a few K a second on a real Master (to be measured on Tom's), so a
  race's two files (track, cars) at ~15K packed are a few seconds. D7 blanks the display to the HUD row for a
  load so the file can land in the screen; showing a picture during it (the ST's "prepare to race" waits 8 s)
  would need the file to land in the screen not shown, which the OS's ACCCON handling has to allow: measured
  in step 3 (`beeb-measure-fact`), and until then a load shows "LOADING" in the HUD row.
- **The DFS's 31-file catalogue**: 8 tracks + ~10 screens + tunes + the resident files is near
  it already, so screens and tunes share files where they're shown together.

## 5. Where these figures could be wrong

- The per-track file sizes assume 2:1 packing for the logic's data and the priority cells; nothing but the
  background has been packed.
- The tightest banks per track are the objects' (2,491 free on track 5) and the cars' (422 on track 6), with
  every object and three humans (§8); the demo's set is the same size as a race's (10,275, MEASURED).
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
| D20 | The cars' frames per race | (a) a file per combination of humans (8); (b) a file per colour, the tables built at the load | Decided (Tom, 2026-11-03): (a); **revised 2026-11-04: neither, all four sets resident** (`docs/decisions.md`) |
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
   writes any of it (`load_takeover`, built in 3c); a load swaps the game's out and the OS's in, and
   back after it, so every OS and filing-system call sees its own values, and whatever a filing system leaves
   in `&B0`-`&BF` is swapped out before the game resumes. `&00`-`&8F` is the language's, unused, never swapped.
   The two copies go in `&0900`-`&0AFF` (D26), which survives loads. The loader's own code uses no zero page
   at `&90`-`&FF` while the OS is back. Proved by: a sentinel in the OS's copy across a race (`beeb-bss-bugs`),
   and `*CAT` and a load working after it on DFS, ADFS and Econet.
   **How (2026-11-03, from the eight tracks' play builds compared byte for byte):** what differs between
   tracks is the data, as §2 has it, and code only where per-track data sits mid-region: the objects'
   variants and the drone path vary in size, so everything after them moves, and main RAM's code differs
   in 45 bytes, all addresses. Genuine constants in code are few (`TrackGates`, `PathCount`, the banner's
   place and keys, `LgTrack`). So, in order, each its own commit:
   - **3a, a fixed layout**: in each region the per-track part in a slot at a fixed address (`*Slot` to
     `*SlotEnd`), every per-track array padded to the largest track's, each per-track constant a byte in
     the slot; the generators make every track's data so they know the largest. Proved by
     `tools/track_slots.py`: the eight tracks' play builds differ in no byte outside the slots (it fails
     the suite otherwise), and every check as before.
     **Built 2026-11-03.** Slots: the background (16,000), the track's priority cells and tables (`PrioSlot`, last in the cars' bank, up to 3,947), the
     objects' tables (964, padded to 48 variants and 48 entries) and moving objects' tables (927) and their
     bytes (`ObjSlot`, last in its bank, page-aligned, up to 7,390), the fourth bank's slots' backgrounds
     (640), keys (188) and attribute map (1,199, with the track's gates, number and banner's place), mask B
     in ANDY (padded to track 8's 3,427), Shared's path, hazards, gate entries and tornado keys (1,353, the
     path padded to 142 entries). The code put first in the cars' and objects' banks; the logic's moving
     keys in one order on every track (the tornado's compiled code had followed the traced race's). Cost,
     least free over the tracks: the cars' bank 422 -> 370, the objects' 2,491 -> 2,338, Shared 648 -> 607,
     ANDY 237 (now every track's), the fourth bank 1,244 -> 1,230; main RAM 780 unchanged. The hazard race:
     32,863 -> 32,879 cycles a frame (the track's constants read, not immediate), fields repeating 6 -> 5,
     all 2,240 frames matching. `tools/track_slots.py` (in `tools/all_tracks.sh`, so the suite): outside the
     slots the same on every track. The suite 19 of 19, `tools/tracks_check.sh` 48 of 48.
     **Mistake found on the way, not this step's**: the logic tracer kept "the longest run of frames"; with
     every race 17 traced at 9,000 VBLs, track 1's (1,852 frames) ends inside the run and the game's next
     race (track 3's) ran longer, so the re-traced track 1 file was track 3's race. It keeps the first race
     now. (The tracers' file times had moved, so make re-traced every race in Hatari.)
     (`CarsSlot`, then, by who's human, went with D20's revision: the frames are the same in every build.)
   - **3b, the files**: each track's slots as one disc file, its parts ZX02-packed by a disc builder (the
     kit's `make_disc.py` and `dfs.py`), and the car sets' (D20) likewise.
     **Built 2026-11-03** (no car files: D20, revised): `make game`,
     `tools/make_game.py` on `tools/all_tracks.sh`'s eight builds, the kit's ZX02 built from its source
     (`build/zx02`), its `dfs.py` used in place. MEASURED: TRACK1-TRACK8 6,380 to 7,519 bytes (29,905 to
     35,577 unpacked); the disc 14 files of 31, 500 sectors of 800 (128,000 bytes).
   - **3c, the loader**: D7's sequence and the zero page's swap (below), the unpacker, a track's file
     loaded before a race.
     **Built 2026-11-03.** `src/load.6502` (main RAM, 50 bytes: `load_go` copies the rest and runs it) and
     `src/loadcode.6502` (501 bytes, kept in the fourth bank's first 4K and run at `&7C00` in the main
     screen), the takeover's half in `src/entry.6502`, the kit's depacker forked (`src/zx02depack.6502`).
     The play build's race's end asks for the ST's next track (`LoadWant`); the frame loop's top loads it
     and starts the race from the top. Main RAM 780 -> 682 free (the VIAs' and the state's set-up moved
     there from the loader, 72; the objects' copier first in main RAM, its page padding less).
     Faults found by the check: `shared_copy` and `load_go` patched their copy loops' operands and never put
     them back (run once until now); and the MOS's colour flashing, left on (D7 had said to turn it off),
     wrote its own Video ULA control while it had the machine, which halved the CRTC's clock, so the field
     after a load was 40 ms. Tom: OSBYTE 9 and 10 with X = 0 at startup; and a flash already counting when
     the game takes IRQ1V stays frozen (`&251` read 20) and runs out in the first load, so OSBYTE 193 clears
     the counter too (`load_takeover`). `tools/load_check.mjs` checks 10 vsyncs in 10 fields after each load
     and the counter 0, and failed on each of the two lesser builds (no calls; 9 and 10 alone).
     **Found by Tom on his Master** (2026-11-04): the disc's seek times changed from the second race. The game
     set the System VIA's DDRB to `&0F`; MOS 3.20 writes `&CF` there once, at reset (ROM offset `&1C034`,
     its only write), and PB6-7 drive the CMOS chip, so the filing system's read of its seek time
     (`LDY &FE4F` at `&98C9`) got `&FF`, `&00` on a good read in Tom's logs. DDRA needs nothing: every OS routine
     sets it first. The game no longer writes DDRB. In jsbeeb the same read gives `&C8` in every load, and `&FF`
     with `&0F` forced back (287 fields against 186); `tools/load_check.mjs` checks DDRB. It explains
     most of the later loads' time: 241-294 fields -> 162-186. The rest is expected (Tom, 2026-11-04): by then the
     drive has spun down, so a load seeks to track 0 for the catalogue and back to the file; the first
     comes straight after the boot's. (Not timed, but it fits: one CMOS read in the first load, two after.)
     Seen on Tom's Master, 2026-11-04, the disc of `ca4de2e`: the first race to its end and the second loaded,
     "it works as expected now", the seeks to and from track 0 plain to hear. A brief test: one load, no lap of
     the eight tracks yet.
   - **3d, the proof**: every track's race 17 replayed from one disc, through the loads.
     **Done otherwise, 2026-11-03**: outside the slots every track's build is the same (3a), so a track
     loaded right is that track's build, which `tools/tracks_check.sh` checks race by race.
     `tools/load_check.mjs` boots the game disc, loads each track in the ST's order and compares every slot
     with that track's build, both screens' Shared too, then runs 300 frames of its race. MEASURED: all 8
     load right; in jsbeeb's 1770 DFS the first load 87 fields, the others 162-186 (3-4 s). Seen: track 7 racing
     after its load (`docs/img/jsbeeb-game-t6-loaded.png`). Not yet: ADFS, MMFS, Econet (step 11).
   - **3e, the rest (2026-11-04).** D20 revised (above): every logic build now has the game's four sets, so
     `tools/tracks_check.sh` tests the frames a race uses, and the wall probes' shapes go by each car's drone flag
     (`PSet`, 128 bytes): they'd been fixed from the trace, wrong for players 2 and 3 on 2-5 facings each. Not
     checked against the ST with more than one human: step 5's traces will. Escape off (OSBYTE 229). `Loading` in
     the HUD's row during a load; a disc error shows the OS's own message and ` - press a key`, and the load goes
     again on a key (`load_check`: a file that isn't there, then the name put right). The font: OSWORD 10 was
     tried and returned 8 zero lines (the VDU's workspace is in ANDY, the game's, D15; D7 said no VDU calls). Tom:
     the MOS's font is at `&B900` in ROM 15 from ASCII 32, documented for the Master's MOS (the Master 128 and
     Compact), so `row_char` pages it in for each character, interrupts off. It would serve the front end's text
     too (step 8), if the screens want it. The retry no longer releases the NMIs a second time.
4. **The race count's hazards on every track**: races traced with the barriers (every third race) and
   without, the tornado (after race 3) and without, on each track, through the one disc's loads. (D21's
   question withdrawn: the objects are already complete per track.)
   - **Done (2026-11-04).** The disc had played every race as race 17 from one seed. Now `GmRace`, `GmSeed` and
     `GmDrone` (in `LowFree`, as `clear_state` clears GameVars) carry what outlives a race: the counter goes up by
     one at each race's end, at most 50, and the generator goes on where it was. The disc starts at race 0, on
     the seed of track 1's traced race: a real seed, and the drone-won decrement, wait for step 6. Cost: 16 bytes in
     the fourth bank (1,130 free), and the loader's.
   - `tools/disc_races.mjs` plays a traced race on `build/game.ssd` itself, through its load: every frame the
     logic's whole state against the ST's (`tools/logic_compare.mjs`, `logic_check`'s, now shared) and the screen
     against the model; at the race's end the race over on the trace's last frame, the counter, the generator
     and the next track. `tools/disc_races.sh` (in the suite) runs it round the tracks five times at once, the races
     in turn, so each kind of race follows others. 40 races: race 1 (no hazards), 2 (barriers), 4 (the tornado,
     forced), 17 (both, cones, oil; the tornado and cones forced), 50 (the counter's end, the same forced), on
     each of the 8 tracks, 126,141 frames. **All 40 exact, state and screen.** Seen to fail: the coin not forced,
     a byte of the background changed, a wrong next track and counter (the first try at the background
     changed nothing: the byte was already `&55`). `make hazardtrace` records the traces (about 3 hours one at a
     time; these ran three at once, `TRACEDIR`).
   - Fields repeated (a frame late), by race, in each track's run (the start's pause left out):

     | Race | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
     |---|---|---|---|---|---|---|---|---|
     | 1 | 1 | 0 | 1 | 1 | 3 | 1 | 1 | 1 |
     | 2 | 2 | 1 | 2 | 7 | 5 | 3 | 2 | 2 |
     | 4 | 1 | 1 | 2 | 1 | 15 | 4 | 1 | 2 |
     | 17 | 3 | 5 | 19 | 3 | 11 | 18 | 11 | 5 |
     | 50 | 3 | 3 | 3 | 7 | 34 | 23 | 2 | 12 |

     The worst, track 5's race 50: 34 fields in 1,689 frames (2%), so that race runs about 2% slow (D2: 50 fps,
     logic once a frame). Track 5's race 17 repeats 11 here against 6 in the test build at Phase 4's end; why
     hasn't been looked into (the play build also reads the keys, and the frame's cycles have moved since).
   - Also found: the object tracer stopped at 7,000 VBLs, so track 8's race 17 had only 3,935 of its 4,599
     frames, and `make check TRACE=h7` had never seen its end; and `st_race.py` kept the longest run, as the logic
     tracer had. Both fixed (14,000 VBLs, the first run over 100 frames).
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
