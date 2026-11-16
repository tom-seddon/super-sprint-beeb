# Report - the suite's wall time, and !BOOT above a Model B's PAGE (2026-11-16)

Branch `suite-boot`, off `main` at 8688a11. Brief: `docs/brief-suite-boot-2026-11-16.md`. Nothing merged, nothing
pushed.

**Waiting on your Master:** `!BOOT` now loads at `&2000`, not `&1200`. Every disc's boot changes (only `!BOOT`: its
load and exec addresses and its bytes). Checked in jsbeeb on a Master (the whole suite) and on Model Bs; not yet on
real hardware. To try: `make -j2 game && make -j2 ta` on the branch, then `build/game.ssd`, `build/game.adl`,
`build/ta.ssd`, `build/ta.adl` as usual.

## Where it ended

Both items done. The suite runs in about 2,465 s here, against 2,637 before (6.5%, one run each), and every verdict
passes (run D at 4168329: 61 verdicts, all 0, 2,460 s). `!BOOT` is at `&2000`, above both Model Bs' PAGE, and a new check, `tools/modelb_check.mjs`, proves
it and is in the suite.

## What was built, and what proves it

1. **A fault of mine, fixed** (1fdac6f). The README change on 2026-11-15 (d0ac217) gave `make_game.py` a fourth
   argument, and `tools/suite.sh` still called it with three: the suite's `game_disc` and `ta_disc` would have
   failed (MEASURED: exit 2). The suite also lists MERGE's two checks now.
2. **Timing in the suite** (436f1a9): each step's start and end in `OUT/times.txt`, each disc job's in
   `OUT/disc_races/<job>.time`.
3. **The disc's jobs in the background, in their own copy** (bdad135). They start as soon as the disc's made, in
   `OUT/disc_races/tree`: what they read copied first (build/gen's tables, the discs, the tools: 64 files, under a
   second), then the traces and models hard-linked (165 files, 2 s). The builds and short checks after the disc's,
   and time attack's build and checks, run beside them. What the jobs read is one list now, `tools/disc_files.sh`,
   which `tools/remote.sh` uses too (the same 229 paths). 2,637 s to 2,500 (137 s).
4. **The disc's jobs longest first** (b30bdb2), by the baseline's times. 2,500 to 2,469 s; the last six jobs end
   within 6 s of each other, where `game_adfs` had run alone for its last 61 s.
5. **`MACHINES=2`**: 2,462 s against 2,469, noise. Dropped (nothing to undo).
6. **The Model B check** (ffb5069): both discs, SHIFT-BREAK on jsbeeb's Model B with DFS 1.2 and its 1770 model: the
   refusal shown, then after BREAK `!BOOT`'s load at or above PAGE, `*CAT` and BASIC fine. At `&1200`: 4 wrong (the
   load below PAGE, each disc and machine), the rest right.
7. **`!BOOT` at `&2000`** (4168329), its section guarded below `&3000`. Both discs built before and after with the
   version, commit and date pinned: only `!BOOT` differs. `modelb_check` right (16 checked); the Master's boot at
   the same fields as before.

The runs (`tools/suite.sh`, this laptop, MACHINES=4 but run C):

| Run | Commit | Total | Verdicts |
|---|---|---|---|
| baseline | 436f1a9 | 2,637 s | 2 failed, mine (below) |
| A2 | bdad135 | 2,500 s | all 0 |
| B | b30bdb2 | 2,469 s | all 0 |
| C, MACHINES=2 | b30bdb2 | 2,462 s | all 0 |
| D, the end | 4168329 | 2,460 s | all 0, `modelb_check` among them |

## Mistakes along the way

- The baseline's `crash_check` and `options_check` failed because I added a file to the tree during the run: the
  next build rewrote `build/gen/version.6502` with "m" after the disc was made. The copy in step 3 now keeps the
  disc's jobs from seeing such a change; I kept the tree untouched during the later runs.
- Run A failed at once: my copy made `.mcp.json` a directory. My test of the copy had counted the files, not checked
  where they went. Fixed and tested properly (every path, and a check run in the copy) before run A2.

## Decisions TAKEN - please review

None. The two items were as the plan had them, and the four suite guesses were judged by the rule you agreed.

## For you to see

- On a Model B the refusal, 42 characters, wrapped on MODE 7's 40 columns, mid-word: "Super Sprint needs a Master
  128 or Compa" / "ct". It was so at `&1200` too. Changed (Tom, 2026-11-16: "I think for the shorter message, remove
  the `a `"): "Super Sprint needs Master 128 or Compact", 40, one row (the OS's newline before it), `boot.6502`
  asserting it's no longer (MEASURED: the assertion fails with the "a" back). `modelb_check` right, the boots' fields
  as before.
- An ADFS-only Model B, your worry, can't be tried in jsbeeb (it has none). Tom tried it in b2 (2026-11-16): "Tried
  on b2 with BBC B+ADFS - got the expected error."

## What's open

- Your Master: the boot at `&2000`, then the merge into `main` if you agree.
- The suite's wall time, agentbox's half: the ghost checks split by track (`GHOSTS=4 MACHINES=8`), when agentbox is
  back.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `suite-boot` | the commit adding this report, its last | no | no | no |
