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
| The fourth bank's first 4K (`&8000`-`&8FFF`, under ANDY while the logic runs) | 4,096 (D16) | the game's rules between races (copied to the background's bank to run: step 6), the loader's code (copied out to run) | itself; the high-score and lap-record tables went to Shared |
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
     (`PSet`, 128 bytes): they'd been fixed from the trace, wrong by one pixel of player 2's car at facing 6, the line 3 column 4 that the drone-driven frame hasn't; not, as first written here, players 2 and 3 on 2-5 facings. Not
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
   - **With two and three humans** (Tom's question, 2026-11-04: can the traces test them?). The tracers take keys by
     car (cars 1 and 2 by the joysticks' bytes, `G_01DFCC`'s devices; fire held in the attract mode joins a car).
     `tools/steer_script.py` drives at random, and `tools/human_traces.sh` traces four races a track: cars 0-2 on
     race 17, 1-2 on race 2 (car 0 a drone), 0-1 on race 4, 0 and 2 on race 1. With those, 72 races on the disc,
     249,274 frames, 123,093 of them with two or three humans.
   - **That found a bug the other 40 races couldn't**, in Phase 4's `cells.6502`: `.ramp` took the cell's type from
     A, which the dispatch had just overwritten with the handler's high byte, so a ramp `&20` (facing 0-7, sequence
     8) was treated as a `&10` and never launched a car. Seen on track 2, race 4, cars 0 and 1, frame 2407, as car 1
     stayed on the ground at facing 3. No other race had started a sequence 8 jump, or it would have differed too.
     Fixed for no bytes: the type is kept before the dispatch.
   - **The old probe fault needed placing, not driving.** The fault's one pixel (line 3, column 4 at facing 6) decides
     a wall only at 10-31 of a track's 40,000-odd places. Put back, it changed nothing in any of the 32 driven races,
     though a control (facing 14's shape at facing 6) is caught at once, so that was a true miss. So
     `tools/logic_scripts/probe_t0.json` puts cars at such places, the same on both machines at the same flip: 6
     for car 1, one held for 30 frames for the drone in car 0. The ST bounces car 1 off the first at frame 301,
     which shows the pixel counts, and the BBC follows exactly, 2,113 frames. With the faults back,
     `disc_races.mjs --probes` sees car 1's at frame 301 and car 0's at 807. State only: there's no object trace.
   - Fields repeated with humans: the worst is track 5's race 17 with cars 0-2, 93 fields in 2,246 frames (4.1%),
     then track 3's, 95 in 2,759 (3.4%), against 2% for the worst race with one human. **The cause is the sparks**
     (measured 2026-11-04, each frame's cycles by routine on the disc). Humans themselves cost about 100 cycles a
     frame more than drones; random driving hits walls far more, and a bounce's sparks are movers, about 1,490
     cycles a piece to draw and erase (`objmov` 918, `erase_cars` 365, `build_movers` 137, `mov_all` 71). Track 5's
     race has 4.2 pieces a frame against 2.75 with one human, and a mean frame of 36,645 against 32,772. With the
     sparks left out of the drawing, the logic exact: 93 repeats become 7 and 95 become 2, the means 31,798 and
     30,927. A frame may run long: it flips anywhere in the blank (98 lines, 12,544 cycles), so repeats come from
     runs of long frames, not from single ones, and 551 frames over 39,936 give only 93. A simulation of the
     flips from those cycles gives 87 and 91, so it's fit to predict: pieces 25% cheaper 48 and 38, 50% cheaper
     19 and 10. **Put aside until the three-player playtest (Tom, 2026-11-04: in general play it doesn't feel
     like it'll be an issue).** Random driving isn't how people drive. If it starts to feel necessary, in order:
     1. Sparks get a plotter of their own, as the tornado did (its took the race's mean from 22,602 to 20,994).
        Exact, so the oracles stand. They go through the general `mov_plot` (clipping, patching, bands) for at
        most 32 bytes; how much of its 918 cycles is set-up hasn't been split, nor the objects' bank's room
        checked. Halving the plotting alone makes a piece about 30% cheaper: roughly 40 repeats, an estimate.
     2. Only if that's not enough, sparks dropped when the frames are running late. Cheap, but the screen no
        longer matches the ST in those frames: a decision to log, and the screen oracle changed to allow it.

     To measure again: the profile was a scratch copy of `tools/disc_races.mjs`, not kept. It hangs
     `tools/game_profile.mjs`'s `debugInstruction` hook, labels from `build/tracks/tN.json`, on `race()`, and writes
     each frame's cycles by routine with `Repeats`, `CarCount` and `MovCount`; the sparks are left out by cutting
     `MovCount` at `logic_frame.built`, keeping the last piece if `RcTornado`'s set. The flips: a frame shown at
     once if it ends inside a blank with no flip yet, else at the next blank's start.
   - Two traces stopped at the tracer's limit with the race unfinished: track 6's cars 0-2 and track 8's cars 0-1,
     about 11,000 frames each. On the ST every drone left in those races stays wrecked (state 2) to the end, the
     helicopter coming and going, and the humans never finish; why the drones aren't picked up wasn't looked into.
     The BBC matches every frame, and a trace where no car has 4 laps has no end to check. **Mistake, mine**:
     `disc_races.sh` passed its path through BSD `xargs -I`, which cuts an argument at 255 bytes, so a long `OUT`
     failed before any race ran.
5. **The sequence tracer**: Hatari traces of a whole game (select, two or three races, joins, an elimination,
   upgrades bought, a game over), the state between races at each screen. The demo race traced on each track.
   - **Done (2026-11-04).** `tools/st_trace_game.py` plays a game from a script of steps, each at a pc, the Nth Vsync
     or the Nth flip after the last (every front-end wait goes through `xbios_01194C`), and dumps all the data and
     BSS, 11,486 bytes with the high scores and lap records, at the game's start, each return to `F_0141B0` and the
     initials' entry. So each screen is a function: the state before it and its inputs give the state after it. A
     race isn't driven: its loop only tests a car's laps for 4, so a step pokes the result wanted (the races are
     checked on their own). Random numbers and the steps' VBLs are logged too. `tools/game_traces.sh` makes them all.
   - Three games (`tools/game_scripts.py`): **three** (the dial moved, joins at the select and prepare, an elimination,
     an upgrade bought, initials for one car and then two at once, a drone's win, game over), **alone** (the select's
     countdown run out, Esc at prepare, F5, a lap record, the upgrade's time run out, game over with no entry),
     **rejoin** (both humans eliminated, one back at the last prepare, F10 abandoning race 2).
   - The demo race on every track at race counters 0 and 17: `build/trace/logic_tN_demoR.json`, 16 races, 16,252
     frames, in `st_trace_logic.py`'s form for `logic_compare.mjs`. Oil, cones, barriers and the tornado all appear.
   - Repeatable: `rejoin` run twice, every dump the same at the same VBL, and the same 55 random numbers. Nothing
     checks these against the BBC yet: that's step 6. `tools/game_diff.py` lists what each screen changes.
   - **What step 6 needs that the docs didn't say** (`docs/st-logic.md` §9, corrected):
     - `G_01EBC2` is a signed word: a drone winning race 0 takes it to -1, then back to 0. `GmRace` (a byte, 0-50) must
       allow for it.
     - The upgrades' timer running out buys what the dial's on, as fire would. (The BBC has no limit: D27.)
     - The winner's circle draws 17 or 18 random numbers, so it moves the next race's seed, and F5 changes how many.
       F5 made no real difference to the circle's length: what it shortens is unread.
     - `F_017A42` (initials) runs at the end of every prepare, not only when there's an entry.
     - The demo's drone flags stay 0, and its hazards follow the counter the last game left.
     - The scores have a second copy at `G_01DF90`, changing with them: not read yet, probably what `F_01BBAA` restores.
6. **The game's rules** on the BBC, one screen's logic at a time, each checked against step 5's traces, with
   placeholder screens (text in the HUD row's font): select, prepare, winner's circle and its bonuses,
   elimination, upgrades, next track, game over, the demo race and the attract loop's order and timings.
   - **Done (2026-11-04)**, but for two things: the demo's car 3 is drawn in the drone-driven colours (D20's small
     file: below), and the initials are step 10's, as planned (a score in the table simply stays, for now).
   - **Where it lives, not where §3 said.** `src/game.6502` is kept as an image in the fourth bank's first 4K, as the
     load's code is, and `game_go` copies it to `&9000` in the background's bank when a race ends, a page at a
     time through `&7F00`. Every load rewrites that bank, so nothing's lost and no disc's needed; `&9000` is above
     ANDY, so the race's state stays in reach, and the rules work on it where the logic left it. `save_game` keeps
     what outlives a race in LowFree (`Gm*`), `load_game` and `logic_start` give it back; the lap records and high
     scores (SSPRINT.HSC, 295 bytes) are in Shared, as the copy doesn't survive a load, and written to both
     screens' copies. Scratch is `GameScratch`, `&B800` up in the bank. The first 4K has 473 bytes free: steps
     7-10 will want more, and ZX02-packing the image is the way out, the unpacker being there already. Main RAM 474
     free, the fourth bank 1,086, Shared 312, LowFree 118. First tried in the objects' bank, on a figure of 6,626 free: that was track 1's
     alone, `ObjSlot` isn't padded, and track 5 overflowed by 521. `tools/track_slots.py` said so at once.
   - **The oracle.** `tools/game_check.mjs` plays each of step 5's games on `build/game.ssd` from the ST's seed. Every
     read of a player's input is given as the ST's read it, in order, so the BBC's screens must ask as often and for
     the same car; a race's result goes in at the frame the ST's did; and the state's compared at every point the ST's
     was dumped, all of the logic at a race's return, the game's state elsewhere (who's playing, wrenches, scores,
     upgrades, race counter, lap records, the generator). **Three games, 35 points, 3,440 reads: exact.** Seen to
     fail: place points, the upgrades' order, the next track, the points added. `tools/attract_check.mjs` leaves the
     disc alone from the ST's seed: every screen's order and time, each demo's track, and the generator against the
     ST's after each of three demos back to back; then fire ending a demo. All 16 demo races are in
     `disc_races.sh`, exact frame by frame (16,252 frames, state only). Keys: Escape 112, f5 116, f0 32, measured in
     `keys_check`. Played with real key presses too, as no oracle does: fire, the dial, a track loaded, a race run.
   - **What the second races found**, each traced race so far having been a game's first: the ST never resets the
     coasting phase, which changes the cars' handling, or the sparks' timers: `GmPhase`, `GmSparks` carry them. It
     leaves the last track's gate variables too, which a track without gates never reads: not carried, and not
     compared on such a track. The demo leaves `G_01E35C` and `G_01E364`, which only the human handler reads.
   - **Faults of mine that these caught**: the attract loop's `LDX` between a read and its `BMI`; `score_add` given
     the race's `Ten`, in a bank not paged in here, so background bytes were added as digits; `save_game` before
     anything had been loaded, zeroing the seed; F10 running one more race frame; and a demo's car 3, whose
     `SetOf` entry was the generator's 255 for "no such set", plotted from set 15 until it overwrote `plot_car`'s
     first opcode with 0, which the next call ran as `BRK`.
   - **Not done, to decide**: car 3's own colours in the demo. D20 expected one small file here. It wants a file over
     the drone-driven set for a demo and back for a game's first race, so a load path of its own, and the screen
     model checking it; it changes only how one car looks in the attract mode, so it's left until the screens
     (steps 7-8) can be judged together. F1's options, F9, and the music's gaps are later steps' (G_01D312 is taken as
     on: one random number in the circle depends on it).
7. **The ST's front-end data decoded**: `SUPER.DAT`'s first three blocks, the credits' plane, `SUPER1.DAT`,
   maps 8-10, initials entry and options captured; written up in `docs/st-graphics.md`.
   - **Done (2026-11-04).** Every screen captured as raw memory and palette, the four never seen before among them
     (select, upgrades, initials, options). `tools/st_frontend.py` decodes against those, in the suite: the title,
     credits, high scores and lap records are **exact, 0 pixels different**, the last two wholly composed, table and all;
     prepare differs only by the cars' flickering details. The select, circle, upgrades, initials and options
     aren't composed: their pictures and routines are decoded, and step 8 draws them against the captures.
   - **Most of the screens change palette down the screen** (`docs/st-graphics.md`): select and the circle 4 bands of 16
     colours, prepare, initials and options 3, upgrades 2, on Timer B. Tom spotted it: the first captures took one
     palette for the whole screen, so the options' three cars came out alike where the video has blue, yellow and red.
     Now each shot records the bands, and `tools/st_screens_check.py` compares the colours with Hatari's own picture.
     **This changes step 8's sums**: D18's "each screen its own 4 of the BBC's 8 colours" meets up to 64 ST colours a
     screen. The Video ULA's palette can be changed down the screen too, so a screen's bands could each have their
     own 4, at a cost of raster timing the front end has plenty of; that's for the option sheets to show.
     Against that (Tom, 2026-11-04): the BBC's cars aren't the ST's colours anyway (D1, option B: white, green, yellow,
     not blue, red, yellow), so the screens needn't match the ST's. Proposed for step 8: the front end's cars in the
     BBC's colours, so they're the cars you race, and the words with them ("BLUE CAR", "RED CAR"): to show on the sheets.
     The winner's circle must also colour each place's car by who came there (Tom, 2026-11-04; `docs/st-graphics.md`), a
     drone-driven car looking different. The ST does it by palette, but second and third share a band. The four cars
     are four different drawings (the first's a small side view, second and third face each other, the fourth's huge and
     cut off), and each place's heading ("FIRST PLACE") is in the same palette entries as its car. So: the cars stay in
     the picture, and two parts of each are rewritten (Tom, 2026-11-04), matching the in-game cars: the main bodywork and
     rear spoiler (the place's third palette entry) and the sides and front spoiler (its first). Its second, edges
     and headings, stays in the picture. Two 1-bit masks a place, 1,204 bytes packed in all (measured). A car's look,
     body and sides, as `G_01DC18`'s seven rows: player 1 white, white; player 2 green; player 3 yellow; drone-driven,
     black with sides white, green or yellow as its player's; car 3 black, black. Proposed; to judge at that screen.
     The cars' colours may be changed later (Tom, 2026-11-04: perhaps a separate colour for the player cars' sides), and
     the circle must follow: so the seven looks live in one place, `tools/convert.py`'s table, which makes both the race's
     sprites and the circle's colours. The masks hold shape, not colour, so a change is a rebuild, nothing redrawn.
     Prepare, options and initials follow it too, and are simpler (Tom's reading, measured): their three cars are one
     drawing, 5,696 and 5,683 of 5,700 pixels alike in shape, so one stored car drawn three times, with the same parts'
     masks, not a picture of three. Their colours don't map one to one (the left car's colour 3 is two on the right), so
     the parts come from comparing the three. They sit at x 6, 165 and 86: not the same place in a byte, 4 pixels each.
   - The credits aren't a plane, as §1 projected, but RLE, as is prepare; upgrades has no picture at all. **`SUPER1.DAT` is
     never read**: wiped after its load, a whole game came out the same to the byte, with a control that the file was
     there and the wipe took. 17K nobody has to convert. The disc budget improves by that, and the screens' data
     is small: credits 6,194 bytes as stored, prepare 8,572, the frame block 3,488, the dial 7,040.
8. **The screens converted** (D18): option sheets and a viewer disc for Tom; then drawn by the game, with the
   wipe. **One screen at a time** (Tom, 2026-11-04): after each, a testing stage, Tom checking it by eye and reporting
   back, before the next. Ten screens: title, high scores, lap records, credits, select, prepare, winner's circle,
   upgrades, initials, options. The credits are lower priority (Tom, 2026-11-04): if space looks tight the screen can go,
   its text moving to a README on the disc.
   - **The title** (2026-11-05): MODE 2, the checked option (Tom, on a CRT: "may change my mind"). `tools/screens.py`'s `Looks` says how a
     screen looks; `tools/screen_options.py` makes the option sheets and a viewer disc of them. MODE 1's sets were tried too,
     black, red, yellow and blue by hand the best. The last line, "(c) 1986 ATARI GAMES", is redrawn by hand in 3 x 7 letters (Tom: option C of
     four; `title_line` in `tools/screen_options.py`), as the ST's fill in at MODE 2's width. The file `TRACKF` (`src/front.6502`) holds the front end's code, the wipe's
     tables and the packed picture: loaded through the OS, copied to `FrontOrg`, `&A000` in the background's bank, and back
     to `game_go` with no race. A track's load wipes it (`GmFront`), so it's loaded again before each title.
     The picture's unpacked into the shadow screen and wiped into the main one. **The wipe** (`F_014E34`) is an 8 x 8 diamond:
     2 bytes by a cell in either mode, so 16 byte masks a level, and a step skips the masks that haven't changed. In
     54 fields with the unpacking, out in 28. Only the title has it so far: the rest cut, until they're pictures.
     `attract_check` compares the picture byte for byte. `tools/suite.sh OUT quick` runs 8 of the 88 races: 10 minutes, for
     the pictures alone.
   - **The credits** (2026-11-05): MODE 1, 4 colours, as the letters are a pixel wide and MODE 2 would lose them: black, red,
     yellow and cyan, every blue and the white flat cyan (`tools/screen_options.py`'s ranking has the same set first; Tom
     agreed the flat look from a preview). Checks on the darkest blue broke the letters up. 1,863 bytes packed, which leaves
     TRACKF 520 bytes free. A demo's track wipes the pictures, so TRACKF now loads after the wait that follows a demo,
     before the credits, not before the title. `GmPicture` says which mode a picture's in, and the wipe follows it, MODE 1's
     table in use for the first time.
   - **The high scores** (2026-11-05): MODE 1, as the 6-pixel font wants it: black, blue, magenta and yellow, flat, the ST's white
     text and greys yellow; `build/viewer/scores.ssd` has that, white for yellow, and both with red for magenta. Only the frame's
     packed (1,804 bytes); the game draws the table over it from `HiScores`, in the shadow screen, by `F_0171B6`'s places, so a new
     score will show with nothing more. The text is logical 3, OR'd in, so the frame's colour needn't be known. TRACKF had no room,
     so it's two parts now: the credits and this frame at `BgOrg`, in the background's bank under ANDY after the erase's code (45
     bytes free), the rest at `FrontOrg` (1,740 free). They're unpacked with ANDY out. The MODE 1 wipe out takes 50 fields, the
     title's 28. `attract_check` compares the whole screen with `tools/st_frontend.py`'s composition, table and all.
   - **The lap records** (2026-11-05): the high scores' frame and colours. Only its heading differs, so `RecordsPic` is just those two cell
     rows, unpacked over the frame (445 bytes; `tools/screens.py` stops if the frames differ anywhere else). "ALL TIME BESTS", "TRACK n",
     the times and "SECS" are drawn by the high scores' glyph routine, the times live from `LapRecords` by `F_01BE60`'s sums, limit
     99.9 and all. TRACKF has 1,015 bytes free at `FrontOrg`.
   - **Prepare to race** (2026-11-05): MODE 1 in the race's palette, so the cars are the ones you race, white, green and yellow (the middle
     panel's the bottom car's), the checker dim green (Tom; `build/viewer/prepare.ssd` had six looks, MODE 2's letters filling in). His ideas for
     later: a palette split, for the right colours and a fifth for the checks; an editable PNG. It's a game screen, and a race overwrites
     the background's bank, so **the front end's code moved** to an image at the objects' bank's end (`FrontImage`, 2,304 bytes; 34 left
     there on track 5), copied by `game_go` beside the game, and picture files hold only pictures. `TRACKP`, 2,803 bytes, is loaded
     before each prepare, `save_game` before and `load_game` after, `GmBack` saying where to go on (one more load a race, to judge on a
     Master). Each car's panel is a stream of its own, playing or not, unpacked under ANDY and copied in by rows, which covers a join. The
     cars' flickering details are left out for now.
   - **The options** (2026-11-06): F1 in any wait, keys and sound for now (Tom: joysticks later, D5). Prepare's picture, its own file `TRACKO`, code and all
     (`src/options.6502`), so it costs prepare nothing; f0 goes back to the title, a load each way. Tom's ideas: F2-F4 ask for a car's keys again,
     in `PlayerKeys`, which no load touches, refusing the game's own keys and those taken, Escape putting them back; each key's name
     is in the BBC's font (Tom: only there, the wording's the small font's), arrows from its 136-139, and in inverse while held, so a
     name lit with nobody pressing that key is a clash; and a warning when the nine keys can ghost, `tools/keys_ghost.py`'s model as a loop test,
     once a car's keys are in. The keypad's keys are named PAD 4 and so on, their numbers Tom's. Lost at a reset until step 10's save, which
     can hold them and the sound. A joystick could later be picked at the same prompt.
   - **The select screen** (2026-11-06): the race's palette, its dithered road (Tom's choice over green), in `TRACKS`, loaded as a game starts, its own
     code in `src/select.6502`. Where the ST changes the chosen track's palette a 2-pixel yellow rectangle goes round it (Tom's idea), drawn and taken
     away by EOR; the rows of tracks move up 1 to 3 lines for it. The dial's 16 positions are packed one by one but for 5-8, 3-0 upside down, as
     the ST stores them (229 bytes each; all 16 didn't fit). The panels are prepare's way, the difficulty and the seconds the small font, live. The
     rectangle's steady, though the ST's highlight wasn't on in every capture. 379 bytes left in the file's high part, 213 under ANDY.
   - **The upgrades** (2026-11-06): prepare's palette and dim green checks, in `TRACKU`, its own code in `src/upgrades.6502`, loaded after the circle only when a
     player has 4 wrenches (one more load between those races, none otherwise). `F_01A130`'s picture is composed by `tools/st_frontend.py`, 0 pixels from all three
     captures outside the HUD, the dial and the seconds. The ST lights a box by palette, each box a plane of its own; the BBC's four colours are all in use, so a box is lit by
     EOR through 39 rectangles, the top left box's, the others mirrored as the game draws them. The white car can't be lit white, so its boxes and bought levels are yellow
     (Tom: looks good, in jsbeeb). The level lines sit on black bars, and "TAKEN" clears its own, as small coloured text is lost on the checks. The panels are drawn live: names, the
     wrench, the ST's HUD digits (`G_01DF4E`'s first set, a byte a line), comma and laps, by EOR. The dial is 5 stored positions, packed:
     5-8 upside down as on the select, and 9-15 turned round, on a black ground the width of what any position lights, so no frame reaches a box and none needs a mask. **Mistake,
     the placeholder's**: a pass is 3 fields, not 2 (`F_01A844`'s Vsync is the third), so its time was 6.3 seconds, not 9.5; a pass now paces itself from its start, so the dial's unpacking
     hides in it: every pass is 3 fields, moving or not. **No time limit** (Tom, D27): the screen waits for fire, and the seconds are gone. **Flicker** (Tom, in jsbeeb): figures were taken away and drawn
     again at each payment, so the display caught them gone. A figure's now changed in one pass, its old glyph and new EOR'd together, and only if it's changed. `tools/upgrades_check.mjs`, in the suite, pokes the circle's end and
     compares every pass with `tools/upgrades_model.mjs`, which plots the text itself: 382 screens, all 16 positions, full boxes, "TAKEN", a score bought, 171 passes waited. It watches every write to the panels while paying: no pixel
     that ends as it began may be written any other way (24 payments; a build that erases and redraws fails all 24). Seen to fail too: a box mirrored wrong, the dial's span, the lit colour.
     `game_check` compares the traced games' screens the same way, giving fire at the ST's time's end, and `flash_check` now goes through this load. 779 bytes left in the file's high part, 357 under ANDY. `tools/cheat_disc.py`
     makes a copy of the disc that starts every game with 8 wrenches, for trying it by hand. The tune and the "ding" are step 9's; the dial's pointer isn't in the car's colour, as the select's.
   - **The winner's circle** (2026-11-06; its look Proposed, Tom's to judge): the race's palette, the ground flat white and the last panel flat yellow, for the words, the crowd green and yellow on dim checks, the panels on
     black as the upgrades'. Black ground and dim green checks were tried: the words go on the checks, and a black ground loses them unless they're drawn again. The picture has the cars' sides and bodywork black, and masks paint them in
     by the result, the look as `G_01DC18`'s rows, as proposed above; edges and headings stay black. The figure stands on the fourth car, so its frames have masks too. The flags the crowd waves are the winner's bodywork, as the ST's palette has them.
     It's a new file, `TRACKC`, 11K, a load as each race ends, one more between races. It won't go in the usual 7.5K, and needn't: only its code is copied up (807 bytes left), and the rest is read where the load left it, in the main screen, with
     the display off, before `say_clear` clears it (1,948 bytes left below `CircleScratch`). The ST's rules split around the load: `circle_sums` (the order, bonuses, records, random numbers) before it, as GameScratch survives a picture's load, and `circle` after.
     **Mistake, mine**: the packed picture was first taken to the shadow screen's end and unpacked over itself. That can't work when a picture fills the screen to its last byte, as the writes pass the reads; it ran wild and overwrote the game. It's two streams now,
     each copied under ANDY and unpacked from there. `src/panels.6502` is the upgrades' panel and glyph code, assembled into both files, as nothing resident has room. A bonus is counted in decimal digits, each changed in one go as the upgrades' figures are. The count is a pass of 2
     fields, as the ST; the celebration, 200 fields there, waits for a player's fire here (Tom, D28), fire held from the race not counting till it's let go. `tools/st_frontend.py` composes the circle from the ST's tables, 0 pixels from both captures outside the HUD and sparkles, the "-.-" included (`docs/st-graphics.md`). `tools/circle_check.mjs`, in the suite, pokes four races, every car in the places, drones, all
     four kinds, a time below 0, and compares each pass and field with `tools/circle_model.mjs`: 1,388 screens, 584 steps of the count with no flicker. Seen to fail: six faults built in on purpose (a figure erased and redrawn, the cars' places, the sparkles' pace, the negative digits, the figure's masks, the digits' carry), each at the moment it should. `game_check` compares the traced games' circles as shown and as they end, and `flash_check` now goes through both the circle's load and the upgrades'. The tunes are step 9's.
   - **The initials** (2026-11-07): the last of the ten, and not a screen of its own: `F_017A42` draws over prepare's panels when it ends, for each drone among the players, and it's the whole high score entry, so step 10's table goes in here too. Prepare's
     colours; the letters in the big font, packed in `TRACKP` (175 bytes left) and unpacked to FrontBuf, the panels by EOR in the car's colour (`src/initials.6502`). The rules are in `game.6502`. To make room there the circle's count and celebration moved to `TRACKC` and the upgrades' loop to `TRACKU`, which only run with those files in (68 bytes left in the first 4K). The table's kept in both copies of Shared, as the lap records are.
     A letter's changed in one go, only if it's changed. No time limit (Tom, D29): the ST's 30 seconds and its countdown are gone. `tools/st_frontend.py` composes the panels from the ST's tables, 0 pixels from both captures. `game_check` plays the ST's initials' reads, which it skipped till now, and compares the high score table at every point, so the traced entries are exact,
     two at once included; it compares the screens as they start and end. `tools/initials_check.mjs`, in the suite, pokes scores and tables and plays F_017A42's rules out itself: 441 screens, 422 reads, 10 entries, the left and right wrap, fire held, one entry pushing another down and one off the end, "GAME OVER", a wait past the ST's 30 seconds, both copies of the table.
     Twelve faults built in on purpose failed it, eight before D29 and D30 and four after. **Gaps found that way**: fire held wasn't tried, as the scripts always let go, so a case holds it now; and a letter taken early can look the same on the screen, so it now insists every entry's finished as the screen ends. With no time limit a fault can leave an entry waiting for ever, so it stops itself after 1,000 reads. `tools/cheat_disc.py` (Tom asked for a cheat mode to try this) makes `build/cheat.ssd`, a patched copy of the disc: 8 wrenches a game, 1-lap races, last place worth 100 points, and a table from 1,500 down to 50, so being knocked out reaches the entry in about a minute. Played through headless: a race of 509 frames, then place 19 with 650 points. Tom found the keys slow to answer, so a press now acts in the field it's made, a held key repeating after a wait (D30), `initials_check` driving those by field. Saving the table is the rest of step 10.
   - **One load after a race** (2026-11-07, Tom, D31): the circle's, upgrades' and prepare's files are read back to back under one "Loading", two kept in track slots till they're wanted. Between races on DFS, 9.7 s to 7.2, or 12.4 to 8.2 with the upgrades. **Found by the suite**: with no load between the screens, nothing recopies the game any more: copying the upgrades in by whole pages from `BgOrg` ran 128 bytes into it, which a load had been putting right unseen; and the files share addresses, so `game_check`'s stops in them only count with that file's own bytes there (`fileGate` in `tools/jsbeeb.mjs`, a jsbeeb breakpoint condition). Moving the tracks' files near the catalogue also took a track's load back under `attract_check`'s 4 seconds. The select's loop moved to `TRACKS` for room.
   - **One load into the game** (2026-11-07, Tom, D31): fire on the title reads prepare's file, kept as after a race, and the select's in one load. Fire to the race in jsbeeb, 3 loads to 2: 8.50 s of loading to 6.99.
   - **On a Master** (2026-11-07): the winner's circle, the upgrades and the initials tried on Tom's: "they're good". That's all ten screens seen on real hardware or passed by Tom, and step 8 done.
