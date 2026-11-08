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
Tom, 2026-11-03: "D5: let's leave joysticks open for now. I think it's probably worth supporting, but not urgent. Joysticks weren't terribly popular on the BBC, and the sort of digital arcade-type joystick that would work for ST Super Sprint even less so." And: "3 players on keyboard is a bit of a squeeze but this can wait until a proper 3 person playtest."
So the joysticks are open and not part of Phase 4; the three-player keyboard waits on a three-person
playtest (with D12's real-keyboard check).

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
  shows the MOS doesn't need it kept (revised by D15, 2026-11-02: the game's, for mask B and the logic's state).
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
  Escape off (`*FX229,1`); the OS's colour flashing off (OSBYTE 9 and 10 with X = 0, and OSBYTE 193 to clear a
  count in progress, built 2026-11-03), since its IRQ would otherwise rewrite the ULA's control register; no VDU
  calls. The System VIA's DDRB stays the OS's `&CF` (MOS 3.20 sets it only at reset, and PB6-7 reach the CMOS chip,
  where the filing system reads its seek time: found by Tom on a real Master, 2026-11-04).
- **Cost**: 112 bytes of main RAM, and HAZEL's 8K, ANDY's 4K and about 2K of low pages not available to the
  game.

Tom: "I think copying HAZEL is worth considering, as it's an 8 KB chunk. But for the main RAM in OS, it feels a
bit more questionable to exchange 2 KB of contiguous sideways RAM for 2 KB of fragmented main RAM. I agree with
the idea of leaving this stuff alone for now, and revisiting if the game turns out to actually need it."
So: leave the OS's memory alone for now, as above. If the game turns out to need more room, the first thing
to consider is HAZEL, swapped through a bank (sized by how much each filing system claims: DFS, MMFS, ADFS,
Econet). The OS's low pages stay the OS's: 2K of contiguous bank isn't worth giving up for 2K of fragmented
main RAM.

### D8. Object sprites: the explosion and the helicopter on 4-pixel steps: Decided (2026-11-01)
Proposed (2026-11-01, Phase 3): the moving objects stored pre-shifted as the cars are would take about 21K,
more than a bank. Snapping the explosion (26 frames, 16 x 14) and the helicopter (4 frames, 48 x 36) to
4-pixel steps, so each needs one shift, brings the objects to about 8K; either can then sit up to 3 pixels
left of where the ST draws it. The banner (fixed per track) and the sparks (8-pixel aligned on the ST) need
one shift anyway; the background objects (gates, barriers, pickups) are 16-pixel aligned; the tornado keeps
its 4 shifts (about 1K).
Tom: "Yes, snap them. The snapping can be reconsidered later if it looks too ugly."


