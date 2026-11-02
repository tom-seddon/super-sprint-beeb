# Report: Phase 4's first steps, 2026-11-02

**Where it ended.** On the branch `phase4-start` (not merged, not pushed). The plan is
`docs/brief-phase4.md`; your answers are D9-D13 in `docs/decisions.md` (D13 decided after the first
report). Done: the Hatari logic tracer (step 2), the logic's oracle (step 3), mask B's storage (part of
step 4), the humans' cars (step 5) and the walls (step 6): car 0 matches the ST bit for bit in every
movement variable on every stretch of the race the logic can reach so far, 1,933 frames with 23 wall
bounces. To try it: `.venv/bin/python tools/logic_stretches.py 0`, or `make logiccheck LOGICARGS="--until
75 --cars 0"`. The renderer's disc is byte-identical to Phase 3's. Next is step 7: the track's cells,
car-to-car, drones.

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

## Please review

- **D12**: I recorded the layout as Proposed until you've tried it on a real BBC.
- **D11** replaces the plan's earlier sound idea (a sequencer at 83 Hz): `docs/plan.md` now points to D11.
- One finding that follows from D9: 7 of the 16 facings' car shapes differ between the car sets, so the
  wall probes have to use each frame's own shape. The cheaper fixed shape per facing would not be bit-exact.

## Hardware gates

None yet. The key layout (D12) will need your real BBC once it's built.

## What is open

Resume point: **step 7** (`docs/brief-phase4.md` §6): the attribute cells (car 0's stripes differ from
frame 26), car-to-car and drones (frame 76), then wrecks and the helicopter, and the race's end (2031). The tracer
doesn't yet record the wrench and bonus timers or the attribute map's changes; it will when a step needs
them. The logic's state is at `&0400` in the test only; where it goes in the game is step 8's question.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `phase4-start` | see `git log -1 phase4-start` | no | no | no |
