# Brief - a time attack version

> **Status: PROPOSED (2026-11-10), nothing built.** Branch `timeattack`. Tom, 2026-11-10: "I'm thinking it could
> benefit from having a special version, built from the same code and using the same basic game engine and tracks: a
> time attack mode, with persistent high score tables and ghost car recordings of the fastest lap (up to some lap
> time limit as dictated by memory)." On the first look (§1-§6 below, as given in chat): "This all looks good. I have
> a couple of notes but nothing significant I don't think. Please create a new branch for this and then write up the
> brief." His notes are still to come; §7's questions are being answered one by one (the gates: D36; the ghost's look: D37; the first lap: D38; the name: D39; the table: D40; a race's entry: D41). Tom, on the answers: "A
> number of the first pass answers will be slightly speculative, as this version is venturing into the unknown much
> more so than the initial conversion. But it'll all become clearer as development goes on I think."
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

**The cars' bank: one car set, not four (the ghost's room).** The bank holds four sets of the car's 16 facings, each
pre-shifted to 4 positions: cars 0-2's own and the drone-driven one, 10,275 bytes (`CarDataSize`,
`build/gen/cars.6502`, MEASURED; D20). A data table recolours only a frame's value-1 pixels, the body (`tools/gendata.py`:
0 black, 1 the body, 3 white). The white car's body is stored as white, value 3, so its frames can't be drawn black; the
green car's is value 1. So time attack keeps the green car's set alone, and draws the player through `DataWhite` and
the ghost through `DataBlack` (D37), tables that are in main RAM already. Over the 16 facings (COUNTED,
`build/ta/car_colours.png` from `car_values`): the player 11 pixels from today's white car, the ghost 95 from today's
black car (car 3, the drone-driven set through `DataBlack`), most of them white highlights the black car hasn't.

| The cars' bank, time attack | Bytes |
|---|---|
| Code and tables: 14,172 used on track 1 (MEASURED), less the sets (10,275) and track 1's priority cells (2,105) | 1,792 (COUNTED) |
| One car set, the green car's: a quarter of 10,275 | ~2,570 (ESTIMATED) |
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
- Most frames are the one byte, so a lap is likely nearer 1.2 bytes a frame (ESTIMATED; measured at step 4). Two
  buffers of 3,000 bytes, the current lap and the best, hold 30 s even if every frame took 2, and leave about 2,070
  of the 8,070 (ESTIMATED) for the ghost's code. A lap that fills its buffer is timed but leaves no ghost. A new best
  is the two buffers' pointers swapped, no copy.
- The lap's upgrades (§4) are kept with it.

**Where it runs.** In the cars' bank beside `plot_car`, which is paged in while the cars are drawn: the player's
record is read and coded into the current buffer, and the ghost's next record decoded and put in the draw order (by
y, elevated after, as the logic orders the cars). The ghost's on-top bit puts it under bridges as a car is.

**How it looks (D37).** A black car, solid, no flicker: the green car's set through `DataBlack` (§2). Tom,
2026-11-10: "I think use the black car. I'm not very keen on the idea of flicker. Again, this may have to change once I
see it running." Then, of the one-set ways to colour it: "The green set". If black on the road's checkerboard is hard
to see, the same set draws it green or yellow (`DataId`, `DataYellow`) at no cost.

