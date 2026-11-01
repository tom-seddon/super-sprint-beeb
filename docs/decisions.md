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

### D2. Frame rate: Decided (2026-11-01)
Proposed in the plan: 25 fps, double-buffered. Phase 1 found that the ST runs its race at 50 fps, logic and
drawing, with every speed and timer per frame. Proposed then: draw at 25 fps and run the game logic twice per
drawn frame, so every constant stays as the ST has it (`docs/st-logic.md` §12). 50 fps drawing to be tried
in Phase 3 if the timings allow.
Tom: "D2: I think 50 Hz should be the goal, even if it currently seems like the timing would be be tight.
It'll make a big difference when played on a CRT."
So: 50 fps, double-buffered, the logic once a frame as on the ST: 40,000 cycles a frame. The estimate is about
42,000 (`docs/plan.md`), so the work is to get under it. The main loop counts vsyncs and runs the logic once
for each, so a frame that overruns costs that frame only: the game's speed stays right, and the display drops
to 25 fps for a moment.

### D3. Multiload or everything in memory: Decided (2026-11-01)
Proposed in the plan: a 1770 loader, one track's data per race. Phase 2 found that all 8 tracks' art packs to
about 20K (ZX02) and their masks to about 10K, but the race's data as a whole is about 90K against 64K of
sideways RAM (`docs/plan.md`), so the per-race load stands. It also frees room for unrolled code.
Tom: "For D3, multi load, I think it'd be nice if the game could use the standard OS entry points for loading
files. This would ensure compatibility with filing systems (e.g., MMFS and Econet)."
So: a multiload, one track's data per race, loaded through OSFILE with the OS brought back for each load. No
1770 loader. How the OS comes back is D7.

### D4. Machines: Decided (2026-11-01)
Proposed in the plan: the Master 128 only (shadow RAM, ANDY, HAZEL, 64K of sideways RAM).
Decided in part (2026-11-01). Asked whether the game must run with a filing system loaded in sideways RAM,
leaving 3 banks, Tom answered: "No, need 4 free banks". So the game needs 4 banks of sideways RAM that the
ROM type table doesn't list; a filing system has to be in ROM. `!BOOT` counts the free banks and stops with a
message if there are fewer than 4.
Tom: "D4: Master 128 only is fine. This means 65c02, more flexible shadow RAM, and leaves open the option of
using HAZEL for something."
So: the Master 128 only, with what that allows:
- **CMOS opcodes**, in sections with Baron's `cmos = TRUE`. This overrides the beeb-baron skill's NMOS-only
  rule for this project (noted in `CLAUDE.md`). The Master's CPU is a 65C12: `BRA`, `STZ`, `PHX`/`PHY`/
  `PLX`/`PLY`, `TSB`/`TRB`, `(zp)`, `INC A`/`DEC A`, `JMP (abs,X)` and the extra `BIT` modes, but not the
  Rockwell bit opcodes (`RMB`, `SMB`, `BBR`, `BBS`). Baron's CMOS set matches: it assembles the first and
  refuses the second (checked with `baron --check`). Cycle counts are the 65C12's, and some differ from NMOS
  (`JMP (abs)` is 6).
- **Shadow RAM through ACCCON** (`&FE34`): bit 0 (D) picks the screen displayed, bit 2 (X) sends all of the
  CPU's `&3000`-`&7FFF` accesses to shadow, bit 1 (E) only those made by code running at `&C000`-`&DFFF`.
- **HAZEL** stays the OS's for now (D7), free to be taken later.

### D5. Controls: Decided in part (2026-11-01)
Proposed in the plan: two joysticks and the keyboard, as on the ST, once keyboard ghosting has been tested.
Tom: "let's leave open the option of having the 3rd player on keyboard too, as well as possibly on joysticks,
as joysticks weren't super popular on the BBC. Leave thinking about keyboard clash until later."
So: any player can be on the keyboard, all three included, and the joysticks are an option rather than the
way in. The input code reads each player's left, right and accelerate from either. Which keys, and what
ghosting allows, is left until later.

