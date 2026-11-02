# Brief - Phase 4, one race: the first steps

> **Status: PROPOSAL, 2026-11-02 (Tom asked for Phase 4's first steps, planned before any code).**
> Branch `phase4-start`, off `02741da` (the commit Tom last saw). Tom's four answers are D9-D12 in
> `docs/decisions.md`; the one this brief takes itself is D13 (mask B's storage), Proposed.
>
> Figures say **MEASURED** (a tool run, named), **COUNTED** (off the source or a listing) or
> **PROJECTED** (arithmetic on top).
>
> *Read first: `docs/st-logic.md` §1-6 and §12, `docs/renderer.md` "How it draws" (the priority cells),
> `docs/plan.md` Phase 4, D2, D3, D7, D9-D13.*

**Resume point: step 3.** If this session ends, the next starts at step 3 (§6), the oracle, reading this
brief, `tools/st_trace_logic.py` (what the trace holds), `tools/render_check.mjs` (the harness to follow)
and `src/memory.6502`. Step 2 is done (§8).

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
| Fourth bank | 11,361 | mask B 1,152 cells + ~660 map (track 8: 2,136 + ~810); probe shapes ~1K; drone path ~700; the wall code beside them | ~7K (track 8: ~6K) |
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
| D13 | Mask B's storage | (a) whole, (b) rebuilt, (c) mixed cells | Proposed: (c) |

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
