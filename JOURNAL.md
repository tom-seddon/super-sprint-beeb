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
- **The logic's speed**: 18,940 cycles a frame to 11,439 (mean), worst 26,737 to 17,947, all exact: the
  divide's 8-step path and /8 by shifts, 0 / n at once, the direction multiply in shifts, a cell looked up
  once per cell row. `tools/logic_profile.mjs` says where the rest is.
- **The effects** (sparks, banner, the helicopter's flight): exact on every frame, 118 variables now.
  The sparks' state carries over from race to race (the set-up only clears their x), so the test seeds it
  from the trace's frame 1.
- **The draw calls**: the BBC's logic now makes the ST's draw calls (slot sprites, cars and explosions in
  order, sparks, banner, helicopter), checked against the ST's own on all 2,195 frames
  (`tools/logic_draws.mjs`). Mistake found by it: a car wrecked by a wall is drawn as a car that frame
  (the ST draws before the probe), so what's drawn is noted at the draw, not read from the state after.
- **The game drawn from its own logic**: `make check TRACE=logic0`, all 2,197 frames of the race match the
  model made from the ST's draws. The frame builder had to go in the fourth bank (main RAM was 331 bytes
  over); 234 bytes are left there, 973 in main RAM. 25,967 cycles a frame on average, 3 frames over.
- **Keys** (D12): Z X SHIFT, V B N, , . / proposed: every key in its own matrix column, so none can
  ghost another (checked on paper over all 511 combinations, the model checked against Paradroid's
  hardware ghost). All read right in jsbeeb. `make beeb TRACE=play` makes a disc to play track 1 with three
  players, for a real BBC.
- **Trap**: a headless check that reads a bank number at boot reads 0: the disc copies its banks first.
- **Player 1's keys: Q W E**, not Z X SHIFT (Tom: the two SHIFT keys are one key, at opposite sides). Same
  columns, so still no ghosting on paper; all read right in jsbeeb.
- **Sound**: the race's effects captured from the ST (YM writes per VBL), converted to the SN offline,
  played from the vsync IRQ; engines live. All 31 starter calls match the ST's; all 29 started effects
  found at the chip, field for field. Mistake found by the chip check: the loader left the latch's line 3
  low, so the keyboard drove PA7 and every sound byte lost bit 7; the loader now leaves it high (as the
  MOS does) and the key read drops it. Hatari ran away with 16 breakpoints set (a 2.9 GB log).
- Room is the next problem: 52 bytes of main RAM left in the play build, 136 in the fourth bank.
- **A RAM hunt** (`docs/brief-ram-2026-11-02.md`): the ledger over all 8 tracks first, seven levers costed,
  three built. Main RAM 52 -> 416 free, the fourth bank 136 -> 2,398, the objects' bank +1,563, every oracle
  passing after each (`tools/suite.sh`), the default disc byte-identical. The logic's 128 hottest bytes in
  zero page paid twice: 654 bytes and 105 cycles a frame. Mistake: the shadow copy ran in the loader, whose
  code is in `&3000`-`&7FFF`, so setting ACCCON's X hid the running code; it runs from a bank now. And
  `sn_check` lined the chip's writes up by assuming the first came in the first field; the new boot's
  first came in the third, so it found nothing while the chip was right. It goes by the writes' own cycles
  now (they're the CPU's). Another: a `git stash` to test the old build left the old generator's files in
  `build/lgen` with a newer timestamp, and the next build failed on duplicate symbols.
