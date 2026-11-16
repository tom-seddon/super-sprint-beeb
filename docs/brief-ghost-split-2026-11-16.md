# Brief - time attack's ghost checks split on agentbox (2026-11-16)

> **Status: IN PROGRESS.** An unattended job (Tom away). Branch `ghost-split`, off `main` at 85c48f4. Nothing
> merged, nothing pushed. Report: `docs/report-ghost-split-2026-11-16.md`, written last.
>
> **Resume point:** step 6 (step 5 committed; its confirming run, `tools/suite_remote.sh` with no settings, noted with it). If this session ends, the next starts at the step named here, reading this brief, then
> `tools/ta_checks.sh`, `tools/suite_remote.sh` and the step's notes below.
>
> Figures say **MEASURED** (a run, named), **COUNTED** (off the source or a listing) or **ESTIMATED**.

## 1. What Tom asked for

The plan's "suite's wall time", agentbox's half (Tom, 2026-11-16: "I think it'd be worth looking at issue 3 next.",
then of the plan below: "Sounds good. Please continue."). Time attack's two ghost checks (`ta_ghost_check`, the DFS
and ADFS discs) are its longest; split each into `GHOSTS` pieces, each its own machine racing a share of the eight
tracks (`TRACKS=`, which the check takes already), on agentbox only: on the laptop the split was slower (MEASURED
2026-11-13: 477 s against 447, `JOURNAL.md`), and agentbox runs 14 at a time against time attack's 13 checks.

- `tools/ta_checks.sh` makes the pieces and `ghost.status`/`ghost_adfs.status` from theirs, so `tools/suite.sh` is
  unchanged; `GHOSTS` defaults to 1 (as now); `tools/suite_remote.sh` passes the value kept.
- Timed with `tools/suite_remote.sh`, three runs a setting (agentbox's load varies: `mediaanalysisd` held a core,
  2026-11-16): the baseline, then `GHOSTS` 2, 4 and 8. Kept only if every check passes and the suite is clearly
  faster; anything else dropped, with its figures.
- Anything else the timings show as the longest wait: reported for Tom, not changed (Tom agreed "(a)").

## 2. Steps

1. This brief, committed.
2. The baseline: `tools/suite_remote.sh` three times at step 1's commit, every verdict and the times (the suite's,
   time attack's checks', each ghost check's).
3. The split in `tools/ta_checks.sh`, `GHOSTS=1` unchanged; checked failing (a piece's failure fails the ghost's
   verdict) and passing.
4. `GHOSTS` 2, 4 and 8 on agentbox, three runs each.
5. The setting kept (or none) in `tools/suite_remote.sh`.
6. The report; the plan, journal, `CLAUDE.md` if its oracles' text changes; the memory note.

## 3. Gates

None of hardware: the checks' scripts alone change, not the discs. Not merged, not pushed: Tom's word for the merge.

## 4. Notes as the steps land

- Step 2 (2026-11-16): the baseline at 9787068, `tools/suite_remote.sh` three times, every verdict 0 each time.
  MEASURED: the suite 222, 214 and 216 s on agentbox (218-227 s with the copying, here). Run 1's steps: the builds to
  the game's disc 51 s; the disc's races beside the rest, 51-154 s; the short checks, one at a time, 51-114 s; time
  attack's tracks 114-145, its disc 145-156, `modelb_check` 156-158; time attack's checks 158-222 (64 s; 72 and 74 in
  runs 2 and 3). In those, the ghost checks the longest, 63-74 s, the next `merge_adfs` 32-35 s. So the suite's tail is
  the ghost checks alone, about 30-40 s of it past everything else.
- Step 3: `tools/ta_checks.sh` takes `GHOSTS` (1 to 8, default 1): piece k of each ghost check races tracks k,
  k+GHOSTS, ...; `ghost` and `ghost_adfs` made from their pieces (wrong if any is or left no status; the log theirs
  in turn; the time the longest). MEASURED with stand-in checks (a scratch tree, each printing its arguments and
  `TRACKS`): `GHOSTS=1` the same 13 checks as before, `TRACKS` unset; 2, 3 and 8 the tracks split as said, the other
  checks without `TRACKS`; one piece wrong (`GHOSTS=3`, tracks 1,4,7 on the DFS disc) made `ghost` wrong,
  `ghost_adfs` right, the exit 1; `GHOSTS=9` refused. The real checks in step 4's runs.
- Step 4: `GHOSTS` 2, 4 and 8 on agentbox at 3320948, three runs each. MEASURED (the suite's own time there; time
  attack's checks; its two ghost checks' longest pieces):

      baseline (1)   222 214 216 s   ta_checks 64-74 s   ghost 63-64, ghost_adfs 63-74 s
      GHOSTS=2       181 182 179 s   ta_checks 36-39 s   34-38, 35-39 s   every verdict 0
      GHOSTS=4       185 185 182 s   ta_checks 39-42 s   20-21, 21-23 s   every verdict 0
      GHOSTS=8       189 189 192 s   ta_checks 46-48 s   12-13, 13-14 s   ghost and ghost_adfs wrong, every run

  With 2, the ghost checks end with `merge_adfs` (33-35 s); with 4, `merge_adfs`, last in the list, starts late and is
  the tail (ta_checks 39-42 against its 33-36). With 8: tracks 5 and 8 (TRACKS 4 and 7) draw no ghost in the check's
  2400 frames, so their pieces alone fail its rule (no ghost drawn: wrong), on both discs, every run. They draw none in
  the whole check either (the baseline's log: "0 ghosts" on both passes); the other six cover for them. A gap in the
  check, for Tom (the report); not changed here.
- Step 5: `GHOSTS=2` kept, `tools/suite_remote.sh`'s default (agentbox), 214-222 s to 179-182 (about 35 s, 16%; three
  runs each, the ranges apart). `tools/ta_checks.sh` takes 1 to 4 (5 and up put track 5 or 8 alone), default 1 (the
  laptop, `tools/suite.sh` alone: unchanged).
