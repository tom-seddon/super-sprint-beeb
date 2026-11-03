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

**Resume point: Phase 4's end** (§8's last entries). Step 13 is done: every track's race 17 bit-exact through
the BBC's logic and drawn exactly from it (`tools/tracks_check.sh`, 48 checks). Speed's fourth round is done,
the helicopter replaced by a cue (D16), and frames are shown in the blank after the display, not at the
vsync (D17): the fields repeating a frame on the nine races drawn from the logic 332 -> 42 (the hazard race
105 -> 5), every frame exact. D17 seen on a real Master (no tearing). The fourth bank has 2,608 free and its first 4K
(under ANDY) empty. Left open (Tom, 2026-11-03, D5): the joysticks, not urgent; three on the keys waits on a playtest. Optional: run-ahead logic (simulated 42 ->
about 9 more for about 15 ms of latency) if Tom wants it.

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

11. **The hazards** (planned 2026-11-02, after the RAM hunt): the tornado (F_00B7E6, F_00B852, and F_00F1A8's
   spin), the pop-up barriers (F_00B97C, F_00B9A0), the gates (F_00AF7A, F_00B1B2, the drones' lanes) and the
   cones (F_00B10C), with their set-up draws, their draw calls for the renderer, and mask B's changes: a
   gate (F_014A04) writes its whole 48 x 16 box of mask B, a barrier (F_014A80) its studs' pixels, so a closed
   gate is a wall. Mask C and A only matter to the drawing, which the renderer already does its own way.
   - **The trace**: the Phase 3 renderer's own race, track 5 (index 4), race 17, accelerate held, the tornado
     and cones forced (`build/trace/race_t4_r17.json`): it has all four hazards, 3 gates among them, and its
     model already exists, so `make check` can be driven by the logic. The logic tracer gains the forcing
     (`st_trace_objects.py`'s breakpoints), dumps G_01EB54-G_01EBC1 whole (the gates, banner, barriers,
     tornado and cones), and each gate's and barrier's box of mask B (&63A76 on), every frame. Proved by:
     its cars equal the renderer trace's on every frame.
   - **The BBC's forcing**: the ST's coin flips were forced after the draw; the test builds force them the
     same way (a constant from the trace), the play build never.
   - **Mask B's changes**: per gate position and barrier frame, the bytes of the reserved cells (D13) they
     write, made by `gen_logic.py` from SUPER.DAT (a gate's 5 positions differ in 15 of its 48 words, a
     barrier's frames only inside its studs), and copied into mask B's cells at each step.
   - **Proved by**: the logic oracle (every variable, the hazards' state, the boxes of mask B, every frame),
     `logic_draws` with the gates', barriers', cones' and tornado's calls, and `make check TRACE=logic4`, the
     renderer's model of that race drawn from the BBC's logic. Each broken on purpose once.
   - **Room**: in the fourth bank, which has about 1,583 for them on track 5 (`docs/brief-ram-2026-11-02.md`).

12. **Speed** (planned 2026-11-02): the hazard race (track 5, race 17, `make check TRACE=logic4`) averages 37,308
    cycles a frame and 721 of its 2,237 race frames take two TV frames. Those frames average 45,784: the logic
    22,462 (with the IRQ's sound), the cars' plot 14,655, the erase 5,597, the objects 1,100 (MEASURED,
    `render_check.mjs --json`). The logic's worst 200 frames (`logic_profile.mjs --worst 200`, 24,924 a
    frame): mask B's cell look-ups 4,359, the wall probes 3,417, the gates' and barriers' mask B writes 2,109
    (a look-up a byte), the drones 2,060, TOS's generator 1,943 (the tornado draws 2 numbers every 8th
    frame, a 32-step multiply each), the cells 1,421, the divide 1,319. In that order of yield for bytes:
    1. `mb_box` a cell at a time, not a byte (one look-up for a cell's lines);
    2. TOS's multiply by its constant a byte position at a time (8 shifts, its 16 bits' adds);
    3. mask B's look-ups: a row's map found once for a line's three bytes, the cell's offset stored in the
       map (if no row has more than 31 mixed cells), the line's shift by table;
    4. profile again, then the drones, the cells and the divide.
    Each exact on both traces (logic_check, logic_draws) and measured: the logic's cycles (logic_profile)
    and the game's frames over a TV frame (`render_check`), before and after, bytes by region.

13. **The other tracks** (planned 2026-11-02, Tom: "Yes, other tracks"). Every track's race 17 as track 5's was
    done in step 11: the renderer's own race (accelerate held, the tornado and cones forced), traced from the
    logic's side in Hatari (`make build/trace/logic_tN_r17.json`, the rule now for any track), replayed through
    the BBC's logic (`make logiccheck LOGICTRACE=build/trace/logic_tN_r17.json`: every variable, mask B's boxes
    and the map, every frame; mask B's bytes; the wall columns; the draw calls), and drawn from it
    (`make check TRACE=hN`, against the model of `race_tN_r17.json`). Each track's own features the first
    two never reached (ramps and jumps, the long ramp, bridges and the upper level, water and oil, nudges)
    are what's expected to fail first; each fault fixed as its own commit, found by the oracle, the race a
    frame further each time. Then the suite gains them all.

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

**Step 9, the keys** (D12, layout Proposed). `src/keyboard.6502`: the kit's keydown, forked (the loader
already stops the free-running scan), and `read_players`: each player's left, right and accelerate into
the ST's input bits. Layout: Z X SHIFT, V B N, comma full-stop slash, each key in a column of its own, so no
combination can ghost another (`tools/keys_ghost.py`: 0 of 511, the model checked against Paradroid's
hardware ghost). Key numbers from the kit's measured table, comma and full stop measured. In jsbeeb
(`tools/keys_check.mjs`, on the play build): each key alone and all nine together read as their player's.
The play build (`make beeb TRACE=play`, `GenPlay`): three players, car 3 the drone, every car's frame set
(the cars' bank 1,962 bytes free), the race restarting when it's over; `docs/img/jsbeeb-play-t0.png`. Not
yet: the joysticks; the ST's "TRACK 1" and "DRONE LAP" text, still in the play area's bottom row (Phase 2's
plan to paint it out with grass hasn't been done).

**Step 10, sound: the capture, measured.** Hatari 2.6.1's `--trace psg_write` logs every YM write as
`ym write data reg=R val=V` with its video cycle and pc: 113,804 writes in 1,400 VBLs of a race (the game's
749 Hz timer writing tones and volumes; register 14, the floppy select, among them). Frames can be marked
by a flip breakpoint's dumps, as the tracers do, so each field's register state can be rebuilt, its
hardware envelope stepped (D11), and converted by a fork of the kit's `py/beeb_port_kit/ay2sn.py`. Not
built: the capture tool, the effects (isolated: the attract race plays no engines), the player in the IRQ
sharing each car's channel by the ST's priorities, the live engines (F_012BA2's formulas). The conversion
is the part the kit says is judged by ear.

**Step 9, player 1's keys changed** to Q (left), W (right), E (accelerate), Tom's suggestion: the BBC's two
SHIFT keys are one, at either side of the keyboard. The same columns (0-2), so still no ghosting on paper
(0 of 511), and in jsbeeb each key and all nine read as their player's; `make check TRACE=logic0` still
matches on all 2,197 frames.

**Step 10, sound: the plan** (D11). The race's sounds, from the ST's driver (st-logic §8, `tools/logic_snd.py`):
each effect is a short sequence on one channel, `car MOD 3`, started only if that channel's priority is
under the starter's threshold, and ending with instrument 0, which leaves the engine's volume at 0; the
wreck's runs on two channels into the helicopter (instrument 1, the YM's hardware envelope, until the
helicopter-gone starter); the engine is instrument 0, its volume, period and rate moved each frame by
F_012BA2 from the human car's speed, its pitch alternating period +- 900 at the 749 Hz timer's rate.
1. **Capture** (`tools/st_trace_sound.py`): a race with Hatari's `psg_write` trace, the flips' dumps (the
   frame, the channels' priorities and states), and the starters' calls (which, the car, whether it
   started); each field's YM state rebuilt; each effect's channel cut from its start to its sequence's end.
   The logic race has the start, bounces, bumps, the wreck and helicopter, the wrench, the finish; a
   hazard race (track 5, race 17, as Phase 3's) the water, oil, yellow patch, cones and tornado.
2. **Convert** (`tools/ay2sn.py`, the kit's, forked): per field, a tone period (the YM's at 2 MHz is the
   SN's at 4 MHz; over 1023 raised an octave at a time), an attenuation (the hardware envelope stepped from
   its period and the time since R13 was written), and the noise (the nearest of the SN's rates, its
   volume the channel's).
3. **Play** (`src/sound.6502`): the vsync IRQ writes each channel's field: an effect's stream while one
   plays, else a human car's engine (F_012BA2 on the BBC, its +- 900 sampled at 50 Hz, two octaves up as
   st-logic's plan), else silence. The logic starts effects where the ST does (the stubs left so far).
4. **Prove**: the BBC's effect starts (which, the channel, the frame) against the ST's on the logic race;
   the BBC's SN writes against the streams (`beeb-sound-verify`'s way); WAVs of both chips for Tom's ears.

**Step 10, sound, built.** `tools/st_trace_sound.py` captures a race's YM writes (Hatari's `psg_write`
trace), sampled at each VBL (TOS's VBL routine, &FC06C0: the start's sound plays in the race's 1 s pause,
when there are no flips), with each conditional starter's call (its channel, the priorities it found, the
frame). Three captures: the logic race, a hazard race (track 7, race 17, tornado and cones) and the logic
race with oil poked across the start straight (no traced race's car ever met the oil). Two traps on the
way: 16 breakpoints set at once made Hatari run away (a 2.9 GB log: the always-starting starters lost
theirs), and at the VBL the frame counter's reset is never seen (the race starts at a fall to 1).
`tools/sound_gen.py` cuts each effect (11: the start on each channel, bounce, bump, slow, skid, wrench,
bonus, tornado, wreck with the helicopter's loop) from its start to its channel's priority falling to 0,
steps the hardware envelope (period 700, shape 12, the only one used), and converts with the kit's rules
(`tools/ay2sn.py`, forked): 1,566 bytes, in the objects' bank, copied at the start into both screens' &3000
area so the IRQ reads them whatever is paged. `src/sound.6502`: the starters (`fx_car`, `fx_two`, the ST's
thresholds; a starter's priority taking effect at the next vsync, as the ST's driver sets it at its next
tick, so two in one frame both start), the engines (F_012BA2), and `sound_irq` in the vsync IRQ (each
channel's field, the noise from the loudest, written where changed).
MEASURED: `tools/sound_check.mjs`, all 31 of the ST's starter calls in the logic race match the BBC's,
frame by frame, channel and effect, and whether each started. `tools/sn_check.mjs` (the chip's writes
captured in jsbeeb, cut into fields at each vsync): all 29 effects the ST started are found at the chip,
field for field, on their channels. Its first run found none: our loader left the addressable latch's line
3 low (the keyboard's scan off), and while it's low the keyboard drives PA7, so every byte to the chip lost
its bit 7 (jsbeeb models it; so does a real BBC: the MOS keeps line 3 high and drops it only to scan). Now
the loader leaves it high and `key_down` drops it for its read (the kit's keydown, unforked in that). The
default renderer disc differs from Phase 3's in that one byte (&0B for &03), its check still all frames
matching. `make check TRACE=logic0`: all 2,197 frames still match; 27,012 cycles a frame (mean), 5 frames
over a TV frame (3 before: the IRQ's sound, about 700 cycles a vsync). To listen: `build/sound/race_bbc.wav`
and `race_st.wav` (`tools/sound_wav.py`), and each effect in `build/lgen/wav` (`sound_gen.py --wav`).

**Step 11, the hazards** (`src/hazards.6502`, in the logic's bank). The trace is the renderer's own default race,
track 5 race 17, accelerate held, the tornado's and cones' coins forced (`make logictrace` makes it as
`build/trace/logic_t4_r17.json`; `LOGICTRACE=` picks it for the logic builds): its cars equal the renderer
trace's on all 2,240 frames, and two runs give the same file. It has all four hazards: the tornado (14 cars
caught), the barriers, 3 gates, 4 cones (2 hit), one water patch. The tracer now also dumps G_01EB36-
G_01EBC1, each gate's and barrier's box of mask B, and the attribute map, every frame (track 1's re-recorded
trace keeps its old content byte for byte). The test builds force the coins the ST's were forced on, after
their draws (`LgForceTornado`, `LgForceCones`).
- The logic: F_00B7E6/F_00B852 and F_00F1A8 (the tornado and its spins), F_00B97C/F_00B9A0 (barriers),
  F_00AF7A/F_00B1B2 (gates, the drones' lanes), F_00B10C (the cones' road). What a gate (F_014A04) and a
  barrier (F_014A80) write into mask B, from SUPER.DAT: a gate's bar is its box's lines 6-10, the same 6
  bytes each, by position (the rest is 0 in every position); a barrier's frame keeps by kind and sets by
  frame. MEASURED: all 2,239 frames exact, 164 variables, the seed, every byte of the boxes and of the map.
  Broken on purpose, each caught: a gate's bar a line low (frame 1), a barrier a frame on (31), a gate's wait
  a visit longer (73), the tornado's reach 6 (2011), its jitter as a step (4). Two that can't fail, and why:
  a barrier's kept bytes (it stands on road) and F_00B10C's clearing of a cone's cell (the cell code clears it
  at the hit, in the ST as here).
- The drawing: the frame builder makes the set-up's slot sprites (hazards, cones), the gates' and barriers'
  events (gendata.py --logic makes every frame, every step and first draw as an entry, by instance and code;
  the ST's again-calls marked), and the tornado as a moving object (every frame and shift). MEASURED:
  `make check TRACE=logic4`, all 2,240 frames match the model; `logic_draws` all 2,238 frames' calls.
- A Phase 3 tracer bug, found by it: `st_trace_objects.py` filed only the first line of a spark call's state
  with the call, so sparks 4-7's places went to the frame's memory and neither the model nor the trace-driven
  renderer drew them (car 2's and 3's sparks); every check had passed because both lacked them. Re-parsed
  from the Hatari logs, only the sparks' logged state changed, and every renderer trace (race, t0-t7,
  heli1-3) matches its model with them.
- Sound: a new capture of this race (`build/trace/sound_t4_r17_hz.json`, `st_trace_sound.py 4 17 ... tornado,cones`):
  all 112 starter calls match. At the chip (`sn_check.mjs --capture`) 91 of 96 effects are found. Two rules
  learned: the SN has one noise channel, the loudest effect's, so where two noise effects overlap the quieter
  one's noise is the louder's (the check now allows that); and the 5 left follow from this race's slow
  frames: the BBC's effects run in vsyncs, its starters test the priority at its frames, so with frames
  taking two vsyncs an effect ends sooner in frames than on the ST (the bonus's before frame 1534 here, so
  the BBC starts a wrench the ST didn't, which then holds off a bounce). Track 1's race: 29 of 29.
- Room: the hazards' code 1,122 bytes and the frame builder's part ~280 in the fourth bank, their data 285
  in Shared; two levers taken for it (Shared from &3070, not &3100; the state area &1C0, not &200) and the
  hazards' data moved there (`f8e4fa8`). The play build: the fourth bank 998 free, main RAM 402, Shared 486,
  the objects' bank 7,364 (the tornado's 12 compiled frame-shifts and every gate and barrier frame).
- Cycles: track 1's race 27,220 a frame (mean), 5 over a TV frame; the hazard race 38,207, 734 of 2,240 over.

**Step 12, speed, the first rounds.** Six exact changes (each checked on both traces; mask B's columns also by a
new unit test, `tools/walls_check.mjs`), MEASURED on the hazard race with `make check TRACE=logic4`:

| | Logic test, mean (worst 300) | Game, mean | Drawn frames taking 2 TV frames |
|---|---|---|---|
| Before (`3bbc668`) | 17,945 (about 21,300) | 38,207 | 734 of 2,240 |
| mask B's box writes a band at a time | 17,085 | | |
| TOS's multiply from byte j on | 16,964 | | |
| all_road cached per car | 16,354 (20,771) | 36,641 | 576 |
| the wall columns a cell row at a time; spent sparks | 15,711 (19,887) | 35,934 | 481 |

Track 1's race: 27,220 -> 26,314 mean, 5 -> 2 frames over. A fault on the way (mask_cell's flags for a wall
from a row's map) passed the hazard race and failed track 1's; the unit test now catches it.

Where the 480 slowest frames go now (`render_profile.mjs`, its regions brought up to date): the logic about
23,400 (the fourth bank's 16,800, main RAM's 6,600, the sound interrupt about 1,000 of it), the cars' plot
about 10,000, the erase 5,800, the moving objects about 4,000 (the tornado 900, the helicopter 1,100), the
gates' and slots' copies about 3,000. They average about 47,600 against 39,936. The logic's own profile is
spread thin: the drones 1,908, the cells 1,416, the divide 1,198, the wall columns 946, mask B's look-ups 883,
the sound interrupt 849, collide_car 848, car-to-car 700, all_road 606, line_hit 551, mul_dir 541, the rest
under 460 each (mean a frame). Each further lever is worth a few hundred cycles; clearing most of the slow
frames needs about 6,000-8,000 off them, from the logic and the renderer both.


**Step 12, speed, the second round (by hand, Tom: "Keep going by hand").** Nine exact changes, each checked on
both traces before its commit, MEASURED with `tools/logic_profile.mjs` (the logic test, mean a frame; in
brackets the worst 300 frames):

| | Hazard race | Track 1 |
|---|---|---|
| Before (`0bddd80`) | 15,711 (19,887) | (not measured) |
| TOS's multiply unrolled by the multiplier's bits; random(3) by folding | 15,424 (18,874) | 12,355 |
| a wall line's mask B row found once; n * 8 by byte shifts | 15,081 (18,297) | 12,321 |
| the draw order by places counted over the six pairs | 14,977 | 12,042 |
| a drone on its line skips its steer | 14,535 | 11,587 |
| mask B's boxes a column at a time (barrier tables column-major) | 14,459 | 11,587 |
| car-to-car's distance test without negating | 14,366 | 11,509 |
| a cell probe reads through its row; the pair's address only where a cell acts | 14,225 | 11,363 |
| div_s16's quotient bits shifted in by ROL | 14,191 (about 17,500) | 11,320 |

The game (`make check TRACE=logic4`, all 2,240 frames matching the model): mean 35,934 -> 34,357 cycles a
frame, drawn frames taking two TV frames 481 -> 329 of 2,240 (734 before step 12). Of the 322 frames over
39,936 cycles, most are near it (two changes earlier, 136 of 333 were over by under 2,000 and 226 by under
4,000): each 1,000 cycles off the busy frames saves roughly 50 of them. The slowest (56,000-62,000) are a wreck with the helicopter on screen and
cars under the priority cells, out of reach. Track 1's traced game: mean 26,314 -> 25,290, 2 -> 1 frame
over. The suite (`tools/suite.sh`, now 18 checks) passes.

Room: track 5's traced game had its fourth bank 16 bytes over after the wall-line change; the traced
inputs (test builds only) moved to Shared, and it ends with 10 bytes free. Main RAM's code (play build)
441 -> 224 free, the fourth bank 988 -> 874 (track 1). New checks: `tools/arith_check.mjs` (the divide and
both multiplies against the 68000's, 158,340 cases, in the suite; writing it found mul_s16 and mul_dir read
the multiplier's sign from the flags, now in their headers), and the map's evenness asserted.

Measured and not built:
- **The drones' moves since the segment's start** (RcAccX/Y, G_01E2DC/G_01E2D4): read only by F_00F92E,
  which is dead code. D14, decided by Tom ("Yes, drop them") and built: the hazard race's logic 14,191 ->
  14,056 cycles a frame, track 1's 11,320 -> 11,192, every frame of both still matching in the 162
  variables left; the logic's state 16 bytes smaller, track 5's fourth bank 10 -> 72 bytes free. The game
  (`make check TRACE=logic4`): mean 34,357 -> 34,185, frames taking two TV frames 329 -> 315; the suite
  passes.
- The probe lines' shifts (by x AND 7, y AND 7: about 530 cycles a frame on the hazard race) unrolled with a
  computed entry: about 20 cycles a call saved (COUNTED), not worth its bytes in the fourth bank; stored
  pre-shifted in the objects' bank about 350 a frame (PROJECTED) for about 6K of it.
- The erase: about 80 cycles of set-up a band, 14 bands and 75 lines a frame; its copy is 9 cycles a byte.
  At its floor without a different screen layout.
- The plot's slow path (cars under the priority cells): twice the fast loop's cost a byte by its nature.

**Step 13, the other tracks** (2026-11-02). Every track's race 17 (accelerate held, the tornado and cones
forced) traced from the logic's side in Hatari: tracks 1-5's within the tracer's default 6,000 VBLs (1,852,
2,516, 2,679, 2,878 and 2,240 frames), tracks 6-8's races longer (3,583, 3,517, 4,599 frames), so traced with
9,000 (`VBLS`; the default cut them at about 2,920, which the draw-call check caught at their last frame). Each
one's random numbers one run of TOS's generator.

The first pass of the logic oracle: tracks 1, 2, 3, 6 and 7 exact on every frame at once. Then, each found by
the oracle named and fixed:
- **The bonus's cell** (tracks 4 and 8, one frame each): F_00B326 stores the chosen slot's cell (G_01EB62)
  before testing whether it's free; the BBC stored it only when free. Tracks 1 and 5 never chose a taken slot.
- **The logic test's inputs** (tracks 6-8): carried raw, 3 bytes a frame, they overflowed its file (track 6
  by 1,638 bytes). Now runs, as the game carries them (`inputs.rle`); `logic_check --from` positions the
  runs. (`--from` restores the cars' variables but not the map or the pickups, so it fails from frame 500 on
  track 1 before and after this change: with whole races exact on every track it's no longer needed.)
- **The helicopter's tables with ANDY in** (track 2's drawing, from frame 647): `heli_pieces` (logicframe)
  reads the helicopter plotter's `MovDX` and `MovW` to leave out pieces off the screen's side; they're in the
  fourth bank's first 4K, so with ANDY paged in (D15) it read mask B instead. A fault of D15's, which said
  the logic never reads the helicopter: track 5's helicopter comes from below, every piece on the screen
  whatever the tables say. `heli_pieces` now pages ANDY out while it reads them.
- **Moving objects at the screen's sides** (track 2's drawing, from frame 725): the plotter had no horizontal
  clipping (the traced frames never needed it: their conversion asserts no piece crosses the side); a spark
  at x 304 ran past column 79 into the next row's first. `movplot` now clips to the screen's columns as the
  model does (left: the columns before 0 skipped; right: those from 80 left off), in a path only an object
  across the side takes (an unclipped one pays a test and a branch, about 14 cycles). It's in both copies:
  the helicopter's too, since coming down at x 272 its pieces cross x 320 (track 2, frame 725; its sideways
  pieces come in whole groups, but not the others). The path sits after the plot loop: before it, it pushed
  the loop across a page (107 bytes of padding). The helicopter's copy is 896 bytes, so `gendata.py`'s
  allowance for it (`HeliCode`) is 900, not 840: the traced renderer test (`make beeb`) keeps 304 of its
  race's frames, not 306. Every play build's fourth bank 108 bytes less (3,428 free on each track) and
  the objects' bank 91 less (its copy grew too); the hazard race game 34,190 -> 34,227 cycles a frame, frames
  over 306 -> 311 (MEASURED, `make check TRACE=logic4`).
- **The race's end after the flip** (track 7's last frame, the HUD): `race_end` (F_00C592's end: other cars
  that finished in the last 4 frames put back to lap 3) ran before the frame's records were built, so the HUD
  showed it a frame early; the ST runs it after the flip. Now after the records.

`tools/tracks_check.sh` runs every track's checks: the logic oracle, mask B's bytes, the wall columns, the
draw calls and the game drawn from the logic (`make check TRACE=hN`). MEASURED: all 48 pass (about 13 minutes,
so outside `tools/suite.sh`, whose 19 also pass). Every track's race 17 is bit-exact through the BBC's logic on
every frame and drawn exactly from it.

**Step 12, speed, the third round** (2026-11-02, Tom: "Yes, speed"). First a profile of the game itself by
label (`tools/game_profile.mjs`, new: each bank's labels, so set-up shows apart from loops): in the slowest
frames the cars' plot spent more on its per-car and per-band set-up (about 4,800 cycles) than in its loop
(2,600), the erase likewise (2,600 against 2,500), the logic's wall tests spiked (about 4,500), and the sound's
field cost about 1,100 every TV frame. Five exact changes, each checked by the suite before its commit,
MEASURED on the hazard race (the logic test, `tools/logic_profile.mjs`; the game, `make check TRACE=logic4`,
all 2,240 frames matching the model each time):

| | Logic test, mean (worst 300) | Game, mean | Frames over a TV frame |
|---|---|---|---|
| Before (`8e1672d`) | 14,015 (17,111) | 34,228 | 311 |
| the wall probes' shapes stored pre-shifted | 13,476 (16,324) | 33,634 | 258 |
| a divide by 40 under 2,048 from a table of DIV 5 | 12,989 (15,767) | 33,141 | 225 |
| the sound's field: port A set once, the engine's step by immediates | 12,815 | 33,120 | 212 |
| a tone's second byte worked out in the chip's wait | 12,731 | 33,113 | 209 |
| the cars' plot patches its data once a car | (the renderer's) | 33,056 | 209 |

- **The probes**: every car sprite set's 16 facings have 17 sets of probe shapes between them, so each is
  stored 8 times, shifted by x AND 7 (the lines) or y AND 7 (the columns), instead of shifted a bit at a
  time (about 20 cycles a bit, 530 a frame). 1,696 bytes of the fourth bank; the per-car tables leave
  Shared (640 bytes).
- **The divide**: 18,383 of the race's 18,878 divides are by 40 (a drone's D), nearly all under 1,024 from 0;
  n DIV 40 = (n >> 3) DIV 5. `arith_check.mjs` now tries every number from -2,100 to 2,100 by 40 too.
- **The sound**: the chip's writes are identical, field for field (2,246 fields, `sn_check.mjs --fields` on
  the builds before and after).
- **The plot**: Y runs on through a car's rows (8 * the band + the line), so only the screen's operands are
  patched each band. Smaller than counted (57 cycles a frame, not about 140: the first band still patches
  both, and only 4 of a frame's 8 bands are later ones); 31-35 bytes of the cars' bank.

Room (play builds, `tools/all_tracks.sh`): the fourth bank 3,428 -> 1,476 free on every track, Shared +640
(tracks 4 and 6: 128 -> 768), main RAM's code 224 -> 213, the cars' bank 31-35 less (track 6: 396 -> 361).
The suite's 19 checks pass, and `tools/tracks_check.sh`'s 48.

Measured and not built:
- The plot's per-band screen patches (10 operands, about 90 cycles a band, 8 bands a frame): what's left of
  the band's set-up. Zero-page pointers instead would cost 2 cycles a byte more in the loop.
- `obj_bands` patches all 12 columns a band: but gates, 12 bytes wide, are 978 of its 1,054 copying bands.
- The wall columns' line loop over a mixed cell (about 400 cycles a frame in the slowest): mask B's mixed
  cells stored a second time, transposed, would make it one AND, but take as many bytes again (2,136 on
  track 8), more than the fourth bank has left.
- The erase's set-up (about 95 cycles an entry, 8 a frame, and 116 + 8 a column a band): its col * 8 by
  table would save about 12 an entry.
- The engines' two periods (+ and - the step, octave-reduced) worked out when the logic sets them, not each
  field: the same work moved, saving only in frames that span two fields.

**Step 12, speed, the fourth round** (2026-11-02, Tom: "Yes, round four"). Four exact changes, each checked by
the suite before its commit, MEASURED on the hazard race (the game, `make check TRACE=logic4`, all 2,240
frames matching the model each time):

| | Game, mean | Frames over a TV frame | Room |
|---|---|---|---|
| Before (`a1f1e4e`) | 33,056 | 209 | |
| the slow loop runs a band's columns, its set-up once a band | 32,661 | 164 | cars' bank +50 |
| the slow loop's byte as data EOR ((screen EOR data) AND keep) | 32,628 | 162 | cars' bank +11 to +14 |
| the HUD's scores compared only after points were added | 32,224 | 150 | main RAM -5 |

- **The slow loop** (cars under the priority cells): it was called a column at a time with a count always
  1, so each column's operands were copied twice and the next column's sums done only to return. Now one
  call a band. (Counted about 95 cycles a slow column instead of about 250.)
- **The HUD**: `build_hud` compared all four cars' 6 score digits each frame to find a change; `score_add`,
  the only writer in a race, now flags the car (`RcScored`), and only a flagged car is compared. Track 1's
  race (`TRACE=logic0`): mean 24,338 -> 23,939.

Room (play builds, `tools/all_tracks.sh`): the cars' bank 61-64 bytes more (track 6: 361 -> 422), main RAM's
code 213 -> 208 (the HUD's 4 flags fit the logic's fixed state in ANDY). The suite's 19 checks pass, and `tools/tracks_check.sh`'s 48.

What's left over a TV frame is structural (per-frame routine costs, `tools/game_profile.mjs` and a
frame-by-frame breakdown): frames 97-195, the start of the race, have the helicopter on screen (about 7,700
cycles a frame, 4,700 of them its copy loop) and a gate stepping every 6 frames (its copies, `obj_bands` and
`obj_runs`, 4,600-8,200 over its two frames, and `mb_box` 1,230); the slowest (frame 180, 54,046) adds cars
under a bridge (the slow loop 5,600) and against walls (`column_hit` and `mask_cell` 3,200). Clearing those
needs about 5,000-14,000 off a frame: more than any lever left at this level.

Measured and not built:
- The erase's two patch sequences as one (the background's high byte is the screen's EOR &C0, stored by
  STX): counted 1 cycle a band, since the cell's low byte then needs a zero-page store.