**When it starts (D38).** With the race, and again at each crossing of the finish line, from the best lap's first
frame, so player and ghost start each lap together. Tom, 2026-11-10: "The first lap should be a standing start for the
player. If there's a ghost car, the ghost car should be shown in that lap too. The player will almost certainly fail to
keep up, but that's OK, and fairly standard for time attack modes. It can give the player a chance to study its line
if they want."
- The grid is on the line: on every track the first car's 16-pixel box straddles the finish's cells (COUNTED, grid x
  from `tools/logic_maps.py summary` against `docs/st-logic.md` §6's checkpoint 4), and the start's crossing doesn't
  count (checkpoints 1-3 come first). So lap 1 is a full lap from a standstill, and the ghost leaves the same line at
  its lap's speed.
- Lap 1 is timed like any other, and can be the best (and the ghost) if it's the only lap finished; its record starts
  at the race's first frame, so that ghost starts from a standstill too.
- A ghost that reaches the line first is put away there until the player crosses (proposed, the usual way; not yet
  asked).

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
- **The menu (D40)**: every track's best at once, so a player picks by who they'd like to beat as well as by the
  track. Text in the MOS's font, drawn by `font_char` (LowFree, resident) as the options screen names keys (the HUD's
  font has only 15 glyphs, its digits and a few more), a row a track: its number, best time, name and upgrades, 29 of
  the row's 40 characters with a 10-letter name. Then the upgrades (5 points over three, forked from
  `upgrades.6502`), then the race. After Escape, a name for a new record, then the save, then the menu.
- **A track's list (D40)**: a second screen, from the menu, a track's 10 entries, a row each as the menu's. Its code
  in its own file, about 200 bytes (ESTIMATED), as the name's.
- **The name (D39)**: up to 10 characters typed on the keyboard. The options screen already finds any key held from a
  table of key numbers (`opt_find`, `OptNumbers`, through `key_down`), so the name's screen is that with a table of
  A-Z, 0-9, space, Delete and Return and their characters (about 80 bytes), the typing loop and the drawing: about
  250 bytes (ESTIMATED), in its own file, not resident. Which characters beyond those (lower case, punctuation; the
  MOS's font has them all) is for later.
- **Saved**:
  - One table for all 8 tracks (D40), 10 entries a track, 13 bytes an entry (the time 2, the name 10, the upgrades 1:
    three levels that sum to 5 or less are 56 combinations): 80 entries, 1,040 bytes (COUNTED). Resident, in Shared,
    as `HiFile` is now, which time attack leaves about 1,550 free (ESTIMATED: the 267 free, the drone path's 996 and
    `HiFile`'s 295), so the menu and the lists read it without a load; loaded once at the boot and saved like `SCORES`
    (`save.6502`: one file, only when changed, a failed save said once and ignored, D23).
  - Laid out a column a field (the times' low bytes, their high bytes, the upgrades, then the names), indexed by
    track * 10 + place, each track's 10 kept in order, best first: the menu reads places 0, 10, 20 and on, a track's
    list reads its 10 in a row, and a new time moves the slower ones down within its track's 10. The best entry's
    lap is the track's ghost.
  - A race enters its best lap only (D41), on the way out, if it's faster than the track's 10th: one entry a race,
    so a race that doesn't beat the ghost can still make the list. A name can be there more than once.
  - A ghost a track, one file each (`GHOST1`-`GHOST8`, up to about 3K), saved when beaten. OSFILE can't save from a
    sideways RAM bank (the filing system's ROM is paged in while it runs), so the lap's copied first to main RAM, to
    the screen not shown.
  - Saved on the way out of a race, not during it, so a record is lost if the machine is switched off before Escape.
  - The DFS catalogue: the game's disc has 21 of its 31 entries (MEASURED, `build/game.ssd`); this one has fewer
    screens' files and 8 ghosts.

## 7. To decide (Tom)

1. ~~The gates~~: the ST's schedule (D36, Tom, 2026-11-10), to be revisited after playing it (§5).
2. ~~The ghost's look~~: a black car, solid, no flicker, from the green set (D37, Tom, 2026-11-10), to be revisited once running (§3).
3. ~~The first lap~~: a standing start, timed, the ghost shown from the race's start (D38, Tom, 2026-11-10) (§3).
4. ~~The name~~: up to 10 characters, typed on the keyboard (D39, Tom, 2026-11-10) (§6).
5. ~~How many entries a track's table keeps~~: 10, every track's together, the bests on the menu and a track's 10
   on a screen of their own (D40, Tom, 2026-11-10) (§6).
6. Wrecks kept, as the ST's (§4).
7. ~~What a race puts in the table~~: its best lap only, one entry a race; a name can be there more than once, from
   different races (D41, Tom, 2026-11-10) (§6).

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
