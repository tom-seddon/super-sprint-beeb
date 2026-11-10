# Brief - a time attack version

> **Status: PROPOSED (2026-11-10), nothing built.** Branch `timeattack`. Tom, 2026-11-10: "I'm thinking it could
> benefit from having a special version, built from the same code and using the same basic game engine and tracks: a
> time attack mode, with persistent high score tables and ghost car recordings of the fastest lap (up to some lap
> time limit as dictated by memory)." On the first look (§1-§6 below, as given in chat): "This all looks good. I have
> a couple of notes but nothing significant I don't think. Please create a new branch for this and then write up the
> brief." His notes are still to come; §7's questions are being answered one by one (the gates: D36).
>
> Figures say **MEASURED** (a build's listing or a tool run, named), **COUNTED** (off the source or a listing)
> or **ESTIMATED** (arithmetic on top).

## 1. What Tom asked for

From his message (2026-11-10), in his words where quoted:
- One player, two cars on the track: the player's, and the ghost of the fastest lap if there's one. "Just keep
  racing until you get bored, then press Escape to get back to the front end."
- The best time and the ghost lap saved "as appropriate"; an enter-your-name screen.
- Hazards: "no tornado, no sand, no oil, and no barriers - but maybe the opening/closing gates would be ok if they
  open and close on a fixed timing schedule. Maybe this aspect will need iterating on."
- "a different, much simplified front end: most of it would be just a select track menu, with best lap time/name
  shown, so the player can pick whichever track they fancy racing on."
- Upgrades picked before play: 5 of them ("the equivalent of 20 wrenches"), not all of which need be spent. "The
  powerups used would be recorded as part of the ghost data and shown in the front end too."
- About 8K free in a sideways RAM bank during a race would hold the current lap and the best lap's ghost.
- The multiload stays: each track a file loaded on demand.

## 2. Where the room comes from

Today's room is tight (`docs/memory-map.md`, MEASURED from the play build; the least over the tracks from
`docs/plan.md`'s Phase 5 figures): most regions have under 300 bytes free, the cars' bank 370 on track 6 (index 5),
the objects' bank 34 on track 5 (index 4). Time attack frees room by what it leaves out.

**The cars' bank: one car set, not four (the ghost's 8K).** The bank holds four sets of the car's 16 facings, each
pre-shifted to 4 positions: cars 0-2's own and the drone-driven one, 10,275 bytes (`CarDataSize`,
`build/gen/cars.6502`, MEASURED; D20). A car's colour isn't in its frames but in the data table its `CarId` picks
(`CarTables`: `DataId`, `DataYellow`, `DataWhite`, `DataBlack`). So time attack needs one set: the player's (car 0's,
white), and the ghost drawn from the same frames through another table (§3).

| The cars' bank, time attack | Bytes |
|---|---|
| Code and tables: 14,172 used on track 1 (MEASURED), less the sets (10,275) and track 1's priority cells (2,105) | 1,792 (COUNTED) |
| One car set: a quarter of 10,275 | ~2,570 (ESTIMATED) |
| The largest track's priority cells (`PrioSlot`, 3,947 on index 5, `build/game_slots.json`, MEASURED), which every track's layout leaves room for | 3,947 |
| **Free on every track** | **~8,070 (ESTIMATED)** |

The ghost's buffers go above the largest slot, at a fixed address, so a track's load never touches them.

**Elsewhere** (for the new race code, not the ghost):

