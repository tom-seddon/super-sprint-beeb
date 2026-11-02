# Report: Phase 4's first steps, 2026-11-02

**Where it ended.** On the branch `phase4-start` (not merged, not pushed). Track 1's race runs on the BBC
from its own logic, bit-exact with the ST on every frame of the traced race, drawn exactly (every frame
matches the model), with three players on the keys (Q W E, V B N, , . /; you've tried it in jsbeeb) and now
sound: the ST's effects captured from its own YM and converted for the SN76489, the engines live. The
sound's starters match the ST's call for call, and every effect the ST started is found at the BBC's chip
field for field; how it sounds is yours to judge: `build/sound/race_bbc.wav` against `race_st.wav`, and
each effect in `build/lgen/wav`. A disc to play: `build/play.ssd` (`make beeb TRACE=play`). The next
thing is room: 52 bytes of main RAM left, 136 in the fourth bank; then the hazards (tornado, barriers,
gates, cones) and the other tracks.

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

## Please review

- **D12, the keys**: Q W E, V B N, , . / (Proposed; player 1 was Z X SHIFT until your suggestion). Please play `make beeb TRACE=play` on a real BBC:
  the paper check says no ghosting, but jsbeeb can't show it, and comfort is yours to judge.
- **D11's details** (Proposed, for your ears): each effect one captured instance; tone and noise together
  play as the noise alone (the kit's 1942 rule); the engine two octaves up, its growl sampled at 50 Hz; the
  start's 1 s pause kept. Each is a small change if it sounds wrong.
- One finding that follows from D9: 7 of the 16 facings' car shapes differ between the car sets, so the
  wall probes have to use each frame's own shape. The cheaper fixed shape per facing would not be bit-exact.

## Hardware gates

- **The keys** (D12): the play disc on a real BBC, three players holding keys together.
- Nothing else in this job touches timing a real machine sees differently (no new mid-frame tricks).

## What is open

Resume point: **room** (`docs/brief-phase4.md`): 52 bytes of main RAM in the play build, 136 in the fourth
bank (the logic's code, data and state, the frame builder and the inputs beside the helicopter). The next
features need a plan for what goes where across all 8 tracks (`beeb-ram-hunt`): the objects' bank has
10,124 bytes free on track 1 but much less on others (2,933 on track 5 in Phase 3). Then: the tornado,
barriers, gates and cones (they trap), the frame's worst cases (5 of 2,197 frames over a TV frame), the
other 7 tracks, and the joysticks once measured on a real Master.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `phase4-start` | see `git log -1 phase4-start` | no | no | no |
