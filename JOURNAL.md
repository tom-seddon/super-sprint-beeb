# Journal

## 2026-11-01: Phases 1 and 2

### Tools
- `.venv` (git-ignored): Python 3.14 from MacPorts with pillow, numpy and capstone.
- Hatari 2.6.1 at `~/Applications/Hatari.app`. `tools/hatari.sh` runs the original headless: TOS 1.04, the game
  from a write-protected copy of `orig/st`, fast-forward (550-730 VBL/s), `--alert-level fatal` so no dialogs
  appear. TOS 1.02 can't run a program from a folder in Hatari, so `tools/mkst.py` makes a floppy image for
  it.
- `tools/st_disasm.py`: the 68000 disassembly at run-time addresses (text at `&AA56`). Megamax C: far calls
  through a 101-entry jump table, globals off `a4` = `&1F296` (both confirmed in Hatari). 283 functions,
  70,696 of 72,908 text bytes as code, with seeds from a Hatari profile.
- `Makefile`: `make disasm`, `make tracks` (Hatari dumps), `make convert`, `make sheets`, `make viewer`.

### Phase 1: the original
- Traced the OS calls (`--trace gemdos,xbios`) and profiled 600 frames of the attract-mode race. The game uses
  70% of the 8 MHz 68000, about 112,000 of each frame's 160,000 cycles; the car plotter alone is 15%.
- **Mistake: I first wrote that the race runs at 16.7 fps** (3 VBLs a flip). Hatari's trace collapses
  repeated lines unless given `--msg-repeat`, so most race flips were missing and the 3-4 VBL gaps left were
  the screen wipe's. The logic agent measured 1 VBL a flip over 1,469 to 2,600-frame races; with
  `--msg-repeat` the attract race's last 199 flips each have one Vsync. **The race runs at 50 fps.**
- Graphics and data files: `docs/st-graphics.md`. Tracks are 40 × 25 maps of 8 × 8 tiles (decoded for all 11
  maps); cars are 16 × 12 in 16 directions with colour 8 transparent; three 1-bit masks per track (solid,
  road, priority) are built at set-up from the art, line lists and rectangle lists.
- **Mistake: the car sprites' planes are stored 0, 2, 1, 3,** not 0-3 (the plotter's word shuffle). Read the
  wrong way, red and yellow swapped and car 3 came out grey. Found when the logic spec called car 1 red; the
  colours each car drew in a Hatari dump settled it. The Phase 2 car maps were redone after.
- Got each track's finished background by patching the attract race's track argument in Hatari and dumping at
  the set-up's return (`tools/st_dump_tracks.py`; re-run for track 6 gives identical bytes).
- Game logic: `docs/st-logic.md`, by a second agent (about 42 minutes, checked against per-frame traces in
  Hatari). 4 cars always; positions in 1/8 pixel; 16 directions; walls from mask B probed per direction; a
  40 × 25 attribute map for laps, checkpoints, bridges, ramps and pickups; drones on straight-segment paths,
  difficulty by top speed only; 4 laps; tracks in the order 0, 2, 6, 5, 1, 4, 7, 3. It also found how to drive
  the original from the debugger (pokes to start a game and hold keys).

### Phase 2: colours
- `tools/convert.py`: per-colour maps (solid, checkerboard or 2 × 2), per-car maps, MODE 1 cell order. Six
  options: A, A2, B, B2, C, D (`docs/colours.md`).
- On jsbeeb (Master): 26 rows from `&3F00` with the HUD row works as planned; converted bytes match the PNGs.
- No HUD palette split is needed: the HUD's colours are the cars', which are in the play area's palette.
- First attempt at option A showed the cars losing their black outlines on the black road. A2 draws the
  cars' black as a grey checkerboard: every car reads clearly, and drones are hollow outlines.
- Packed (ZX02): 8 tracks 19,262 bytes (A) to 20,763 (D); masks 5,525 (road) and 4,145 (priority).
- Proposed A2 for D1; B is the alternative.
- **D1 decided: option B.** Tom looked at the viewer discs on a real BBC: on a CRT the checkerboard road reads
  as grey and isn't too busy. I had judged it busy from the PNGs, which show every pixel sharp; the real
  display is the test. B's tracks pack to 20,754 bytes for all 8, 1,492 more than A.

## 2026-11-01: D3, loading through the OS
- **D3 decided:** one track's data per race, loaded through OSFILE, so the game works on MMFS, Econet and any
  other filing system. The 1770 loader is dropped.
- Proposed D7 for how: swap the OS's memory back in for each load, as Chase HQ's P5, with the Master's extra:
  the filing systems' workspace is in HAZEL. Up to 10,352 bytes of a bank for the OS's copy. HAZEL's claimed size
  per filing system and the MOS's use of ANDY are to be measured in Phase 3.