| What goes | Where | Bytes |
|---|---|---|
| The tornado's compiled frames (`gen/tornado.6502`) | the objects' bank | 3,100 (MEASURED) |
| The pickups', oil's, cones' and barriers' variants in `ObjSlot` (3,102 on a track with no gates to 7,390 on index 4, MEASURED; what's left is the gates', the explosion's and the banner's) | the objects' bank | to be measured |
| `drone.6502`, `pickups.6502` | the fourth bank | 742 + 701 (MEASURED) |
| The tornado's, the barriers', the oil's and the cones' parts of `hazards.6502` | the fourth bank | some of 1,203 |
| The drone path (`lgen/path.6502`) | the `&3000` area | 996 (MEASURED) |
| The attract mode, title, credits, high scores, circle, prepare and options code (`front.6502`, the screens' files) | between races | most of it |

## 3. The ghost

**Record what's drawn, not the inputs.** Two ways to make a ghost:
- *Inputs*, replayed through the logic. Tiny: the build already run-length codes a race's inputs, 248 bytes for a
  4-lap traced race on track 1 (`build/lgen/inputs.rle`, MEASURED). But the ghost would be a second car simulated
  bit-exactly from a snapshot of the car's state at the lap's start, and some of the state it reads is shared and
  won't be as it was: the 7-frame coasting cycle (`G_01D178`, one for every car), the gates' positions (§5), and the
  rule that only one helicopter flies at a time. Any of them sends the ghost off its line, and it costs a second car's
  logic each frame.
- *Positions*, drawn as recorded. The player's draw record each frame (`logicframe.6502`'s `record`: `CarId`,
  `CarXLo`, `CarY`, `CarFlags`, which carry x's high bit, the frame, the facing and the on-top bit) is appended to the
  current lap's buffer; the best lap's is read back into the draw list as a fifth record. No physics for the ghost,
  nothing it can disagree with, and a wreck's explosion and the helicopter's blink play back as they were.

Proposed: positions.

**Its size.** The ST's lap records are 275 to 662 frames (5.5 to 13.2 s, `SSPRINT.HSC`); its par lap, the lap
bonus's zero, is 15 + track seconds, 22 s on track 8 (`docs/st-logic.md` §6). A cap of 30 s, 1,500 frames, holds any
lap worth keeping; a longer one is timed but leaves no ghost.
- A frame's move is at most 4 pixels each way (top speed with level-5 top speed is 27/8 pixels a frame) and the facing
  changes by at most 1 (a turn waits at least 2 frames; a spin turns on odd frames), so a frame codes as a byte of
  dx and dy, plus a byte when the facing, the flags or the record's kind changes, or for a jump (a wrecked car put back).
- At 2 bytes a frame at most, 3,000 bytes a lap; the current lap and the best, 6,000 of the 8,070 (ESTIMATED). A new
  best is the two buffers' pointers swapped, no copy.
- The lap's upgrades (§4) are kept with it.

**Where it runs.** In the cars' bank beside `plot_car`, which is paged in while the cars are drawn: the player's
record is read and coded into the current buffer, and the ghost's next record decoded and put in the draw order (by
y, elevated after, as the logic orders the cars). The ghost's on-top bit puts it under bridges as a car is.

**How it looks.** Either solid, in green, yellow or black (`DataId`, `DataYellow`, `DataBlack`), or drawn on every
other frame, a 25 Hz flicker, which reads as a ghost on a CRT and halves its cost: §7.

**When it starts.** At each crossing of the finish line, with the best lap's first frame, so player and ghost cross
together. The first lap is a standing start from the grid: timed, but almost never the best (§7).

## 4. The race

- **One car.** No drones, so no car-to-car collisions. The logic assumes four cars in about 34 places across
  `race.6502`, `logicframe.6502` and the code they call (COUNTED, a rough grep for 4-car loops and limits): either
  a car count through those loops, or cars 1-3 parked and skipped. The main unknown in the race; step 2 settles it.
- **No end.** The race's 4-lap end (`race.6502`'s lap 4 test, the banner) goes; laps count on. Escape (from the matrix,
  `KeyEscape`, as `game_esc` reads it between races) back to the front end, which saves (§6).
- **Upgrades** from the 5 points picked before the race, put in the car's levels where the ST's race set-up puts
  them (`docs/st-logic.md` §2): top speed, turbo acceleration and super traction, each 0 to 5 as in the ST.
  "Increase score" means nothing here.
- **The HUD** (D6): the lap number, the lap's time and the best, `0:07.34` and so on (50 fields a second, so a field
  is 2 hundredths, `RcLapTimeLo`'s frames, `cells.6502`). The hundredths change every frame and the seconds every 50,
  so 1 to 4 characters a frame, within the HUD's 4 a frame (`docs/renderer.md`).
- **Hazards**: the gates only, or none (§5). Wrecks stay (tracks 2 and 6's bridge edges and jumps, leaving the
  area), as the ST has them.
