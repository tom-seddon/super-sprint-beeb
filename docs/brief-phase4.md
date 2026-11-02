# Brief - Phase 4, one race: the first steps

> **Status: PLAN, agreed 2026-11-02 (Tom: "Yes, D13 as proposed"); steps 1-3, 5 and mask B's part of 4 built.**
> Branch `phase4-start`, off `02741da` (the commit Tom last saw). Tom's four answers are D9-D12 in
> `docs/decisions.md`; D13 (mask B's storage) was this brief's proposal, decided by Tom 2026-11-02.
>
> Figures say **MEASURED** (a tool run, named), **COUNTED** (off the source or a listing) or
> **PROJECTED** (arithmetic on top).
>
> *Read first: `docs/st-logic.md` §1-6 and §12, `docs/renderer.md` "How it draws" (the priority cells),
> `docs/plan.md` Phase 4, D2, D3, D7, D9-D13.*

**Resume point: step 9 (keys), or the frame's speed.** The game drawn from its own logic matches the model
on every frame of the race (§8; `make check TRACE=logic0`). Its worst frames go over a TV frame (3 of
2,197). Next: the keys (D12: a layout, its ghosting, the key numbers measured), then sound (D11).

## 0. The proposal in one paragraph

Phase 4 starts with the instrument, not the game: a Hatari tracer that plays a race on track 1 (index 0)
with scripted inputs and records, every frame, the inputs each car's logic read, every per-car variable,
the scores and every random number drawn; and a jsbeeb oracle that feeds the same inputs and seed to the
BBC's logic and compares every variable, every frame (D9: bit-exact). Then the logic goes in one ST routine
at a time, each proved by that oracle before the next: humans' movement and steering, walls, the attribute
cells (stripes, checkpoints, laps), car-to-car, drones, scoring and the race's end, the wrench and bonus;
then the renderer driven by the logic instead of the trace, then input and sound. Mask B (walls) is stored
as the priority mask already is: 8 bytes of 1-bit mask for each 8 x 8 cell that isn't all road or all
wall, found through a map of each row's span (D13). On track 1 that is 144 cells and 1,152 bytes against
8,000 for the whole mask; on the worst track, 8 (index 7), 267 cells and 2,136 bytes (MEASURED,
`tools/maskb_stats.py`). It costs about 30 cycles a mask
byte read, and a car's probes read about 22 (PROJECTED).

## 1. What the original does - measured

All in `docs/st-logic.md`; the parts this brief leans on:
- **Walls** (§3, checked in Hatari): `F_01519C` ANDs each of the car's 12 lines of opacity (its frame's
  pixels not colour 8, rotated right by x & 15) with mask B into `G_01E434`; `F_00C4F6` then tests two
  whole lines and two one-pixel columns from `G_01E160[facing]` (re-read for this brief: the column masks
  are single bits, the columns tested on the lines from the top probe to the one above the bottom probe),
  giving a 4-bit code, made a push direction by `G_01E140`.
