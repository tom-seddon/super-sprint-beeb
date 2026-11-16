# Report - time attack's ghost checks split on agentbox (2026-11-16)

Branch `ghost-split`, off `main` at 85c48f4. Brief: `docs/brief-ghost-split-2026-11-16.md`. Merged into `main`
2026-11-16 (Tom: "Please merge this into main."); not pushed. Nothing for your Master: only the checks' scripts changed, not the discs.

## Where it ended

Done. The whole suite on agentbox (`tools/suite_remote.sh`) runs in about 180 s there, against 214-222 s before
(about 35 s, 16%; three runs each, the ranges well apart), every verdict 0. Time attack's two ghost checks run as two
pieces each on agentbox, four tracks a piece (`GHOSTS=2`); the laptop is as it was (`GHOSTS=1`).

## What was built, and what proves it

1. **`GHOSTS` in `tools/ta_checks.sh`** (6e5f295): each ghost check as that many pieces, piece k racing tracks k,
   k+GHOSTS, ... (`TRACKS=`, which the check took already); `ghost` and `ghost_adfs` made from their pieces (wrong if
   any is, or left no status), so `tools/suite.sh` reads them as before. Tested first with stand-in checks in a
   scratch tree: `GHOSTS=1` the same 13 checks as before; 2, 3 and 8 split as meant; one wrong piece made its ghost
   check wrong and the script exit 1.
2. **`GHOSTS` passed to agentbox** by `tools/suite_remote.sh` (3320948), then **2 kept** as its default (7910266), and
   `GHOSTS` limited to 1-4 at first (lifted in 4).
3. **The autopilot fixed** (8537ea8, after the first report, Tom: "Yes, fix the autopilot"). The ghost check had
   never seen a ghost on tracks 5 and 8: the autopilot (`tools/ta_pilot.mjs`) wedged against a wall there and never
   finished a lap (MEASURED, a probe: track 5 stuck from frame 400, track 8 from 600, to 6,000). It steered for each
   segment's far end, moving on up to 4 segments a frame: on track 8 it skipped a hairpin's short segments at speed
   and turned the short way, clockwise, into a pocket under a barrier; on track 5, wide off a fast corner, it drove
   up into the outer wall's bulge. And a car bouncing off a wall ignores its input (`human.6502`'s `RcBounce`), a
   slight turn along one straightened (its nudge), so it never got free. Now it steers for a point 320 along the
   path from its place on it, moves on only past a segment's end, and wedged (under 32 moved in 64 frames) lets go
   while it bounces, then turns for a point just ahead on the line. MEASURED, each track one race of 2400 frames:
   every track records a ghost with the look-ahead anywhere from 240 to 400 (without the recovery, 300-340 only);
   320 chosen.
4. **A ghost on every track** (8972c9b): the check failed only if no track drew one, which let 5 and 8 pass with
   none; now each track raced must, so any split holds, and `GHOSTS` is 1 to 8. Shown failing: 300 frames a race,
   no lap done, "no ghost drawn (pass/track): 1/1 1/5 2/1 2/5", exit 1.

The runs (`tools/suite_remote.sh`, the suite's own time on agentbox):

| Setting | Runs | Time attack's checks | Ghost checks (longest piece) | Verdicts |
|---|---|---|---|---|
| baseline (1) | 222, 214, 216 s | 64-74 s | 63-74 s | all 0 |
| `GHOSTS=2` | 181, 182, 179 s | 36-39 s | 34-39 s | all 0 |
| `GHOSTS=4` | 185, 185, 182 s | 39-42 s | 20-23 s | all 0 |
| `GHOSTS=8` | 189, 189, 192 s | 46-48 s | 12-14 s | ghost and ghost_adfs wrong, every run |
| `GHOSTS=2`, the default, at 7910266 | 182 s | 39 s | 36, 39 s | all 0 (61) |
| The autopilot fixed, at 8972c9b: `GHOSTS=2` | 179 s | 37 s | 37, 36 s | all 0 (61) |
| ... `GHOSTS=4` | 181 s | 39 s | 21, 23 s | all 0 (61) |
| ... `GHOSTS=8` | 188 s | 46 s | 14, 14 s | all 0 (61) |

At 2 the ghost checks end about when `merge_adfs` does (33-35 s), which is now time attack's longest check; 4 gains
nothing (its ghost pieces done in about 21 s, `merge_adfs` then the tail).

## Decisions TAKEN - please review

- **The autopilot's look-ahead, 320** (eighths of a pixel): the middle of 240-400, where every track laps.

## For you to see

- **Tracks 5 and 8 now checked with a ghost**: since the autopilot's fix, each track's two races on each disc draw
  the ghost (the second from the saved file), so `GHOST5` and `GHOST8` are checked too, which they never were. The autopilot's laps changed on the other tracks too (a different line): every check that uses
  it (`ta_ghost_check`, `ta_save_check`, `ta_table_check`) passes.
- **What the rest of agentbox's suite is waiting on** (the baseline's run 1): the builds to the game's disc 51 s; then
  the short checks one at a time, 51-114 s, beside the disc's races (51-154 s, done before time attack starts); time
  attack's tracks 114-145 s and its disc 145-156 s, one after another; its checks from 158 s. So about 105 s of the
  remaining 180 is one step after another on a 16-core machine: the short checks run side by side, or time attack's
  build started sooner, would be the next places to look. Not tried (as agreed).

## What's open

- Nothing of this item. The note above on what agentbox's suite still waits on: on the plan's list for a possible
  later version (Tom, 2026-11-16: "I think at this stage maybe it isn't quite worth it for 2 minutes."), with three
  changes costed (about 179 s to 150, or 120 with the track builds in parallel; ESTIMATED).

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `ghost-split` | the merge's commit, its last | yes (fast-forward) | no | no |
