# Notes for upstream

Things found on this port that might be worth an issue or a PR for the projects it leans on. Nothing here has
been sent anywhere. Tom, 2026-11-04: note them as they come up; at the end of the project, go through them and
decide which would be real improvements for each upstream.

Each note says what was found, how it was checked, and what's still to check. Add to this file whenever a fault,
a gap or a workaround looks like it isn't only this project's.

**Checked against each upstream's latest, 2026-11-17**, before going through them with Tom (the plan's "At the end of
the project"): none of the notes below is dealt with there yet, so each still stands as written.
- The kit: `origin/master` at a460d4e, two commits after the submodule's 341c985 (2026-11-14, from two Amstrad CPC
  demo ports): `docs/hardware-facts.md` +89 lines, `docs/gotchas.md` +105, `PORTING.md` +32, nothing on DDRB, the
  flash, `&0900`-`&0CFF`, OSWORD 10, the keypad, an empty socket, ADFS's disc id or ROMSEL's reading (`git grep` of
  each). One new gotcha is near ours on overlays (below). The submodule not moved.
- jsbeeb-mcp 4.5.0 (2026-11-08; pinned here 4.3.0) and jsbeeb 2.23.0 (pinned 2.18.0), read from their npm packages:
  `set_breakpoint` still takes `address`, `type` and `bank` alone, no tool reads the VIAs, an empty socket's read and
  the disc's starting place unchanged in `6502.js` and `disc-drive.js`. New since: stepping back (`step_back`,
  `reverse_continue`, `who_wrote`) and sideways ROMs placed by bank (`create_machine`'s `bank_roms`, which would
  make the bank probe's layouts easier to set up). `MasterADFS` with no disc not run again.
- Baron: `rich/baron`'s 4f71e73 is its remote's latest. Hatari: v2.6.1 is still its latest release (its `main` not
  read for the prompt).

Then the Master Reference Manual (`reference/`), read against the kit's latest docs the same day: "From the Master
Reference Manual", at the end, and a line added to several notes below.

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
- **The manual**: a CMOS byte read as `&FF` is FDRIVE 7: 30 ms a step on a 1770, but 3 ms on a 1772 (C.5-4), so the
  same fault on a 1772 board would step too fast, not too slow.

### Giving the machine back to the OS after a takeover: colour flashing
- **Found** (`7ef8a09`): the MOS's flash writes its copy of the Video ULA's control (`&248`) to `&FE20`. Run
  during a load after the game has set its own mode, it put the ULA in the MOS's MODE 7 clock, which halved the
  CRTC's: 5 vsyncs in 10 fields. Tom's OSBYTE 9 and 10 with X = 0 stop new flashes; a count in progress when the game
  takes IRQ1V stays frozen (`&251` read 20) and fires in the first load, so OSBYTE 193 with X = Y = 0 clears it.
- **In the kit**: nothing in `docs/hardware-facts.md` or `docs/gotchas.md` on this (searched for flash and OSBYTE 9).
- **Could be**: a hardware fact. Measured in jsbeeb only: worth seeing on real hardware first.
- **The manual**: OSBYTE 9 with X = 0 "sets an infinite duration and forces the mark state" (D.2-22), so it may write
  `&FE20` when called (harmless before the game sets its ULA, as here); OSBYTE 154 writes the register and `&248`
  together and resets the flash counter (D.2-46), so calling it re-arms the flash unless 9 and 10 are 0. What a count
  of 0 means (OSBYTE 193, D.2-59) it doesn't say: our jsbeeb measurement stands.

### A worked "load after the takeover"
- `lib/loader.6502`'s header says a load after the takeover is possible, but its contract is the load before it.
  `src/load.6502` and `src/loadcode.6502` here do the whole round trip: zero page `&90`-`&FF` swapped, the VIAs,
  IRQ1V, NMIs (OSBYTE 143's owner kept), BRKV, the load's code run from the blanked screen.
- **Could be**: a `lib/` file or a section of `PORTING.md`. Proved since on DFS and ADFS L (Tom's Master 128 and a
  Compact), MMFS and a hard disc in b2, and BeebLink (Phase 5, 2026-11-08); Econet never run (only ANFS's logon
  refused in jsbeeb, D26).

### `&0900`-`&0AFF` in the memory tables
- `docs/hardware-facts.md` calls `&0A00` the printer buffer. Tom, from the Master Reference Manual: `&0900`-`&0AFF`
  are the tape and serial buffers (D26). **Checked** (2026-11-17, `reference/Master_Reference_Manual_Part_1.pdf`,
  section F.6, pages F.6-3 and F.6-4): the printer buffer is `&0880`-`&08BF`; `&0900`-`&09BF` the RS423 output
  buffer, part of the cassette's output buffer, or envelopes 5-16; `&09C0`-`&09FF` the speech buffer or the rest of
  the cassette's output; `&0A00`-`&0AFF` the RS423 or cassette input buffer; each free "if" its uses aren't. So on a
  Master the kit's table (line 811 at a460d4e, "`&0A00` | printer buffer") and its line 596 ("`&0800-&0BFF` (sound,
  serial, soft keys)") are wrong. The Model B's map isn't in this manual: from memory the same for `&0A00`, not
  checked.
- Its table gives `&0B00`-`&0BFF` (soft keys) and `&0C00`-`&0CFF` (user-defined characters) as free once the MOS
  is gone or not printing: the Model B's map. Tom, 2026-11-09: "On the Master 128, this is tagget as Econet
  workspace." And: "The $b00...$cff region is documented in one of the Master reference manuals, so it's an
  official Acorn guideline I guess!" jsbeeb's DFS and ADFS left both pages alone, which says nothing about Econet
  (D26). **Checked** (the same page): "&0B00–&0CFF Econet workspace. ... should not be used by programs which might
  possibly be run in a network environment. Note that this area of the memory map was used for other purposes in
  previous BBC microcomputer systems." Page 13 likewise: `&0D00`-`&0D5F` the NMI routine, `&0D60`-`&0D7F` Econet's,
  `&0D80`-`&0D91` unallocated, `&0D92`-`&0D9E` the trackerball's, `&0D9F`-`&0DEF` the expanded vectors, `&0DF0`-`&0DFF`
  the ROMs' workspace bytes. **Could be**: the kit's table split by machine, a Master's column from F.6. (This
  project's own plan and `src/memory.6502` had called `&0B00` the soft keys and font too, the Model B's: corrected.)

