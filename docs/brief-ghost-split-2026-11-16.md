# Brief - time attack's ghost checks split on agentbox (2026-11-16)

> **Status: IN PROGRESS.** An unattended job (Tom away). Branch `ghost-split`, off `main` at 85c48f4. Nothing
> merged, nothing pushed. Report: `docs/report-ghost-split-2026-11-16.md`, written last.
>
> **Resume point:** step 2. If this session ends, the next starts at the step named here, reading this brief, then
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