- **The hazards** (step 11): the tornado, barriers, gates and cones exact on track 5's race 17 (every frame,
  mask B's boxes and the attribute map compared too), and drawn from the logic (all 2,240 frames match).
  First full run of the oracle passed, so each piece was broken on purpose; two breaks can't fail and the
  reason is written down. A Phase 3 bug surfaced: the objects tracer dropped sparks 4-7's places, and the
  model and the trace-driven renderer agreed on drawing none of them. Mistakes: a Python text replacement
  that silently did nothing (the tornado's frame call missing until the oracle showed it), `STX abs,X`
  again (it doesn't exist), and branches out of range twice. The race is slow: 734 of 2,240 frames take two
  TV frames. Room: track 8 would be about 260 bytes over in the fourth bank.


## 2026-11-02 to 11-03: Phase 4, speed, room, every track, the flip (Phase 4 done)

- **Speed, step 12, four rounds**, every change exact on both traces: mask B's box writes a band at a time,
  TOS's multiply from the byte that matters and then unrolled, a car's road test cached, the wall columns a
  cell row at a time, the draw order by counted places, the divide's quotient by ROL, the wall probes'
  shapes pre-shifted, a divide by 40 from a table, the plot's slow loop once a band. The hazard race's frames
  taking two TV frames 734 -> 150, its mean 38,207 -> 32,224 cycles. New unit checks: the wall columns
  (caught a fault the races missed) and the arithmetic (`tools/arith_check.mjs`, 158,340 cases).
  `tools/game_profile.mjs` (cycles by label) found set-up costs the regions hid.
- **Room** (`docs/brief-room-2026-11-02.md`): every track measured; mask B and the logic's state moved into
  ANDY once measured untouched by the game and by loads (D15); all eight tracks assemble
  (`tools/all_tracks.sh`, in the suite).
- **D14**: the drones' two accumulators that only dead ST code reads dropped (135 cycles a frame).
- **Every track** (step 13): each track's race 17 traced and replayed through the BBC's logic, exact and
  drawn exactly (`tools/tracks_check.sh`, 48 checks). Five of seven new tracks exact at once. Faults: the
  bonus's cell stored before the free test (as the ST does), moving objects not clipped at the screen's
  sides, the race's end run before the frame was drawn. **Mistake**: the helicopter's tables read with ANDY
  paged in, which D15 had put over them.
- **D16**: the helicopter not drawn; in a wreck's last 28 frames the car blinks where it comes back.
  Frames over 150 -> 106, the fourth bank +1,132. A copy of mask B by column was built, measured (about
  100 cycles a frame for up to 2,320 bytes) and reverted at Tom's word.
- **D17, the flip in the blank** (Tom's idea): System VIA T1 at the display's end shows a frame done during
  the display; one done in the blank shows at once; T2 closes the blank. Measured in jsbeeb, every flip in
  lines 212-309 of the blank's 208-311; the vsync interrupt starts at line 250, 2 lines after its edge, not
  the kit's 4. Fields repeating a frame over the nine races 332 -> 42. Seen on Tom's Master 128 (CUB):
  no tearing. Run-ahead logic (simulated 42 -> about 9, for about 15 ms of latency) closed, not built.
- **The play build's restart** (Tom found it: a pickup left lying when the race ends): the restart cleared
  the logic's state but not the attribute map or the clean background. Each slot's cells and 32 bytes of
  background now go back. **Mistake**: `slot_put`'s `fresh` was set before the loop, where a sibling
  callee (`slot_cell`) shares its zero-page byte; it's set just before the call now.
- **The replay discs' pauses** (`worst_h4`): after the race the replay builds don't restart, and the 8-bit
  countdown wraps, so the cars drive about 90 frames in 256. A replay artefact, not in play.
- **Tom's reviews, 2026-11-03**: D11's sounds all agreed by ear; D12's real-keyboard check and three
  players on the keys wait on a three-person playtest; the joysticks (D5) left open, not urgent; D16's chop
  kept for now, 336 of the wreck effect's 402 bytes, perhaps another sound later.
- **Phase 4 closed**: `docs/plan.md` Phase 4 done, its budget table moved to `docs/brief-phase4.md` §9, the
  brief BUILT. Next: Phase 5, the game, and main RAM (103 bytes free in the play build) first.

## 2026-11-03: Phase 5 begins: the brief, room, one build for every track, the loads

- **The brief** (`docs/brief-phase5.md`): the ST's front-end screens found in its code (the title, winner's
  circle and select screens are tile maps 8-10; `SUPER.DAT`'s first three blocks the high-score backdrop,
  prepare to race, select and upgrades). Tom decided D18-D20 and D22-D25 as proposed (D21 withdrawn: built on
  a wrong reading), and D26: `&0900`-`&0AFF` the game's. D23's saving is lower priority.
- **Room** (`docs/brief-ram-2026-11-03.md`): the memory map had credited files' code to the constants files
  they include; fixed first. Main RAM 103 -> 780 (the font into Shared, the logic's arithmetic and tables
  into its bank), every check passing.
- **3a, one layout**: every track's part of each region in a slot at a fixed address, padded to the largest
  track's; outside the slots the eight tracks' builds are the same byte for byte (`tools/track_slots.py`, in
  the suite). **Mistake, Phase 4's, found now**: the logic tracer kept the longest run of frames, so track 1's
  race 17, traced again at 9,000 VBLs, came out as the next race on track 3; it keeps the first race now.
- **3b, 3c: the loads**: `make game` makes the disc (a packed file a track, 6.4-7.5K); `src/load.6502` gives
  the OS back its zero page, VIAs and vectors, loads through OSFILE, takes the machine back and unpacks. Its
  code lives in the fourth bank's first 4K and runs in the main screen (main RAM 682 free). All eight tracks
  load right (`tools/load_check.mjs`). **Mistakes**: two copy loops that patched their operands and never
  reset them (run once until now), and the MOS's colour flashing left on, which rewrote the Video ULA and
  halved the CRTC's clock after a load (D7 had said to turn it off). Off now (Tom: OSBYTE 9 and 10), and the
  flash counter cleared by OSBYTE 193: one already counting froze at the takeover and fired in the first load.
  **Found on Tom's Master** (jsbeeb had shown it only as slow loads, which I'd put down to the head's travel): the
  game's DDRB `&0F` cut off the CMOS chip, so the filing system read its seek time as `&FF`. The game leaves
  DDRB at the OS's `&CF` now, which MOS 3.20 writes only at reset. Seen working on Tom's Master, 2026-11-04: the
  first race, then the second loaded.
- **The rest of step 3** (2026-11-04): D20 revised with Tom: every real race needs only cars 0-2's own sets and the
  drone-driven set, so all four stay resident and there are no combination files (a wrong premise of mine, found
  building it). That found a real fault: the wall probes' shapes were fixed from the trace, wrong by one pixel of player 2's car at facing 6 (first written up, wrongly, as players 2 and 3 on 2-5 facings).
  Escape off; `Loading` and the OS's error text in the HUD's row, in the MOS's font at `&B900` in ROM 15 (Tom).
  **Mistake**: OSWORD 10 for that font first, against D7's "no VDU calls": the VDU's workspace is in ANDY, which is
  the game's, and it returned zeros.
- **Step 4, the race count's hazards** (2026-11-04): the disc had played every race as race 17 from one seed; the
  counter, the generator and the drones now outlive a race (`GmRace`, `GmSeed`, `GmDrone`). `tools/disc_races.mjs`
  plays traced races on the disc itself, state and screen every frame: 40 races (none, barriers, tornado, all, the
  counter's end, on every track), 126,141 frames, all exact first time, so it was made to fail three ways before
  that was believed. **Mistake**: my first screen mutant "passed", because the byte it changed was already that
  value; checked before the oracle was doubted or trusted. **Mistake, Phase 4's**: the object tracer's 7,000 VBLs
  cut track 8's race 17 short, and `st_race.py` kept the longest run; both fixed. Worst timing: track 5's race
  50, 34 repeated fields in 1,689 frames.
- **Two and three humans** (2026-11-04, Tom's question): the tracers drive cars 1 and 2 by the joysticks' bytes, and
  32 randomly driven races join the disc's check: 72 races, 249,274 frames. **Mistake, Phase 4's, found by them**:
  `.ramp` in `cells.6502` read its type from A after the dispatch had overwritten it, so a `&20` ramp never launched
  a car; no race had taken one until random driving did, on track 2. Fixed for no bytes. The old probe fault stayed
  out of reach of all 32 (one pixel, 10-31 places a track), which a control showed to be a true miss, so a short
  race puts cars at those places on both machines: the ST bounces off them, the BBC matches, and both faults put
  back are caught. **Mistake, mine**: I'd told Tom that fault was on players 2 and 3 at 2-5 facings; measured, it's
  one pixel of player 2's car at facing 6. **Mistake, mine**: `disc_races.sh` through BSD `xargs -I`, which cuts an
  argument at 255 bytes. Worst timing is now three humans, track 5's race 17: 93 fields in 2,246 frames (4.1%).
- **Step 5, the sequence tracer** (2026-11-04): `tools/st_trace_game.py` plays whole games from scripts and dumps all the
  ST's data at every screen, so a screen is a function of the state before it and its inputs; races are ended by
  poking the result. Three games and 16 demo races traced, and Hatari shown to repeat them to the byte. The traces
  corrected the docs: the upgrades' timer buys, the race counter goes to -1, F5 barely changes the circle's length.
  **Mistakes, mine, all in the scripts**: taps before the select's loop had started, so the dial never moved; a
  release step that outlived the initials' entry, so the chain waited through a whole race; F5 pressed after its one
  read. Each showed up in the trace's own timeline. Also a stray `rm -f /dev/null` in a command, refused, no effect.
- **Step 6, the game's rules** (2026-11-04): `src/game.6502`, all of it but the initials: select, prepare, the circle and
  its bonuses, the elimination, the upgrades, next track, game over, the demo, the attract loop. `tools/game_check.mjs`
  plays step 5's games on the disc read by read: 35 points, 3,440 reads, exact, and seen to fail on four mutants.
  `tools/attract_check.mjs` proves the attract mode's order and times, and three demos back to back against the
  ST's generator. All 16 demos exact frame by frame. **Mistake, mine**: the rules first went in the objects' bank on
  a free figure that was track 1's alone; track 5 overflowed. They run from the background's bank now, copied from
  the fourth bank's first 4K at each race's end. **Mistake, mine**: a `SetOf` entry I'd meant to look at and didn't:
  255, so a demo's car 3 plotted from set 15 and overwrote `plot_car`'s first opcode, which ran as `BRK`. The
  second races found what no race trace could: the ST never resets the coasting phase or the sparks' timers. Left:
  car 3's own colours in the demo.
- **Found on Tom's Master** (2026-11-04): the sound went on after a race's end. The ST silences its channels again as a
  race really ends (`&D166`) and on F10, not only at the win; a bounce after the win falls back to the engine, which
  nothing moves once the race has stopped. **Mistake, mine**: I'd copied only the win's, and no oracle listened after
  a race. Measured on the chip (2 of 3 races left at 0.013), now silenced in `game_go`, and `disc_races.mjs --silence`
  and `game_check` read the chip after a race.
- **Step 7, the front end's data** (2026-11-04): every screen captured from the ST as raw memory; `tools/st_frontend.py`
  decodes `SUPER.DAT`'s front-end blocks against them: title, credits, high scores and lap records exact to the pixel,
  prepare but for its flickers. `SUPER1.DAT` is never read, shown by wiping it. **Mistake, mine**: the first wipe was
  before the file loaded, so it proved nothing; caught by asking for a control, and done again after it.
  **Mistake, mine, found by Tom against the video**: the captures' colours were wrong on every screen with raster bands, as
  I'd read one palette from the Shifter for the whole screen; the ST changes palette down the screen on Timer B, in code
  the disassembler had left as data. The bands are recorded now, and checked against Hatari's own pictures. My first
  limit for that check, by the row, passed the very fault it was for; the mutant showed it, so it's a total now.
- **Step 8, the title** (2026-11-05): first of ten, a screen at a time, each checked by Tom. Nine options on a viewer disc; he chose
  MODE 2 (his idea), checked, on a CRT. In the game through a new file, `TRACKF`, with the wipe, which turned out to fit
  the BBC's cells in either mode. **Mistake, mine**: moving attract_check's stop for the title broke two of its timings; the
  suite said so.
- **Found on Tom's Master** (2026-11-05): the old score row stuck during a load, and "Loading" came late. His guess was right: the
  wrong screen shown. The load restored the OS's ACCCON whole, D and all, and his OS had the shadow screen showing, which
  jsbeeb's doesn't. Reproduced by setting D in `OsAcccon`; the load now keeps D and X clear, and `load_check` starts from that.
- **The races on another machine** (2026-11-05): `tools/disc_races.sh`'s jobs run on `agentbox` by default (`tools/remote.sh`: rsync what they
  read, 10GB once and about 1MB after, run them there, bring back logs and statuses); `REMOTE=` keeps them here. One rotation and the
  silence race gave logs identical byte for byte on both machines, from the same disc. A corrupted model and an unreachable host each fail
  the run. The suite sends them off as soon as the disc's made, so `all_tracks` and `game_disc` come first now. MEASURED: the races 1,961s here, 100s there;
  the whole suite about 38 minutes, now 6m37s, nearly all of it the local oracles.
- **Step 8, the credits** (2026-11-05): second of ten, MODE 1 in black, red, yellow and cyan. The load of `TRACKF` moved ahead of them,
  since a demo's track wipes the pictures. `attract_check` compares the picture byte for byte, and its time is the ST's 325 fields exactly.
- **The suite in half the time** (2026-11-05): with the races away, this machine's stages one after another were all of the 6m37s, so more cores on them would have saved nothing. `game_check`, `attract_check` and `load_check` joined `tools/disc_races.sh`'s jobs, so they run wherever the races do, and `all_tracks` keeps its 50MB trace copies, which took 46 of its 105 seconds to write again. MEASURED: the suite 3m34s, every check passing, with those checks' files first cleared from `agentbox` to prove the copy list; `REMOTE= tools/suite.sh OUT quick` 9m42s, passing, with the trace copies made afresh. All nine discs the same as before, byte for byte. A byte changed in the credits' expected picture fails `attract_check` and the suite.
- **Step 8, the high scores** (2026-11-05): third of ten, MODE 1 in black, blue, magenta and yellow. The frame's a picture and the table's drawn over it from `HiScores`, so new scores will show. `attract_check` compares the whole screen byte for byte with the ST's as `tools/st_frontend.py` composes it. TRACKF was full, so its pictures now reach under ANDY in the background's bank. **Mistake, mine**: I put them at `&8000`, over the erase's code, which no track's load restores, so the demo's race crashed. `attract_check` stopped there; they start at `BgOrg` now, which leaves 45 bytes there. The suite 3m30s.
- **The title's last line** (2026-11-05): "(c) 1986 ATARI GAMES" was unreadable, as its colour is one of the oranges that go to checks and its letters are 5 pixels wide in a mode with half the ST's pixels across. Solid yellow alone still fills in. Four options measured, packing to 2,945-2,997 bytes against 2,949, so room didn't decide it; Tom chose letters redrawn by hand, 3 x 7 (`title_line` in `tools/screen_options.py`), 2,957 bytes and no code, over a MODE 1 last row, which would have kept the ST's own letters for a timed split. The line's half as wide again as the ST's.
- **Step 8, the lap records** (2026-11-05): fourth of ten, the high scores' frame with only its heading's two cell rows packed apart (445 bytes), the rest drawn by the high scores' glyph routine, the times live from `LapRecords`. `attract_check` compares the whole screen byte for byte with the ST's composition, right first time; on the disc before the screen was built it failed, and a byte changed in the expected picture fails it. Eight poked times (0, 4, 499, 500, 4994, 4995, 5000, 32767 ticks, past the ST's 99.9) drew exactly what the model draws. TRACKF's second part has 1,015 bytes left, which won't hold the screens to come. The suite 3m40s.
- **Step 8, prepare to race** (2026-11-05): fifth of ten, and the first game screen, which a race's overwriting of the background's bank decides: the front end's code is resident now, at the objects' bank's end, copied by `game_go`, and `TRACKP` holds only the picture and six panels. `game_check` compares the screen with `tools/screens.py`'s as it's shown and ends, whichever cars play, a join's panel included: three games exact, 16 screens, 2 with a join, and a byte changed in the expected screen fails it. My first build never reached the attract mode: `game_go`'s copy set only the high byte of its source, and `game_image` doesn't start on a page. The suite 3m24s, the races' checks on `agentbox` with the new files.
- **Found on Tom's Master** (2026-11-05): junk flashing around the attract mode's loads, and a blank pause after a demo. All reproduced in jsbeeb by reading the finished frames field by field; his guess was near, as the file lands in the screen, but the first flash was the CRTC: `load_track` set R6 to 1 mid-frame, and once past that row it never matches, so the display ran on past the screen's end. R6 now drops in the blank, before the load's code lands in the screen; at a load's end the display goes off by R8 until the screen's clear (`say_clear`, or `start`); `game_go`'s page in transit goes through the shadow screen, not shown. The pause was my `say_clear`: the ST leaves the race's last frame up for its 150 fields, so that's what happens now. `tools/flash_check.mjs`, in the suite, watches every field from the title to a race's start: 54 fields wrong on the disc before, none after. The suite 3m38s.
- **Step 8, the options** (2026-11-06): sixth of ten, with Tom's redefining and key tester, in `TRACKO`. `tools/options_check.mjs`, in the suite, drives it by the matrix: the screen byte for byte, MOS font and all, the inverse names, redefining and each refusal, F9 and the sound's field stopping, the keys kept through a track's load and read by the game, and the warning against an independent copy of the ghost model on 40 random layouts, 21 of them clashing. A byte changed in the expected screen fails it. It found my first F2-F4 never fired (a `PLX` between the key read and its branch). My `SoundOff` broke the non-play builds, there being no keyboard file; `make check` said so. jsbeeb doesn't ghost, so the markers on a real clash are for a real keyboard, and it can name 24 of the keys: the punctuation it can't are from the matrix's layout, not measured. The suite 3m29s.
- **The keypad** (2026-11-06): Tom's keys names and the ghost check good on his Master. The keypad's 19 keys added from his numbers, named PAD 4 and so on, the clash test's columns now 13; jsbeeb's key map agrees on all 19, and he's pressed them on his Master, `#`, `,` and Delete included.
- **Step 8, the select screen** (2026-11-06): seventh of ten. `game_check` compares it as shown and as it ends, panels, dial, rectangle, difficulty and seconds, and `tools/select_check.mjs` walks all 16 dial positions, which the traces don't. That comparison caught the difficulty's clearing cutting the right-hand rectangle's edge, so the rectangle's off while it's redrawn. **Mistake, mine**: a `save_game` before the file's load overwrote the seeded generator; `game_check` showed all 13 points wrong at once. The suite passes. Tom: looks good.
- **Step 8, the upgrades** (2026-11-06): eighth of ten, in `TRACKU`, composed against the ST's captures, 0 pixels. Boxes lit by EOR through 39 rectangles, the ST's by palette; figures drawn by EOR too; 5 packed dial positions, the rest flipped and turned round. `tools/upgrades_check.mjs` and `tools/upgrades_model.mjs` compare every pass, `game_check` the traced games, `flash_check` the new load. **Mistake, the placeholder's**: its pass of 2 fields made the time 6.3 seconds; it's 3, as the ST's, and now paced from the pass's start, so a moving dial costs nothing. Tom, in jsbeeb: looks good, the load's fine at the slowest seek (his Master to come). He asked for no time limit (D27) and no flicker in the score line as it's paid for: figures were taken away and drawn again, and now change in one pass, only if they've changed. **Mistake, mine**: the check's "before" was `ram()`'s live view, so its first failure proved less than it seemed; fixed, and proved again on a build erasing and redrawing on purpose, which fails all 24 payments.
- **Step 8, the winner's circle** (2026-11-06): ninth of ten, in `TRACKC`, composed against the ST's captures, 0 pixels outside the HUD and sparkles. Each place's car painted by the result through masks, the figure's frames too, in the race's palette on a flat white ground (Proposed). The file's 11K, so only its code's copied up and the rest is read from the main screen with the display off. `tools/circle_check.mjs` and `tools/circle_model.mjs` compare every pass and field of four poked races, `game_check` the traced games, `flash_check` the new load. Found on the way: the figure has 16 frames, not 12; the crowd's "sparkles" are flags in the winner's colour; a time below 0 is real, and is the capture's "-.-". **Mistake, mine**: the picture unpacked over itself at the shadow screen's end, which can't work for a full screen: two streams under ANDY now. And making `flash_check` start at the race's end quietly lost the upgrades' load, the car being eliminated: the load count stayed at 6, which is what gave it away, and it now puts the car ahead and insists on 7. `upgrades_check` timed a pass from its read, which can fall either side of a field's end, and moving the panels' code by a few bytes made it read 4 then 2 fields: it times from `fstart` now, what the game paces by. The suite passes on agentbox again, 4 minutes.
- **The circle waits** (2026-11-06): Tom: it went too quickly. D28: the celebration runs until a player's fire, held fire from the race not counting. `circle_check` holds fire past the ST's 200 fields and waits to 300; `game_check` gives fire at the 200th, and the traced games stay exact.
- **Step 8, the initials** (2026-11-07): tenth of ten, over prepare's panels: the whole high score entry, table included, up to three cars at once. Composed against the ST's captures, 0 pixels in the panels. `game_check` now plays the ST's initials' reads instead of skipping them, and compares the table at every point, exact in all 3 games; `tools/initials_check.mjs` and `tools/initials_model.mjs` try what the traces don't. The game's code ran out of room, so the circle's count and the upgrades' loop moved into their own files. Of eight faults built in, one showed a gap in the check (fire held, now a case), and one was no fault at all (time counts in twos, so +24 for +25 changes nothing).
- **No limit on the initials** (2026-11-07): D29, Tom's. The entry waits for every car's three letters, and the seconds are gone.
- **The initials' keys** (2026-11-07): Tom: a tap had to be held for a few frames. The ST reads a car every 6 fields, so a press could wait 120 ms or be missed. D30: the keys are looked at every field too, and a press acts at once; a held key waits 24 fields, then repeats as the ST's. The ST's reads are kept, so the traced games stay exact. That left 15 bytes in the first 4K. Two faults got past `initials_check` at first: a letter taken early looks the same when they're all A, so it now insists the entries finish, and an entry left waiting hung it, so it stops after 1,000 reads.
- **On Tom's Master** (2026-11-07): the winner's circle, the upgrades and the initials tried on real hardware. Tom: "they're good".
- **Load times** (2026-11-07, jsbeeb, a load's start to the game back): DFS circle 3.30 s, upgrades 2.73, prepare 2.46, a track to its first frame 3.94; ADFS M 2.87, 2.56, 2.20, 3.76. By size a load is about 2 s and 0.11 s a K. The game ran on ADFS in jsbeeb for the first time: `tools/adfs_disc.py`, with `bootDisc` taking how long SHIFT's held. **Mistake, mine**: an `.adl` first, laid out in order, when jsbeeb's interleaves the sides, which looked like the game's boot failing.
- **One load after a race** (2026-11-07): D31, Tom's: all three screens' files in one load, back to back with the motor running, two parked in track slots, the three first on the disc. In jsbeeb on DFS 2.5 s saved between races, 4.2 s with the upgrades. **Mistake, mine**: the upgrades' copy into place ran 128 bytes into the game, as a comment in `sprint.6502` had warned; `upgrades_check` caught it as a score that didn't change. On ADFS it's now slower than DFS, as DFS's files were moved next to the catalogue and the ADFS disc's weren't looked at. On Tom's Master: "The updated disk is much better".
- **`game_check`'s stops by the code's bytes** (2026-11-07): the screens' files share addresses, so a stop in one fired in another. The check had looked at `GmFront` after stopping, and the game stored `'U'` and `'P'` there only for the check. Now `fileGate` (`tools/jsbeeb.mjs`) reads the file's bytes off the disc from the symbols and gives jsbeeb a breakpoint condition on the bytes at `PC`, four in each case here; the two stores went, 10 bytes of the front end's code (192 free). With the conditions taken off, the check fails on the first game in 20 s, a select stop taken in another file; with them, all 3 games exact and the suite passes on agentbox.
- **Two discs and two machines** (2026-11-07): Tom made the ADFS disc an official one beside the DFS one, for hard disc installs and Compacts with no DFS (D32), and the Master Compact a target (D33), assumed to work until he tries it; jsbeeb has no Compact. The boot's refusal now names both machines. The ADFS disc's work is listed in step 11. Then Tom's idea, ADFS L with the files split over both sides: ADFS numbers side 0's sectors first, so the race's files went on side 0 (to track 19) and the rest on side 1 (to 23). 0.19 s saved between races in jsbeeb over M. **Mistake, mine**: the first L image assumed the sides went track by track, and a `*LOAD` with no error was taken as a good read; comparing the bytes showed it. Tom, on his Master: it "runs well", and L is the official ADFS disc, made by `make game`; no M disc (D32).
- **One load into the game too** (2026-11-07, Tom's): fire on the title reads prepare's file and the select's back to back, prepare's kept in the cars' bank as after a race (D31). In jsbeeb, fire to the race: 3 loads to 2, loading 8.50 s to 6.99, 24.54 s to 23.01 in all; the track's own load 0.2 s longer, as prepare's no longer just ran the motor. The committed disc was rebuilt for the comparison and came out at its SHA-1. 106 bytes left in the first 4K. Tom, on his Master: "an improvement".
- **Step 9, the front end's tunes** (2026-11-08): all ten captured whole on the ST (`tools/st_trace_tunes.py`, 35 s), converted by sound_gen's rules into a stream a channel (`tools/tune_gen.py`, played back in Python to the converter's fields exactly) and packed: four kept at the fourth bank's end (1,003 bytes), the circle's five in TRACKC (2,058). A screen unpacks its tune into ANDY; the IRQ plays it from three rings in Shared, fed by the front end's waits. As the ST: after the wipe-in, only with the sound on, the jingle and the ding in its place, a fade over 75 fields if a screen ends first. `tools/tune_check.mjs` (in the suite): 9 tunes, 4,197 fields at the chip like the converter's; three faults built in each failed it. **Mistakes, mine**: the first captures started at a fixed VBL and were cut by the demo's race; logging every sound driver entry showed it. The logic test's build broke on the tune's code in the race's player; it's the play build's alone now. Room: main RAM 408 to 206, the &3000 area 312 to 15. Not yet heard by Tom.
- **Step 10, saving** (2026-11-08): the table, lap records, keys and sound as one file, `SCORES` (307 bytes, D23), written by TRACKF's last 106 bytes as the title's file loads, only if its sum's changed, and read at the boot by SPRINT's loader if its size and sum are right. A failed save is said in the HUD's row ("Disc read only - press a key") and not tried again until something else changes. A save adds 1.27 s to the title's load on DFS, 1.47 on ADFS L. `tools/save_check.mjs` (in the suite): DFS and ADFS L, five spoilt files, a write-protected disc; four faults built in each failed it, after one first got through (**mistake, mine**: no spoilt file changed only the sum's first byte). Room: the first 4K 62 to 52, the &3000 area 15 to 3, main RAM none. Tom committed step 9 (f543a20) having heard some of the tunes: "the ones I did hear did sound good".
- **Other filing systems** (2026-11-08, Tom): "Game works as expected on MMFS in b2." "Game works as expected with BeebLink." Then: "Works with hard disk on b2. Installation via `*COPY` works fine." And: "Works on Master Compact." (D33). Econet waits: Tom has no network to try it on (in `docs/plan.md` for later).
- **ADFS in the suite, and its cost** (2026-11-08): `game_check --adfs` and `load_check --adfs` run on `build/game.adl` (MasterADFS, SHIFT-BREAK), both in the suite: all 3 games exact, all 8 tracks loaded right. With the 1770's commands logged, ADFS's extra time is per track, not per file: after each step it verifies and settles 15 ms, and sector 0 has just passed, so 198 ms for the track's first sector against DFS's 74. The load after a race: 5.15 s ADFS L, 4.61 DFS; the load into a game: 3.20 and 3.33. Real hardware depends on the disc's own sector skew, which jsbeeb invents.
- **Phase 5 closed** (2026-11-08, Tom: "Please close phase 5."): the brief BUILT with its §9 (what landed, what was tried and not built, what's left), the plan rewritten (Phase 5 done, "After Phase 5" the list Phase 6 is to be chosen from, D27-D33 in its table), the memory map regenerated (unchanged). The suite's last run: 38 of 38 pass. Every `TRACE` build assembles (the suite's, and heli1-3, attract, h0, h7 by hand); the discs rebuild byte-identical to those tested (`game.ssd` 200aab38, `game.adl` dac5d958).

## 2026-11-08: after Phase 5

- **The restart's sound** (2026-11-08, Tom: the helicopter noise "sounds a bit odd (as there's no helicopter)"): the chop also ran 20-50 frames past the put-back, the car racing with no engine, and held two channels. Options rendered as WAVs of a whole restart (`build/wav_restart`); Tom chose a rising sweep, first at the put-back, then ("the timing isn't quite right", "It feels like it should play when the car reappears on the track") over the blink's 28 frames to it. The wreck is the crash alone, the helicopter's going no longer resets the engines, and with no loop left `FxLoop` and its code went, and the field's offset is Y (no effect passes a page). D16. The `&3000` area 3 -> 267 bytes free, main RAM 206 -> 222.
- **The suite's ADFS disc** (2026-11-08): `tools/suite.sh` rebuilt `build/game.ssd` but not `build/game.adl`, so since step 11 `game_adfs` and `load_adfs` checked whatever ADFS disc the last `make game` left. Found when two overlapping `make game`s (my mistake) left a stale one: both failed against the rebuilt tracks. The disc step now makes both.
- **The score pickups' digits** (2026-11-08, Tom: "They just look like yellow boxes"): the ST's are white on pink, and option B makes the pink yellow. Six colourings rendered on track 1's road; Tom chose black digits on the yellow box, to be seen on a CRT, and after seeing it there: "Good, commit". D34: `objects.slot_bbc` marks the digits as colour 16, black in option B's map, used by `gendata.py` and `render_model.py`. The same bytes.
- **The demo's car 3** (2026-11-09): Tom saw cars hitting the wall in t5's demo and wondered about D20. The hits are
  the ST's. Its traces have cars 0 and 2 at x 299, y 69 in both demo races, and the BBC's demo races match them
  frame for frame. D20's real gap was colour: the demo drew car 3 from the drone-driven set with green stripes. Tom:
  "Yes, try it" to the no-cost version. The table entry for car 3 when it isn't a drone is now `DataBlack`, so car 3
  is black as in a race, 29 pixels from the ST's own frames. In jsbeeb, the first demo's screenshots differ from the
  old disc's only at car 3, which has lost its green. `make check TRACE=attract`, which draws car 3 from its own
  frames: all 572 frames match.
- **"Loading" from the boot's start** (2026-11-09, Tom's idea): D35. `!BOOT` sets up the game's screen in shadow
  MODE 1 with "Loading" in the HUD's row before it loads anything, and the files load into main RAM behind it. SPRINT's
  loader draws the same row into the main screen before showing it, and a load redraws its row after a vsync.
  `tools/boot_check.mjs`, in the suite on both discs, watches every field from SHIFT-BREAK to the title's file. On
  the old disc it fails: "Loading" first appears 470 fields after `!BOOT` starts. Now it's 9, and nothing changes
  until the file's in. **Mistakes, mine**: my first loader copied the row out of the shadow screen with ACCCON's X
  set, which hid the loader's own code from the CPU (as `entry.6502` says above `shared_copy`), and the game crashed;
  the check caught it. And building the old disc for that comparison left it in `build/`, so my first disc-error
  test ran on the old boot. On the new one, a missing bank file goes back to MODE 7 and says "Not found". Tom, on
  his Master: "Looks much better".
- **Track 1's parts cut from the boot's files** (2026-11-09): Tom noticed SPRINTA held track 1's whole background. The
  disc is made from track 1's play build, and SPRINTA ended in its `BgSlot` (16,000 bytes), SPRINTB in its
  `PrioSlot` (2,105). Neither is ever read: `game_go` copies the game's and front end's code over three quarters of the
  background at the boot, prepare's file is parked in the priority cells, and every race loads its track's file first.
  Tom: "Yes, cut them". `make_game.py` now cuts a bank's file where a slot at its end starts (SPRINTA 384 bytes,
  SPRINTB 12,067); the boot still copies 16K. `boot_check`: the title's file in at field 563, not 654, on DFS (1.82 s),
  759 not 840 on ADFS L (1.62 s); `load_check`: all 8 tracks load right. The DFS disc 701 sectors to 633. On Tom's
  Master: "it looks good".
- **The boot's files packed** (2026-11-09): Tom asked whether any files were ZX02 packed; the tracks' and the
  pictures were, the boot's five weren't, and nothing had been decided. Tom: "Yes, build it". `make_game.py` packs
  SPRINT and SPRINTA-D on the game's discs (60,134 bytes to 29,147) and gives each a load address that isn't `&3000`:
  a bank's packed file loads at `&4000` and `!BOOT` unpacks it straight into its bank (no 16K copy); SPRINT's loads at
  `&4D07`, `dfs.in_place_delta` ahead of its output, and unpacks into `&3000` in place. A file at `&3000` is copied as
  before, so the builds' own discs boot unchanged. `boot_check`: the title's file in at field 464, not 563, on DFS
  (1.98 s sooner), 649 not 759 on ADFS L (2.2 s); with the cut, 3.8 s sooner than this morning on both. The DFS disc 633
  sectors to 512. Two tools read the boot's files off the disc: `fileGate` (`game_check`'s stops) now unpacks a
  packed one (`unzx02` in `tools/jsbeeb.mjs`, proved against `t0.ssd`'s five files byte for byte), and
  `tools/cheat_disc.py`, which patched bytes it found on `game.ssd`, now makes its disc through `make_game.py`, its
  patches put into the raw files first (its disc boots with its low table). **Mistake caught by the check**:
  `game_check` failed all 3 games until `fileGate` unpacked. On Tom's Master: "Looks good and I left it running through
  the attract for about an hour without problems."
- **The bank probe** (2026-11-09): on Tom's Master, one boot printed "Loading", then characters 128-255, and hung.
  A BRK followed by junk, under the OS's BRKV, gives exactly that in jsbeeb: the message goes after "Loading", the
  rest to rows not shown. Between `!BOOT` and the title is the only time that can look so: a disc error during
  `!BOOT`'s loads goes to MODE 7, and during the game's to "... - press a key" (checked with TRACKF renamed).
  `tools/seed_check.mjs`, new: the Master's MOS clears main, shadow and HAZEL RAM at power-on, not ANDY or the banks
  (measured: `&A5` left in ANDY's 16 pages); with those full of junk, 230 boots ran to the title's file. jsbeeb's
  boots all keep the same time, the disc turning in step with the fields from power-on (two boots 80,000 cycles
  apart at `!BOOT`'s start reached SPRINT on the same cycle), so the check turns the disc to a random place as
  `!BOOT`, SPRINT and each load start: 480 DFS and 60 ADFS boots on agentbox, all to the title and 500 fields on.
  Tom asked what the bank 8 probe was for: nothing, it was the skill's Model B recipe (15 down to 0), and a stock
  Master's bank 8 is an empty socket, which the OS's type table doesn't list. Tom: the Master's data bus is
  unbuffered, so an empty socket reads the video's last byte, and the probe ran in MODE 7 with the boot screen up,
  calling a bank RAM when two reads differed: a space and a letter would do it. Not proven the cause (jsbeeb's
  empty socket reads 0), but it fits. Now (D4): banks 7 to 0, after MODE 129 has cleared the screen on show, a
  bank counted only if it reads back the `&FF` EOR written. In jsbeeb with the RAM in banks 0-3, 1/3/5/7, 4-7 and
  0-7 the game runs, on the highest 4; with 2/5/6 the error comes up in MODE 7. `boot_check`: "Loading" still 9
  fields after `!BOOT`, the title's file at 464. On Tom's Master: "Looks good on my Master 128, though it has the
  default config of sideways RAM in banks 4-7 so it wasn't exercising every case."
- **A RAM hunt** (2026-11-09; Tom: "this is probably worth thinking about next, as it's a potential blocker for any
  further work"; `docs/brief-ram-2026-11-09.md`). Three agents read main RAM's code, the fourth bank with ANDY and
  Shared, and the code between races, for levers; the shortlist went to Tom in batches. First, `tools/memmap.py` was
  wrong twice: TunesFixed counted as pshift's, and ANDY given 45 free (the first PRINT *containing* "ANDY"), not 237.
  `&0B00`-`&0CFF` was unwritten by DFS and ADFS in jsbeeb, but Tom: "On the Master 128, this is tagget as Econet
  workspace" (D26). Tom on ANDY: "ANDY can be assumed to survive every load" (D15). Batch 1 (Tom: "Build batch 1"),
  six levers, none costing cycles: the play build's restart path was dead (every race starts after its track's file
  has loaded, rewriting the slots), fourth bank +780 and main RAM +49; `say` and `TextAttract`, never called, first 4K
  +134; TunesFixed at the bank's end (its length from `tools/tune_gen.py`), +74; `fill_screen` into the background's
  bank below BgOrg, main RAM +76; `font_char` into LowFree's top, copied by the loader, +56; `human.6502` into the
  fourth bank, +780. Main RAM 222 to 1,183, the fourth bank 21 to 95, the first 4K 47 to 181. The hazard race: mean
  32,903 to 32,884 cycles, 116 frames over a TV frame both, fields repeated 8 to 6, every frame the model's. The
  suite 40/40 on agentbox, which built the same discs as here (`game.ssd` c41a9f80be30c74c01ceff6fdab5568ffe4f241d,
  `game.adl` 93468c98ad5246b7b9ee736c601dae94b8777e06).
- **BREAK after the game** (2026-11-09, Tom on his Master: "when pressing BREAK after playing the game, the character
  set can be messed up, because its RAM copy (held in ANDY) was overwritten"). His fix: OSBYTE 200,3 at the loader's
  start, so the next BREAK clears memory as power-on does and the MOS makes its soft font again (D15).
  `tools/break_check.mjs` boots the disc to the title's file, presses BREAK, and compares ANDY's `&8900`-`&8FFF` with
  a fresh machine's: 965 of 1,792 bytes wrong before, 0 after, on DFS and ADFS. Added to the suite. On Tom's
  Master: "I've tested on my Master."
- **The track's own text taken out** (2026-11-09; Tom: "the tracks still say `DRONE LAP` at the bottom", then "Would
  it be possible to apply a similar fix to remove the TRACK N lettering from the track as well?"). Filling the text
  green would have suited six tracks, but cut a tree on track 3 and left green letters on track 8's white road edge;
  "TRACK 5" has trees over it too. Tom chose the re-dump from Hatari, step by step. `tools/st_text_cells.py` finds a
  tile for each text cell that matches it everywhere but the text: one for every cell on all 8 tracks, track 8's
  edge included (the text tiles were the edge's tiles with the letters added). `st_dump_tracks.py --clean` writes
  those words into the map in the ST's memory (SUPER.DAT at `&29500`, checked against the file) before the track's
  set-up, which then draws its trees over clean ground: `bgclean_tN`, `maskcleanK_tN`, the old dumps kept. The new
  dumps differ from the old only inside the text cells (246 to 267 pixels a track); of the masks, the solid one
  (which the port doesn't read) and on tracks 5 to 8 the priority one change there too, the road mask not at all.
  The game takes the new picture and priority mask (`convert.py`, `gendata.py`, `render_model.py`). On the BBC,
  3,824 to 4,256 screen pixels change a track, all in the bottom row. Every track's free bytes the same; the suite
  41 of 41 on agentbox, the same discs as here (`game.ssd` bca7c0e28524fce7959178f4ea985cd89d5bce2a, `game.adl`
  13e2c19a4302ead964c4b72e344fc0b71846a108). On Tom's Master: "Looks good, though I didn't play every track."
- **The build's version** (2026-11-09; Tom, 2026-11-08: "so it's easier to be confident about which build you're
  playing"). Not on the loading screen (Tom: "if running from a fast filing system, the initial loading screen won't
  stick around for long enough"), but on the options screen: "in the bottom right corner, in the small font", the
  commit's first 5 hex digits, then "in green, so it's clearly different from the rest of the text". The Makefile's
  VERSION is git's, with "m" after it if the tree has changes (the small font has no "+"); `tools/version.py` writes
  the glyphs and the line `options_check` expects, each only when it changes, so an unchanged version rebuilds
  nothing. `opt_line` writes it after clearing the status line (x 284, or 278 with the "m"; the status texts end by
  252) and ANDs those bytes with `&0F`, white to green. The options' file 263 to 216 bytes free. agentbox has no
  `.git`, so `tools/suite_remote.sh` gives it the version from here. `options_check` passes, and with the version
  left out of what it expects finds 51 wrong. The suite 41 of 41 on agentbox at 9bcd0, the same discs as here. Tom,
  after trying 0b3c1's disc: "Looks good."
- **New default keys** (2026-11-09, D12; Tom: "White car: Left=Caps Lock Right=Ctrl Accelerate=A / Green car: Left=,
  Right=. Accelerate=/ / Yellow car: Left=Pad 5 Right=Pad 6 Accelerate=Pad Delete"). On the ghosting model the nine
  make no loop, so none ghosts another (0 of 511 combinations); but A, Pad 5 and Pad Delete ghost F1, read in the
  attract mode's waits, and Caps Lock, Pad 5 and Pad Delete ghost Escape, read on prepare to race. Pad 4 for Pad 5
  would clear both; Tom kept his: "I'll keep an eye out for it when testing." I was wrong twice on the way: that the
  Compact has no keypad (Tom: "the Master Compact definitely does have a numeric keypad"), and that prepare to race
  reads F1 (Tom: "The Prepare to Race screen doesn't appear to respond to the f1 key?": it's `wait`, the attract
  mode's, that reads it, not `fields`). `keys_check` now presses the keys by jsbeeb's own matrix table, as Caps Lock
  and the keypad have no host keys of their own there; it and `options_check` pass.
  Then white back on Q, W, E (Tom: "This will ensure the game is playable out of the box in single player mode with
  the default keys on jsbeeb"): jsbeeb has no host key for Caps Lock. With Q, W, E nothing ghosts at all, F1 and
  Escape included. On Tom's Master, 2026-11-10: "Tested on Master."
- **A crash handler** (2026-11-10). Before, a BRK went to the OS's handler from `!BOOT`'s hand-over to the title and
  between loads, with only the HUD's row shown or the game's screens up, so the machine looked hung. Designed with
  Tom: MODE 7 set from the hardware ("would it be cheaper overall to have it set Mode 7?": a teletext screen holds
  ASCII, no font or palette, and the OS's VDU workspace is in ANDY, which the game has), ACCCON showing the screen the
  CPU writes ("It'll need to make sure that ACCCON is set to display the same bank that's mapped in to RAM"), and only
  the BRK's address and the build's version ("Then any investigation can be done offline"): the MOS pages the
  language ROM in before BRKV (Tom), so ROMSEL is gone, and `&024A`'s copy of `&F4` is stale wherever the game
  doesn't keep `&F4` in step, which is 39 of its 47 ROMSEL writes. I'd said ROMSEL can't be read on the Master: it can
  (Tom), as can ACCCON; the skill's hardware notes say otherwise (`docs/upstream-notes.md`). `src/crash.6502` in main
  RAM's code, 164 bytes (1,183 to 1,019 free); the loader sets BRKV once that's in, and load_takeover keeps it as the
  BRKV each load puts back. `tools/crash_check.mjs` makes a BRK at the title and in the demo race at a frame showing
  one screen and writing the other (ACCCON `&14`), and reads the screen back; with the ACCCON fix broken in memory it
  finds 3 wrong.
  The suite: 42 of 42 on agentbox at f0d2009, `crash_check` among them. Merged untested on hardware, Tom: "There's
  not supposed to be any way to hit the BRK handler, so this will get ongoing testing just through general use."
- **Time attack, the brief and step 1** (2026-11-10, branch `timeattack`). Tom's idea: a special version, one player,
  endless laps, a ghost of the best lap, a table and ghosts saved per track. The brief,
  `docs/brief-timeattack-2026-11-10.md`, then his answers one by one, D36-D50: the ST's gates; a black ghost from the
  green car's set alone; a standing start, the ghost shown in it; 10-character names typed; 10 entries a track, all
  resident; a race enters its best lap; wrecks and gates kept; the ghost waiting at the line; a front end in 32 rows
  with the select screen's maps, the ST's small font and the credits' logo (mock-ups in `build/ta`, the chosen one
  `docs/img/timeattack-menu.png`); a track's screen with its 10 and the upgrades; a name every time, for hot seat.
  Step 1: `GenTimeAttack` and `make ta`, the game's discs the same byte for byte (`VERSION=ident` both), the suite 43
  of 43 on agentbox.
  Step 2: one car (`Cars`, 4 in the game), the green set alone drawn white, no pickups or optional hazards, endless
  laps, Escape out. The cars' bank 8,228 bytes freer on every track. Tried in jsbeeb by scripts: past lap 4 on, the
  demo still ending, a wreck put back as on the game's disc, no frames dropped. Tom: work in smaller steps here, each
  tried ("there being no existing target to work against"); step 2's disc for his Master before step 3.
  Step 3: the lap timing (`ta_lap`, the ST's measure) and the HUD, the lap's time, the best and the ghost's (Tom
  dropped the lap number, asked for 0.00 shown when there's none, and added the ghost's time). Checked by a script
  reading the HUD's text each frame around three poked crossings, and on the screen.
  Step 3c (2026-11-11, after Tom tried 3b): the code time attack never runs left out of its build, found by recording
  what runs, then read (the drones kept: the demo race uses them). The fourth bank 193 to 1,931 bytes free, main RAM's
  code 705 to 1,298. An autopilot along the drones' path drove every track before and after, the same every frame.
  Step 4 (2026-11-11): the ghost, recorded as drawn (car 0's record a frame, 1.1 to 1.4 bytes a frame coded from the
  last) into two buffers at the cars' bank's end, the best lap's kept; played back from each crossing, waiting at
  the line if its lap is done first, drawn as the black car in y order. `tools/ta_ghost_check.mjs` checks every
  frame's draw list against a model of the player's laps, 0 wrong over 19,200 frames; no frames dropped. Tom tried
  it: his car now always drawn over the ghost (he'd mixed them up), and a green player tried and reverted.
  Step 5a: each track's ghost saved as `GHOSTn` at the load after the race that made it, and loaded with the track,
  so lap 1 has it; `tools/ta_save_check.mjs` for the files' cases, as `save_check.mjs` is for `SCORES`. Tom tried
  it; no attract mode or demo race in time attack's front end (D51).
  Step 5b: the table, 10 entries a track in the cars' bank, a race's best entered as it ends, saved as `TIMES` with
  a sum when changed, loaded with each track until step 6; `tools/ta_table_check.mjs` against a model.
  Step 6 planned in pieces, Tom's answers D52-D54 (the driving keys and 1-8 on the menu, any player's keys drive,
  a simplified options screen). 6a: the tornado's frames out of the objects' bank (3,584 bytes). 6b: `tagame.6502`,
  a plain menu in place of the game's front end, the game's other screens off time attack's disc;
  `tools/ta_menu_check.mjs` drives it key by key. Tom tried it: "Looks good!". Then the drones and the demo's code
  out of time attack's build (D51), the path's place in Shared kept as room; the autopilot reads the path from the
  ST's data instead. The fourth bank 788 bytes freer, main RAM's code 340; play the same every frame.
  And the table read only at the boot's first load, kept from then on in the cars' bank.
  6c: the menu in 32 rows, switched to and from the race's 26 with the palette black; each track's file now puts
  back the whole of Shared, which the menu's rows overwrite (SCORES's sum kept in LowFree so it isn't saved each
  race). `tools/ta_rows_check.mjs` checks the screen field by field around the switches.
  Tom tried 6c on his Master (2026-11-12) and answered D55: no tunes in time attack (room kept for the front end's
  sound effects), and SCORES the keys and sound alone. Then the tunes out of time attack's build, and the drones'
  path's room that sat under their rings: Shared 1,292 bytes smaller, each track's file 276 bytes shorter.
  Then SCORES the keys and sound alone, 12 bytes saved from main RAM, `tools/ta_scores_check.mjs` its cases.
  Then Shared's part every track has kept in the fourth bank from the boot and put back before each track's load
  (Tom chose it over copying back from the shadow screen, which keeps the shadow screen free): track 1's file 6,001
  bytes, a load from the menu 1.73 to 1.95 s in jsbeeb, was 1.88 to 2.17.
