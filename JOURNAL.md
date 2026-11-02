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
- **The HUD row** (D6): 40 characters from an 8 x 8 font of 15 glyphs (`tools/font.py`), each player's 6-digit
  score and laps in their car's colour, then the track and the drone's laps. The trace now records the ST's
  scores and laps; their 78 changes go into the trace's bank as events. Each screen keeps what it shows and
  catches up a few characters a frame (at most 4), so a score rolling over can't cost a frame: 98 cycles a
  frame on average, 2,076 at most (was 5,556 before the cap). The model follows the same rule; every frame
  matches, HUD row included, and swapping two players' colours fails it.
- The ST's HUD shows laps completed (its drone digit's glyphs are indexed by `G_01E354` directly).
- **Mistake: a stale screenshot.** After a breakpoint stops jsbeeb's `runFor`, the next `runFor` also runs the
  cycles the stopped runs had left, so "frame 700 plus 20,000 cycles" was about 1,000 frames later, the race
  wrapped round. `tools/screenshot.mjs` stops at breakpoints only; both screenshots were retaken.

## 2026-11-01: Phase 3, objects (under way)

- D8 decided (Tom): the explosion and the helicopter snapped to 4-pixel steps. (The ST already draws the
  helicopter on 16-pixel steps.)
- `tools/st_trace_objects.py`: a real race in Hatari (a one-player game started by the pokes, the race's track
  and race counter poked at `F_00C592`'s entry), every call of the car plotter and the object routines logged
  with its arguments (Hatari's `m a7` dumps the stack). Track 5 as race 17: gates, barriers, pickups, the
  banner, sparks, a wreck at frame 80 with its explosion and the helicopter.
- The ST draws a background object into the screen being drawn and the clean background, and calls it
  again the frame after for the other screen. Gates and barriers write mask C too: the priority around them
  changes in the race.
- **Mistake: the track dumps missed tracks 5-7's skid marks.** `F_01C3E4`, listed in the logic spec as "HUD
  and car panels", draws fixed lines from per-track tables into the background, after the point
  `st_dump_tracks.py` dumped at. Found because `tools/objects.py`'s background didn't match a dump of the ST's
  at race frame 300. The dump is now at `&D218`; the conversions and pictures for tracks 5-7 are redone (the
  marks show on the grey road options; on A and A2's black road they're black). With that, `objects.py`
  matches the ST's background and mask C to the bit below its HUD strip.
- The renderer test now needs 4 banks: SPRINTD is the objects'. The trace is variable-length records (the cars
  drawn, then the background object events), the cars each with their own data table, and up to 3 frame sets.
- Background objects work (every frame of the 857 matches the model) but are slow: 4,770 cycles a frame on
  average, 112,820 at worst. Two quick changes (the ST's second call left out, both screens written by the
  first; the cells found once each) took the average from 6,809; the bytes need the plotter's treatment next.
- Background objects faster: the ST's two calls kept, the first writing the variant into the screen and
  copying it into the background, the second only copying the background into the other screen; each copy
  through unrolled column blocks patched once a band. Objects 4,770 -> 1,865 cycles a frame on average; a
  gate's step 12,542 then 3,626. One frame over a TV frame: the race's first, setting up 7 objects.
- Two bugs on the way, caught by the model check: the objects' bytes were packed in pages relative to a
  label that wasn't on a page (each column then read across a page), and `ADC doff` (minus the line) left
  the carry set for the next column's add. And the second call wasn't recognised for gates: the ST's stack
  holds other words after a call's arguments, and they differed between the two calls.
- **Moving objects**: the explosion (in its car's place), banner, sparks and helicopter, drawn by a plotter in
  the objects' bank, a copy of the car plotter's fast loop with clipping. Checked first against the ST's own
  screens dumped at frames 190, 200 and 251 (they match but for the drone-lap digit), then the BBC against
  the model: all 560 frames match. 18,864 cycles a frame on average, 38,023 at 99%; the worst frames are a
  gate's step with the helicopter in flight.
- **Mistake: car 3 isn't always drawn in its own colours.** In a real race the ST draws every drone-driven
  car, car 3 included, from the second set (grey with stripes); only the attract race uses the cars' own.
  Found from the ST's screen at frame 200. Car 3 is now drawn from the shared set, black-striped through a
  fourth data table.
- Bugs on the way, all caught by the model check: the erase handled 5 columns, the helicopter needs 8; the
  helicopter's 272-byte variants overran a page in the packer and the next block was put over their tail;
  the top clip's data offset took a borrow for a carry.
- jsbeeb: after a breakpoint stops `runFor`, the next `runFor` runs the stopped run's leftover cycles too.
  `tools/jsbeeb.mjs`'s `runTo` now drops them first (`settle`), so a debugging script's `runFor(1)` is one
  instruction, not a jump of thousands of frames.
- Tom's idea: per-track code or data for the per-track objects. Generated code for the gates' bytes would be
  23K (14K for the changed bytes only), too much; precomputed per-track data for their priority fits. Each
  gate and barrier is numbered by place, and each of its frames' finished cell bits worked out at build time
  (3,072 bytes on track 5), so a change copies up to 3 runs into the cars' bank instead of finding each cell
  through the map. And the work of a change is split between the ST's two calls (the second copies the
  screen into the background). A gate's step 12,542 -> 8,142 on its first call (6,772 on its second); the
  worst 20 frames 37,576 -> 33,760. Every frame matches.
- Two bugs on the way, caught by the model check: the run loop read its targets from the objects' bank's
  tables after paging the cars' bank in (it wrote into the car frames); and the runs' buffer, aligned to a
  page, landed on car 3's black data table.
- The helicopter: 156 of its 288 bytes are empty, its columns 2 to 36 rows high. Moving sprites are now cut
  into pieces of neighbouring columns (`moving_pieces`, a piece costing 50 bytes), each its own record and
  erase box; the object plotter and the erase patch only a box's own columns (unrolled patching entered by a
  table on the width). The worst 20 frames 33,760 -> 32,718, the average 18,751 -> 18,318; every frame
  matches. The pieces alone gained nothing: their set-up patched all 8 columns each band.