- `mb_box`: 29 cycles a byte (a gate's step), its loop's end by a patched CPY # 1 cycle less.
- The logic's routines are each near their floors: the largest left are the cell probes (646 cycles a
  frame), a drone's move (528), the road test (388), car-to-car's pairs (352) and the draw order (334).
- The wall columns' line loop over a mixed cell, where its lines run contiguously: an unrolled ORA chain
  entered at the first line would be about 7 cycles a line instead of 16-25, but needs first- and last-bit
  tables (512 bytes); about 300 cycles in the wall-scraping frames.

**The helicopter replaced (D16)** (2026-11-02, Tom: "Blinking car cue sounds good."). The helicopter isn't drawn
in the game; its logic, timing and sound stay the ST's. In a wreck's last 28 frames the car shows where it
comes back, 4 frames on and 4 off (the model takes the wait and the safe place from the race's logic trace:
a race can end with a car still wrecked; two faults fixed after the track checks, D16). MEASURED (`make check`, every frame matching the model): the hazard race's
frames over a TV frame 150 -> 106, mean 32,224 -> 31,874; track 1's race mean 23,939 -> 23,534. The fourth bank
1,476 -> 2,608 free on every track (play builds), and its first 4K, under ANDY, empty.

Then the wall columns from a copy of mask B's mixed cells by column (Tom: "Moving mask B back out of ANDY
sounds like it'd be worth trying after that, then measuring the result."). Mask B didn't need to move: the
copy fitted above ANDY where the helicopter was, read with no paging; the cells a gate or barrier changes kept
out of it (each row's numbered last, `MbDyn`). Exact, but MEASURED small (`7b70c1c`): the logic test 12,730 ->
12,650 cycles a frame, the game 31,874 -> 31,771 and its frames over unchanged at 106, the wall-scraping frames
about 100 less each, for 1,200-2,320 bytes of the fourth bank (track 8 left 229). The line loop it replaced
cost less than projected (a column touches few of a cell's lines). Reverted (Tom: "Yes, revert it."); the room
stays free.

**The flip in the blank (D17)** (2026-11-03, Tom's idea: a VIA timer at the display's end). A frame is shown
at the display's end if it was done during the display (System VIA T1, started at each vsync), at once if
done in the blank, once a blank; before, it waited for the vsync, 40 lines later, and a frame that missed it
waited a whole field. Measured: every flip lands in the blank (lines 212-309 of 208-311); the fields
repeating a frame on the nine races drawn from the logic 332 -> 42 (the hazard race 105 -> 5), every frame
exact. `render_check` now counts those fields (irq.6502's `Repeats`); its cycles a frame now take in the
vsync's sound field (about 1,000), which used to fall just before a frame's start, so its "over a TV frame"
no longer measures what's shown. A hardware gate, passed: Tom, 2026-11-03: "D17: looks good. No noticeable tearing running on real Master 128 with CUB."

**The play build's restart** (2026-11-03, Tom: "it occurs if there's a powerup lying around uncollected when
the race finishes. When the race restarts, it's not erased, and it's no longer collectable, and driving over
it might (not reliably I don't think) produce the grey square."). The play build starts the race again by
clearing the logic's state, but two things kept what the last race wrote: the attribute map (assembled into
the logic's bank) and the clean background. A bonus or wrench left lying stayed drawn, and its cells stayed
`&11` or `&0D`. Driving over a stale bonus took it again, and `bonus_frame` drew road at the new race's bonus
slot: the map's cell (0, 0), the play area's top-left, until the new bonus was placed (read from the code, not
reproduced headless). Fixed until D3's load per race: at a restart the 20 slots' cells go back as the track
has them (`SlotCellL`, `SlotCellR`, from `gen_logic.py`) before the new race places its own; on the set-up's
two flips each slot's 32 bytes of clean background (`slotbg.bin`, from `gendata.py`) go into the background
and the screen being written, then the other screen (`slot_put`, in main RAM). Not the ST's road sprite: on
track 6 slot 17 and track 8 slot 4 the background isn't that sprite, and on tracks 5 and 7 a slot's left cell
is `&08`. MEASURED (a check left to race with the drone alone, two restarts): after each restart the old
disc's background differed from the boot's in 20 then 72 bytes and its map in 2 then 6 cells, the new disc's
in none, and both screens match the background at every slot. The play build's main RAM 152 -> 103 bytes
free, the fourth bank 2,608 -> 1,828.
