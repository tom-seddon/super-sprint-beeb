# Report - time attack's ghost checks split on agentbox (2026-11-16)

Branch `ghost-split`, off `main` at 85c48f4. Brief: `docs/brief-ghost-split-2026-11-16.md`. Nothing merged, nothing
pushed. Nothing for your Master: only the checks' scripts changed, not the discs.

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
   `GHOSTS` limited to 1-4 (below).

The runs (`tools/suite_remote.sh`, the suite's own time on agentbox):

| Setting | Runs | Time attack's checks | Ghost checks (longest piece) | Verdicts |
|---|---|---|---|---|
| baseline (1) | 222, 214, 216 s | 64-74 s | 63-74 s | all 0 |
| `GHOSTS=2` | 181, 182, 179 s | 36-39 s | 34-39 s | all 0 |
| `GHOSTS=4` | 185, 185, 182 s | 39-42 s | 20-23 s | all 0 |
| `GHOSTS=8` | 189, 189, 192 s | 46-48 s | 12-14 s | ghost and ghost_adfs wrong, every run |
| `GHOSTS=2`, the default, at 7910266 | 182 s | 39 s | 36, 39 s | all 0 (61) |

At 2 the ghost checks end about when `merge_adfs` does (33-35 s), which is now time attack's longest check; 4 gains
nothing (its ghost pieces done in about 21 s, `merge_adfs` then the tail).

## Decisions TAKEN - please review

- **`GHOSTS` at most 4.** At 8 the pieces with track 5 alone and track 8 alone fail (below). 5 to 7 would put one of
  those tracks alone too. So `tools/ta_checks.sh` refuses more than 4.

## For you to see

- **The ghost check never sees a ghost on tracks 5 and 8.** In its 2400 frames a race, the autopilot's laps there
  record no ghost: "0 ghosts, the ghost drawn on 0" on both passes, both discs, every run, split or not (the
  baseline's logs). Those two tracks' frames are still checked (0 wrong), but only with no ghost to draw; the other
  six tracks draw it, and the check's rule ("wrong if no ghost is drawn on any track") is met by them. Not changed
  here (you agreed: report anything else, don't change it). If you want those tracks covered: more frames for them,
  or a look at why the autopilot's laps there don't make a ghost (gates on track 5 and 8? D36 kept the ST's).
- **What the rest of agentbox's suite is waiting on** (the baseline's run 1): the builds to the game's disc 51 s; then
  the short checks one at a time, 51-114 s, beside the disc's races (51-154 s, done before time attack starts); time
  attack's tracks 114-145 s and its disc 145-156 s, one after another; its checks from 158 s. So about 105 s of the
  remaining 180 is one step after another on a 16-core machine: the short checks run side by side, or time attack's
  build started sooner, would be the next places to look. Not tried (as agreed).

## What's open

- Nothing of this item. The plan's "suite's wall time" can close, if you agree, with the two notes above as new items
  or not, as you choose.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `ghost-split` | the commit adding this report, its last | no | no | no |