### D6. The HUD: Decided (2026-11-01)
Tom: "it might be worth showing the scores and lap indicators as simple 8-pixel text, outside the main 320x200
play area, rather than the large, masked text that the ST version uses."
Then: "I reckon one row would be enough. `99,999 L1` (for example) is 9 chars; now there's room for 3 of those
in 1 line, and still space for the drone's lap and the track number. It doesn't matter if it's a little
cryptic."
So: one row of 8 × 8 text above the 25-row play area, 26 rows in all.

### D7. Bringing the OS back for a load: Decided (2026-11-01)
First proposed (2026-11-01): swap the OS's memory, HAZEL included, to and from a bank around each load, so the
game could use HAZEL for code. Tom asked whether the game would actually need all that or whether it was being
kept aside just in case, and pointed out that a bank's paging costs little and gives a lot of contiguous space
for unrolled loops. It was just in case: nothing measured says the game needs HAZEL. So, revised:
- **Leave the OS's memory to the OS**: HAZEL, `&0200`-`&03FF` and `&0800`-`&0DFF`. The game writes only the
  vectors it hooks (IRQ1V, BRKV), and puts them back for a load. Zero page `&90`-`&FF` (112 bytes) is the
  game's during a race and swapped with a copy in main RAM around a load. ANDY stays the OS's unless Phase 3
  shows the MOS doesn't need it kept.
- **The game's unpaged space** is then zero page, `&0400`-`&07FF` (the language's workspace), `&0E00`-`&2FFF`
  and `&3000`-`&3EFF`: about 13.5K for the IRQ, the main loop, the logic and the state. The renderer and other
  big or unrolled code go in the banks, each beside the data it reads; paging is a `STA &F4:STA &FE30`.
- **At the takeover**, after the OS has started the filing system: claim NMIs (OSBYTE 143, service call 12),
  so a network filing system stops listening.
- **For a load**, between races: under SEI, swap zero page, give back IRQ1V and BRKV's old values, the VIAs'
  enables, ROMSEL with `&F4`, and ACCCON; release NMIs (service call 11); CLI; OSFILE. The display shows only
  the HUD row ("LOADING", R6 = 1), so the rest of both screens is free to land the file in. The filing
  system's ROM is paged in at `&8000` during the call, so nothing loads straight into a bank: the file lands in
  main RAM, packed, and is unpacked into the banks. Then the reverse.
- **Traps known from Rich's projects**: the files' load addresses carry `&FFFF` (Chase HQ: `&0000` would go
  over the Tube); both DFSes write the catalogue back into OSFILE's block, so the load address goes back in
  before each call (Teddy Boy); `!BOOT` uses only banks the ROM type table doesn't list (Chase HQ); the 1770
  DFS's NMI claim runs the ROMs' service calls with interrupts off for 582 us (Teddy Boy), harmless between
  races.
- **Also needed**: BRKV caught while the OS is back, so a disc error shows in the HUD row and offers a retry;
  Escape off (`*FX229,1`); the OS's colour flashing off (OSBYTE 9 and 10), since its IRQ would otherwise
  rewrite the ULA's control register; no VDU calls.
- **Cost**: 112 bytes of main RAM, and HAZEL's 8K, ANDY's 4K and about 2K of low pages not available to the
  game.

Tom: "I think copying HAZEL is worth considering, as it's an 8 KB chunk. But for the main RAM in OS, it feels a
bit more questionable to exchange 2 KB of contiguous sideways RAM for 2 KB of fragmented main RAM. I agree with
the idea of leaving this stuff alone for now, and revisiting if the game turns out to actually need it."
So: leave the OS's memory alone for now, as above. If the game turns out to need more room, the first thing
to consider is HAZEL, swapped through a bank (sized by how much each filing system claims: DFS, MMFS, ADFS,
Econet). The OS's low pages stay the OS's: 2K of contiguous bank isn't worth giving up for 2K of fragmented
main RAM.