### A load that gives ACCCON back to the OS can show the wrong screen
- **Found** (the kit, or jsbeeb; filed under Baron till 2026-11-17): a game double-buffering on the
  Master's shadow RAM and restoring the OS's ACCCON for a load inherits its D bit: with the OS showing shadow, the load
  showed the shadow screen, not the main one being written. jsbeeb's Master boots with D clear, so nothing there showed
  it; seen on Tom's Master (2026-11-05: old HUD row stuck, "Loading" unseen), reproduced by setting D in the saved value.
  His had it set, he suspects, because the tool writing his disc selected MODE 135, shadow MODE 7, so any machine or
  tool that boots in a shadow mode will do it. Worth a line in `gotchas.md`, and perhaps a way to boot jsbeeb that way.
- **The manual**: `*CONFIGURE MODE 128`-`135` makes every boot shadow (C.5-4), after the next CTRL+BREAK or power-on
  (C.5-2), so a disc tool isn't needed; `*SHADOW` (on with no number or 0, C.5-11) and OSBYTE 114 act at the next mode
  change. The kit's `*SHADOW` then soft BREAK (`hardware-facts.md` line 680, ACCCON `&1B`) is a way in jsbeeb.
  OSBYTE 117 bit 4 and 239, 250, 251 (D.2-32, D.2-78, D.2-82/83) read the shadow state; VDU variable `&55` doesn't
  tell 7 from 135 (E.4-2).

### OSWORD 10 after ANDY is overwritten
- **Found** (2026-11-04): with the game's data in ANDY, OSWORD 10 returned 8 zero lines for every character: MOS
  3.20's VDU reads a font workspace there. The kit's ANDY notes (`docs/hardware-facts.md`) list which pages the MOS
  writes; this is the reading side, and a port that owns ANDY and returns to the OS might want the warning. Which
  page it reads wasn't traced: to check before raising.