9. **The front end's tunes** (D11's method): captured, converted, sized, heard against the ST's.
10. **High scores** (D23): the entry and the table are done (step 8's initials); saving and loading them is lower priority (Tom,
    2026-11-03), dropped if the disc's catalogue or the room for its error handling runs short.
11. **The disc on every filing system**: DFS and ADFS in jsbeeb (`beeb-target-matrix`), MMFS and Econet on
    hardware or another emulator; the BRKV retry on a disc error tried.
    - **ADFS, first try** (2026-11-07): `tools/adfs_disc.py` makes `build/game.adf`, an ADFS M disc of the same files. In jsbeeb's `MasterADFS` the game boots with `*MOUNT 0` and `*RUN !BOOT` (SHIFT-BREAK didn't mount it there: not looked into) and gets through the circle's, upgrades', prepare's and a track's loads. Not yet: a whole game on it, or a real Master.
    - **An official ADFS disc** (D32, Tom, 2026-11-07), beside the DFS one: ADFS L, `build/game.adl`, made by `make game` (Tom, on his Master: "runs well"; no M disc). Still: the suite to check it (at least `load_check` and a traced game on it); SHIFT-BREAK booting it; why ADFS costs more than DFS a file (L 7.39 s and 8.79 between races, against 7.24 and 8.24); a copy made with `*COPY` into a directory of a hard disc, as Tom expects people to install it, and run from there, `*RUN !BOOT` with that directory current, with step 10's save writing to the same directory. The Master Compact (D33): a target, assumed to work until Tom tries it, as jsbeeb has none.
    - **ADFS L** (2026-11-07, Tom's idea): on two sides the files could sit in about half the tracks, some on each side. ADFS numbers side 0's sectors first, then side 1's (seen in jsbeeb: logical sector 22 read from side 0's track 1, the 1770's writes logged), so files end to end fill one side. `tools/adfs_disc.py build/game.ssd build/game.adl` splits them: side 0 has the race's files and reaches track 19, side 1 the attract mode's and options' pictures and then the boot's files, reaching track 23. Between races in jsbeeb, a load's start to the track's first frame (track index 2, then 7): DFS 7.24 and 7.10 s, 8.24 and 8.10 with the upgrades; ADFS M 7.58, 7.44, 8.98, 8.84; ADFS L 7.39, 7.25, 8.79, 8.65. L saves 0.19 s, all in the load after the race; the track's load is the same, as M already has the race's files in its first 20 tracks. ADFS's extra over DFS grows with the files read (0.3 s for two, 0.7 for three), so it's per file, not seeking; not looked into yet. On a real drive the step rate may make seeks dearer than in jsbeeb. **Mistake, mine**: the first L image assumed the sides went track by track and didn't load; nothing had checked a file's bytes, only that `*LOAD` gave no error.

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
