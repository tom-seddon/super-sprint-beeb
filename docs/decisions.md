# Decisions

Each decision is Proposed until Tom agrees. Tom's words are recorded verbatim, with the date.

### D1. Palette and dithering: Decided (2026-11-01)
Proposed (2026-11-01, after Phase 2): option A2 from `docs/colours.md`, a black road with grey-outlined cars,
with option B (a grey checkerboard road, which keeps the bridges' shading) as the alternative.
Tom, after the viewer discs on a real BBC: "I think track viewer option B looks the best on a CRT. The
dithering looks like grey and isn't too busy."
So: option B. MODE 1 in black, green, yellow and white; the road a black/white checkerboard fixed to the
screen, its shadows black; the players' cars white, green and yellow with black outlines, car 3 and
drone-driven cars black.

### D2. Frame rate: Proposed
Proposed in the plan: 25 fps, double-buffered. Phase 1 found that the ST runs its race at 50 fps, logic and
drawing, with every speed and timer per frame. Proposed now: draw at 25 fps and run the game logic twice per
drawn frame, so every constant stays as the ST has it (`docs/st-logic.md` §12). 50 fps drawing to be tried
in Phase 3 if the timings allow.

### D3. Multiload or everything in memory: Decided (2026-11-01)
Proposed in the plan: a 1770 loader, one track's data per race. Phase 2 found that all 8 tracks' art packs to
about 20K (ZX02) and their masks to about 10K, but the race's data as a whole is about 90K against 64K of
sideways RAM (`docs/plan.md`), so the per-race load stands. It also frees room for unrolled code.
Tom: "For D3, multi load, I think it'd be nice if the game could use the standard OS entry points for loading
files. This would ensure compatibility with filing systems (e.g., MMFS and Econet)."
So: a multiload, one track's data per race, loaded through OSFILE with the OS brought back for each load. No
1770 loader. How the OS comes back is D7.

### D4. Machines: Proposed
Proposed in the plan: the Master 128 only (shadow RAM, ANDY, HAZEL, 64K of sideways RAM).
Decided in part (2026-11-01). Asked whether the game must run with a filing system loaded in sideways RAM,
leaving 3 banks, Tom answered: "No, need 4 free banks". So the game needs 4 banks of sideways RAM that the
ROM type table doesn't list; a filing system has to be in ROM. `!BOOT` counts the free banks and stops with a
message if there are fewer than 4.

### D5. Controls: Proposed
Proposed in the plan: two joysticks and the keyboard, as on the ST, once keyboard ghosting has been tested.

### D6. The HUD: Decided (2026-11-01)
Tom: "it might be worth showing the scores and lap indicators as simple 8-pixel text, outside the main 320x200
play area, rather than the large, masked text that the ST version uses."
Then: "I reckon one row would be enough. `99,999 L1` (for example) is 9 chars; now there's room for 3 of those
in 1 line, and still space for the drone's lap and the track number. It doesn't matter if it's a little
cryptic."
So: one row of 8 × 8 text above the 25-row play area, 26 rows in all.

### D7. Bringing the OS back for a load: Proposed
Proposed (2026-11-01, for D3): swap the OS's memory back in for each load rather than reserve it for the whole
game, as Chase HQ plans (its P5), but sized for the Master, where the filing systems' workspace is in HAZEL.
- **At the takeover**, after the OS has started the filing system: claim NMIs (OSBYTE 143, service call 12),
  so a network filing system stops listening, and copy the OS's state to a bank: zero page `&90`-`&FF`,
  `&0200`-`&03FF` and `&0800`-`&0DFF` (vectors, OS variables, buffers, the NMI handler at `&0D00`), and the
  part of HAZEL the ROMs have claimed. ANDY too if the MOS turns out to touch it during a load.
- **For a load**, between races: under SEI, put the game's copies of those areas in the screen not shown and
  the OS's back; give back IRQ1V, the VIAs' enables, ROMSEL with `&F4`, and ACCCON; release NMIs (service call
  11); CLI; OSFILE. The display shows only the HUD row ("LOADING", R6 = 1), so the rest of both screens is
  free to land the file in. The filing system's ROM is paged in at `&8000` during the call, so nothing loads
  straight into a bank: the file lands in main RAM, packed, and is unpacked into the banks.
- **Afterwards**: under SEI, copy the OS's state back to the bank (the filing system may have changed it: a
  catalogue, Econet's sequence numbers), put the game's back, claim NMIs, and take over again.
- **Traps known from Rich's projects**: the files' load addresses carry `&FFFF` (Chase HQ: `&0000` would go
  over the Tube); both DFSes write the catalogue back into OSFILE's block, so the load address goes back in
  before each call (Teddy Boy); `!BOOT` uses only banks the ROM type table doesn't list, so a filing system in
  sideways RAM is spared (Chase HQ); the 1770 DFS's NMI claim runs the ROMs' service calls with interrupts off
  for 582 us (Teddy Boy), harmless between races.
- **Also needed**: BRKV caught while the OS is back, so a disc error shows in the HUD row and offers a retry;
  Escape off (`*FX229,1`); the OS's colour flashing off (OSBYTE 9 and 10), since its IRQ would otherwise
  rewrite the ULA's control register; no VDU calls.
- **To measure in Phase 3**, on DFS, MMFS, ADFS and, if one can be had, Econet: how much of HAZEL each claims,
  and whether the MOS touches ANDY during OSFILE or its IRQ. If the filing systems claim most of HAZEL, leaving
  HAZEL to the OS for the whole game is simpler at the same cost, and the code goes elsewhere.
- Cost: up to about 12K of a bank for the OS's copy (3K of pages, up to 8K of HAZEL, zero page), against 8K of
  HAZEL and the low pages kept for code. Unpaged code space is scarcer than a bank's data space, so the swap
  is worth it unless the measurements say otherwise.
