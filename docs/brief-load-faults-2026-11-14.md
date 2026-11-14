# Brief - the game's loads' two screen faults (an unattended job, 2026-11-14)

> **Status: DONE, ready for Tom's Master** (`docs/report-load-faults-2026-11-14.md`). Branch `game-load-faults`, off `main` at 0b3b3c2 (the commit Tom last saw). Tom away; the
> `beeb-unattended-job` skill. Everything runs on Tom's laptop (agentbox away). Nothing merged, pushed or published.
>
> **Resume point**: none, all done. If this session ends, the next one starts at the first step not marked done below,
> reading this brief, `docs/plan.md`'s item "The game's loads' two screen faults" and `src/loadcode.6502`.

## Why

`docs/plan.md`, "After Phase 5": two faults in the game's loads, found in time attack (2026-11-12) and fixed there
only, under `IF GenTimeAttack` in `src/loadcode.6502` (Tom: "Please leave the game alone for now, but make notes for
later, as it'll be worth fixing once everything is merged back into one branch"). Time attack is merged, so now:

- `.past`: the first load's "Loading" redrawn too soon. `load_track.again` clears and redraws the HUD's row from
  OSBYTE 19's vsync, 64 lines before the row's shown, and the redraw takes 72. The game's ends at about line 0 in
  jsbeeb, 6 lines to spare, but where it ends hangs on the OS's interrupts. The fix: 90 lines' wait after the vsync.
- `.edge`: `rows_back` writes R8 &F0 whenever a load ends, so in about 8 lines in 312 a field shows the row's first
  lines alone. The fix: from a vsync, CA1's flag polled.

## Steps

1. Done: the brief committed (this).
2. Done (see its commit): the two `IF GenTimeAttack`s dropped, so the game has both fixes; time attack's build unchanged (its code already
   both). `make game`, `make ta`: the game's discs differ (expected: LoadCode 20 bytes more), time attack's the same
   byte for byte at one `VERSION=`. The room in LoadCode (`&7C00`-`&7FFF`) read from the listing. First checks:
   `boot_check` (DFS, `--adfs`), `flash_check`, `load_check` (DFS, `--adfs`).
3. Done (see its commit): fault test: `boot_check` passes the game only because its loads happen to end elsewhere, so each fault is forced
   with a delay put in a mutant build, at a length measured from where the load's end lands in the frame: without the
   fix it must fail, with it pass. Mutants in the scratchpad only, never committed.
   MEASURED (DFS, `boot_check` copied with each delay's count poked as it's reached, so one build for each of the old
   and new code; the delay N lines of 131 cycles; 358 boots, 550 s two at a time):
   - a hold-up after OSBYTE 19's vsync, `PAST` 0-40 by 1, then 60-240 by 20: the old code fails from 3 to 60 lines
     (1 field wrong: the row's last line cleared), the new from 220 (its redraw then reaching the next field's row);
   - the load's end later before `rows_back`, `EDGE` 0-254 by 2: the old code fails at 84-90 (53 or 54 fields wrong:
     the row's first lines alone, then lit again), the new at none.
4. Done: the whole suite passed (every verdict 0, 40 min 32 s; the report has each part's time). The whole suite (`tools/suite.sh OUT`), detached, OUT in the scratchpad; its time and each step's reported (Tom
   asked for time attack's checks' times). Any check whose expected numbers move with the loads being up to a field
   longer: looked at, the cause said, and changed only if it's that.
5. Done: the report, `docs/report-load-faults-2026-11-14.md`, and the plan's item marked built, ready for Tom's Master.

## Gates

This changes when the CRTC's R8 is written and when the HUD's row is drawn: a display timing change, so it stops at
"ready for hardware". Tom tries `build/game.ssd` and `build/game.adl` on his Master (and a load or two in the attract
mode) before it's merged.
