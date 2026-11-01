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
