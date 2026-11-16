# Brief - the suite's wall time, and !BOOT above a Model B's PAGE (2026-11-16)

> **Status: IN PROGRESS.** An unattended job (Tom away). Branch `suite-boot`, off `main` at 8688a11. Nothing merged,
> nothing pushed. Report: `docs/report-suite-boot-2026-11-16.md`, written last.
>
> **Resume point:** step 1. If this session ends, the next starts at the step named here, reading this brief, then
> `tools/suite.sh` and the step's notes below.
>
> Figures say **MEASURED** (a run, named), **COUNTED** (off the source or a listing) or **ESTIMATED**.

## 1. What Tom asked for

Two of the plan's open items, one after the other, without him (Tom, 2026-11-16: "I will be away for a while, so it
should like these two items might be good things to do right now. I don't mind which order, so the suggestion sounds
fine to me." Then, of the defaults below: "These all sound good. Please begin.").

- **The suite's wall time**, the laptop's half only: agentbox is unreachable (its name didn't resolve, 2026-11-16), so
  the ghost checks split by track (`GHOSTS=4 MACHINES=8`) stays on the plan's list. The four guesses (`JOURNAL.md`,
  2026-11-13; the plan's item): `disc_races` started as soon as the disc's made, as with `REMOTE=` (perhaps 2
  minutes); time attack's tracks built while the disc's checks run (perhaps 1); `game_adfs` earlier in
  `disc_races`' list (perhaps 30 s); `MACHINES=2` (about 2%). Each kept only if every check passes and its section is
  clearly faster, timed from the suite's own logs (this laptop's times vary: time attack's checks took 397-713 s on
  one build); anything not clearly better dropped, with its figures.
- **`!BOOT` above a Model B's PAGE** (the plan's "Possible later"): `boot.6502`'s `BootOrg` from `&1200` to `&2000`,
  with a check first, shown failing at `&1200`: on jsbeeb's Model B with DFS 1.2 and with the 1770 (DFS and ADFS),
  SHIFT-BREAK on `build/game.ssd` and `build/ta.ssd` shows the error, then BREAK, PAGE read against `!BOOT`'s load
  address, and `*CAT` working. Then the whole suite.

## 2. Steps

1. This brief, committed. Then the suite's fault found on the way: `tools/suite.sh` calls `tools/make_game.py`
   with three arguments since the README's kind became its fourth (`d0ac217`, 2026-11-15), so `game_disc` and
   `ta_disc` fail (MEASURED: exit 2). The fix, and MERGE's two checks (`merge`, `merge_adfs`) in its verdicts.
2. The baseline: the whole suite at step 1's commit, every verdict and each section's time.
3. The speed-ups, each a commit if it's kept, timed against step 2.
4. The Model B check, failing at `&1200`.
5. `BootOrg` at `&2000`: the check passing, the four discs changed in `!BOOT` alone.
6. The whole suite at step 5's commit.
7. The report; the plan and journal.

## 3. Gates

- `!BOOT`'s move changes every disc's boot: built and checked in jsbeeb, then **ready for Tom's Master**, not merged.
- The ADFS-only Model B can't be tried in jsbeeb (it has no such model); said so in the report.

## 4. Notes as the steps land
