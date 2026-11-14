# Report - the game's loads' two screen faults (2026-11-14)

**Ready for your Master; not merged, not pushed, not published.** This changes when the HUD's row is redrawn and when
R8 switches the display off at a load's end, so it waits on real hardware (the brief's gate).

## Where it ended

Done on the branch `game-load-faults` (off `main` at 0b3b3c2): the game now has time attack's two load fixes, the
`IF GenTimeAttack`s around them dropped in `src/loadcode.6502`. The whole suite passes. To try it:
`build/game.ssd` and `build/game.adl`, built by the suite at 19ae959 (the options screen says `19ae9`;
SHA-1 6ba5fba0… and 4c45460d…). What to watch: the boot's "Loading" and the attract mode's loads, as in time
attack's 6f, the HUD's row never cut short or its last line missing for a field.

## What was built and what proves it

- `7f11b1e`: `.past` (the row redrawn 90 lines after OSBYTE 19's vsync, so after it's shown) and `.edge`
  (`rows_back` writing R8 from a vsync) for the game too. Time attack's discs the same byte for byte at one
  `VERSION=` (its code already both); the game's differ. The first 4K 181 to 161 bytes free (20 bytes), the rest the
  same. `boot_check` DFS and ADFS, `flash_check`, `load_check` DFS and ADFS all pass.
- The fault test (`19ae959`, in the brief): a copy of `boot_check` with a delay's count poked into a test build of the
  old code and one of the new, 358 boots (550 s):
  - a hold-up after the vsync: the old code fails at 3 to 60 lines, the new passes to 200 (it fails from 220,
    its redraw reaching the next field's row: no OS interrupt is that long);
  - the load's end later: the old code fails at 84 to 90 lines (the row's first lines shown alone), the new at
    none of 0 to 254.
  So the game's `boot_check` passed before only because its loads end where they do; with the fixes it passes
  wherever they end.
- The whole suite (`tools/suite.sh`, here, at 19ae959): **every verdict 0, 40 min 32 s** (`disc_races` 1,764 s, its
  72 races exact, `game_check`, `attract_check` and the rest passing; none of the checks pinned the loads' times).
  Time attack's part: tracks 53 s, discs 38 s, checks 356 s (ghost 343, ghost_adfs 356, table 119, save 114, scores
  69, menu 21, picture 17, options 16, rows 10, boot_adfs 6, boot 4).

## Decisions TAKEN

None.

## Gates waiting on hardware

- The discs above on your Master: the boot and a few loads (the attract mode, a race's).

## What's open

Merging into `main` (a fast-forward: three commits plus this report's) once you've tried it. Nothing else.

## Branch ledger

| Branch | Head | Merged | Pushed | Published |
|---|---|---|---|---|
| `game-load-faults` | this report's commit | no | no | no |
| `main` | 0b3b3c2, 6 ahead of `origin/main` | - | no | no |
