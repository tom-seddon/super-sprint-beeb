# Report: Phase 4's first steps, 2026-11-02

**Where it ended.** On the branch `phase4-start` (not merged, not pushed). Track 1's race runs on the BBC
from its own logic, bit-exact with the ST on every frame of the traced race, drawn exactly (every frame
matches the model), with three players on the keys (Q W E, V B N, , . /; you've tried it in jsbeeb) and now
sound: the ST's effects captured from its own YM and converted for the SN76489, the engines live. The
sound's starters match the ST's call for call, and every effect the ST started is found at the BBC's chip
field for field; how it sounds is yours to judge: `build/sound/race_bbc.wav` against `race_st.wav`, and
each effect in `build/lgen/wav`. A disc to play: `build/play.ssd` (`make beeb TRACE=play`). A RAM hunt
then made room (main RAM 52 -> 416 bytes free, the fourth bank 136 -> 2,398, nothing on the screen or in the
play changed), and the hazards went in: the tornado, pop-up barriers, gates and cones, bit-exact on track 5's
race 17 and drawn from the logic, all 2,240 frames matching. That race was too slow: a third of its
frames took two TV frames. Fifteen exact speed changes in two rounds bring that to 329 of 2,240 (from 734),
the average 38,207 -> 34,357 cycles; what's left is spread thin across the logic and the renderer (below).

## What was built and what proves it

- **The plan** (`docs/brief-phase4.md`): the tracer and oracle first, then the ST's routines one at a time,
  each proved frame by frame before the next (humans' movement, walls, attribute cells, car-to-car, drones,
  scoring and the race's end, the wrench and bonus), then the renderer driven by the logic, keys, sound.
- **The logic tracer** (`make logictrace`, `tools/st_trace_logic.py`): 2,197 frames of track 1, race 0,
  with every per-car variable, the human's inputs and every random number, each frame. The blue car is
  driven by an autopilot (`tools/logic_scripts/t0.json`, conditions on its x, y and facing, each a chained
  one-shot breakpoint): 3 laps, wall bounces, a wreck and the helicopter, every checkpoint; the drone wins.
  Two runs are byte-identical. The race's 14 random numbers are one run of TOS's XBIOS Random
  (`seed * 3141592621 + 1`), so the BBC can start from the trace's seed and nothing else draws from it.
- **Mask B** (`tools/maskb.py`): stored as each cell row's span map and its mixed cells, 2,168 bytes on
  track 1 to 3,427 on track 8 (gates' and barriers' cells included) against 8,000. Every track decodes to
  the ST's mask with 0 of 8,000 bytes wrong; track 1's equals the ST's RAM to the pixel; broken on purpose,
  the check fails.
- `make check` (the renderer, unchanged, re-run after the Makefile change): all 317 frames match the model.

- **The logic's oracle** (`make logiccheck`): a test disc with no display replays the traced inputs
  through the BBC's logic; `tools/logic_check.mjs` compares 38 of the ST's variables every frame. Broken
  on purpose (the velocity halved rounding down), 70 of 75 frames fail from frame 6.
- **The humans' cars** (`src/human.6502`, F_00DC4C): car 0 exact for frames 1-75. 3,824 cycles a frame for
  one car, mostly the general 16-bit multiply and divide, to be made faster once the logic is whole.

- **Walls** (`src/walls.6502`, in the logic's bank with mask B): exact on all of car 0's free stretches;
  `mask_byte` right on all 8,000 bytes (`tools/maskb_check.mjs`). `logic_check.mjs --from K` loads the
  ST's state at a frame into the BBC, so a part can be proved before what leads to it is built. Cars over
  all-road cells skip the probes: 6,149 cycles a frame (mean) with one human car, from 11,702.

- **The rest of the race logic** (step 7): the track's cells, drones, the draw order, car-to-car, wrecks,
  pickups and points, the race's end, the effects. Each proved on the trace and broken on purpose once.
  `logic_check.mjs --from K` and `tools/logic_stretches.py` check a stretch before what leads to it exists.
- **Speed**: 18,940 cycles a frame to 11,439 by four exact changes (the divide's short path, /8 by shifts,
  the direction multiply in shifts, a wall cell looked up once per row); `tools/logic_profile.mjs` shows
  where the rest goes. The worst frames (18,814 with the effects) are still over what the renderer leaves
  at its worst on track 1 (15,045), so a rare frame would drop to 25 fps (D2).
- **Two corrections to st-logic** from the asm: cell types 5 and 7 set flags &1000 and &2000 (the steering
  reads them); a finish line makes laps `(laps AND 3) + 1`.

- **The game drawn from its logic** (step 8): `src/logicframe.6502` builds each frame's draw records from
  the logic's draw calls; `make check TRACE=logic0` matches the model on all 2,197 frames. Logic and
  drawing average 25,967 cycles a frame; 3 frames go over a TV frame (worst 40,820), so the display drops to
  25 fps for a moment 4 times in the 44 s race. Main RAM has 890 bytes left, the fourth bank 236.
- **Keys** (step 9): `src/keyboard.6502`; `tools/keys_ghost.py` (ghosting on paper), `tools/keys_check.mjs`
  (each key and all nine read right in jsbeeb), and the play build.

- **Sound** (step 10, D11): `tools/st_trace_sound.py` (the capture), `tools/sound_gen.py` (11 effects,
  1,566 bytes), `src/sound.6502` (starters, engines, the IRQ's player). `tools/sound_check.mjs`: all 31
  starter calls match the ST's; `tools/sn_check.mjs`: all 29 started effects at the chip. A real fault
  found and fixed: the loader left the keyboard driving PA7, so every byte to the sound chip lost its top
  bit; the default disc differs from Phase 3's in that one byte now (its check still passes).

- **Room** (a RAM hunt, `docs/brief-ram-2026-11-02.md`; the map `docs/memory-map.md`, generated by
  `tools/memmap.py`). Three levers, each measured and checked by every oracle (`tools/suite.sh`, all 10):
  the logic's 128 hottest bytes of state in zero page (654 bytes of code, 105 cycles a frame faster), the
  traced race's carried-over state as tables (330), and the read-only data (the sound's effects, the drone
  path, the wall probes) in both screens' `&3000` area, put there by SPRINT's own load (3,263 from the
  banks). Projected over all 8 tracks, the hazards fit if their code comes in under about 1,100 bytes
  (track 8 the tightest), with more levers costed if not. `tools/sn_check.mjs` was fixed on the way: it
  lined the chip's writes up by an assumption the new boot broke (the chip was right).

- **The hazards** (step 11): the tornado, the pop-up barriers, the gates and the cones, bit-exact with the ST
  on track 5's race 17 (the renderer's own default race, which has all four) and drawn from the BBC's own
  logic, every one of its 2,240 frames matching the model. On the way, a Phase 3 tracer bug: the model had
  never drawn cars 2's and 3's sparks, nor had the trace-driven renderer, so every check had agreed; fixed,
  and every trace still matches. The sound's starters match the ST's (112 calls); at the chip 91 of 96
  effects are found, the 5 others because this race's frames are slow (below).

- **Speed** (step 12, `docs/brief-phase4.md` §8): mask B's box writes a band at a time, TOS's multiply from
  the byte that matters, a car's road test cached, the wall columns a cell row at a time, spent sparks
  skipped (the first round); then by hand TOS's multiply unrolled, a wall line's row found once, the draw
  order by counted places, a drone on its line skipping its steer, mask B's boxes a column at a time,
  car-to-car's distance test, the cell probes through their rows, the divide's quotient bits by ROL (the
  second). Exact on both traces; new unit tests for the wall columns (it caught a fault the races missed)
  and for the arithmetic (`tools/arith_check.mjs`, 158,340 cases). The hazard race's frames taking two TV
  frames 734 -> 329, its mean 38,207 -> 34,357; track 1's 5 -> 1. The suite, 18 checks, passes.

## Please review

- **D12, the keys**: Q W E, V B N, , . / (Proposed; player 1 was Z X SHIFT until your suggestion). Please play `make beeb TRACE=play` on a real BBC:
  the paper check says no ghosting, but jsbeeb can't show it, and comfort is yours to judge.
- **D11's details** (Proposed, for your ears): each effect one captured instance; tone and noise together
  play as the noise alone (the kit's 1942 rule); the engine two octaves up, its growl sampled at 50 Hz; the
  start's 1 s pause kept. Each is a small change if it sounds wrong.
- **D14** (Proposed): drop the drones' two accumulators that only dead ST code reads: 135 cycles a frame
  and 46 bytes of the fourth bank, nothing in the race changed, but D9 compares every variable.
- One finding that follows from D9: 7 of the 16 facings' car shapes differ between the car sets, so the
  wall probes have to use each frame's own shape. The cheaper fixed shape per facing would not be bit-exact.

## Hardware gates

- **The keys** (D12): the play disc on a real BBC, three players holding keys together.
- Nothing else in this job touches timing a real machine sees differently (no new mid-frame tricks).

## What is open

Resume point: **speed's third round, or room** (`docs/brief-phase4.md`). Track 5's race now averages
34,357 cycles a frame and 329 of its 2,240 drawn frames take two TV frames (734 before the speed work);
each further lever is 100-300 cycles. Room binds now: track 5's fourth bank has 10 bytes free, and tracks 6
and 8 would be over (PROJECTED; HAZEL per D7 is your call). Then the other 7 tracks, and the joysticks once
measured on a real Master.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `phase4-start` | see `git log -1 phase4-start` | no | no | no |