- **Sound**: one engine.
- **Speed**: one car simulated, two drawn, no tornado or pickups. Every track's frames fit 40,000 cycles with four
  cars and every hazard (Phase 4), so there's room to spare; measured at step 2.

## 5. The gates

The ST's gates already run on a fixed schedule, with no randomness: tracks 3, 5 and 8 (1, 3 and 1 gates), 5
positions, 6 frames a step, a wait of 84 + 90 * the gate's number frames at each end, the first wait 48 * (number + 1)
(`docs/st-logic.md` §3, checked in Hatari). So a gate repeats every 216 + 180 * its number frames (ESTIMATED: 4.3 s for
gate 0, 7.9 s, 11.5 s). A lap's time then depends on where the gates are when it starts: some luck from lap to lap.
A position-recorded ghost isn't affected (it drives through a gate that's closed now, as a ghost would).
Options, for Tom (§7): the ST's schedule; no gates; or the schedule started again at each crossing of the line, which
is fair (every lap meets the gates the same) but makes them jump.

**Decided (D36):** the ST's schedule. Tom, 2026-11-10: "I think keep the ST's schedule, and accept the player may need
to be a little strategic about how they time crossing the line. I may end up having to change my mind about this after
playing it though."

## 6. The front end, saving and the disc

- **The disc**: its own, `build/ta.ssd` and an ADFS L one beside it, from the same source as a build variant chosen
  as `TRACE=` chooses the race today (CLAUDE.md: no `-D` flags). The game's build stays byte for byte as it is
  (proved with the `beeb-identical-build` skill), and the whole suite still passes on it.
- **Each track a file**, loaded on demand as now: the time attack variant's, with the pickups' and hazards' objects left
  out, so smaller.
- **The menu**: text in the HUD's font, a row a track: its number, best time, name and upgrades. Then the upgrades
  (5 points over three, forked from `upgrades.6502`), then the race. After Escape, a name for a new record (forked
  from `initials.6502`), then the save, then the menu.
- **Saved**:
  - A table, a few entries a track (time, name, upgrades), a few hundred bytes, saved like `SCORES` (`save.6502`: only
    when changed, a failed save said once and ignored, D23).
  - A ghost a track, one file each (`GHOST1`-`GHOST8`, up to about 3K), saved when beaten. OSFILE can't save from a
    sideways RAM bank (the filing system's ROM is paged in while it runs), so the lap's copied first to main RAM, to
    the screen not shown.
  - Saved on the way out of a race, not during it, so a record is lost if the machine is switched off before Escape.
  - The DFS catalogue: the game's disc has 21 of its 31 entries (MEASURED, `build/game.ssd`); this one has fewer
    screens' files and 8 ghosts.

## 7. To decide (Tom)

1. ~~The gates~~: the ST's schedule (D36, Tom, 2026-11-10), to be revisited after playing it (§5).
2. The ghost's look: solid in another colour, or flickering at 25 Hz (§3).
3. The first lap: a standing start, timed; the ghost starts at each crossing of the line (§3).
4. The name: three initials, as the ST's table, or longer.
5. How many entries a track's table keeps.
6. Wrecks kept, as the ST's (§4).

Each becomes a row in `docs/decisions.md`, Proposed until Tom agrees.

## 8. The steps

One commit each on `timeattack` (CLAUDE.md), the measurement in its body.

1. **The variant.** A time attack build from the same source, its own discs; the game's build proved unchanged.
2. **The race, one car.** One car set; no drones, pickups, oil, cones, barriers or tornado; endless laps; Escape out.
   Then the room measured on every track (`tools/all_tracks.sh`'s figures for the variant) and the frames' cycles
   (`tools/render_profile.mjs`).
3. **The lap timer and HUD.**
4. **The ghost.** Recorded and played back in the cars' bank. Its check: a scripted lap driven, then replayed, every
   frame's ghost record the same as the player's was (a headless oracle on `tools/jsbeeb.mjs`, in the suite).
5. **Saving.** The table and the ghosts; a check as `tools/save_check.mjs`'s (saved, booted back, spoilt files
   refused, a write-protected disc's error said once).
6. **The front end.** The menu, the upgrades, the name; checks driven key by key as the screens' are now.
7. **Close**: the variant's suite, both discs, Tom's Master.