- **Answered** (the manual, F.6-10 and E.4-5): `&8900`-`&8FFF` is the "soft font", the current definitions of
  characters 32-255, character n at `&8900 + 8(n - 32)`; the ROM's copy is at `&B900`-`&BFFF`. This project's
  `tools/break_check.mjs` already reads that range as the font (MEASURED: a soft BREAK doesn't make it again, so
  `entry.6502` sets OSBYTE 200 for a hard one). OSBYTE 25 with X = 0 restores 32-255 (D.2-28; OSBYTE 20 only
  32-126 on a Master, D.2-26): not tried. So the kit's ANDY table is wrong where it calls `&89`-`&8E` free to a game
  that keeps the MOS's text (below).

### The rest of the key numbers, the Master's keypad's among them
- **Found** (2026-11-06): `docs/hardware-facts.md` section 7 lists the letters, arrows and a few others, not the digits, most of the
  punctuation, the function keys, or a Master's keypad. A key-redefining screen needs all of them, with a name for each.
- **Checked**: the main keyboard's table is in `tools/screens.py`'s `Matrix`, the keypad's in its `Pad` (Tom's numbers: `&7A` 4, `&7B` 5,
  `&7C` 2, `&6A` 0, `&6B` 1, `&6C` 3, `&5A` #, `&5B` *, `&5C` comma, `&4A` /, `&4B` Delete, `&4C` full stop, `&3A` +, `&3B` -, `&3C` Return,
  `&2A` 8, `&2B` 9, `&1A` 6, `&1B` 7). Tom pressed them on a real Master's options screen, keypad and main keyboard, and each named itself.
  jsbeeb's `keymap.js` has all 19 keypad keys at the same places, so it needs nothing.