### D9. How exact the race logic is: Decided (2026-11-02)
Asked at the start of Phase 4. Tom: "the race logic is bit-exact with the ST - same arithmetic, tables and
random number generator - checked frame by frame against Hatari traces with the same inputs."
So: every routine of the race is the ST's, transliterated, its 16-bit signed arithmetic and its rounding
kept; the tables are the ST's; the random numbers come from TOS's own generator (XBIOS Random) started from
the same seed. The check is a Hatari trace of a race (inputs, every per-car variable, every random number,
frame by frame) replayed on the BBC and compared variable by variable (`docs/brief-phase4.md`). What this
rules out: st-logic §12's cheaper forms that change results, a fixed car shape per facing for the wall
probes (7 of the 16 facings' shapes differ between the car sets, `tools/maskb_stats.py`), reciprocal tables
that round differently from the ST's division.

### D10. The first track: Decided (2026-11-02)
Tom: "track 1 (index 0). Get physics, drones, laps, scoring and sound right there, then the others."

### D11. Sound: Decided (2026-11-02)
Tom: "50 Hz from the vsync IRQ. Jingles and effects captured from the ST in Hatari and converted offline to
SN76489 register streams (the beeb-port-kit's ay2sn.py approach, with the YM's hardware envelope stepped
first); engine tones computed live from each car's speed."
So: no sequencer on the BBC and no 83 Hz timer. Each tune and effect is the YM's registers captured from the
running ST, its hardware envelope stepped into volumes, converted to SN76489 writes a frame (`ay2sn.py`), and
played by the vsync IRQ. The engines (one tone per human car) are worked out each frame from the car's speed
by `F_012BA2`'s formulas. Effects take a car's channel by the ST's priorities (st-logic §8).

Built 2026-11-02 (brief step 10). The details taken, agreed by Tom 2026-11-03 (below), heard in (`build/sound/race_bbc.wav`
against `race_st.wav`, and each effect's `build/lgen/wav/*_ym.wav` against `*_sn.wav`):
- each effect is one captured instance (its fields at the ST's VBLs; another instance differs a little, by
  where the 749 Hz timer stood);
- a channel with tone and noise both on plays the noise alone (the kit's 1942 rule, `tn_noise`: the SN can't
  gate one by the other): the skid, the slow patches, the crash, the helicopter;
- a period over 1023 goes up an octave at a time, so the engine (3000 - 4 * speed +- 900) sounds two
  octaves up, and its +- 900 alternation (every rate + 1 ticks of 749 Hz, 50 to 125 Hz) is sampled at 50 Hz;
- the race's start keeps the ST's 1 s pause (50 VBLs), the start's sound in it.

The engine agreed, Tom, 2026-11-03: "D11: the general engine sound sounds good to me." Then: "D11: the sounds all sound good to me." So all four details are agreed.

### D12. Keys: Decided in part (2026-11-02)
Tom: "propose a three-player keyboard layout, check it for ghosting on paper and in jsbeeb, joysticks as an
option alongside; I'll test it on a real BBC later."
So: a layout for three players on the keyboard (left, right, accelerate each), its internal key numbers
measured, every combination of held keys worked through against the matrix for ghosts on paper and the
keys held together in jsbeeb (which may not model ghosting: the check there is that each is read); the
Master's two joysticks as an option for any player. The layout itself is Proposed until Tom has tried it on
a real BBC. Hardware gate: real keyboard.

Proposed layout (2026-11-02): player 1 Q left, W right, E accelerate; player 2 V, B, N; player 3 comma,
full stop, slash. (First proposed with player 1 on Z, X, SHIFT; Tom: "instead of Z/X/SHIFT, what about
Q/W/E? The shift key is not ideal, as there are 2 shift keys, both equivalent, on opposite sides of the
keyboard." Q, W and E are in the same columns, 0-2, so the property below holds.) The matrix has no diodes, so held keys can make a key whose row and column they join read
as held; each of these nine keys is in a column of its own (0 to 8), so no combination of them can ghost
another of them. `tools/keys_ghost.py` checks all 511 combinations on that model (0 ghost) and the model
against a ghost seen on hardware (Paradroid's Z, X, K, M, L firing C). Key numbers measured (the kit's
table; comma 102 and full stop 103 measured with jsbeeb-mcp's key_down on a Master). In jsbeeb, which has
no ghosting, `tools/keys_check.mjs` holds each alone and all nine together and the game reads each as its
player's. The disc to try it: `make beeb TRACE=play` (track 1, three players, car 3 the drone, the race
restarting when it ends). Alternatives if a key is awkward: any other key in the same column keeps the
property (SLASH's column 8 also holds `:`, `]`, `[`, `^`, `_`, `\`; RETURN, in column 9, is free for any one
player). Not built yet: the joysticks (the Master's ADC and the fire buttons are to be measured first), left
open by Tom 2026-11-03 (D5).
The real keyboard's gate deferred, Tom, 2026-11-03: "D12: I think this one can wait. If there turn out to be problems with the keys chosen, we can choose a different set." The layout stays as built; a
problem found later means another set, each key still in a column of its own.

### D13. Mask B (walls): only the mixed cells: Decided (2026-11-02)
Proposed for Phase 4's first steps (`docs/brief-phase4.md` §3).
Mask B is 8,000 bytes a track at 1 bit a pixel, 70% of the fourth bank's 11,361 free. Of its 1,000 8 x 8
cells, 144 to 267 a track are neither all road nor all wall (track 1: 144, 1,152 bytes; track 8: 267,
2,136; `tools/maskb_stats.py`). Options:
- (a) the whole mask: 8,000 bytes, a read about 15 cycles; no room left in the bank for sound or the
  logic's data;
- (b) rebuilt per race from the wall vectors: saves disc, not RAM;
- (c) **proposed**: as the priority mask (`docs/renderer.md`): 8 bytes for each mixed cell, a map of each
  row's span (a byte a cell: road, wall or its number in the row); a read about 30 cycles (projected),
  and none at all for a car whose cells are all road. The gates' and barriers' cells reserved as mixed and
  written from precomputed runs. Measured with them (`tools/maskb.py`): 2,168 bytes on track 1, 3,427 at
  most (track 8), decoding to the ST's mask with 0 bytes wrong on every track.
Tom: "Yes, D13 as proposed"

### D14. The drones' dead accumulators (G_01E2DC, G_01E2D4): Decided (2026-11-02)
Each frame a drone adds its move to G_01E2DC/G_01E2D4 (its moves since its segment's start, x8 and y8), and
zeroes them on a new segment. Only F_00F92E reads them, and nothing calls F_00F92E (`docs/st-logic.md`
"Dead code"). The BBC keeps them as RcAccX/RcAccY because D9 compares every per-car variable. Options:
- (a) keep them (as now): D9 to the letter;
- (b) **proposed**: drop them, and drop accx/accy from `tools/logic_check.mjs`'s list with this row as the
  reason. Nothing the race does changes. MEASURED (a build without them, 2026-11-02): the hazard race's
  logic 14,191 -> 14,056 cycles a frame (mean), the fourth bank 46 bytes more (track 5's traced game 10 ->
  56 free), and 16 bytes of the logic's state.
Tom: "Yes, drop them"
Built 2026-11-02: RcAccX/RcAccY gone from `src/drone.6502` and accx/accy from `tools/logic_check.mjs` (162
variables compared); the logic's state reserves 16 bytes less, so track 5's fourth bank 10 -> 72 free.

### D15. ANDY for the logic's data: Decided (2026-11-02)
D7 left ANDY to the OS "unless Phase 3 shows the MOS doesn't need it kept". Tom, 2026-11-02: "I don't think the
OS doesn't use this for anything relevant to the game: it's some OSWRCH bits, and function key definitions.
If not already used, it should therefore be free for game use without interfering with any filing system
stuff." It isn't used (no ROMSEL write sets bit 7), and the kit measured the MOS writing it only on `*KEY`, a
mode change or soft BREAK, and `VDU 23`, and not in 26 OSFILE loads (`reference/beeb-port-kit/docs/
hardware-facts.md`, ANDY; jsbeeb, MOS 3.20, 1770 DFS). Proposed (`docs/brief-room-2026-11-02.md`): mask B
and the logic's state in ANDY, filled by the loader at the takeover, paged in with the fourth bank while the
logic runs (the helicopter, in the bank's first 4K, is drawn only outside it): the fourth bank 3,536 free on
every track, where tracks 6 and 8 are now 138 and 322 over. First measured for this game: ANDY seeded, then
the boot, a whole race and an OSFILE with the OS brought back, ANDY unchanged. Not measured: ADFS, MMFS, real
hardware (with D7's loads, Phase 5).
Tom: "Yes, build it" (to the proposal). Built 2026-11-02 (`docs/brief-room-2026-11-02.md` §7). Measured first,
jsbeeb Master (MOS 3.20, 1770 DFS): ANDY seeded after the takeover, 0 of 4,096 bytes changed after the hazard
race's 2,240 frames; from BASIC, 0 changed after `*LOAD` of the disc's five files and `*CAT`, 30 after
`*KEY 1 HELLO`. So D7's "ANDY stays the OS's" no longer holds: the game fills it at the takeover; the OS's
soft keys and user-defined characters there are lost, which the game never uses.
A fault found in step 13 (2026-11-02): the premise that the logic never reads the helicopter was wrong.
`heli_pieces` (logicframe) reads its plotter's `MovDX` and `MovW` to leave out pieces off the screen's side, and
with ANDY in it read mask B; track 2's sideways helicopter showed it (track 5's comes from below). It now pages
ANDY out for those reads.

### D16. The helicopter: not drawn, a cue in its place: Decided (2026-11-02)
After speed's fourth round the hazard race's slowest frames are its start (the helicopter on screen, about
7,700 cycles a frame, 4,700 of them its copy loop, with the gates stepping) and its pile-ups (the helicopter
with cars under a bridge and against walls). Tom, 2026-11-02: "If the helicopter is just inherently going to
be too expensive, maybe we should just get rid of it? It's purely cosmetic and could be replaced with some
alternative effect. This would presumably free up some space that could be spent on optimising something
else that's relevant to the gameplay."
In the logic the helicopter is a timer: a wrecked car waits for its flight (40-100 frames, by distance,
`docs/st-logic.md` "Wrecks and the helicopter") and only one flies at a time. That stays, bit-exact (D9); only
the drawing goes. MEASURED (a build with the helicopter's pieces left out of the movers, its logic kept,
2026-11-02, `make check TRACE=logic4`): the hazard race's frames over a TV frame 150 -> 101 of 2,240, the mean
32,224 -> 31,698 cycles, the 99th percentile 47,350 -> 43,738. The model differs in the 116 frames the
helicopter is on screen, as it must.
Room: the helicopter is 5,114 bytes of the fourth bank (its plotter's copy and tables at &8000, its 84
pieces to &93F9): all 4K under ANDY, usable only with ANDY out (as the helicopter now is), and 1,018 bytes the
logic can use directly. One use for gameplay: mask B back out of ANDY into that 4K, leaving ANDY for a
second, transposed copy of mask B's mixed cells, so a wall column's test over a mixed cell is one AND, not a
loop over its lines (about 300-400 cycles in the wall-scraping frames, PROJECTED; 2,136 bytes on track 8).
Options:
- (a) keep it, as now.
- (b) leave it out: the wreck stays where it is until the car is put back, at the ST's frame.
- (c) **proposed**: as (b), with a cue where the helicopter would have shown the player where the car comes
  back: in the wait's last frames, the wreck replaced by the car blinking at its put-back place. It's drawn
  as the wreck is (one of the four car records, the cars' plotter), so it costs about what the wreck does:
  PROJECTED the same as (b). The car frames exist already; no new data.
- The sound (the helicopter's chop, D11) either way: kept as the car's "coming back" sound, or the engine
  back at the wreck's end. Proposed: kept, for your ears.
  Tom, 2026-11-03: "D16: let's leave the helicopter sound in for now, but I'm not 100% sure about it, and perhaps it'd be better to replace it with another sound." So kept for now, open. Its cost, MEASURED in the play
  build's listing: the wreck effect (`Fx_wreck`, `&34A0`-`&3631`, in Shared, both screens' `&3070`-`&3EFF`) is
  134 fields, 402 bytes: the crash 22 fields (66 bytes), then the chop 112 (336 bytes), looped until the car
  is back. The loop is only the chop's: `FxLoop` (11 bytes) and its four instructions in `sound.6502`.
Either (b) or (c) also changes the renderer's tests: the model (`tools/render_model.py`) leaves the
helicopter out of the races drawn from the logic, and the traced races' helicopter checks (`make check`,
`heli1`-`heli3`) go with it.
Tom: "Blinking car cue sounds good." Then: "Moving mask B back out of ANDY sounds like it'd be worth trying
after that, then measuring the result."
Built 2026-11-02, (c): in the game (the races drawn from the logic) the helicopter isn't drawn; its logic, its
timing and its sound are the ST's still. `build_cars` (logicframe) draws, in a wreck's last 28 frames
(`CueFrames`; `RcBounce` is the frames left), the car at its safe place on the ground for 4 frames and not for
4, shown first and last; the model (`render_model.py --cue`) the same, from the ST's own wait and safe place
in the race's logic trace (G_01E3B4, G_01E3EC/E4/DC, frame for frame with the race's draw trace). The traced races (Phase 3's renderer tests, `heli1`-`heli3`) keep the ST's
helicopter. MEASURED (`make check`, every frame matching the model): the hazard race 150 -> 106 frames over a TV
frame, mean 32,224 -> 31,874; track 1's race mean 23,939 -> 23,534. The fourth bank 1,476 -> 2,608 free on every
track (play builds), and its first 4K, under ANDY, empty.
Two faults the track checks found (2026-11-03), fixed: the cue's y used the byte holding x's high bit, so a
car put back at x 256 or more was drawn 256 to the left (tracks 2 and 8); and the model first found the cue
from the frame the car is drawn again, which a race that ends with a car still wrecked doesn't have (track 6),
so it now reads the wait from the logic trace.
Mask B and ANDY, after (2026-11-02): the copy of mask B's mixed cells by column this row proposed for the
room was built (`7b70c1c`, above ANDY: mask B didn't need to move) and measured: exact, the game's mean 31,874
-> 31,771, its frames over unchanged at 106, for 1,200-2,320 bytes. Tom: "Yes, revert it." Reverted; the room
is free.

### D17. The flip at the display's end, or in the blank: Decided (2026-11-03)
A drawn frame was shown at the vsync after it was done (the vsync interrupt flipped ACCCON's D), so one that
missed a vsync waited a whole field, and the next started then. In this mode the display ends at scan line
208 (26 rows), the vsync comes at 248 (R7 31) and the next display starts at 312 (39 rows): a blank of 104
lines, 13,312 cycles, of which a flip anywhere is unseen. Tom, 2026-11-03: "Regarding waiting for vsync: the
vsync occurs at scanline 272, well past the physical end of the visible display. What if there were a VIA
timer set up to interrupt at the point the visible display ends? Then the next frame's processing could start
the moment the last visible scanline of the current frame has scanned out." (272: the lines from the vsync to
the display's end.) So: a frame done during the display is shown at its end, by a System VIA T1 interrupt
started at each vsync; one done during the blank flips at once; never two flips in one blank. SIMULATED on the
nine races' per-frame cycles (logic and drawing): fields repeating a frame 332 -> 28 (the vsync and an
8,000-cycle late window: 50; with the logic run a frame ahead as well: 9, for about 15 ms more latency). The
keys are read about 2.6 ms earlier than the frame's showing, and a field less in the frames that were late.
Tom: "Yes, build it". A hardware gate: a new interrupt source and flip timing, to be seen on a real Master.
Built 2026-11-03: the vsync interrupt starts System VIA T1 and T2 (one-shot); T1, 3 lines after the display's
end, opens the blank and shows a waiting frame; T2, 3 lines before the next display, closes it; a frame done
in the blank is shown by the main loop at once, interrupts off (`irq.6502`, `main.6502`). MEASURED in jsbeeb
over the hazard race (2,240 frames): the vsync interrupt in at line 250 (2 lines after its edge, not the kit's
4), T1's 2,092 flips all at line 212, the main loop's 148 between lines 212 and 309, T2 at 310: every flip in
the blank (208-311). Fields repeating a frame (`render_check`, now counting irq.6502's `Repeats`), the nine
races drawn from the logic: 332 -> 42 (tracks 1 and 1's race 0: 0; 2: 14 -> 2; 3: 71 -> 12; 4: 17 -> 1; 5:
105 -> 5; 6: 70 -> 12; 7: 32 -> 8; 8: 25 -> 2), every frame still matching the model. Seen on a real Master, Tom, 2026-11-03:
"D17: looks good. No noticeable tearing running on real Master 128 with CUB."
The logic run a frame ahead (simulated above: 42 -> about 9 repeated fields, for about 15 ms more latency)
closed, not built, Tom, 2026-11-03: "Run-ahead logic: let's close this, on the basis it's ended up unnecessary. The current setup is fine, and lower latency is better."

### D18. The front-end screens' colours: Decided (2026-11-03)
Proposed (`docs/brief-phase5.md` §6): (a) each screen its own 4 of the BBC's 8 colours, dithered, converted as
Phase 2 did the tracks, with option sheets and a viewer disc; or (b) the race's palette for all.
Tom chose (a) ("Own palette each").

### D19. How exact the game around the race is: Decided (2026-11-03)
Proposed: (a) D9 extended to the select dial, joins, bonuses, elimination, upgrades, next track and race count
and the demo race, bit-exact with the ST and checked against Hatari traces; the screens' layouts by eye.
Tom chose (a) ("Bit-exact, traced").

### D20. The cars' frames per race: Decided (2026-11-03)
Proposed: (a) a file per combination of human cars (the 7 non-empty subsets of cars 0-2 and the demo's four
own colours: 8), the generator as it is; (b) a file per colour, the frame tables built at the load.
Tom chose (a) ("File per combination"), (b) only if the disc doesn't fit (D22).
Revised, Tom, 2026-11-04 (found building it: a real race only ever draws cars 0-2's own sets and the drone-driven
set, car 3 always being a drone, and those four are one 10,275-byte block): **all four resident, no files per
combination**. Any mix of humans picks its sets by each car's drone flag; the wall probes' shapes likewise (they'd
been fixed from the trace, wrong by one pixel of player 2's car at facing 6, the line 3 column 4 that the drone-driven frame hasn't; not, as first written here, players 2 and 3 on 2-5 facings). It costs no bank room, since the slot had
to hold the largest anyway, and saves about 5.8K a load, about 40K of disc and 7 catalogue entries. Only the demo
differs: car 3 in its own colours, which aren't the drone-driven set through `DataBlack` (12 of 16 facings differ),
so one small file at step 6. (Step 6 left it out, 2026-11-04: the demo draws car 3 in the drone-driven set for now,
and Tom's to say when: `docs/brief-phase5.md` step 6.)

### D21. Withdrawn (2026-11-03)
Proposed as "every object variant a track can draw"; the play build already makes them from the track's
tables, not a traced race (`tools/gendata.py`'s `logic_objects`), so there was nothing to decide.

### D22. The disc: Decided (2026-11-03)
Proposed: (a) one 80-track single-sided DFS disc (200K, 31 files) that copies as it is to MMFS, ADFS or
Econet; (b) double-sided, the second side as drive 2; (c) ADFS only.
Tom chose (a) ("80T single-side DFS"); its size and catalogue are measured at the brief's step 3.

### D25. The display between races: Decided (2026-11-03)
Proposed (`docs/brief-phase5.md` §6): every screen in the race's 26 rows (CRTC R6 = 26, start `&3F00`), the
ST's 320 x 200 pictures in the play area's 25 rows and the HUD row blank or used for text; or a 25-row
screen for the front end, with a CRTC change around each race.
Tom: "I think keep the race's 26 row layout for all screens, so the screen only needs to get set up once. The spare row can be erased as appropriate."
So: one layout for the whole game, set up once; the wipe runs between a race and a screen with no CRTC change.

### D23. High scores and lap records: Decided (2026-11-03)
Proposed (`docs/brief-phase5.md` §6): (a) saved to disc after each game as the ST does (its 295-byte
`SSPRINT.HSC`), a failed save (a write-protected disc, Econet without rights) said in the HUD row and ignored;
(b) kept for the session only.
Tom chose (a) ("Save to disc").
Then: "One note about the high score saving: this is a good feature, but lower priority. If the disk runs out of catalogue entries, or if handling all the error cases takes up too much room, it can be abandoned."
So: saving is lower priority; it gives way to the disc's catalogue and to room, and is dropped (scores kept
for the session) if either runs short.
Built 2026-11-08 (brief step 10), with the keys and sound the options set (Tom, 2026-11-06: "saving keys and
sound belongs with step 10's save"). One file, `SCORES`, 307 bytes: `SSPRINT.HSC`'s 295 as the ST has them, the
sound flag, the nine keys and a 2-byte sum. Not on the disc as built: the first save makes it, so a disc that's
never saved to has 20 files (of 31). Saved as the title's file loads (after every game, as the ST's
F_010760, and on leaving the options), only if the sum's changed; a failed save's error is said in the HUD's
row with " - press a key", and isn't tried again until something else changes. Read at the boot if it's there,
307 bytes long and its sum good; otherwise the table and keys as built. Room: the first 4K 10 bytes, the &3000
area 12 (3 left), main RAM none; the save's code is TRACKF's last 106 bytes, the load's in the loader (SPRINT's, run once).

### D24. The ST's keys: Decided (2026-11-03)
Proposed: the ST's F1 options, F5 the celebration shortened, F8 pause, F10 the race abandoned, Esc prepare to
race ended, F9 sound on/off; on the BBC f1, f5, f8, f0 (it has no f10), Escape read from the matrix (Escape
itself is off, D7), f9. The options screen offers each player keys or (later, D5) a joystick, and sound.
Tom chose it as proposed ("Yes, as proposed").

### D26. `&0900`-`&0AFF`, the MOS's serial and cassette buffers: Decided (2026-11-03)
Revises D7, which left `&0800`-`&0DFF` to the OS. Tom, 2026-11-03, on the memory map: "$900...$aff - tape/serial
buffers, again not used by the game". Then: "These regions are documented in the official Master Reference
Manual."
So: `&0900`-`&0AFF` (512 bytes) is the game's, kept across loads. Checked in jsbeeb 2.18.0 (Master, MOS 3.20), a
pattern in both pages, then `*CAT`, `*LOAD`, `*SAVE`, `*LOAD` on the 1770 DFS: 0 of 512 bytes changed; on
ANFS (MasterANFS), the logon refused ("No directory") and the pattern intact. ADFS not tried (jsbeeb's
MasterADFS reached no prompt without a disc): Phase 5's step 11 tries the real loader on each. `&0800`-`&08FF`
and `&0B00`-`&0DFF` stay the OS's. (`&0400`-`&07FF`, the language's workspace, was already the game's: the car
plotter's tables.)

### D27. The upgrades have no time limit: Decided (2026-11-06)
Departs from D19, which has the game around the race bit-exact with the ST. The ST's choice runs out after 158 passes, 9.5 seconds, and buys what the dial's on.
Tom, 2026-11-06, trying the screen: "there's a timeout, that it'd be nice to remove. It makes sense for an arcade game, but not so much for home computer".
So: the screen waits for fire, and the seconds are gone. A pass stays the ST's 3 fields, for the dial and the flashing. Nothing else moves: the ST's time running out and fire do the
same thing, so `tools/game_check.mjs` gives fire at the traced game's 158th read, and that game stays exact. Only this screen: the select's countdown and prepare's wait are as they were.

### D28. The winner's circle waits for fire: Decided (2026-11-06)
Departs from D19, as D27 does. The ST's circle ends 200 fields after its count, 4 seconds.
Tom, 2026-11-06, trying the screen: "The winner's circle screen disappears quite quickly. Like the upgrades screen, this probably makes sense for the arcade machine, but less so here. I think it should wait for a keypress."
So: after the count the celebration runs until a player's fire, the key that moves every other screen on, and fire already held doesn't count until it's let go, as accelerate may be held from the race. Nothing else moves: the celebration draws no random numbers, so `tools/game_check.mjs` gives fire at the ST's 200th field and the traced games stay exact.
No prompt on the screen (Tom, 2026-11-07: "I think it's fine without a prompt.").

### D29. The initials have no time limit: Decided (2026-11-07)
Departs from D19, as D27 and D28 do. The ST's entry ends after 30 seconds, its last 9 counted down on the screen, keeping what's entered by then.
Asked whether the initials should keep the limit, Tom, 2026-11-07: "Remove the limit".
So: the entry goes on until every car entering has its three letters, and the seconds are gone. Nothing else moves: a car's read every third pass of 2 fields, as on the ST.

### D30. The initials take a key's press at once: Decided (2026-11-07)
Departs from D19. The ST reads a car's keys every 6 fields, so a press waits up to 120 ms, and a shorter tap can be missed. Held, a letter moves on at each read, 8 a second.
Tom, 2026-11-07, trying the screen: "The keys don't feel very responsive though - it's as if there's a slight delay before the initial press takes effect, meaning you have to hold the key down for a few frames. You should be able to select a different letter with just a brief tap."
So: the keys are looked at every field as well, and a key newly down acts in that field, one step or one letter taken. A held key then waits 4 of the ST's reads, 24 fields, before they go on repeating it, or a tap at the ST's rate would often move two letters. The next position's letter shows at once too, and fire held as the entry starts isn't a press. The ST's reads are all still made, in order, so `tools/game_check.mjs` plays them as before: its keys are only ever seen there, and the traced entries stay exact.

### D31. One load after a race: Decided (2026-11-07)
Measured in jsbeeb on DFS, a load cost about 2 seconds and 0.11 a K, and a race's end had up to three before the track's: the circle's, the upgrades' and prepare's. Proposed: fold the circle's and prepare's, as all three (21.9K) don't fit the main screen's 14.8K.
Tom, 2026-11-07: "I think it'd be better to have 1 load (even if it's slightly longer than necessary) than 2 separate loads, so it'd be good if all 3 screens - winner's circle, upgrades, prepare - could be folded into one load."
So: they stay three files, read back to back while the OS has the machine, under one "Loading", so the motor needn't spin up again (`src/loadcode.6502`, `GmChain`). Prepare's is kept in the cars' bank at `ParkPrepare` and the upgrades' in the objects' bank at `ParkUpgrades`, both in track slots only a track's load writes, and copied to where they run when wanted (`front_parked_*`). The circle's comes last and stays where it lands. The upgrades' is only read if a player has 4 wrenches as the race ends. On the disc those three come first, then the tracks, next to the catalogue DFS goes back to. A race's load stays separate, as it overwrites the bank the screens run from.
Between races, a load's start to the track's first frame, in jsbeeb: DFS 9.7 s to 7.2, or 12.4 to 8.2 with the upgrades; ADFS 7.6 and 9.0.
Tom, 2026-11-07, on his Master: "The updated disk is much better".
Then, Tom, 2026-11-07: "there are still 3 loads when first entering the game: one for the track select screen, one for the prepare screen, then one for the race itself. Could the track select and prepare be folded into one load?"
So fire on the title reads prepare's file, kept at `ParkPrepare` as after a race, then the select's, in one load (`GmChain` now the letter of the file after prepare's: 'S', 'U' or 'C'). The select always ends in prepare, and touches neither the cars' bank nor the slot. In jsbeeb, fire to the race's first frame with fire pressed at once: 3 loads, 8.50 s of loading, to 2 loads, 6.99 s; 24.54 s to 23.01 in all.
Tom, 2026-11-07, on his Master: "I think it's an improvement. Even if jsbeeb says it's slower, it feels better to have one longer load than two short ones."

### D32. An ADFS disc as well: Decided (2026-11-07)
Adds to D22, which chose one 80-track DFS disc to be copied as it is to the other filing systems.
Tom, 2026-11-07: "I think the ADFS build should be an official build of the game. This will make hard disk installation easier (the user can use ADFS's `*COPY` to do it). Most Compact users will have DFS installed these days, but, for those that don't, the ADFS version will be there for them too." And: "The DFS build should remain."
So: two discs from one build, `build/game.ssd` (DFS, D22) and an ADFS disc (`tools/adfs_disc.py`), the same files. The game's loads name no filing system or directory, so they read from the current directory, and a copy in a hard disc's directory should run from there. Still to do, in step 11: the ADFS disc checked by the suite, booted by SHIFT-BREAK, and a copy into a directory tried.
Measured in jsbeeb: an ADFS L disc with the race's files on side 0 and the rest on side 1, each side's from track 0, saved 0.19 s between races over ADFS M (brief, step 11). Tom, 2026-11-07, on his Master: "I've tested the ADFS L disk on my Master and it runs well. I think the ADFS L disk should be the official one - you can assume double sided drives these days. The ADFS M disk is unnecessary."
So the ADFS disc is `build/game.adl`, ADFS L, made by `make game`; no ADFS M disc. A `*COPY` to another floppy loses the layout but still runs (`*BACKUP` keeps it); the README is to say so.

### D33. The Master Compact as well: Decided (2026-11-07)
Adds to D4 (the Master 128 only). Tom, 2026-11-07: "Please do treat the Compact as a target. The hardware is quite similar to the Master 128, with the main relevant difference for this project being hardware level access to the joystick (as yet unimplemented, so not an issue)." And: "Until joystick support is added, I think it'll be possible to just assume it works. I'll test it later, and we can look at any matters arising as a separate issue."
So: the Master 128 and the Compact, the same disc for both (D32's two). Nothing is checked on a Compact here, as jsbeeb has none; Tom will try it. The boot already lets a Compact through (OSBYTE 0 gives 3 or more on both); its refusal now names both machines. When the joysticks (D5) are built, the Compact's are read differently.