## 2026-11-01: Phase 3, the tornado and cones

- `tools/st_trace_objects.py` takes a fourth argument, the coin flips to force (`tornado`, `cones`): a
  breakpoint after each one's call of `F_00ADB8` sets the register it's tested in (`d0` at `&CA4A`, `d1` at
  `&B00E`). The Makefile's race forces both.
- **Mistake: the recorded race wasn't race 17.** Hatari's `w` reads its values as decimal, and the tracer
  wrote the race counter as hex, so "race 17" was counter 11 (and cones, from 16, could never come up).
  Found when forcing the cones' flip still left `G_01EBB0` at -5. Now written in decimal; the track's poke
  was right only because tracks are 0-7. The objects' earlier measurements are from the counter-11 race.
- The tornado (`F_0147A0`): 3 frames of 16 x 16, colour 0 transparent (not 8), at any pixel. It
  sign-extends each plane word before rotating it into place, which would smear a set leftmost pixel; no
  frame has one (asserted). On the BBC it's one more moving object: its frames at 4 shifts, each one piece,
  through the existing plotter; nothing in the 6502 changed. Every frame matches the model (463, the
  bank's worth); with the shift left out of the model, 362 fail.
- The cones are the slots' sprite &14, drawn at the race's start; a hit draws the road (&15) over one,
  twice for the two screens. The background objects' path already did it.
- The model now places a moving object at its x plus its key's shift (the banner's was always 0 in the
  races recorded, so it didn't show).
- Cost: the tornado about 4,200 cycles a frame, all race long (22,602 a frame on average with it, 18,424
  without); 5 frames of 463 over a TV frame. It's the general path's set-up and bands for a small sprite.
- **The tornado's own plotter** (Tom chose it over the gates' speed): its 12 frame-shifts compiled by
  `tools/gendata.py` (an opaque byte `LDA #:STA (zp),Y`, a mixed one `LDA:AND #:ORA #:STA`, an empty one
  nothing), drawn through 16 zero-page pointers, one a line, set each call (about 230 cycles), so its
  character rows cost nothing and a line outside the play area just points at a junk area. The plot fell by
  1,609 cycles a frame (22,602 -> 20,994 on average; the worst 20 frames 39,541 -> 37,905). Every frame
  matches. The cost: about 2.8K more of the objects' bank (3,561 for the routine and code, less the
  pieces' 736); 1,346 bytes left in it.
