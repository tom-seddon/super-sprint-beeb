# Brief - the suite's wall time, and !BOOT above a Model B's PAGE (2026-11-16)

> **Status: IN PROGRESS.** An unattended job (Tom away). Branch `suite-boot`, off `main` at 8688a11. Nothing merged,
> nothing pushed. Report: `docs/report-suite-boot-2026-11-16.md`, written last.
>
> **Resume point:** step 6 (the whole suite at step 5's commit), then step 7. If this session ends, the next starts at the step named here, reading this brief, then
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

- Step 1 (2026-11-16): `tools/suite.sh` gives `make_game.py` its kind (`game`, `ta`), and lists `merge` and
  `merge_adfs` among time attack's verdicts. MEASURED: its `game_disc` line exit 0 (43 s), the old exit 2. The rest in
  step 2's run.
- Step 2 (2026-11-16): the baseline at 436f1a9, 2,637 s: 249 s before the disc's jobs (the builds 108, the short
  checks 141, mostly one core), the disc's jobs 1,868 s (the races 249-1,995; the tail, from 2,006 to 2,117, fewer
  than four jobs, `game_adfs` 122 s the last), time attack's build 90 s and checks 430 s (the ghost checks 426 and
  429 s). `crash_check` and `options_check` failed: a file was added to the tree 174 s in (this job's draft check),
  so the next build rewrote `build/gen/version.6502` as 436f1m while the disc said 436f1 (MEASURED: the files'
  times, the logs' lines). Not the game's fault; the lesson: nothing changes in the tree while the suite runs (the
  brief's notes kept in the scratchpad meanwhile).
- Step 3, run A (2026-11-16): the disc's jobs failed in 3 s, every one: the copy made `.mcp.json` a directory
  (`mkdir -p` of a path with no `/`), so `tools/jsbeeb.mjs` couldn't read its pin. A mistake of mine: the copy's test
  counted files, not where they went. Fixed (amended into bdad135), then tested: every path of `tools/disc_files.sh`
  in the copy (find against the list), and `boot_check` passing in it. Run A2 started.
- Step 3, run A2 at bdad135 (2026-11-16): every verdict 0, 2,500 s against the baseline's 2,637 (137 s, 5%: about the
  2-2.5 minutes the idle core's arithmetic predicted, the 249 s mostly on one core and time attack's 90 s of builds
  now beside the disc's jobs). The disc's jobs 101-2,500 s; time attack's build and checks inside them (the ghost
  checks 927 and 939 s, sharing the cores, against 426 and 429). One run each, so within this laptop's noise in
  principle, but as predicted; kept, as the copy also keeps a change to build/gen during the run (the baseline's
  failure) from the disc's jobs. The tail: `game_adfs` alone for the last 61 s.
- Step 3, run B at b30bdb2 (the disc's jobs longest first): every verdict 0, 2,469 s against A2's 2,500 (31 s). Small
  for the whole, but the tail shows it: the last six jobs ended within 6 s of each other (2,463-2,469), where A2 had
  `game_adfs` alone for its last 61 s. Kept.
- Step 3, run C at b30bdb2 with `MACHINES=2`: every verdict 0, 2,462 s against B's 2,469 (7 s: noise). Dropped, as
  before for time attack's checks alone (437 against 447 s, 2026-11-13); nothing to undo, it's the environment's.
  So the suite: 2,637 s to about 2,465 (6.5%), MEASURED, one run each.
- Step 4: `tools/modelb_check.mjs`, in `tools/suite.sh` after time attack's disc (13 s). MEASURED at b30bdb2's discs
  (`!BOOT` at `&1200`): 4 wrong, each disc on each Model B its load below PAGE (`&1900` on DFS 1.2, `&1F00` on the
  1770), the rest right: the refusal shown, `*CAT` and BASIC after BREAK. Its first run also had the refusal wrong:
  the message, 42 characters, wraps on MODE 7's 40 ("...Master 128 or Compa" / "ct"), so the check reads the rows
  run together now. The wrap's for Tom to see (the report).
- Step 5: `BootOrg` `&2000`, its section guarded below `LoadAddr` (`&3000`). MEASURED, both discs built at b30bdb2's
  source and at this, `VERSION=00000`, `COMMIT` and `WHEN` pinned: on each `.ssd` only `!BOOT` differs, its load and
  exec `&1200` to `&2000` and its bytes, 719 both (4 sectors: the catalogue's and its 3); `modelb_check` right (16
  checked); `boot_check` and `boot_check --ta` right, "Loading" and the title's file at the same fields as before
  (129, 138, 468; 126, 135, 394).