- **The car's opacity is the frame's own**: of the 16 facings, 7 have opacities that differ between the 8
  sets (cars 0-3, own and drone-driven) (MEASURED, `tools/maskb_stats.py`), so a
  shape per facing (st-logic §12's cheaper form) would not be bit-exact. The probes are made from each
  frame the race uses, as the renderer's frames are.
- **The random numbers**: every one comes from `F_00ADB8(n)` = ((XBIOS Random & &FFFF) >> 1) mod n. TOS's
  Random is a linear congruential generator over a seed in TOS's RAM (to be read in Hatari: step 2); its
  seed at the race's start and every call's result go in the trace.
- **The order of a frame** (§1): track objects, car control in index order, lap events, the 64-frame
  points, the HUD, then `F_00E66A` (collisions and drawing). The BBC's logic keeps that order, because
  the probes in `F_00E66A` read what the car drawing wrote.

Not yet measured: a race driven with steering. The Phase 3 traces have the blue car accelerating with no
steering and are recorded at the plotter's calls, not the logic's variables.

## 2. The ledger

From `docs/plan.md` Phase 4 (measured at the end of Phase 3; the build on this branch is the same code).

| Region | Free now | This job wants (track 1) | After |
|---|---|---|---|
| Main RAM `&1813`-`&29FF` | 4,589 | the logic's code, about 3-4K (PROJECTED) | ~1K |
| `&2E00`-`&2FFF` | ~300 | per-car state: 4 cars x ~45 bytes (COUNTED from §2's table) | ~120 |
| `&3000`-`&3EFF`, both copies | ~3,700 | the attribute map 1,000, the direction vectors and small tables ~200 | ~2,500 |
| Fourth bank | 11,361 | mask B 2,168 (track 8: 3,427; MEASURED, `tools/maskb.py`, gates' and barriers' cells included); probe shapes ~1K; drone path ~700; the wall code beside them | ~7K (track 8: ~6K) |
| Objects' bank | 2,933 (track 5) to 8,424 | gates' and barriers' mask B runs (tracks 3, 5, 8 by number), later | |
| The frame (cycles) | 24,180 mean, 15,045 worst on track index 0 | the logic: aim 10,000-12,000 | |

Sound (about 12K of the ST's before transcoding) isn't in this ledger: it comes after the logic, and its
size after conversion decides where it goes.

## 3. The options for mask B, costed

### (a) The whole mask, 1 bit a pixel
8,000 bytes a track in the fourth bank: 70% of it. A read is an address calculation and a load, about 15
cycles. Leaves ~3.3K of the bank for the attribute map's copy, the drone path, the probes and the code,
and nothing for sound. Simple, but it takes the bank the logic and sound need.

### (b) Rebuild it per race from the vectors
3,000 bytes of vectors for all 8 tracks, a line draw and a flood fill at the race's set-up. Saves the
disc and the load, not the RAM: the built mask is still 8,000 bytes. Only worth it combined with (c),
and the per-race load (D3) already brings each track's data, so there's nothing to gain over shipping
the built mask in (c)'s form.

### (c) Mixed cells only, as the priority mask - the one I'd build
`tools/gendata.py` builds mask B (`logic_maps.wall_mask`, proved 0 pixels different from the ST's RAM on
track 1), and keeps only the 8 x 8 cells that are neither all 0 nor all 1:

| Track (number) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| All road | 521 | 543 | 613 | 565 | 648 | 533 | 603 | 588 |
| All wall | 335 | 277 | 205 | 242 | 172 | 205 | 170 | 145 |
| Mixed (8 bytes each) | 144 | 180 | 182 | 193 | 180 | 262 | 227 | 267 |
| Rows' spans of mixed cells | 638 | 664 | 688 | 685 | 720 | 795 | 827 | 786 |

(MEASURED.) The map is the priority's: per row, the span from its first mixed cell to its last, a byte a
cell (0 all road, &FF all wall, n the row's nth mixed cell), and outside the span the row's own fill
(road, or wall at the screen's sides). At most 2,136 + ~810 + 50 bytes. A gate's or barrier's cells are
reserved as mixed, written at run time from precomputed runs as their priority is.

A read: the cell row's span (row table), the map byte, then the cell's line: about 30 cycles (PROJECTED).
A car's probes read 2 lines of 3 bytes and 2 columns of up to 9 lines; the lines of a column in one cell
share one map read. About 22 reads, ~700 cycles a car, ~2,800 for 4 (PROJECTED), and less when every cell
under a car is all road: then the code is 0 with no reads at all, and the ST's answer is the same.

## 4. Where these figures could be wrong

- The ~30 cycles a read and ~22 reads a car: counted from the shape of the code, not written yet. Step 5
  measures them (`beeb-cycle-timing`).
- The logic's code at 3-4K: a guess from §2-6's size. If main RAM's 4,589 run out, the wall and drone code
  go in the fourth bank beside their data (the renderer's pattern).
- The fourth bank's free 11,361 is track 5's helicopter build; the helicopter's size is the same on every
  track.

## 5. The decisions

| # | Question | Options | State |
|---|---|---|---|
| D9 | How exact is the race logic? | bit-exact / close | Decided (Tom): bit-exact, frame by frame against Hatari |
| D10 | First track | | Decided (Tom): track 1 (index 0) |
| D11 | Sound | | Decided (Tom): 50 Hz IRQ, captured streams, live engines |
| D12 | Keys | | Decided in part (Tom): a proposed layout, checked for ghosting; joysticks too |
| D13 | Mask B's storage | (a) whole, (b) rebuilt, (c) mixed cells | Decided (Tom): (c) |

## 6. The steps

Each step one commit with its measurement in the body; `make check` (the renderer) run after each that
touches the build.

1. **This brief and D9-D13** - no code.
2. **The logic tracer** (`tools/st_trace_logic.py`, forked from `st_trace_objects.py`): track 1, race 0,
   one human (the blue car), the other three drones; the inputs scripted, the copy-protection poke. Per
   frame at the flip: the frame counter, the coasting phase, the per-car block `G_01E2A0`-`G_01E437`, the
   scores; each human car's input bits as `F_010CF2` returned them; every `F_00ADB8` call's n and Random
   result; the generator's seed. Proved by: two runs give the same file; every random number one run of
   TOS's generator from the seed. (Done, §8.)
3. **The oracle** (`tools/logic_check.mjs`, on `tools/jsbeeb.mjs` and the symbols): a build that reads its
   inputs and seed from the trace (in the trace's bank, as the renderer's tests do) instead of the keys;
   after each frame's logic, every traced variable read from the BBC and compared; exit 1 and the first
   frame, car and variable that differ. Proved to fail: on a build whose logic does nothing.
4. **The data** (`tools/gendata.py`): track 1's mask B as D13 (c), the attribute map, the drone path, the
   probe shapes for the race's frames, the tables (direction vectors, coasting, jumps, the push
   directions). Proved by: the Python decode of the stored mask B equal to `logic_maps.wall_mask(0)`, and
   that to the ST's RAM dump (0 pixels).
5. **Humans' movement and steering** (`F_00DC4C`): speed, steering delay and timer, smoothing, position.
   Proved by: the oracle, every frame up to the first wall touch.
6. **Walls and bouncing**, the probes against mask B. Oracle to the first car-to-car or attribute event.
7. **Attribute cells**: stripes, checkpoints, laps. Then **car-to-car**. Then **drones** (`F_00F23C`).
   Then **the 64-frame points, the race's end, the wrench and bonus** (the random numbers). Each its own
   commit, the oracle a race further each time.
8. **The renderer driven by the logic**: the cars' calls made from the logic's state, not the trace;
   `make check` still matches (the logic being the ST's, the ST's calls are what it makes).
9. **Keys** (D12): the layout on paper with the ghosting worked through, the internal key numbers
   measured (`beeb-key-numbers`), all 9 keys held in jsbeeb; joysticks through the ADC.
10. **Sound** (D11).

Then the other tracks.

## 7. What was costed and put down

- Mask B whole (a): 8,000 bytes of the fourth bank's 11,361, leaving no room for sound or the logic's data.
- Mask B rebuilt from vectors at set-up (b): saves the disc, not the RAM.
- A fixed car shape per facing for the wall probes (st-logic §12): 7 of 16 facings differ between the
  sets, so it wouldn't be bit-exact (D9).

## 8. What landed, 2026-11-02

**Step 2, the logic tracer.** `make logictrace` (about 30 s of Hatari) writes
`build/trace/logic_t0_r0.json`: 2,197 frames of track 1, race 0 (MEASURED). The blue car is driven by an
autopilot (`tools/logic_scripts/t0.json`): each entry a condition on car 0's x, y or facing (or a frame
number) and the keys to hold from then, each a one-shot conditional breakpoint on the flip arming the next,
so one breakpoint slot drives the whole race. Over the race the car steers, bounces off walls, is wrecked
once (frame ~320, the helicopter brings it back), crosses every checkpoint and completes 3 laps; the
drone in car 3 wins at frame ~2040, which ends the race. 1,964 inputs and 14 random numbers. Two runs give
byte-identical files. The random numbers fit TOS's XBIOS Random, `seed = seed * 3141592621 + 1`, result
`(seed >> 8) & &FFFFFF`: all 14 are one run of it, so nothing else draws from it during a race and the BBC
can start from the trace's seed. Hatari's "CPU=$pc" header sometimes heads another breakpoint's dumps; the
parser tells the reports apart by their "Next PC" line instead.

**Step 4, mask B's part** (D13). `tools/maskb.py` encodes mask B as §3 (c) - a header of 8 bytes a cell row,
the rows' span maps, the mixed cells, plus every cell a gate or pop-up barrier can cover kept as mixed -
and decodes it the way the 6502 will read it. MEASURED: track 1 2,168 bytes (200 header, 768 maps, 1,200
cells: 150), up to track 8's 3,427 (290 cells), against 8,000; every track decodes to the ST's mask with 0
of 8,000 bytes wrong, and track 1's mask is the ST's RAM (`attract2600.bin`) to the pixel. Broken on
purpose, the check fails (a cell byte flipped: 1 wrong; a wall cell mapped as road: 8 more). The reserved
cells cost 6 to 47 cells a track over the bare count; the header (200 bytes) could shrink to 4 a row.

**Step 3, the oracle.** `make logiccheck` builds `build/logic.ssd` (`src/logictest.6502`: no display,
interrupts off, the OS never called after the load) and runs `tools/logic_check.mjs`. The test sets the race
up as the trace's (`race_setup`), then runs `race_frame` once for each traced frame with the human's inputs
the ST read (`build/lgen/inputs.bin`, from `tools/gen_logic.py`, which also writes the ST's tables: the
direction vectors from `INIT.DAT`, and the coasting and jump tables from F_012276's own stores, run from the
disassembly). The harness stops it after the set-up (against the trace's frame 1) and after each race frame
(frame k against frame k), and compares 35 per-car variables and 3 race-wide ones, the ST's words against
the BBC's `Rc` arrays; `--cars`, `--vars` and `--until` narrow it. A frame the BBC never finishes (a path not
built yet traps with a BRK) is reported and fails. It fails when it should: with the set-up's multiply
not handed to its divide (a real slip on the way) all 75 frames were wrong from frame 1; with the
velocity's halving rounded down instead of towards 0, 70 of 75, from frame 6.

**Step 5, the humans' cars.** `src/human.6502` (F_00DC4C, the jump and spin paths included), `src/arith.6502`
(`mul_s16`, `div_s16`: the 68000's `muls.w` low word and `divs.w` rounding, sharing `num` so one feeds the
next), and of F_00E66A in `src/race.6502` the coasting phase, the area check and the last safe place.
MEASURED: car 0 matches the ST in all 28 of its movement variables, the phase and the frame counter, on
every frame from 1 to 75 (`make logiccheck LOGICARGS="--until 75 --cars 0"`). Frame 76 is its first
car-to-car shove (step 7); its stripes and latches differ from frame 26 (the attribute cells, step 7); it
stops at frame 143, a crash the BBC can't do yet. The logic costs 3,824 cycles a frame with one human car
and nothing else (mean; max 3,939): the general multiply and divide (about 200 and 400 cycles, 7 of them a
frame) are most of it, and are the first thing to make faster once the logic is whole (D9 allows any
method that gives the same results; each can be checked against every input it can get).

**Step 6, walls** (correct; not yet fast). `src/walls.6502`, in the logic's bank with mask B: F_00C4F6 over
F_01519C's buffer, reduced to what the probes read. Per car and facing, `tools/gen_logic.py` writes the
top and bottom probe lines' opaque columns and, for each side column, the lines it's tested on where the
frame is opaque there (from the car's own frame: set car + 4 if a drone drives it); `walls` shifts a
line's columns to x's place and ANDs them with the 3 mask bytes under it, and tests a column's pixel line
by line. `mask_byte` reads mask B through D13's maps. In `collide_car`: the push from `PushDir`, the
wreck tests (a trap for now), and the bounce (`bounce_car`). And F_00F038's clearing of the car-to-car
flags each frame. The test disc now copies the logic's bank image into sideways RAM bank 4.

The walls can't be reached by playing from the start (car 0's first bounce, at frame 143, comes after car
3's shove at 76), so `logic_check.mjs --from K` loads the ST's state at frame K - 1 into the BBC and checks
from K, and `tools/logic_stretches.py CAR` runs it on every stretch where the car is free of what isn't
built (racing, touching no car, not just shoved, no car finished). MEASURED: car 0's 28 movement
variables match on all 1,933 frames of its 9 stretches, which hold 23 of its 24 wall bounces; the
stretches stop at frame 2024, when the drone finishes. `tools/maskb_check.mjs`: `mask_byte` gives all
8,000 of track 1's mask bytes right. Broken on purpose (the side columns a pixel right), 2 stretches fail,
from frames 204 and 398. Two bugs on the way, both caught: the line's row clobbered in A before the call
(every frame a wreck), and `--from`'s input pointer written before the test set its own.

Cost: 12,405 cycles a frame (mean) against 3,824 before: every car's walls are probed, about 2,150
cycles each, the 3 drones' too though they don't move yet. Too slow for 4 cars (D2's budget leaves the
logic 10,000-12,000); next, the all-road cells skipped.

Then the cells under a car's probes tested first (`all_road`: each cell row's fill outside its span, its
map inside): all road, no wall can be touched, and the probes are skipped. MEASURED over frames 361-2024
(car 0 near walls often, the 3 parked drones on road): 11,702 cycles a frame (mean) to 6,149, max 12,990
to 8,593; still exact on all 1,933 frames of the stretches. Of what's left, about 3,800 is car 0's own
control and move, the general multiply and divide most of it.

**Step 7, the track's cells.** `src/cells.6502` (in the logic's bank, with the map), F_00BEEA followed
branch for branch from its hand-written asm: the stripe count, then each probe's class 0 (levels, ramps,
the long ramp, nudges, the flag cells), class 1 (water, oil, the yellow patch, wrench, bonus, cones: the
pair's cells cleared), class 2 (checkpoints, laps, the lap's frame), class 3 (bridge edges, the push), and
an elevated car's mask B cancelled. Jump tables for the classes' types (`ZA_CANJUMP`). The map is built by
`tools/gen_logic.py` from INIT.DAT's runs; against the ST's RAM it differs only in the 2 cells of a bonus
the race had placed. MEASURED: car 0's stripes, latches, checkpoints, laps and 4 lap times match with its
movement on all 1,933 frames of its stretches (3 laps). Its wrench count differs from frame 465: the
wrench was placed at run time from a random slot (the pickups aren't built). Broken on purpose (the
stripes not reset at a checkpoint), 2 stretches fail; accepting checkpoints out of order changes nothing
in this race (car 0 never crosses one out of order), so it proves nothing and isn't counted.
Two findings from the asm, corrected in st-logic: cell types 5 and 7 set flags &1000 and &2000 (the
steering reads them), not &0010 and &0020; and a finish line makes laps `(laps AND 3) + 1`.
Cost: 6,648 cycles a frame (mean, frames 2-75) from 5,307; the cells are read for every car every frame.

**Step 7, drones, the draw order and car-to-car.** `src/drone.6502` (in the logic's bank with the path,
from `tools/gen_logic.py`): F_00F23C, F_00FA2E (past the segment's end, by the travel direction's
quadrant) and F_00FB14 (onto a segment), with the drones' set-up in `race_setup`. In `src/race.6502`:
F_00EF9E (the draw order, a bubble sort by y, + 255 elevated, from 0-3 each frame), F_00F038/F_00F092
(the six pairs' tests) and the shove. MEASURED: all 4 cars match the ST in all 48 variables on every frame
from 1 to 294 (`make logiccheck LOGICARGS="--until 294"`), through 2 shoves between cars 0 and 3 and the
draw order's changes; frame 295 is car 0's crash. The set-up matched all four cars, drones included, the
first time; the bugs were a local label `.drone` shadowing the routine it called (the BBC hung) and a
scratch byte shared between two uses. Broken on purpose (the shove 10 * D, not 11), 219 frames fail from
76. A drone's spin, read from the asm: the counter goes down 1, and if that leaves it even, up 2, so it
turns every other frame until it faces its path.
Cost: 19,846 cycles a frame (mean, frames 2-294), 26,455 at most: each drone about 3,800, like the human,
mostly the general multiply and divide. Speed is the next job after the logic is whole.

**Step 7, wrecks.** In `src/race.6502`: F_00BB4E's logic (`wreck`: state 2, the explosion's counter, the
wait for the helicopter from the farther side), F_01510A's (the wait counted down, the explosion counted to
103) and F_00ED28 (`put_back`). The helicopter's own flight only drives the drawing and waits for step 8.
MEASURED: all 4 cars match the ST in 47 variables on every frame from 1 to 2030, the whole race to its end
(`make logiccheck LOGICARGS="--vars ..."` without `wrench`): the crash at 295, its 66-frame wait and the
put-back. From 2031 the race's end differs (not built); car 0's wrench count from 465 (the pickups). The
same mistake again on the way: a local `.wreck` label shadowing the routine, the BBC hanging at once.

**Step 7, the race's end, points and pickups.** `src/random.6502`: TOS's generator (a 32-bit shift-and-add
multiply, rare: a few draws a race) and F_00ADB8, and F_0167D6 (`score_add`). `src/pickups.6502` (in the
logic's bank): F_00AE16 (oil-type hazards), F_00ADDC, F_00AFF2 (cones) at the set-up, in the ST's order of
draws, and F_00B326 (the bonus) and F_00B560 (the wrench) each frame. In `src/race.6502`: the lap events,
the 64-frame points, the countdown and control's stop 4 frames after the finish, and `race_end` (after the
frame, as the ST does it after its flip). The tornado, barriers, gates and cones' per-frame parts trap
(none in this race). The tracer now dumps the pickups' state too (G_01EB54-G_01EB6F; the re-recorded
trace's other content byte-identical), and the oracle compares it, the scores, and TOS's seed (run on
from the trace's by each number drawn). MEASURED: the whole traced race is exact: all 2,196 frames, 68
variables per frame (35 per car and the race's) and the seed (`make logiccheck`). Broken on purpose (the
generator's + 1 dropped), every frame fails from 1.

**The logic's speed.** `tools/logic_profile.mjs` charges every instruction's cycles to its routine over the
race. Four exact changes, each checked on all 2,196 frames:

| Change | Mean cycles a frame | Worst |
|---|---|---|
| Before | 18,940 | 26,737 |
| `div_s16`: a high byte under the divisor needs 8 steps, unrolled; `div8_s16`: a positive number / 8 in 3 shifts | 12,600 | 19,867 |
| `div_s16` returns 0 for 0; `mul_dir` for the direction steps (0, 3, 6, 7, 8 and negatives) in shifts | 11,451 | 18,587 |
| The side columns look each cell up once per cell row (`mask_cell`) | 11,439 | 17,947 |

What's left, a frame on average: the 3 drones' own code 1,937, walls 1,844, cells 1,347, the divide 1,310,
`collide_car` 854, car-to-car 695, the multiply 610, the draw order 605. In the worst 20 frames (16,532 on
average) the walls are 3,571: cars against walls run the full probes. The plan's aim was 10,000-12,000; the
average is there, the worst frames aren't: the renderer leaves 15,045 at worst on track 1 (99% of frames
20,580), so a frame with both at their worst would drop to 25 fps for a moment (D2). More is possible (the
lines' shifts, the cells' probes, the drones' 16-bit work) and is left for when the game runs whole.

**Step 7, the effects.** `src/effects.6502` (the logic's bank): the sparks (F_00BE4A at a bounce, a landing,
a cone; F_00B718 each frame), the banner (F_00BA9E at the start, the final lap and the finish; F_00BABC) and
the helicopter's flight (F_00BB4E's part: its side, place and time; F_00BD4A). They feed only the drawing,
but they're checked the same way: the tracer dumps G_01E070-G_01E0BF, G_01EB28-G_01EB35 and
G_01EB88-G_01EB8D too (the trace's other content byte-identical again), and the test starts the sparks as
the ST had them from before the race (they carry over: the set-up clears only their x). MEASURED: all
2,196 frames exact in 118 variables. The helicopter's flight 117 frames instead of 116: 1,902 frames fail
from 295. 11,985 cycles a frame (mean), 18,814 at worst.

**Step 8, the draw calls.** For the renderer, the logic now notes what it draws where the ST calls its
drawing routines: the slot sprites (`slot_draw`, the bonus's and wrench's, with the ST's second call for
the other screen), what F_01510A drew of each car (the car, or its explosion's frame: at that point, as a
wall can wreck a car after it's drawn), and whether the helicopter was drawn; the sparks and banner are
read from their state. `tools/st_trace_objects.py` takes the autopilot too, so the same race's draw calls
come from the ST (`build/trace/race_t0_r0_script.json`; its car positions equal the logic trace's on all
2,197 frames), and the renderer test plays its first 438 frames from them, every one matching the model.
`tools/logic_draws.mjs` compares the BBC logic's calls with the ST's: MEASURED, all 2,195 race frames'
calls match. The first run found one wrong: car 0 drawn as an explosion on the frame a wall wrecked it,
because the state was read at the frame's end; the ST had already drawn it. Broken on purpose (the bonus's
second-screen draw left out): 21 frames differ, from 252. `gendata.py --logic` makes every moving object's
key and the tables from key to pieces (about 1,400 bytes more), and `gen_logic.py` packs the inputs as
runs (248 bytes, from 6,585).

**Step 8, the game drawn from its logic** (`make check TRACE=logic0`). `src/logicframe.6502` (in the fourth
bank) runs the logic each frame (the set-up's two flips first) and builds the frame loop's records from its
draw calls: the cars in draw order (each the car or its explosion's piece), the slot sprites as background
object events (again, as the ST's second call, where last frame drew the same), the moving objects' pieces
(the sideways helicopter's off the screen left out), and the HUD's changes. The inputs come from the
traced race, as runs. Memory, MEASURED from the listing: the logic's main RAM code leaves 973 bytes below
ObjBuf; the fourth bank (the helicopter, the logic's code and data, the frame builder, the inputs, the
logic's state in its last &200 bytes) has 234 free. The SPRINT file now runs past &3F00 at load (its loader
copies main RAM's code down before anything is drawn there). MEASURED: all 2,197 frames match the model
(made from the ST's own draws), the race whole: driving, walls, the wreck and helicopter, pickups, laps,
the HUD's scores, the finish. Broken on purpose (each car drawn a line low), all 2,197 fail. The default
disc (`make check`) is still byte-identical to Phase 3's and matches. Cycles a frame, logic and drawing:
25,967 mean, 36,414 at 99%, 40,820 at worst; 3 frames over a TV frame (4 drawn frames took 2), so the
display dropped to 25 fps for a moment 4 times in 44 s.