- The recorded tornado never reaches the screen's top or bottom, so `tools/tornado_sweep.py` makes a race
  with its place swept over both edges; every frame matches, and a clipped line put wrong fails 180.
- A trap in the Makefile: build/gen depends on the trace file's date, so after `make check
  TRACEFILE=...` the default race isn't regenerated until its file is touched (the check then fails every
  frame, the disc playing the other race).
- **Room for the helicopter.** The full helicopter is 4 variants (from below, above and either side; the
  52-row frames presumably the sideways ones) of 4 frames, 4,249 bytes; every car's colour shares the
  bytes (cars 0-2 compose identically, car 3 the same bytes through the green table). With the compiled
  tornado the objects' bank was about 2,200 bytes short. Tom: put it in a free bank if there is one; logic
  can be squeezed into sideways RAM, being less reliant on unrolled code or page-aligned data. No bank is
  wholly free (the Master's 4 are the background's, the cars', the objects' and the one the test fills
  with its trace), so it went in the fourth, which in the game holds the race's other data.
- The plotter moved to `src/movplot.6502`, included in each bank with moving objects inside a scope of its
  own (`objmov`, `helimov`) with its own tables: Baron's scopes keep the copies' labels apart, but its
  functions are global, so the blocks' offset function went to `macros.6502`. `mov_all` moved to main RAM
  and pages each object's bank: 29 cycles a frame. The fourth bank: the helicopter 5,520 bytes; the
  objects' bank 2,239 free. 304 frames fit the trace now; all match, the helicopter drawn in 116.
- **The helicopter's other variants**, each checked in a race. The ST picks the side by where the car was
  wrecked (`F_00BB4E`); the recorded wreck brings it from below, so `tools/st_trace_objects.py` takes
  `heliN`, writing the variant into `G_01EB2C` just after the ST has chosen it, and `make check
  TRACE=heli1` (2, 3) plays those races. All match on every frame.
- **Mistake: the sideways frames' shape.** `tools/objects.py` read them as 52 rows of 32 pixels; they're 26
  rows of 64, drawn by `F_0144AA` (which the tracer logged as `heli3`, never seen until now). Found by
  reading the routine once a race called it; a picture of a frame both ways settled it. The helicopter is
  5,023 bytes in the fourth bank, not 5,520.
- The sideways helicopter flies in from x -39 or 319, and the ST clips it a 16-pixel group at a time. Its
  pieces are cut within groups, and the trace leaves out those off the screen's side; the plotter's x DIV
  4 now works for a negative x (a broken one fails 9 frames of the race from the left), and the model
  clips x at both sides (it sliced wrongly for a negative x).
- **Hatari 2.6.1 crashes with 16 breakpoints set**: adding the helicopter's to the 15 aborted it. The forced
  flips' breakpoints now set each other in turn.
- **The Makefile trap fixed**: `build/gen/tracefile` names the trace the data was made from, so changing
  TRACE or TRACEFILE remakes it.

## 2026-11-01: Phase 3, all the tracks

- The same race recorded on all 8 tracks (`make check TRACE=t0` to `t7`); every frame of each matches.
- **Mistake: barriers have 12 frames, not 8** (3 kinds of 4, a track's barriers of one or two kinds).
  Track 4's are kind 1, frames 4-7, so it never showed; tracks 3, 5 and 7 (kind 2, frames 8-11) were wrong
  from the first frame. Only the frames a race uses are stored now (none of the gates' on most tracks).
- Pop-up barriers 9 lines apart share a cell row of the priority map. As they move one at a time, each
  one's frames carry its sharers' lines at rest; the generator checks the race keeps to that.
- Track 2's data put the car plotter's fast loop across a page (an assembly error from `SAME_PAGE`); the
  loop is kept in a page with `INPAGE`.
- Memory: the cars' bank is the tightest with three human players (10,615 bytes of frames): 504 bytes
  free on track 6 (the most priority cells). The objects' bank has 3,263 or more on every track.
- The Makefile deletes a failed generator's target (`.DELETE_ON_ERROR`): a failure part-way had left a mix
  of files that assembled into a test that hung.

## 2026-11-01: Phase 3, the gates' speed

- `tools/render_profile.mjs --list N` prints the worst frames region by region. On track 4 (index) the
  frames over were the set-up (2) and two gate steps with the helicopter and cars under a bridge.
- Weighed and left: drawing only the gate's bytes that change. A step changes 47 to 105 of 192, inside a
  box of 150-165, and a changed byte costs about 22 cycles against 9 copied: about even.
- **The priority runs by transition.** A gate or barrier only steps to a neighbouring frame, so the
  trace's event now gives an entry (instance, from, to), each with its variant and runs trimmed to the
  cells that change (48-80 of a gate's 144 bytes). First call 7,546 -> 4,870 with the next change.
- **The copy passes index the screen by X** from the cell's low byte, as the erase does: only high bytes
  patched a band, no path for a crossed page (the masked barrier pass keeps its). Bands 2,346 -> 1,811 on
  the second call. A step 13,626 -> 10,453; track 4's worst real frame 42,089 -> 39,359.
- Two bugs on the way, both caught at once: the entry test compared the whole kind byte (with the
  instance and flags in it) with 2, every frame wrong; and passes 2 and 3 used pass 0's branch table,
  whose loop end is now a byte longer, and hung.

## 2026-11-01: each screen's own variables at &3000

- Tom's idea: `&3000`-`&3EFF` is the screen buffer's, main RAM's or shadow's by ACCCON's X, so per-screen
  state there is switched with the screen being drawn. The erase lists and the HUD's shown text moved
  there (ScreenVars): `ebuf` and the HUD's address patching are gone, 208 bytes of `&2E00`-`&2FFF` freed,
  about 20 cycles a frame saved. `fill_screen` sets up each copy (an empty erase list, a blank HUD row).
  For Phase 4: read-only tables written into both copies are readable whatever X is.
- **Mistake: the attract race had been checking nothing.** Since the object work, the cars to draw come
  from a frame's calls, and the attract trace has none, so neither the BBC nor the model drew a car (346
  cycles a frame). The model also didn't depend on `gendata.py`, whose race loading it uses, so after the
  fix it stayed stale. Both fixed: the attract race's draw order becomes car calls, and all 576 frames
  that fit now match.

## 2026-11-02: the beeb-port-kit's tools, one jsbeeb

- Tom added `reference/beeb-port-kit` (Kieran Connell's kit from his ports). Its skills are in
  `.claude/skills`; `CLAUDE.md` says what they look up here.
- Its tools work in place: `listing.py` as it is; `harness.mjs` with this build's symbols path, a Master
  and a longer boot. But only on its pinned jsbeeb-mcp 4.3.0 (jsbeeb 2.18.0): 1.13.1 has no `runFrames`.
- **Mistake waiting to happen**: `tools/jsbeeb.mjs` took the first jsbeeb in the npx cache. Installing
  4.3.0 for the kit silently moved every check onto 2.18, where they failed (keys are named since 2.0).
  Now `.mcp.json` pins 4.3.0 and `tools/jsbeeb.mjs` loads exactly that version, printing it, as the kit's
  tools do. Every race matches on 2.18, its cycles the same as on 1.13.1 to the cycle, and a screenshot is
  byte for byte the same.

## 2026-11-02: Phase 4 begins

- Tom's answers to the Phase 4 questions are D9-D12: the race logic bit-exact with the ST, checked frame by
  frame against Hatari; track 1 first; sound as captured YM streams converted to the SN76489, engines
  live; a three-player keyboard layout proposed and checked for ghosting. The first steps are in
  `docs/brief-phase4.md`, on the branch `phase4-start`.
- **Mask B (walls)**, D13 Proposed: only the 8 x 8 cells that are neither all road nor all wall, as the
  priority mask. 144 to 267 a track (1,152 to 2,136 bytes) against 8,000 (`tools/maskb_stats.py`).
- **The cars' shapes differ**: 7 of the 16 facings' opacities differ between the 8 car sets, so the wall
  probes need each frame's own shape, not one per facing.
- **The logic tracer** (`make logictrace`): an autopilot of chained conditional breakpoints drives the blue
  car round track 1 for 3 laps, with bounces and a wreck; every per-car variable, input and random number
  every frame. Deterministic (two runs the same), and the race's random numbers are one run of TOS's
  generator (`seed * 3141592621 + 1`), so the BBC can start from the traced seed.
- **Trap**: Hatari's "CPU=$pc" header can head another breakpoint's output; tell the reports apart by
  their own lines ("Next PC").
- **Mask B encoded** (`tools/maskb.py`): 2,168 bytes on track 1 to 3,427 on track 8, the gates' and
  barriers' cells included, every track decoding to the ST's mask exactly; track 1's mask equals the ST's
  RAM to the pixel.
- **D13 decided** (Tom: "Yes, D13 as proposed").
- **The logic's oracle** (`make logiccheck`): a test disc with no display replays the traced race's inputs
  through the BBC's logic, and `tools/logic_check.mjs` compares 38 of the ST's variables every frame.
- **The humans' cars** (F_00DC4C): car 0 matches the ST in every movement variable to frame 75, its first
  car-to-car shove. 3,824 cycles a frame for one car, most of it the general multiply and divide.
- **Mistake**: the set-up handed `mul_s16`'s result to `div_s16` without a copy (each had its own number):
  every frame wrong from frame 1. They share `num` now. Broken on purpose (the halving rounded down), the
  oracle fails from frame 6.
- F_012276's tables come from its own stores in the disassembly, run by `tools/gen_logic.py`, not from a RAM
  dump that a clean build can't make again. The last word of the jump table is BSS, never stored.
- **Walls** (step 6): `src/walls.6502` in the logic's bank with mask B. Exact on every stretch of car 0's
  race the logic can reach (1,933 frames, 23 of 24 bounces), checked with `--from` (the ST's state loaded
  into the BBC at a chosen frame) and `tools/logic_stretches.py`. `mask_byte` right on all 8,000 bytes
  (`tools/maskb_check.mjs`). About 2,150 cycles a car as written: too slow.
- **Mistakes**: the probe line's row loaded into A and then overwritten before the call, so every car
  wrecked on its first frame (`mask_byte`, checked alone, was right); and the test set its input pointer
  after the label `--from` writes it at.
- The walls skip a car whose probes are over all-road cells: 11,702 cycles a frame to 6,149 (mean, frames
  361-2024), exact still. A label named like a variable of its scope (`row`) was refused by Baron, as the
  skill warns.
- **The track's cells** (F_00BEEA, `src/cells.6502`): car 0's stripes, checkpoints, laps and lap times exact
  over its 1,933 free frames. st-logic had cell types 5 and 7 setting flags &0010/&0020 that nothing
  reads; the asm sets &1000/&2000, which the steering does read. Corrected.
- A mutation that changes nothing proves nothing: accepting checkpoints out of order passed (car 0 never
  crosses one out of order), so the stripe reset was broken instead, and that failed.
- **Drones, the draw order, car-to-car**: all four cars exact in all 48 variables to frame 294 (car 0's
  crash). Mistake: a local label `.drone` in `race_frame` shadowed the routine `drone`, so `JSR drone`
  called itself and the BBC hung; the skill warns of exactly this. The logic now costs about 19,800 cycles
  a frame: the multiply and divide have to get much faster.
- **Wrecks**: the crash, its wait and the put-back exact; all four cars match on every frame to 2030 but the
  wrench count. The label-shadowing mistake twice now (`.drone`, `.wreck`): name branch targets for what
  happens there, never after a routine.
- **The whole race exact.** Pickups (the bonus and wrench state machines), TOS's generator, the scores, the
  lap events and the race's end: the BBC's logic matches the ST on all 2,196 frames of the traced race, every
  car, 68 variables and the random seed. The end of the race had to move out of the frame: the ST resets
  the frame counter after its flip, so the trace never sees it.
