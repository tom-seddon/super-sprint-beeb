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

### The rest of the key numbers, the Master's keypad's among them
- **Found** (2026-11-06): `docs/hardware-facts.md` section 7 lists the letters, arrows and a few others, not the digits, most of the
  punctuation, the function keys, or a Master's keypad. A key-redefining screen needs all of them, with a name for each.
- **Checked**: the main keyboard's table is in `tools/screens.py`'s `Matrix`, the keypad's in its `Pad` (Tom's numbers: `&7A` 4, `&7B` 5,
  `&7C` 2, `&6A` 0, `&6B` 1, `&6C` 3, `&5A` #, `&5B` *, `&5C` comma, `&4A` /, `&4B` Delete, `&4C` full stop, `&3A` +, `&3B` -, `&3C` Return,
  `&2A` 8, `&2B` 9, `&1A` 6, `&1B` 7). Tom pressed them on a real Master's options screen, keypad and main keyboard, and each named itself.
  jsbeeb's `keymap.js` has all 19 keypad keys at the same places, so it needs nothing.
- **Could be**: the table added to section 7, with a line that numbers 2-9 are the keyboard's links and read as keys in a scan.

### Code that shares an address but not a bank number
- **Found** (2026-11-07; D31's chain): `harness.mjs` gates a hook on the paging (`romsel`, `andy`, `hazel`) and
  refuses an ungated one in `&8000`-`&BFFF`, after Stryker's Run's false failures. That doesn't reach overlays:
  here the screens' files are all loaded to `&A900` in the same bank, so paging can't tell them apart. A stop in
  the circle's file also fired at the same address in the upgrades' or prepare's. `tools/game_check.mjs`, which
  doesn't use the kit's harness, stops anyway and then looks at `GmFront` to see whether the stop counts. Any
  port with loaded overlays meets this, and only a check with a stop in more than one of them would show it.
- **In the kit**: the gate's comment names "your overlay addresses" for the filing system during boot only.
  Neither `docs/verification.md` nor `harness.mjs` mentions jsbeeb's breakpoint conditions.
- **Could be**: a third gate beside the paging: the bytes at the label are the bytes the build assembled there,
  taken from the file's own build, as a `?PC = ...` condition (tried, see jsbeeb below) or in `gate()`. It needs
  nothing from the game. A byte the game keeps naming its overlay works too, as here, but it's code in the game
  for the check's sake: `LDA #'U':STA GmFront` and `LDA #'P':STA GmFront` in `src/front.6502`, 10 bytes, are read
  by nothing but `game_check`. Bytes need choosing where two files happen to match; not built here yet.

### Smaller
- A self-patching copy loop that doesn't reset its operands works until it's run a second time (`shared_copy` and
  `load_go` here, 3c). Perhaps a line in `docs/gotchas.md`, if a port's loader is ever re-run.

## jsbeeb and jsbeeb-mcp

**No emulation fault found so far.** jsbeeb reproduced the CMOS read exactly (`&FF` with PB6-7 as inputs), and the
slower loads showed up there before anyone knew why. Tool gaps only:
- **The VIAs' state through the MCP**: DDRA, DDRB, IER, ACR and PCR took `s._machine.processor.sysvia`, jsbeeb's
  internals, from a script. A `read_via` tool, or the registers in `read_registers`, would have shown this at once.
- **The MCP's `set_breakpoint` takes less than jsbeeb does**: `address`, `type` (execute, read, write) and `bank`
  only. jsbeeb's own `addBreakpoint` also takes `condition`, `end`, `hitCount` and `action`, the kinds `access`,
  `brk`, `undocumented`, `irq`, `nmi`, `vsync` and `line`, and has `drainBreakpointLog()` (2.18.0,
  `src/machine-session.js`). So the two things below are there from a script and not from the MCP. Passing those
  options through, and a tool to drain the log, looks a small change.
  - **A log of hardware register writes**: Tom's instruction log found the `STA &FE42`. Corrected 2026-11-07: this
    note said jsbeeb had nothing like it. `addBreakpoint("write", 0xFE00, { end: 0xFEFF, action: "log" })` is it,
    tried on `build/game.ssd`: each hit gives the address, PC, value and old value. It keeps the first 10,000
    and counts the rest (45,658 dropped in one run), so it wants draining often.
  - **A stop that depends on memory**: see "Code that shares an address" under the kit. Tried on `build/game.ssd`
    at `front_title`: `?&A45 = 70` stopped there and `?&A45 = 67` didn't in 400M cycles, and `?PC = 169 && ?(PC+1)
    = 244` stopped there and the same with `<>` didn't. `?` reads whatever is paged in, with no side effects, so at
    an execute stop it reads the code being run.
- **`MasterADFS` with no disc**: `run_basic` failed with "did not hit appropriate breakpoint in time". To check: what
  a real Master does there. A clearer message at least, or a way to give it a formatted disc.

## Baron (`rich/baron`)

- **Leaving the call tree for good**: a routine called from deep in the frame that resets the stack and restarts
  from the top reads as recursion ("ZA_AUTO variable freshly written and held live across recursion"). A computed
  jump needs `ZA_CANJUMP` with a target, and `ZA_UNREACHABLE` after it isn't accepted, so there's no way to say
  "this never comes back". Worked round here by setting a flag and jumping from the frame loop's top level, which
  is arguably better code, so this may be nothing. Worth asking Rich only if another case turns up.

- **The kit, or jsbeeb: a load that gives ACCCON back to the OS can show the wrong screen.** A game double-buffering on the
  Master's shadow RAM and restoring the OS's ACCCON for a load inherits its D bit: with the OS showing shadow, the load
  showed the shadow screen, not the main one being written. jsbeeb's Master boots with D clear, so nothing there showed
  it; seen on Tom's Master (2026-11-05: old HUD row stuck, "Loading" unseen), reproduced by setting D in the saved value.
  His had it set, he suspects, because the tool writing his disc selected MODE 135, shadow MODE 7, so any machine or
  tool that boots in a shadow mode will do it. Worth a line in `gotchas.md`, and perhaps a way to boot jsbeeb that way.

## Checked, nothing to raise

- **Rich's projects**: `teddyboy` and `chasehq-beeb` write DDRB `&0F`, but their OS loads are all in
  `boot.6502`, before the takeover in `entry.6502`, so it doesn't bite; Teddy Boy targets the Model B and knows
  about the flash (`src/boot.6502:102`). `portalc` and `criticalmass` write it too: their loads not read yet.
