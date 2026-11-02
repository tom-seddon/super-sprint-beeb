# Report: Phase 4's first steps, 2026-11-02

**Where it ended.** On the branch `phase4-start` (3 commits on `02741da`, not merged, not pushed). The plan
for Phase 4's first steps is `docs/brief-phase4.md`, and your four answers are D9-D12 in
`docs/decisions.md`. Two of the brief's steps are done: the Hatari logic tracer (step 2) and mask B's
storage (part of step 4). No 6502 has been written yet: the disc is the same as Phase 3's. The next step is
3, the oracle that runs the BBC's logic on the trace's inputs and compares every variable every frame.

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

## Please review

- **D13, mask B as its mixed cells** - Proposed; it's what step 4 will build. The whole mask instead (8,000
  bytes, reads twice as fast) would leave the fourth bank no room for sound.
- **D12**: I recorded the layout as Proposed until you've tried it on a real BBC.
- **D11** replaces the plan's earlier sound idea (a sequencer at 83 Hz): `docs/plan.md` now points to D11.
- One finding that follows from D9: 7 of the 16 facings' car shapes differ between the car sets, so the
  wall probes have to use each frame's own shape. The cheaper fixed shape per facing would not be bit-exact.

## Hardware gates

None yet. The key layout (D12) will need your real BBC once it's built.

## What is open

Resume point: **step 3**, the oracle (`docs/brief-phase4.md` §6). The tracer doesn't yet record the
wrench and bonus timers or the attribute map's changes; it will once the steps that need them come.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `phase4-start` | see `git log -1 phase4-start` | no | no | no |
