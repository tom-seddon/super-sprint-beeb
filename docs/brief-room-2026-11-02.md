# Brief - room for every track

> **Status: DONE (Tom, 2026-11-02: "Yes, build it"), levers 1-3 built and an all-tracks check in the suite.**
> Branch `phase4-start`, from `c6b3c59`. Asked for by Tom ("Room proposal") after speed's second round left
> track 5's fourth bank 72 bytes free; rewritten after Tom asked whether ANDY was used ("If not already used,
> it should therefore be free for game use without interfering with any filing system stuff") and said "Yes,
> rewrite it". Nothing here changes the picture or the play; it's where code and data live. Using ANDY
> revises D7 (D15, decided).
>
> Figures say **MEASURED** (a build's listing or a tool run, named), **COUNTED** (off the source or a listing)
> or **PROJECTED** (arithmetic on top).

**Resume point: done** (§7). Every track assembles; the next job is the other tracks themselves (`docs/brief-phase4.md`).

## 1. The ledger: every track, measured

Until now the other tracks were projected from mask B's growth. Here each track's play build is assembled
for real: `make beeb TRACE=play TRACK=n TRACEFILE=build/trace/race_tn_r17.json` (race 17: the tornado,
cones, barriers and every gate frame, so each track's objects at their most), with the logic's data from a
copy of track 1's logic trace with its track number changed (the play build carries no traced inputs, so
the copy only picks the track's mask B, map, path, probes and hazards). Where a build fails, a scratch copy
of the source with the room asserts off gives the figure (MEASURED, 2026-11-02, from `39cd325`):

| Track (index) | 1 (0) | 2 (1) | 3 (2) | 4 (3) | 5 (4) | 6 (5) | 7 (6) | 8 (7) |
|---|---|---|---|---|---|---|---|---|
| The fourth bank | 936 | 640 | 426 | 494 | 122 | **-138** | 108 | **-322** |
| Mask B (in it; `tools/maskb.py`) | 2,168 | 2,465 | 2,679 | 2,610 | 2,983 | 3,243 | 2,996 | 3,427 |
| Shared, bytes after it | 506 | 492 | 453 | 128 | 347 | 128 | 240 | 215 |
| Shared's whole-page rule | ok | ok | ok | **fails** | ok | **fails** | **fails** | **fails** |
| The cars' bank | 1,898 | 1,649 | 1,239 | 818 | 514 | **5** | 833 | 1,321 |
| The objects' bank | 7,364 | 7,364 | 4,489 | 6,663 | 2,567 | 6,844 | 7,175 | 3,825 |
| Main RAM's code | 224 | 224 | 224 | 224 | 224 | 224 | 224 | 224 |
| ANDY (`&8000`-`&8FFF`) | 4,096 | 4,096 | 4,096 | 4,096 | 4,096 | 4,096 | 4,096 | 4,096 |

So four tracks don't build today, for three different reasons:

- **The fourth bank**: tracks 6 and 8 over by 138 and 322. Mask B is the only part of it that differs
  between tracks (fourth bank + mask B is 3,104 or 3,105 on every track), and tracks 6 and 8 have the
  largest. Tracks 5 and 7 have 122 and 108: any further logic, or a speed change that costs bytes, doesn't
  fit.
- **Shared**: tracks 4, 6, 7 and 8 have 128-240 bytes free, but fail the assert that Shared's pages end below
  the HUD's row (`SharedEnd + &FF <= HudAddr`). The loader copies whole pages *from SharedOrg* (`&3070`), so
  the last page runs `&70` past Shared's end, and the assert keeps up to 255 bytes back for it. Their drone
  paths are the long ones (994 bytes against 616).
- **The cars' bank on track 6**: 5 bytes free, and it fails to assemble anyway: the fast loop's `INPAGE`
  pads up to 80 bytes into the middle of `plot_car` to keep the loop in one page, and on this track the
  padding falls between `BEQ drawn` / `BRA enter` and their targets (out of range by 140 and 130). A layout
  fault any track's data can trigger, not a shortage.

**ANDY is unused.** Every ROMSEL write in the game is a bank number with bit 7 clear (COUNTED, `src/`); D7 and
`docs/plan.md` left it to the OS until it was shown the MOS doesn't need it.

## 2. ANDY: what the MOS does with it, and what the game can

From the kit (`reference/beeb-port-kit/docs/hardware-facts.md`, ANDY; MEASURED 2026-09-04 and 09-11, jsbeeb
Master 128, MOS 3.20, the 1770 DFS):
- ANDY is 4K at `&8000`-`&8FFF`, selected by ROMSEL bit 7, overlaying only that 4K: `&9000`-`&BFFF` stays
  the paged bank's.
- The MOS writes three of its sixteen pages, each on one event: `&80` on `*KEY`; `&8800`-`&882F` on a mode
  change or a soft BREAK; `&8F` on `VDU 23`. 26 OSFILE loads, `*CAT`, the MOS's sound, PRINT and idling wrote
  none of it. So all 4K is the game's if it fills ANDY after its last mode change, never calls `*KEY` or
  `VDU 23` afterwards, and reloads after a BREAK. This game sets its screen up on the CRTC and the ULA itself
  and makes no VDU calls; D7's loads use OSFILE only. Tom's reading agrees.
- The loader can't write ANDY while the filing system is running (its ROM is at `&8000` during a call): ANDY
  is filled after the last load of the boot, at the takeover.
- Not measured: ADFS, MMFS, real hardware. The game's own boot and a race have to be shown to leave it alone
  too (§6, step 1): a map of what the OS leaves isn't a map of what's free (the kit's gotcha, 1942's BUGS
  #24).

**Where it fits this game.** Code that reads ANDY must run outside `&8000`-`&8FFF`: in main RAM or in
`&9000`-`&BFFF` of the paged bank. The fourth bank's first 5,023 bytes (`&8000`-`&939F`) are the helicopter
(its plotter and pieces), drawn only in the moving objects' step; the logic's code starts at `&939F`. Only
`logic_start` and `logic_frame` touch the logic's data (LogicVars, mask B, the map), nothing they call pages
another bank, and the vsync interrupt never writes ROMSEL (its sound state is GameVars, its data Shared) (COUNTED, `src/main.6502`, `src/logicframe.6502`, `src/irq.6502`). So the
logic can run with the fourth bank paged *and ANDY in*: ANDY stands in for the helicopter's first 4K, which
the logic never reads, and the logic gets 4K more on every track.

## 3. The levers, costed

| # | Lever | Bytes | Cycles | Status |
|---|---|---|---|---|
| 1 | **Shared copied from `&3000`**, a page boundary: whole pages then end with Shared's, so the assert becomes `SharedEnd <= HudAddr`. The shadow's ScreenVars (`&3000`-`&306F`) are written by `start` afterwards, so copying main RAM's over them first is harmless | Shared's 128-240 usable on tracks 4, 6, 7, 8 (MEASURED above) | 0 (load only: 112 bytes more copied) | **proposed, a fix** |
| 2 | **The fast loop placed so its page padding isn't inside `plot_car`**: the loop's alignment taken before the routine, or the padding filled with the plotter's small tables (`PlotBack`, `KillOff`, `SlowBit`: 16 bytes) | 0 or less; must not grow, track 6's bank has 5 | 0 | **proposed, a fix** |
| 3 | **Mask B and the logic's state in ANDY.** The logic pages the fourth bank with ROMSEL bit 7 set (`LDA banktrace:ORA #&80:STA &FE30` at its two entries); `build/lgen/walls.6502` (mask B: header, maps, cells) assembles at `&8000` in an ANDY section, LogicVars (432 reserved) at its end; SPRINT carries ANDY's image (its file ends at `&5964` now: 8.8K to `&7C00`) and the loader copies it in after its OS calls | **fourth bank +2,600 to +3,859: 3,536 free on every track**; ANDY 237 (track 8) to 1,496 (track 1) spare (PROJECTED from the measured ledger: fourth bank + mask B + 432) | 0: the same absolute reads and writes, at their new addresses; 2 bytes at each of the two entries | **proposed** |
| 4 | The helicopter and the tornado swap banks (the earlier proposal): the helicopter's pieces into the objects' bank, drawn by `objmov`; the tornado's compiled plotter (3,609) into the fourth bank | fourth bank +1,414 on every track (COUNTED), objects' bank about -400 (PROJECTED) | 0 | **not needed with 3**; kept for later. It doesn't combine with 3 as it stands: lever 3 needs the fourth bank's first 4K to be something the logic never reads, which the helicopter is |
| 5 | The cars' frames packed tighter (659 bytes of page padding, the RAM hunt's lever 7) | ~375 PROJECTED, the cars' bank | 0 | **for the cars' bank, when anything there grows** |
| 6 | Part of the logic's state in GameVars (168 free); mask B's header flags; `logictabs` (252) into Shared | 25-250 each | 0 to a few | not needed with 3 |
| 7 | HAZEL (D7): 8K at `&C000`-`&DFFF` | ~8K, less what each filing system keeps there | ACCCON's Y set in play | **not proposed**: the filing system's workspace there has to survive each race (no free 8K to keep it in, or reselecting the filing system before each load, unmeasured on DFS, ADFS, MMFS and Econet); the MOS ROM under it hidden; a load-path change, so a hardware gate. Left for Phase 5 if the front end and loader need it |

After levers 1-3 (PROJECTED from the measured ledger):

| Track (index) | 1 (0) | 2 (1) | 3 (2) | 4 (3) | 5 (4) | 6 (5) | 7 (6) | 8 (7) |
|---|---|---|---|---|---|---|---|---|
| The fourth bank | 3,536 | 3,537 | 3,537 | 3,536 | 3,537 | 3,537 | 3,536 | 3,537 |
| ANDY | 1,496 | 1,199 | 985 | 1,054 | 681 | 421 | 668 | **237** |
| Shared | 506 | 492 | 453 | 128 | 347 | **128** | 240 | 215 |
| The cars' bank | 1,898 | 1,649 | 1,239 | 818 | 514 | **5** | 833 | 1,321 |
| The objects' bank | 7,364 | 7,364 | 4,489 | 6,663 | **2,567** | 6,844 | 7,175 | 3,825 |

Every track builds, with 3,536 bytes in the fourth bank for the rest of Phase 4 and for speed changes that
cost bytes (the wall probes' shifts stored pre-shifted, say). Mask B now varies in ANDY instead, and track 8
leaves it 237: anything else put in ANDY has to fit there on every track. The cars' bank on track 6 stays the
tightest region in the game: lever 5 when anything there grows.

## 4. What it changes in the tools

The kit's rule: a read of `&8000`-`&8FFF` returns whatever the CPU has paged at that instant, so every tool
that reads mask B or the logic's state names ANDY. `logic_check.mjs`, `maskb_check.mjs`, `walls_check.mjs`
and `logic_draws.mjs` read at points where the logic has ANDY in, so they read it already, but each says so
and checks ROMSEL's bit 7 before it trusts a read. The logic test (`src/logictest.6502`) copies ANDY's image
the way the game's loader does and pages it as the game does, so the oracle tests the game's arrangement.
The profilers attribute by ROMSEL AND 15, unaffected (ANDY holds no code).

## 5. For Tom

Proposed: levers 1 and 2 (fixes), and lever 3 (mask B and the logic's state in ANDY), revising D7's "ANDY
stays the OS's" (D15). Lever 4 (the swap) kept for later; lever 5 when the cars' bank needs it; HAZEL left
for Phase 5.

## 6. The steps (on a yes)

Each its own commit, its bytes per region on all eight tracks (the ledger's method, §1) and the hazard race's
cycles in the body, after the whole suite (`tools/suite.sh`, 18 checks).

1. **ANDY measured free for this game**, the kit's way (`beeb-bss-bugs`'s seeded fill): ANDY filled with a
   pattern after the takeover, then the play build's boot and a whole traced race (and, for D7's loads, an
   OSFILE with the OS brought back as D7 has it), and ANDY compared. The readback recorded in D15.
2. Lever 1: `shared_copy` from `&3000`; the assert `SharedEnd <= HudAddr`. Tracks 4, 6, 7, 8 pass Shared.
3. Lever 2: the fast loop's alignment outside `plot_car`'s branches, the cars' bank no bigger. Track 6
   assembles.
4. Lever 3: the ANDY section (mask B, then LogicVars), its image in SPRINT and the loader's copy, the logic's
   two entries paging ANDY in, the logic test arranged the same; an assert that the fourth bank's code
   starts at `&9000` or above (the helicopter at least 4K) and one that ANDY's section fits. The tools as §4.
   The suite proves the logic and the drawing unchanged; every track's ledger redone.
5. A `make` target (or a suite line) that assembles all eight tracks' play builds, so a track that stops
   fitting fails the suite instead of being found later.

## 7. What landed

Every figure MEASURED, jsbeeb 2.18.0 (Master, MOS 3.20, the 1770 DFS), 2026-11-02. After each lever the
whole suite passed (18 checks, then 19 with `all_tracks`).

1. **ANDY free for this game** (no commit: the measurement, recorded in D15). Seeded with a pattern after the
   takeover in the hazard race game, 0 of its 4,096 bytes changed after the whole race (2,240 frames); the
   bank's own `&8000` read separately held the helicopter's code, not the pattern, so the reads were ANDY's.
   From BASIC with the same disc: before seeding 4,082 bytes differ from the pattern, after it 0; after
   `*LOAD` of the disc's five files and `*CAT`, 0; after `*KEY 1 HELLO`, 30 (the check sees the MOS's writes).
2. **Lever 1** (`852be79`): `shared_copy` from `&3000`; the whole-page assert gone, Shared's guard the limit.
   Bytes none; cycles none.
3. **Lever 2** (`e78abcf`): `INPAGE_AHEAD` (`src/macros.6502`) pads before `plot_car` by the fast loop's
   offset in it; an assert keeps the loop in one page. Track 6 assembles; the cars' bank unchanged
   elsewhere (1,898 on track 1).
4. **Lever 3** (`1ff9ff7`): mask B and LogicVars in ANDY; the logic pages the fourth bank with ROMSEL's bit 7
   at `start` and in the frame loop; SPRINT carries ANDY's image and its loader copies it in after its OS
   calls; the logic test arranged the same (its bank's code from `&9000`). Found on the way:
   - `logic_start` zeroed LogicVars a page at a time from `HI(LogicVarsOrg)`, so it also cleared whatever
     shared that page: on track 5's traced game the attribute map's last 8 bytes (bottom-row cells no car
     reaches, so nothing saw it). It zeroes exactly the state now; under the new layout it would have wiped
     mask B's end.
   - `tools/keys_check.mjs` read RcInput with readMemory's `{ bank }`, which reads the bank's own
     `&8000`-`&8FFF`, and failed 12 of 12: the kit's rule (name ANDY on every read) in practice.
     `tools/jsbeeb.mjs` gains `andy()`; the mask B tools check ROMSEL's bit 7 before reading.
   Cycles: the logic test 11,189 (track 1) and 14,052 (hazard race), as before; the hazard race game 34,190
   a frame (34,185), 306 frames over (305).
5. **All tracks** (`39e1f9a`): `tools/all_tracks.sh`, in the suite.

| Track (index) | 1 (0) | 2 (1) | 3 (2) | 4 (3) | 5 (4) | 6 (5) | 7 (6) | 8 (7) |
|---|---|---|---|---|---|---|---|---|
| The fourth bank (was) | 936 | 640 | 426 | 494 | 122 | -138 | 108 | -322 |
| **The fourth bank** | **3,536** | **3,536** | **3,536** | **3,536** | **3,536** | **3,536** | **3,536** | **3,536** |
| ANDY | 1,496 | 1,199 | 985 | 1,054 | 681 | 421 | 668 | 237 |
| Shared | 506 | 492 | 453 | 128 | 347 | 128 | 240 | 215 |
| The cars' bank | 1,898 | 1,649 | 1,239 | 818 | 514 | **1** | 833 | 1,321 |
| The objects' bank | 7,364 | 7,364 | 4,489 | 6,663 | 2,567 | 6,844 | 7,175 | 3,825 |
| Main RAM's code | 224 | 224 | 224 | 224 | 224 | 224 | 224 | 224 |

**Open:** the cars' bank on track 6 has 1 byte: lever 5 (the frames' page padding, ~375 PROJECTED) before
anything there grows. ANDY on track 8 has 237 for anything else put there. Not measured: ADFS, MMFS and real
hardware with ANDY (with D7's loads, Phase 5). **Measured and not built:** lever 4 (the helicopter and tornado
swap, +1,414; it now conflicts with ANDY's arrangement), lever 6's small ones, HAZEL.
