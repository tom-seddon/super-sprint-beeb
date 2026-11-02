# Brief - room for every track

> **Status: PROPOSAL (2026-11-02), for Tom.** Branch `phase4-start`, from `39cd325`. Asked for by Tom ("Room
> proposal") after speed's second round left track 5's fourth bank 72 bytes free. Nothing here changes the
> picture or the play; it's where code and data live. HAZEL (D7) is weighed and not proposed (§3).
>
> Figures say **MEASURED** (a build's listing or a tool run, named), **COUNTED** (off the source or a listing)
> or **PROJECTED** (arithmetic on top).

**Resume point: Tom's answer** (§4). On a yes, the steps in §5 in order, one commit each, the suite after each.

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
| Shared, bytes after it | 506 | 492 | 453 | 128 | 347 | 128 | 240 | 215 |
| Shared's whole-page rule | ok | ok | ok | **fails** | ok | **fails** | **fails** | **fails** |
| The cars' bank | 1,898 | 1,649 | 1,239 | 818 | 514 | **5** | 833 | 1,321 |
| The objects' bank | 7,364 | 7,364 | 4,489 | 6,663 | 2,567 | 6,844 | 7,175 | 3,825 |
| Main RAM's code | 224 | 224 | 224 | 224 | 224 | 224 | 224 | 224 |

So four tracks don't build today, for three different reasons:

- **The fourth bank**: tracks 6 and 8 over by 138 and 322 (mask B is 3,243 and 3,427 bytes there against
  track 1's 2,168). Tracks 5 and 7 have 122 and 108: any further logic, or a speed change that costs bytes,
  doesn't fit.
- **Shared**: tracks 4, 6, 7 and 8 have 128-240 bytes free, but fail the assert that Shared's pages end below
  the HUD's row (`SharedEnd + &FF <= HudAddr`). The loader copies whole pages *from SharedOrg* (`&3070`), so
  the last page runs `&70` past Shared's end, and the assert keeps up to 255 bytes back for it. Their drone
  paths are the long ones (994 bytes against 616).
- **The cars' bank on track 6**: 5 bytes free, and it fails to assemble anyway: the fast loop's `INPAGE`
  pads up to 80 bytes into the middle of `plot_car` to keep the loop in one page, and on this track the
  padding falls between `BEQ drawn` / `BRA enter` and their targets (out of range by 140 and 130). A layout
  fault any track's data can trigger, not a shortage.

The objects' bank and main RAM are fine everywhere; main RAM's 224 are for Phase 5 (D7: the loader, the
front end).

## 2. The levers, costed

| # | Lever | Bytes | Cycles | Status |
|---|---|---|---|---|
| 1 | **Shared copied from `&3000`**, a page boundary: whole pages then end with Shared's, so the assert becomes `SharedEnd <= HudAddr`. The shadow's ScreenVars (`&3000`-`&306F`) are written by `start` afterwards, so copying main RAM's over them first is harmless | Shared's 128-240 usable on tracks 4, 6, 7, 8 (MEASURED above) | 0 (load only: 112 bytes more copied) | **proposed, a fix** |
| 2 | **The fast loop placed so its page padding isn't inside `plot_car`**: the loop's alignment taken before the routine, or the padding filled with the plotter's small tables (`PlotBack`, `KillOff`, `SlowBit`: 16 bytes) | 0 or less; must not grow, track 6's bank has 5 | 0 | **proposed, a fix** |
| 3 | **The helicopter and the tornado swap banks.** The helicopter is in the fourth bank only for room in Phase 3: its pieces (3,462) and its own copy of the movers' plotter (`helimov`, 1,561 with its tables). Its pieces move to the objects' bank, drawn by the plotter already there (`objmov`, its variants appended); the tornado's self-contained compiled plotter (`mov_tornado` 509, its frames 3,100: no data but its own and `TorJunk` in main RAM) moves to the fourth bank. `mov_all` pages the fourth bank for the tornado and the objects' bank for the rest | fourth bank **+1,414 on every track** (COUNTED, listing extents: 5,023 out, 3,609 in); objects' bank about -400 (PROJECTED: 3,609 out, 3,462 and the helicopter's ~550 bytes of variant tables in) | 0: the same plotters and paging, the bank numbers swapped | **proposed** |
| 4 | Part of the logic's state (LogicVars, 416) in GameVars (`&2E00`, 168 free) | up to 168, fourth bank | 0 (absolute either way) | not needed with 3 |
| 5 | Mask B's header: MbLeft and MbRight (0 or &FF) as one table of flags | 25 | a few a look-up outside a row's span (often) | not needed |
| 6 | The logic's read-only tables (`logictabs`, 252) into Shared | 252 where Shared has it (not tracks 4 and 6) | 0 | not needed with 3 |
| 7 | The cars' frames packed tighter (659 bytes of page padding, the RAM hunt's lever 7) | ~375 PROJECTED, the cars' bank | 0 | **for the cars' bank, when anything there grows** |
| 8 | HAZEL (D7): 8K at `&C000`-`&DFFF`, readable whatever bank is in | ~8K, less what each filing system keeps there | ACCCON's Y set during the race | **not proposed now** (§3) |

After levers 1-3 (PROJECTED from the measured ledger):

| Track (index) | 1 (0) | 2 (1) | 3 (2) | 4 (3) | 5 (4) | 6 (5) | 7 (6) | 8 (7) |
|---|---|---|---|---|---|---|---|---|
| The fourth bank | 2,350 | 2,054 | 1,840 | 1,908 | 1,536 | 1,276 | 1,522 | **1,092** |
| Shared | 506 | 492 | 453 | 128 | 347 | **128** | 240 | 215 |
| The cars' bank | 1,898 | 1,649 | 1,239 | 818 | 514 | **5** | 833 | 1,321 |
| The objects' bank | ~6,950 | ~6,950 | ~4,100 | ~6,250 | **~2,150** | ~6,450 | ~6,750 | ~3,400 |

Every track builds, with at least 1,092 bytes left in the fourth bank for the rest of Phase 4 and for
speed changes that cost bytes. The cars' bank on track 6 stays the tightest region in the game: lever 7
when anything there grows.

## 3. Why not HAZEL now

D7 says HAZEL is the first thing to consider if the game needs room. It would give ~8K, but:
- the game has the machine during a race, and the filing system's HAZEL workspace has to survive to the next
  load: either kept somewhere (8K, or however much each filing system claims; there's no free 8K) or
  rebuilt by reselecting the filing system before each load, which has to be measured on DFS, ADFS, MMFS and
  Econet first;
- with ACCCON's Y set, the MOS ROM at `&C000`-`&DFFF` is hidden: the MOS's IRQ entry (the game's IRQ1V is
  reached through it) must be shown to lie outside it on MOS 3.20, and nothing may call the OS;
- it's a load-path change, so a hardware gate (D7's loads, Phase 5).

Lever 3 gets every track building with room to spare and none of that. HAZEL stays the reserve for Phase 5,
measured then (the filing systems' claims by a write-watch harness, the IRQ entry's address) if the front end
and the loader need it.

## 4. For Tom

Proposed: levers 1 and 2 (fixes), and lever 3 (the swap). Lever 7 when the cars' bank needs it; HAZEL left
for Phase 5.

## 5. The steps (on a yes)

Each its own commit, its bytes per region on all eight tracks (the ledger's method, §1) and the hazard race's
cycles in the body, after the whole suite (`tools/suite.sh`, 18 checks).

1. Lever 1: `shared_copy` from `&3000`; the assert `SharedEnd <= HudAddr`. Tracks 4, 6, 7, 8 pass Shared.
2. Lever 2: the fast loop's alignment outside `plot_car`'s branches, the cars' bank no bigger. Track 6
   assembles.
3. Lever 3: the helicopter's pieces into the objects' variants (`tools/gendata.py`), `helimov` gone, the
   tornado's plotter into the fourth bank, `mov_all`'s paging swapped. The renderer checks (`make check` for
   race, heli1-3, t0-t7, logic0, logic4) prove it draws the same; every track's ledger redone.
4. A `make` target (or a suite line) that assembles all eight tracks' play builds, so a track that stops
   fitting fails the suite instead of being found later.