- **Could be**: the table added to section 7, with a line that numbers 2-9 are the keyboard's links and read as keys in a scan.
- **The manual** (D.2-34/35, and F.3-1's matrix, row × 16 + column) has every key's internal number, and agrees with
  all 19 of Tom's keypad numbers: a source to cite. Its row 0 holds only SHIFT and CTRL, so "2-9 are the links" is
  the Model B's: what a Master reads there is to measure.

### Code that shares an address but not a bank number
- **Found** (2026-11-07; D31's chain): `harness.mjs` gates a hook on the paging (`romsel`, `andy`, `hazel`) and
  refuses an ungated one in `&8000`-`&BFFF`, after Stryker's Run's false failures. That doesn't reach overlays:
  here the screens' files are all loaded to `&A900` in the same bank, so paging can't tell them apart. A stop in
  the circle's file also fired at the same address in the upgrades' or prepare's. `tools/game_check.mjs`, which
  doesn't use the kit's harness, first stopped anyway and then looked at `GmFront`, a byte the game keeps, to see
  whether the stop counted. Any port with loaded overlays meets this, and only a check with a stop in more than one
  of them would show it.
- **In the kit**: the gate's comment names "your overlay addresses" for the filing system during boot only.
  Since (a460d4e, 2026-11-14, not in the submodule): `gotchas.md` class 5, "With code in two sideways banks at
  `&8000`, an address hook fires in both", from Isometrikum: gate on ROMSEL and on the boot. That's the banks' case;
  files loaded over each other in one bank, this one, still isn't there.
  Neither `docs/verification.md` nor `harness.mjs` mentions jsbeeb's breakpoint conditions.
- **Done here since** (2026-11-07): `fileGate` in `tools/jsbeeb.mjs` finds the label's section and file in the
  symbols, reads the file's bytes off the disc, and returns a jsbeeb condition on the bytes at `PC`: four, or more
  until they differ from every other file loaded to the same address that covers it (16 at most, or it throws).
  It needs nothing from the game: two stores the game made only for the check (`LDA #'U':STA GmFront` and the
  same for `'P'`, 10 bytes of the front end's code) went.
- **Could be**: a third gate in `harness.mjs` beside the paging, from the same idea: the bytes the build
  assembled at the label, as a condition or in `gate()`.

### Finding sideways RAM: an empty socket can pass
The recipe (`beeb-baron`'s `hardware.md` §2 step 2 and §7: for X = 15 down to 0, EOR `&8000` with `&FF`, store,
compare) calls a bank RAM when its second read differs from its first, not when it reads back what was written, and
runs while MODE 7's boot screen is up. Tom (2026-11-09): the Master's data bus isn't buffered, so an empty socket
reads the last byte the video read: a space mostly, a letter of the banner now and then, so the two reads can
differ and an empty socket pass. On a stock Master bank 8 is such a socket, and was probed first here. Tom's one
boot that printed "Loading" and then characters 128-255 and hung (2026-11-09) fits a bank 8 taken for RAM, but it
isn't proven: jsbeeb's empty socket reads 0 every time, and 770 jsbeeb boots with junk RAM and the disc's timing
moved (`tools/seed_check.mjs`) all ran. Fixed here: banks 7 to 0 only (8-15 are the Master's ROMs), probed with
the shadow screen MODE 129 just cleared on show, and a bank counted only if it reads back the `&FF` EOR written.
Worth a line in the recipe and in `gotchas.md`.
The manual: banks 0-3 are the cartridges', 8 the empty socket IC27, 9-15 the built-in ROM, 4-7 the RAM (F.2-1/2),
LK18 giving banks 4-5 and LK19 6-7 (F.5-5); OSBYTE 68 returns which of 4-7 the links make RAM (`&0F` on a standard
machine, D.2-28), banks 0-3 not covered. Whether it reads the links or tries the RAM, and what a Compact returns, to
measure.

### ADFS knows a changed floppy by its id alone
- **Found** (2026-11-17, in jsbeeb's Master 128, ADFS from MOS 3.20; Tom asked how the `.adl` discs' ids are made):
  after a swap (the motor stopped first, as a person's), ADFS said "Disc changed" only when the free space map's id
  (`&1FB`-`&1FC`) differed. A disc with the same id but another directory, or another map, went unnoticed: `*INFO`
  and `*CAT` gave the first disc's catalogue. ADFS writes a new low byte on every map write (a `*SAVE`, a file
  overwritten too), depending on timing (`&5350`, then `&91 &DA &A0 &23`, or `&15 &D4 &A3 &41` with pauses
  between): the high byte stays. So two discs from one image, once written, share an id about 1 time in 256, and a
  write after an unmounted swap uses the other disc's map and directory. `*MOUNT` reads both again.
- **Here**: `tools/adfs_disc.py` gives every disc `&5350`; every copy of a release's image starts the same however
  it's chosen. MERGE (time attack's merger, a disc swap at its prompts) says to `*MOUNT` after changing discs on
  ADFS (Tom's wording).
- **In the kit**: nothing on ADFS's disc id in `docs/hardware-facts.md` or `docs/gotchas.md`. **Could be**: a
  gotcha for a port that asks for a disc swap on ADFS (a save disc, a second side). Not seen on real hardware, or
  on the Compact's ADFS.
- **The manual** (`reference/Master_Reference_Manual_Part_1.pdf`, checked 2026-11-17): J.10-2 names sector 1's bytes
  251-252 "Disc identifier", nothing on how it's made or used; J.8's "Disc changed" (error 200) is "a discrepancy
  between the current disc and catalogue information held in RAM"; `*MOUNT` (J.7) "reads the free space map and the
  root directory catalogue into memory". So that the id alone decides it is ours to measure, as above, and worth
  the gotcha. The manual disagrees with itself on its number: 208 in J.8-3's list, 200 (`&C8`) in J.8-5's table (and
  DFS's, J.4). `*DISMOUNT` "normally prior to changing discs" (J.7-7) is its own advice.

### Smaller
- A self-patching copy loop that doesn't reset its operands works until it's run a second time (`shared_copy` and
  `load_go` here, 3c). Perhaps a line in `docs/gotchas.md`, if a port's loader is ever re-run.
- ROMSEL's readability: the `beeb-baron` skill's `hardware.md` (lines 136 and 318) says `&FE30` is write-only, with no
  model named; the kit's `hardware-facts.md` (line 709) rightly says "on a Model B". Tom, 2026-11-10: "ROMSEL isn't
  readable on the B or B+, but it can be read on the Master. ACCCON is also readable." I'd repeated the skill's
  line to him. Not measured here. Also his, worth a line beside it: "by the time the BRK routine has been called,
  the MOS has paged in the current language ROM", saving `&F4` as it was in `&024A`, so a BRK handler can't learn the
  bank from ROMSEL, and `&024A` is only right if the code kept `&F4` in step.

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
- **Empty sockets and the floating bus**: an empty ROM socket reads 0 in jsbeeb (2.18.0, Master: bank 8 checked),
  where a real Master reads the last byte the video read (Tom, 2026-11-09), so a probe fooled by that (see the
  kit's "Finding sideways RAM") can't be seen there.
- **Every boot keeps the same time**: the disc turns from power-on in step with the fields, near enough, and every
  load waits for it, so a delay before a load is lost: two boots 80,000 cycles apart at `!BOOT`'s start reached
  SPRINT on the same cycle. A real drive's turning has nothing to do with the video. `tools/seed_check.mjs` turns
  it by hand (`fdc._drives[0].positionFraction`); an option to start the disc at a random place would do.
- **`MasterADFS` with no disc**: `run_basic` failed with "did not hit appropriate breakpoint in time". To check: what
  a real Master does there. A clearer message at least, or a way to give it a formatted disc.

## Baron (`rich/baron`)

- **Leaving the call tree for good**: a routine called from deep in the frame that resets the stack and restarts
  from the top reads as recursion ("ZA_AUTO variable freshly written and held live across recursion"). A computed
  jump needs `ZA_CANJUMP` with a target, and `ZA_UNREACHABLE` after it isn't accepted, so there's no way to say
  "this never comes back". Worked round here by setting a flag and jumping from the frame loop's top level, which
  is arguably better code, so this may be nothing. Worth asking Rich only if another case turns up.

## Hatari

### The debugger's prompt runs into a quiet breakpoint's first dump
- **Found** (2026-11-10, Linux Mint 22.3, `docs/brief-ci-hatari-2026-11-10.md`): each breakpoint that isn't a
  trace enters the debugger loop (`DebugUI()`, `src/debug/debugui.c`), which prints the prompt `> ` and reads
  stdin, here `/dev/null`. With `:quiet :file`, 2.5.0 and later print nothing between, so the file's first output
  lands on the prompt's line (`> 0001D30E: 00 51`). Seen in Hatari 2.6.1 built from source with GNU readline and
  without readline (then `fprintf(stderr, "> ")`, line 916). The Mac's 2.6.1 doesn't (its traces have no lines
  missing), presumably libedit printing no prompt when stdin isn't a terminal: not checked there.
- **Here**: the tracers now take a leading `> ` (`7c2e218` on that branch).
- **Could be**: no prompt when stdin isn't a terminal, or a newline after it before other output. To check
  first: Hatari's latest release, and the Mac's build (`--parse` with stdin from `/dev/null`).

### 2.4.1's `memdump` prints whole lines (fixed in 2.5.0)
- `m ADDR N` gives whole 16-byte lines in 2.4.1, the Ubuntu 24.04 package (so GitHub's `ubuntu-latest`); the
  tracers count the bytes. Fixed upstream in 2.5.0 ("memdump command always outputs only requested number of
  items", its release notes). Nothing to raise; noted for anyone using a distribution's Hatari.

## From the Master Reference Manual

Read 2026-11-17 against the kit's latest docs (a460d4e; line numbers there), by five agents, one a group of sections
(Part 1's C, D.1-D.2, D.3-D.10 and E.4-E.5, F, G and J; Part 2's N.4 and O.4), each finding's quotes then checked in
the manual's text by hand. The manual is the Master's alone, so a kit line it contradicts may be right for a Model B;
and the manual can be wrong, so "to measure" where it matters. The answers to the notes above are under each.

### The kit: wrong, or the Model B's, on a Master
- **ANDY** (`hardware-facts.md` 546-560, `PORTING.md` 215-217: `&81`-`&87` and `&89`-`&8E` "always" free; a game
  keeping the MOS's text "has `&89`-`&8E`"). F.6-10 and E.4-5: `&8000`-`&83FF` the soft keys' buffer (four pages),
  `&8400`-`&87FF` VDU workspace (flood fills), `&8830`-`&88BF` VDU workspace, `&88C0`-`&88FF` reserved, `&8900`-`&8FFF`
  the soft font, read by every character the MOS prints in MODEs 0-6 (OSWORD 10 above). So free only to a game that
  never prints, fills or expands a key through the MOS. To measure: what a long `*KEY` and a fill write.
- **The low pages' table** (§6, 836-846): `&0A00` "printer buffer" (above); `&0E00`-`&18FF` the DFS's, PAGE `&1900`, are
  a Model B's (a Master's OSHWM is normally `&0E00`, N.4-3, D.2-40: OSBYTE 131 or 180 reads it, which the kit's "read
  OSHWM" never names); `&0100`-`&017F` "untouched" is from loads that worked, where ROMs build their error text
  (F.6-2, N.4-3); `&B0`-`&CF` "after OSBYTE 140" splits: `&B0`-`&BF` the filing system's scratch, free between its
  calls (beware hidden ones, `*SPOOL`), `&C0`-`&CF` kept (F.6-2); `&DF00`-`&DFFF` (599) the MOS's, not the DFS's
  (F.6-11); the soft keys and characters at `&0B00`/`&0C00` (626, 840, 842) are in ANDY on a Master (F.6-10).
- **Loads with interrupts masked** (896-909): every filing system call, OSCLI, OSRDCH and OSWRCH "preserves" the
  interrupt status but interrupts "may be enabled during the call" (J.11-2 to J.11-11, D.4-1, D.5-1, D.7-1). The I
  flag after a load doesn't show the load ran masked; Acorn's DFS may, as a fact of that DFS. To measure on ADFS
  and MMFS.
- **FDRIVE** (1090-1093: CMOS byte 11 bits 1-0, 6/12/20/30 ms on a 1770, 6/12/2/3 on a 1772): C.5-4 gives values
  0-7, 6 ms on both for 0, 1, 4, 5 and 30 ms (1770) or 3 ms (1772) for 2, 3, 6, 7, the odd ones without ADFS's
  precompensation. The kit's figures are the 177x's own step bits; how the DFS turns one into the other, and its "byte
  11 reads `&25`" as FDRIVE 0, to measure.
- **`&FE20`-`&FE3F` at 2 MHz** (288-296, from KC and jsbeeb): F.6-8 lists VIDPROC (`&FE20`) and the 1770 (`&FE28`) as
  1 MHz, `&FE24`, ROMSEL, ACCCON and INTOFF/INTON as 2 MHz. jsbeeb 2.18.0's `is1MHzAccess` has all of `&FE20`-`&FE3F`
  at 2 MHz. To measure on a Master (it bears on `&FE21` loops and qdisc's 35.4 cycles a byte).
- **OSBYTE `&7A` with no key** (1144: "documented as X = 0 (NAUG)", jsbeeb 255): the manual says 255 (D.2-35/36), as
  jsbeeb does. The NAUG's line not checked.
- **The BREAK intercept** (1046-1048, `JMP (&FFFC)`): D.2-82 has it entered twice a BREAK, C set then clear, and
  returning by RTS. The kit's measured way breaks that on purpose; worth saying so.
- **Banks without the links** (`PORTING.md` 676, "two"): LK18 gives banks 4-5 and LK19 6-7 (F.5-5), so 0, 2 or 4.
- **MODE 1 at R8 = 1** (201): only with interlace on; `*TV` or `*CONFIGURE TV`'s second number 1 turns it off
  (C.5-5, C.5-13), and `*CONFIGURE TV` without it means 0, on.

### The kit: not there, would change code
- **ACCCON's top bits** (F.2-3): IRR (7) set raises an IRQ, TST (6) must be 0, IFJ (5) sends `&FC00`-`&FDFF` to the
  cartridges, ITU (4) picks the internal or external second processor. The kit's "compose every write" (514) could say
  to carry IFJ and ITU from the OS and keep 7 and 6 clear (as `entry.6502` and `load.6502` keep only `&30`). jsbeeb's
  `writeAcccon` raises no IRQ for IRR, so a stray bit 7 shows only on hardware.
- **The E bit** (F.2-3): code fetched from `&C000`-`&DFFF` sees shadow at `&3000`-`&7FFF`, with no exception for Y.
  jsbeeb applies E only while Y is clear (code in HAZEL follows X). A port running code from HAZEL (1942's) with E set
  by a shadow boot would differ: to measure.
- **Where the extra 32K is** (F.2-4): ANDY, HAZEL and the shadow screen are one RAM, D adding `&8000` to the video's
  address, so with D set a CRTC address below `&3000` shows ANDY or HAZEL (the kit's line 487, explained).
- **The Master's I/O map** (F.6-8/9): the ADC at `&FE18`-`&FE1A` (a B's `&FEC0`), drive control `&FE24`, the 1770
  `&FE28`, INTOFF/INTON `&FE38`/`&FE3C`; ROMSEL's bits 4-6 zero; banks 0-3 the cartridges', 8 the empty IC27, 9-15
  the ROM (F.2-1/2). OSBYTE 68 says which of 4-7 the links make RAM (D.2-28).
- **Filing systems**: OSFILE's save writes back too, the length at XY+10 and the attributes at XY+14 (J.11-9; the kit
  875 has the load's), so a block saved twice needs its addresses again; ADFS keeps its map and directory,
  checksummed, in HAZEL ("Bad sum" 170, "Bad FS map" 169, cleared only by a hard BREAK, J.8-1, J.10-2/3), where the
  kit's HAZEL window is the DFS's; OSWORD `&70`'s status bit 0, "File ensuring in progress (IRQ pending)" (J.11-12):
  ADFS can finish a write from an interrupt after the call returns, so a game taking IRQ1V straight after a save
  could cut it off (to measure); a save's errors, by number: 201 write-protected on both (DFS "Disc read only", ADFS
  "Disc protected"), DFS "Cat full" 190 (31 files), ADFS "Dir full" 179 (47 entries), "Map full" 153, "Compaction
  required" 152 (J.4, J.8, J.10-4); `*CONFIGURE NODIR` leaves ADFS with no directory, a load failing "No directory"
  (J.7); a bank is loaded by `*SRLOAD` or OSWORD `&43` (G.7-3, G.7-8), code in the DFS ROM, bank 9, so gone if that's
  `*UNPLUG`ged, even on ADFS (the kit's 938, OSFILE can't, still holds).
- **Settings and the test matrix** (C.5): `*CONFIGURE` acts at the next CTRL+BREAK or power-on (C.5-2), `*UNPLUG` and
  `*INSERT` too, so the ROM table at `&02A1` a probe reads is the last hard reset's (C.5-8, C.5-10, C.5-14); ROMs'
  workspace in main RAM raises PAGE (C.5-13/14). Rows worth having: `MODE 135`, `BOOT` (BREAK and SHIFT+BREAK
  swapped, C.5-3), `FILE` set to ADFS, `LANG` not BASIC, `TV 255,0` and `TV 0,1`, `TUBE`/`NOTUBE`, extra ROMs.
- **Smaller**: the VDU's zero page is `&D0`-`&E1`, `&E0`-`&E1` the Master's own (E.4-4); MODE 7 through OSWRCH swaps
  `#`, `_` and `£` (35, 95, 96, E.5-1), which code writing `&7C00` itself must do too; OSBYTE 121 and 122 put the keys
  they see in the input buffer (D.2-35); OSBYTE 234 tells of a Tube (D.2-76); OSBYTE 117 bit 4 and 239, 250, 251
  read the shadow state (D.2-32, D.2-78, D.2-82/83); `STA &F4` before `STA &FE30` when paging ANDY (E.4-9) confirms
  the kit (776). The 65C12 (O.4): no RMB/SMB/BBR/BBS, no WAI/STP, no cycle counts: nothing new.

### jsbeeb
- `&FE20` (VIDPROC) and `&FE28` (the 1770) at 2 MHz, where F.6-8 says 1 MHz (above).
- ACCCON: no IRQ for IRR; E not applied while Y is set (above). Both from 2.18.0's `6502.js`; 2.23.0's
  `writeAcccon` and `is1MHzAccess` are the same (diffed).

### This project (none urgent)
- `SCORES` on ADFS: whether a save leaves OSWORD `&70`'s ensuring bit set when the game takes IRQ1V back; and
  "Compaction required" or "Map full" on a fragmented disc, which `src/save.6502` treats as any failed save (said in
  the HUD's row, not tried again till something changes).
- `loadcode.6502` gives the OS its ACCCON with D and X cleared but E kept, so any text the MOS printed during a load
  would go to shadow: harmless, as the game's BRKV says a disc error itself.
- `!BOOT` at `&2000`: a Master's OSHWM is `&0E00` but ROMs taking main RAM raise it; ANFS or third-party ROMs could be
  tried. `*CONFIGURE BOOT` (BREAK boots the disc) and `FILE` set to ADFS with the DFS disc are untried.

## Checked, nothing to raise

- **Rich's projects**: `teddyboy` and `chasehq-beeb` write DDRB `&0F`, but their OS loads are all in
  `boot.6502`, before the takeover in `entry.6502`, so it doesn't bite; Teddy Boy targets the Model B and knows
  about the flash (`src/boot.6502:102`). `portalc` and `criticalmass` write it too: their loads not read yet.
