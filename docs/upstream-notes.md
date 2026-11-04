# Notes for upstream

Things found on this port that might be worth an issue or a PR for the projects it leans on. Nothing here has
been sent anywhere. Tom, 2026-11-04: note them as they come up; at the end of the project, go through them and
decide which would be real improvements for each upstream.

Each note says what was found, how it was checked, and what's still to check. Add to this file whenever a fault,
a gap or a workaround looks like it isn't only this project's.

## beeb-port-kit (`reference/beeb-port-kit`)

### DDRB `&0F` cuts a Master off from its CMOS chip
- **Found** (Tom, on a real Master, 2026-11-04; `ca4de2e`): after the game wrote `&0F` to the System VIA's DDRB,
  the filing system's read of its seek time (`LDY &FE4F`, MOS at `&98C9`) came back `&FF` and the disc stepped at
  the wrong rate. MOS 3.20 writes DDRB once, at reset (`&CF`, ROM offset `&1C034`); PB6-7 drive the CMOS chip.
  DDRA needs no care: every MOS routine sets it first.
- **In the kit**: `template/src/main.6502:383` and `template/examples/vscroll/src/main.6502:355` write `&0F`.
  Harmless where nothing goes back to the OS, and the template doesn't. But `lib/loader.6502` allows for loading
  after the takeover, and the template has a `MASTER=1` path, so a port forked from it that does both meets this.
- **Could be**: a line in `docs/hardware-facts.md`'s memory and VIA tables, and the template leaving DDRB alone
  on a Master. To check: what a Model B's MOS leaves there, so one line can serve both.

### Giving the machine back to the OS after a takeover: colour flashing
- **Found** (`7ef8a09`): the MOS's flash writes its copy of the Video ULA's control (`&248`) to `&FE20`. Run
  during a load after the game has set its own mode, it put the ULA in the MOS's MODE 7 clock, which halved the
  CRTC's: 5 vsyncs in 10 fields. Tom's OSBYTE 9 and 10 with X = 0 stop new flashes; a count in progress when the game
  takes IRQ1V stays frozen (`&251` read 20) and fires in the first load, so OSBYTE 193 with X = Y = 0 clears it.
- **In the kit**: nothing in `docs/hardware-facts.md` or `docs/gotchas.md` on this (searched for flash and OSBYTE 9).
- **Could be**: a hardware fact. Measured in jsbeeb only: worth seeing on real hardware first.

### A worked "load after the takeover"
- `lib/loader.6502`'s header says a load after the takeover is possible, but its contract is the load before it.
  `src/load.6502` and `src/loadcode.6502` here do the whole round trip: zero page `&90`-`&FF` swapped, the VIAs,
  IRQ1V, NMIs (OSBYTE 143's owner kept), BRKV, the load's code run from the blanked screen.
- **Could be**: a `lib/` file or a section of `PORTING.md`. Wait until it's proved on DFS, ADFS, MMFS and Econet
  (Phase 5's step 11).

### `&0900`-`&0AFF` in the memory tables
- `docs/hardware-facts.md` calls `&0A00` the printer buffer. Tom, from the Master Reference Manual: `&0900`-`&0AFF`
  are the tape and serial buffers (D26). To check against the manual before saying the kit's wrong.

### OSWORD 10 after ANDY is overwritten
- **Found** (2026-11-04): with the game's data in ANDY, OSWORD 10 returned 8 zero lines for every character: MOS
  3.20's VDU reads a font workspace there. The kit's ANDY notes (`docs/hardware-facts.md`) list which pages the MOS
  writes; this is the reading side, and a port that owns ANDY and returns to the OS might want the warning. Which
  page it reads wasn't traced: to check before raising.

### Smaller
- A self-patching copy loop that doesn't reset its operands works until it's run a second time (`shared_copy` and
  `load_go` here, 3c). Perhaps a line in `docs/gotchas.md`, if a port's loader is ever re-run.

## jsbeeb and jsbeeb-mcp

**No emulation fault found so far.** jsbeeb reproduced the CMOS read exactly (`&FF` with PB6-7 as inputs), and the
slower loads showed up there before anyone knew why. Tool gaps only:
- **The VIAs' state through the MCP**: DDRA, DDRB, IER, ACR and PCR took `s._machine.processor.sysvia`, jsbeeb's
  internals, from a script. A `read_via` tool, or the registers in `read_registers`, would have shown this at once.
- **A log of hardware register writes**: Tom's instruction log found the `STA &FE42`; the MCP has breakpoints but
  nothing like it. A write-watch on `&FE00`-`&FEFF` would help.
- **`MasterADFS` with no disc**: `run_basic` failed with "did not hit appropriate breakpoint in time". To check: what
  a real Master does there. A clearer message at least, or a way to give it a formatted disc.

## Baron (`rich/baron`)

- **Leaving the call tree for good**: a routine called from deep in the frame that resets the stack and restarts
  from the top reads as recursion ("ZA_AUTO variable freshly written and held live across recursion"). A computed
  jump needs `ZA_CANJUMP` with a target, and `ZA_UNREACHABLE` after it isn't accepted, so there's no way to say
  "this never comes back". Worked round here by setting a flag and jumping from the frame loop's top level, which
  is arguably better code, so this may be nothing. Worth asking Rich only if another case turns up.

## Checked, nothing to raise

- **Rich's projects**: `teddyboy`, `chasehq-beeb` and `exolon-beeb` write DDRB `&0F`, but their OS loads are all in
  `boot.6502`, before the takeover in `entry.6502`, so it doesn't bite; Teddy Boy targets the Model B and knows
  about the flash (`src/boot.6502:102`). `portalc` and `criticalmass` write it too: their loads not read yet.
