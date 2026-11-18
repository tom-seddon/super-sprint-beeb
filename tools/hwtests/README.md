# Tests for real hardware

Small BASIC programs that print what a real machine does, for the questions in `docs/upstream-notes.md` that jsbeeb
can't settle. Each was run in jsbeeb first, so its output there is in the notes beside the hardware's.

- `irrtest.bas` (`IRRTEST`): does ACCCON bit 7 (IRR) raise an IRQ on a Master? Both VIAs' interrupts off, a short CLI
  window, IRQs counted through IRQ1V; the handler clears IRR and exits as the game's does (A from `&FC`, `RTI`). Run
  once with IRR clear (the control) and once set. If a real Master's IRR can't be cleared that way it may hang: BREAK.
- `etest.bas` (`ETEST`): with HAZEL paged in (ACCCON Y), does code run from `&C000`-`&DFFF` see shadow RAM at `&3000`
  when E is set, as the Master Reference Manual's F.2-3 says, or follow X, as jsbeeb does? Copies 6 bytes to
  `&DE00` (the manual's `*MOVE` workspace), saving and putting back what was there; main `&3000` = `&11`, shadow
  `&3000` = `&22`, both put back after; interrupts off throughout.

Results (Tom's Master 128, 2026-11-18, photographed): IRRTEST 0 IRQs, then 1 with IRR set (jsbeeb 0); ETEST the same as
jsbeeb, line for line (E ignored while Y is set). `docs/upstream-notes.md` has them.

The disc: `build/hwtests/acctest.ssd`, made from jsbeeb's own tokenising (each program loaded, PAGE to TOP saved) with
the kit's `dfs.py`; `CHAIN "IRRTEST"`, `CHAIN "ETEST"`.

Results, Tom's Master 128, 2026-11-18 (photographed): IRRTEST 0 IRQs with IRR clear and 1 with it set, ACCCON reading
`&88` (jsbeeb: 0 and 0); ETEST the same as jsbeeb line for line, E ignored while Y is set. `docs/upstream-notes.md`
has them in full.