- D4 in part: the game needs 4 free banks of sideways RAM (Tom). A filing system loaded into sideways RAM
  isn't supported; `!BOOT` says so.
- **Mistake: I wrote D7's cost as about 12K.** The areas it lists add up to 10,352 bytes at most: zero page
  `&90`-`&FF` (112), `&0200`-`&03FF` (512), `&0800`-`&0DFF` (1,536) and all of HAZEL (8,192). Tom asked what
  the other 4K was; there wasn't any.
- D7 revised after Tom asked whether the game needed HAZEL or it was kept just in case: just in case. Now
  the game leaves HAZEL, ANDY and the OS's low pages alone, puts its big and unrolled code in the banks
  beside its data, and swaps only zero page `&90`-`&FF` (112 bytes) around a load. The bank swap is the
  fallback if Phase 3 runs out of room.
- **D7 decided** (Tom): leave the OS's memory alone for now. If more room is needed, HAZEL (8K in one piece)
  is worth swapping through a bank; the OS's 2K of low pages isn't, being fragmented.
- **D5 decided in part** (Tom): any player can be on the keyboard, all three included, since joysticks
  weren't common on the BBC; joysticks stay an option. Ghosting is left until later.
- **D4 decided** (Tom): the Master 128 only. So CMOS opcodes are allowed (`cmos = TRUE`; Baron assembles the
  65C12's set and refuses the Rockwell bit opcodes, which the Master lacks), overriding the skill's NMOS-only
  rule; noted in `CLAUDE.md`.
- **D2 decided** (Tom): 50 fps is the goal, as the ST, for the difference it makes on a CRT. 40,000 cycles a
  frame against an estimate of about 42,000; the main loop counts vsyncs so an overrun costs one frame, not
  the game's speed.

## 2026-11-01: Phase 3, the renderer test

- `tools/st_trace_cars.py`: the ST's attract race on track 6 recorded in Hatari, 1,144 frames (draw order;
  per car x, y, facing, flags) from a breakpoint on the flip.
- `src/`: the first 6502, in Baron, after Chase H.Q.'s layout (boot, sprint, entry, irq, main, cars, erase,
  memory, constants, macros), CMOS opcodes allowed (D4). `make beeb` builds `build/sprint.ssd`; `make check`
  runs it in headless jsbeeb's Master 128 (`tools/render_check.mjs`) against `tools/render_model.py`.
- All 1,144 frames match the model. Broken on purpose the check fails (priority off: 282 frames wrong; an
  erase skipped: 96 of 100), and passes again once restored.
- Each car's frames use at most three colours, so the fourth is a transparent key: no mask bytes, two
  256-byte tables.
- First version 15,518 cycles a frame on average (erase 5,213, plot 10,094), 21,251 at worst. With the
  columns unrolled (a line of every column a loop pass, operands patched once a band) and each
  frame-shift in a page: 12,311 (erase 3,682, plot 8,418), 20,822 at worst. Priority costs about 1,670 a
  frame on average, about 8,300 at worst; every swap came one vsync after the last.
- The cars' bank is full (57 bytes free): frames 10,615, priority 3,664, tables 1,152, plotter 732. The
  priority expansions moved to main RAM to make room.
- Profiled by region (`tools/render_profile.mjs`): in the worst 20 frames every car was under a bridge and
  the slow loop took 13,900 of 20,223 cycles. Most of its bytes were in cell lines wholly hidden or not
  hidden at all. Each 8 x 8 cell now has a class per half (none, all, some hidden): hidden columns draw into
  a Junk area, clear ones stay in the fast loop, only mixed ones take the slow loop. 11,641 a frame on
  average, 16,689 at worst (was 12,311 and 20,822); every frame still matches the model.
- To fit, the priority map is stored as each row's span padded by 2 cells (643 bytes, was 1,000), the frames
  moved to the bank's start (no alignment), and the frame-shift's column and width share a byte.
- **Mistakes on the way**, both caught by the model check (every frame wrong, some taking 145,000 cycles):
  the page-crossing path's loop left X changed where the row was expected, and the column loop started with
  X holding the cells' OR rather than 0.
- The erase's blocks indexed by X from the cell's low byte, each operand 8n into the page: only the high
  bytes patched a band, no page-crossing path. Erase 3,682 -> 3,134 a frame. The data table's page patched
  only when it changes: 23 cycles. 11,071 a frame on average, 16,259 at worst; every frame matches.
- Stopped there: what's left is spread thin (per car, per band), and the bigger changes weighed (compiled
  sprites, the plot's screen indexed by X) cost memory the banks don't have, or more than they save.
