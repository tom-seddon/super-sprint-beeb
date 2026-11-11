# Brief - a time attack version

> **Status: in progress (2026-11-10): steps 1 to 5 done (§8): the ghosts and the table saved; step 6, the front end, next.** Branch `timeattack`. Tom, 2026-11-10: "I'm thinking it could
> benefit from having a special version, built from the same code and using the same basic game engine and tracks: a
> time attack mode, with persistent high score tables and ghost car recordings of the fastest lap (up to some lap
> time limit as dictated by memory)." On the first look (§1-§6 below, as given in chat): "This all looks good. I have
> a couple of notes but nothing significant I don't think. Please create a new branch for this and then write up the
> brief." His notes are still to come; §7's questions are being answered one by one (the gates: D36; the ghost's look: D37; the first lap: D38; the name: D39; the table: D40; a race's entry: D41; wrecks: D42; the ghost at the line: D43; the maps on the menu: D44; the turnaround: D45; the front end's 32 rows: D46; the menu's layout: D47; the track's screen: D48; the upgrades and the name between races: D49; after a race: D50). Tom, on the answers: "A
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
- **A ghost that reaches the line first (D43)** waits at its lap's first frame, drawn there and still, until the player
  crosses, then sets off from it: a jump from its last frame to its first when it finishes (a few pixels on a flying
  lap, across the line; to the grid if its lap was lap 1), so it leaves smoothly as the player passes. A player who
  crosses first starts the ghost's lap again there, from wherever it had got to. Tom, 2026-11-10: "have the ghost wait
  at the line. I think have it wait at its start position (even if that means a jump from its end position), so that
  it sets off smoothly as the player passes."
  Either way, every lap the ghost and the player start together.

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
- **Hazards (D42)**: the ones a track always has on the ST stay; the ones that come and go with the race count or a
  coin flip go (`docs/st-logic.md` §3).
  - Kept: the gates (tracks 3, 5 and 8, every race; §5, D36) and wrecks (every track: leaving the area, squeezed
    between walls, a wall head-on at top speed; and tracks 2 and 6's bridge edges and jumps), as the game has them:
    the ST's wait for its helicopter (40 to 100 frames), no helicopter drawn, the car blinking where it comes back
    and the sweep over the blink (D16), the lap's clock running.
  - Gone: water, oil and the yellow patch (none in races 0 to 5, then `random(race / 6 + 1)`, at most 3), cones
    (from race 16, half the time), the pop-up barriers (every third race) and the tornado (after race 3, half the
    time). The wrenches and bonus go with them, as there's no score.
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
- **The menu (D40, D44)**: every track's best at once, so a player picks by who they'd like to beat as well as by the
  track, and each track's little map from the select screen, to say which is which. Tom, 2026-11-10: "I think I'd
  like to have the screen use the little mini track maps from the original track select screen. I think the new
  screen will need to work quite differently from the original, so that everything will fit (I was thinking a
  scrolling list perhaps?) - but I think the mini track maps are essential to remind the player which track is
  which."
  - The maps are 75 to 80 pixels by 47 to 50 lines each (MEASURED, cut from `build/gen/select.bin` by
    `select.6502`'s `RectCol`/`RectTop`/`RectBottom`), already in the game's colours, the select screen's picture
    2,440 bytes packed with its text (MEASURED, `build/gen/select.zx02`). Text in the ST's small font (D47,
    below; first planned in the MOS's font, through `font_char`; the HUD's font has only 15 glyphs).
  - **Decided (D47)**: layout A in 32 rows, the text in the small font, the SUPER SPRINT logo across the top in its
    red and yellow, no title or line of keys (`docs/img/timeattack-menu.png`, a copy of `build/ta/menu_a32_logo.png`). Tom, 2026-11-10: "Yes, mockup looks
    good. And I think the logo should be red+yellow." The working below.
  - Two layouts mocked up, in 32 rows (D46: `build/ta/menu_a32.png`, `build/ta/menu_b32.png`) and first in the
    race's 26 (`build/ta/menu_a.png`, `build/ta/menu_b.png`), the BBC's maps and the MOS's font, made-up entries;
    §7 question 8:
    - **A, all eight at once**: two columns of four, a map and 10 characters beside it (number and time, name,
      upgrades). No scrolling, and the screen can be one packed picture, the maps in place, with the text drawn
      over. In 32 rows, rows of 56 lines with a title and a line of keys; in 26, rows of 52, no title, the maps all
      but touching.
      A map (75 to 80 pixels) and 10 characters (80) fill a 160-pixel column, so a 10-character name runs into the
      right-hand column's map, no gap (`build/ta/menu_a32_w.png`, every name `WWWWWWWWWW`). Nine characters leave
      a character's gap (`build/ta/menu_a32_9.png`); the name under the map, the time and upgrades beside it, fits
      10 but leaves 2 lines between rows and no line of keys (`build/ta/menu_a32_under.png`).
      In the ST's small font instead (`G_01D43C`: 6 x 6, 6 pixels a character, drawn at any pixel by `front.6502`'s
      `front_glyph`, in the objects' bank through the front end, its 39 glyphs `SmallGlyphs`, 234 bytes), 10
      characters are 60 pixels and fit with 14 to spare, with room for "TRACK 1" (`build/ta/menu_a32_small.png`;
      the font, `build/ta/small_font.png`). Its glyphs (COUNTED, the ST's `G_01D118` and `G_01D43C`): 0-9, A-Z,
      space, `.` and `!` (the BBC's 39), and `-` and `'` (the ST's, 12 bytes more); no lower case and no colon, so a
      time is seconds, `12.40`, as the ST's winner's circle shows them (to 99.98, 4,999 fields, ESTIMATED as enough
      for a table's lap).
      With the credits screen's SUPER SPRINT logo across the top instead of the title and the line of keys
      (`build/ta/menu_a32_logo.png`): the logo is 34 lines (MEASURED, lines 73-106 of `build/gen/credits.bin`), the
      rows 55 lines each, 254 of the 256 used. The logo is red and yellow, the maps green, yellow and white, so colour
      1 is red over the logo and green below it: its 4 palette entries written at the logo's last line, timed from
      the vsync (about 40 bytes, ESTIMATED), or the logo's red drawn in the maps' colours.
    - **B, a scrolling list**: a row a track, the map then the text (track and time, name, the upgrades in words),
      five rows shown in 32 rows (four in 26), the list moved a row at a time; each map packed on its own (about 300
      bytes, ESTIMATED) and drawn as its row comes into view, on the screen not shown, then flipped. Room for words,
      but not every track's best at once.
  - Return on a track opens its screen (D48), Return there races (the upgrades, 5 points over three, forked from
    `upgrades.6502`, picked on the track's screen, D49). After Escape, a name for a new record, then the save,
    then the menus.
- **32 rows in the front end, 26 in the race (D46)**. Tom, 2026-11-10: "What about changing the 26 row setup in the
  front end? Would it be possible to show a full 32 row (256 scanline) Mode 1?" ... "Then switch to the 26 row setup
  in game." D25 has one layout for the whole game, set up once, for its wipe; time attack has no wipe (D45), and
  changes the layout around each race, during the loads.
  - **Room**: a 32-row screen is 20,480 bytes, `&3000`-`&7FFF`; its extra 6 rows are the screen's `&3000`-`&3EFF`,
    which holds ScreenVars (each screen's own variables, 104 bytes) and Shared (read-only, the same in both screens:
    the sound's effects, the tunes' data, the wall probes, the gates' tables, the drone path; `&3070`-`&3EFF`, 3,696
    bytes). Drawn on the screen not shown and flipped (D45), both screens are 32 rows, so both copies are lost in the
    front end:
    - The table (D40) goes in a sideways bank, not Shared: the objects' bank, which loses the tornado (3,100) and the
      pickups (701) in time attack. The front end's code reads it there; the save copies it to main RAM first, as
      the ghost.
    - Shared is put back in both screens before each race, from a packed copy in a bank (or in the track's file),
      unpacked twice. Time attack's is smaller (no drone path, 996; no table): about 2,500 bytes, perhaps 1,500
      packed (ESTIMATED), and much quicker than the load.
    - A front end tune (if any) carries its own data, not Shared's.
  - **The CRTC**: R6 (rows shown) 32 or 26, R7 (the vsync's row) and R12/R13 (the start, `&3000` or `&3F00`), set with
    the palette black, so a monitor's resync isn't seen. The race's flip into the blank (D17's T1 and T2) is timed
    for 26 rows; the front end flips at the vsync, drawing nothing against the beam. About 60 bytes (ESTIMATED).
  - Or (not proposed): one screen of 32 rows, drawn with the palette black and then shown, the other screen keeping
    Shared; the IRQ's sound then has to page Shared in itself while the front end draws.
- **The turnaround (D45)**: from Escape to the next race as short as it can be, but for the loads. Tom, 2026-11-10:
  "the turnaround time for playing should be as short as possible - I'm not thinking too much about the
  load+decompress time (that will just have to take as long as it takes), but I was imagining not having the
  transition effect, or the prepare to race screen, and so on." So:
  - No wipe between screens (D25's), no prepare to race, no winner's circle; each screen drawn on the screen not
    shown and flipped.
  - Escape, then the name only if the race's best made the table (D41), the save only if something changed (one
    table, at most one ghost), then the track's screen (D50).
  - Back to the track's screen (D50, below), the upgrades as last picked (D49), so another go with no new entry is
    one Return.
  - Proposed: the same track again loads nothing, if the front end's files keep out of the track's slots and the
    ghost's buffers (to be measured at step 6: where the menu's files go).
- **A track's screen (D40, D48)**: a track's 10 entries, a row each, from the menu: the track picked there (how is to
  be settled) and Return. Then Return races, Escape goes back to the menu. Tom, 2026-11-10: "select track on track
  select screen (exact mechanism to be determined) and press Return; game shows per-track high scores. Press Return
  again to race, or Escape to go back to track select". Its code in its own file, about 200 bytes (ESTIMATED), as the
  name's.
  - **The upgrades on this screen (D49)**, set at first as the last race's (whatever its track), not a screen of
    their own. Room: a row is the place, the time, the name and the upgrades, 10 rows in the small font, with the
    track's map, the logo and a line for the upgrades.
  - **The name every time (D49)**: a race whose best makes the table asks for a name, empty, never the last one
    typed: "The game will very likely be played in a hot-seat fashion, with a different people taking the controls
    each time." Tom, 2026-11-10, on the upgrades: "Even though I'm kind of assuming a different player each time, I
    still do like the idea of having the default powerups set to the same as the last play."
  - **After a race (D50)**: the name if the race made the table, the save if something changed, then back to this
    screen, not the menu, the new entry lit; Escape from it to the menu. Tom, 2026-11-10: "Yes".
- **The name (D39)**: up to 10 characters typed on the keyboard. The options screen already finds any key held from a
  table of key numbers (`opt_find`, `OptNumbers`, through `key_down`), so the name's screen is that with a table of
  A-Z, 0-9, space, Delete and Return and their characters (about 80 bytes), the typing loop and the drawing: about
  250 bytes (ESTIMATED), in its own file, not resident. Which characters beyond those (the small font has `.`, `!`, `-` and
  `'`, no lower case, D47) is for later. Typed in the small font, as the menu shows it.
- **Saved**:
  - One table for all 8 tracks (D40), 10 entries a track, 13 bytes an entry (the time 2, the name 10, the upgrades 1:
    three levels that sum to 5 or less are 56 combinations): 80 entries, 1,040 bytes (COUNTED). Resident, in a
    sideways bank (D46: first planned in Shared, as `HiFile` is now, but the front end's 32 rows overwrite Shared), so
    the menu and the lists read it without a load; loaded once at the boot and saved like `SCORES`
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
6. ~~Wrecks~~: kept, as the ST's; the hazards a track always has stay, those that come and go go (D42, Tom,
   2026-11-10) (§4).
7. ~~What a race puts in the table~~: its best lap only, one entry a race; a name can be there more than once, from
   different races (D41, Tom, 2026-11-10) (§6).
8. ~~The menu's layout~~: A, all eight tracks at once, in 32 rows, in the ST's small font, the logo across the top in
   red and yellow (D47, Tom, 2026-11-10) (§6, `docs/img/timeattack-menu.png`).

Each becomes a row in `docs/decisions.md`, Proposed until Tom agrees.

## 8. The steps

One commit each on `timeattack` (CLAUDE.md), the measurement in its body.

1. **The variant.** A time attack build from the same source, its own discs; the game's build proved unchanged.
   **Done** (2026-11-10): `tools/gendata.py --ta` writes `GenTimeAttack` (beside `GenPlay`), `TRACE=ta` is the play
   build with it, `tools/all_tracks.sh ta` builds every track's into `build/tracks_ta`, and `make ta` makes
   `build/ta.ssd` and `build/ta.adl` from them as `make game` does. MEASURED: `make game VERSION=ident` before and
   after, `build/game.ssd`, `build/game.adl` and every track's build the same byte for byte; `build/ta.ssd` the same as
   the game's too (sha256 `5aa5fac010a698a3`), as nothing reads `GenTimeAttack` yet. The suite 43 of 43 on agentbox.
2. **The race, one car.** One car set; no drones, pickups, oil, cones, barriers or tornado; endless laps; Escape out.
   Then the room measured on every track (`tools/all_tracks.sh`'s figures for the variant) and the frames' cycles
   (`tools/render_profile.mjs`).
   **Done, to be tried on Tom's Master** (2026-11-10). `Cars` (`race.6502`: 4, time attack 1) runs the loops that act
   on the cars (control, `collide`'s pass, `build_cars`, the HUD's); no car-to-car or draw order with one; car 0 the
   player's whoever joined; no barriers, tornado, oil-type patches, cones, bonus or wrench, the gates kept (D42); no
   lap events or points, so the laps are endless, but in the attract mode's demo race, which they end; Escape, not
   F10, abandons the race (to the attract mode, until step 6's front end). `tools/gendata.py --ta`: the green car's
   set alone, car 0 through `DataWhite` (D37). The game's front end is still the way in.
   MEASURED: the cars' bank 8,598 (track 6) to 10,440 (track 1) bytes free, 8,228 more than the game's on every track
   (`make ta`'s `tools/all_tracks.sh ta`); the code for what time attack leaves out is still there (the fourth bank
   95 free), for a later step. In jsbeeb (scripts, not yet in the suite): a race goes on 300 frames past car 0's laps
   poked to 4 where the game's disc ends it, one car record every frame; the demo race ends (762 fields); a wreck at
   the area's edge is put back at the same frame as on the game's disc (85 frames, the blink the same); 400 frames on
   each track repeat 12 to 14 fields, as the game's disc does (12 to 16: the start's); Escape back to the attract
   mode, by hand. The game's discs the same but for the README's commit link, every track's build byte for byte; the
   suite 43 of 43 on agentbox.
3. **The lap timer and HUD.** In pieces, each tried:
   - **3a, the timing** (done 2026-11-10): `cells.6502`'s `ta_lap` at the finish, car 0's: the lap's time in frames
     (`TaLast`; lap 1 from frame 0, as the ST's lap times, `game.6502`'s `circle_sums`, the others from the lap
     before), the race's best (`TaBest`, strictly under; 0 none yet); 6 bytes of LogicVars (6 left), the fourth bank
     95 to 29 bytes free (so the dead code time attack leaves out goes next but one). The lap number went (Tom,
     2026-11-10: "If the player is doing endless laps, it's probably redundant"), with nothing else needing it.
     MEASURED in jsbeeb (a script: the car put right of the line on track 1, checkpoints 1-3 passed, at three
     frames): laps of 92, 248, 143 frames and of 233, 106, 205, each its end frame less the last, the best 92, then
     233 to 106 kept (again without the lap number: the same); the game's tracks' builds byte for byte.
   - **3b, the HUD** (done 2026-11-10, to be tried on Tom's Master; Tom: "Yes, looks good. As with everything else,
     there may be adjustments required after seeing it in action"; `docs/img/timeattack-hud.png` in jsbeeb; the
     mock-up `build/ta/hud_mock3.png`): the lap's time running (white), `BEST` and the race's
     best (yellow), `GHOST` and the ghost's (green: the track's record, the table's first entry, D40, which the
     player's lap becomes when it's beaten), the track's `T1` as now; ` 0.00` for a best or ghost not there yet
     (Tom, "I think it'd be clearer if that were actually shown"); no lap number (Tom, above). Tom, on the ghost's:
     "So you know the overall target to beat, as well as your best so far, and if you lose to the ghost you can see
     how much by." Times as seconds and hundredths, `12.40` (D47), a frame 2 hundredths, to 99.98; as a lap ends its
     time held 2 s while the next counts on unseen, white, or yellow if a new best, or green if under the ghost.
     Seven glyphs more for the font (`.`, `B`, `E`, `S`, `G`, `H`, `O`, 56 bytes). Up to 3 characters change
     between a screen's frames as the time runs, within the HUD's 4 a frame; a lap's end changes up to 15 (the
     held time, the best, the ghost's), which takes 4 frames a screen to show, as a score's roll-over does now.
     Until the ghost and the table are in (steps 4 and 5), the ghost's time is ` 0.00`.
     Built: `src/timeattack.6502` in main RAM's code (`ta_lap` moved there from `cells.6502`, `ta_hud` each frame for
     `build_hud`, which time attack leaves out, and `ta_time`); `tools/font.py`'s `GlyphsTA` after the game's
     glyphs, `hud_char` masking 5 bits of a glyph for 4. The ghost is the race's for now: 0 at its start, then any
     lap under it. MEASURED (track 1's build): the fourth bank 29 to 193 bytes free, the `&3000` area 267 to 211,
     main RAM's code 1,061 to 707. In jsbeeb (scripts: the car put right of the line at three frames, the HUD's text
     read back each frame): laps of 233, 106, 205 frames shown `4.66`, `2.12`, `4.10`, each held 100 frames then the
     running time at `2.00`; green for laps under the ghost (lap 1's, with none), white for one beating nothing;
     with the ghost poked to 100 frames, yellow for the two bests over it; 6,000 and 4,999 frames shown `99.98`;
     drawn on the screen as the text says. 12 to 13 fields repeated in 400 frames per track, as before (the start's).
     The game's tracks' builds byte for byte; the suite 43 of 43 on agentbox.
   - **3c, the dead code out** (done 2026-11-11; Tom tried 3b on his Master: "works nicely"): what time attack never
     runs, found by recording every instruction run over 1,500 driven frames on each track (`build/tracks_ta`), then
     read: the pickups' code (`pickups.6502`, its state kept and read as none), the class 1 cells (the patches,
     pickups and cones: `cells.6502`'s dispatch goes on to the next cell; no track's map has one at the start, in the
     game or here), the barriers, cones and tornado (`hazards.6502`, the calls in `race.6502`, the set-up's slot
     sprites and the tornado's mover in `logicframe.6502`), and car-to-car (`shove`, `car_to_car`, `draw_order`,
     under `IF Cars > 1`). Kept: the drones and their path, which the attract mode's demo race drives car 0 with until
     step 6's front end; the objects' bank's tornado frames and the pickups' variants (data, for when that bank's room
     is wanted). MEASURED (track 1's build): the fourth bank 193 to 1,931 bytes free, main RAM's code 705 to 1,298.
     The game's discs the same but for the README's commit link, every track's build byte for byte. Time attack before
     and after (scripts in the scratchpad, not the suite): each track 2,400 frames driven by an autopilot along the
     drones' path, as a drone takes its segments, steering for the segment's end (laps on 6 of the 8 tracks, track 3's
     gates; it wedges on 5 and 8), every frame's car state, draw records, HUD text and both screens the same; the
     demo race still ends (763 fields, as before).
4. **The ghost.** Recorded and played back in the cars' bank. Its check: a scripted lap driven, then replayed, every
   frame's ghost record the same as the player's was (a headless oracle on `tools/jsbeeb.mjs`, in the suite).
   - **4a, the recording** (done 2026-11-11): `src/ghost.6502` in the cars' bank's code (256 bytes), called from the
     frame loop after `logic_frame` (`ghost_frame`) and at the race's start (`ghost_start`): car 0's draw record each
     frame, coded from the last (a byte for a move of up to 4 pixels each way; a byte more when the facing or on-top
     bit changes; `&FE` nothing drawn; `&FF` and the 4 bytes whole: the first, after nothing, an explosion's, a jump),
     into one of two 3,000-byte buffers at the bank's end, above every track's priority cells (asserted). A lap's
     buffer holds its frames from the crossing (or the race's first) to the frame before the next, as many as its time.
     `ta_lap` makes a lap the ghost only if its recording fitted (`GhFull`), and tells the recorder (`GhLapEnd`), which
     keeps that buffer as the ghost's and takes the other for the next lap. Nothing drawn yet.
     MEASURED: the cars' bank 4,184 (track 1) to 2,342 (track 6) bytes free below the buffers; main RAM's code 1,298 to
     1,266. In jsbeeb (a script, the autopilot driving 2,400 frames a track): each lap that became the ghost decoded
     from its buffer against car 0's records drawn in that lap, frame by frame: 14 ghosts on 6 tracks, 0 wrong, each
     as many frames as its time; 1.12 to 1.37 bytes a frame (the estimate 1.2), 588 to 1,204 bytes a lap. Buffer A's
     room poked to 100 bytes: lap 1 no ghost (its time not the ghost's). 12 or 13 fields repeated in 400 frames per
     track, as before (the start's). The game's discs the same but for the README's commit link, every track's build
     byte for byte.
   - **4b, the ghost drawn** (done 2026-11-11, to be tried on Tom's Master): `ghost.6502`'s playback, after the
     recording each frame: at each crossing of the line (and the race's start) the ghost from its buffer's first
     record, then a record a frame; its lap done first, its first record held until the player crosses (D43). Its
     record into the draw list as car 3 (black, D37; an explosion's as it is), at first before the player's or after by
     y + 255 on top (`draw_order`'s key), then always before (below). No ghost in lap 1 until step 5 loads
     one: the first lap finished is the first ghost.
     MEASURED: the ghost's code 768 bytes in all; the cars' bank 3,672 (track 1) to 1,830 bytes free below the
     buffers. `tools/ta_ghost_check.mjs` (not yet in the suite; with `tools/ta_pilot.mjs`, the autopilot): every
     frame's draw list against a model built from the player's logged laps, 2,400 frames a track: 19,200 frames, the
     ghost drawn on about 9,900 and waiting at the line on 264, 0 wrong; with the ghost's x poked a pixel out at a
     frame, 25 frames wrong (to its next whole record). No fields repeated from frame 600 to 2,400 on any track, with
     the ghost drawn. On the screen (jsbeeb): a black car with the white car's highlights, plain on the road's
     checkerboard (`docs/img/timeattack-ghost.png`), harder to pick out against the walls' black shadows (D37 allows
     `DataId` or `DataYellow`). The game's discs the same but for the README's commit link, every track's build
     byte for byte.
     **The player over the ghost** (2026-11-11): Tom, after trying it, found the cars sometimes confused, "at least
     part of the problem is that the ghost car is sometimes drawn on top of the player car ... for this mode it'd be
     nice for the player car always to be drawn on top, even if this would be visually wrong". So the ghost's record
     goes first in the draw list, always (a bridge's priority cells still hide either car). Tried and dropped first:
     the player green (`DataId`), Tom: "Please revert"; mocked up and not built: the ghost dithered
     (`build/ta/ghost_dither.png`: stripes from its table alone, a checkerboard needing the plotter to switch tables a
     line). MEASURED: the cars' bank 3,672 to 3,928 bytes free on track 1 (the code shorter, the frames' page a page lower); `tools/ta_ghost_check.mjs`'s model the ghost first:
     19,200 frames, 0 wrong; `build/ta/ghost_under.png` the white car over the black where they overlap.
5. **Saving.** The table and the ghosts; a check as `tools/save_check.mjs`'s (saved, booted back, spoilt files
   refused, a write-protected disc's error said once). In two pieces, as the front end that will ask for names is
   step 6: the ghosts first, then the table (its names blank until step 6).
   - **5a, each track's ghost on the disc** (done 2026-11-11, to be tried on Tom's Master): `GHOST1`-`GHOST8`, each
     its time (2 bytes), its records' bytes (2) and its records. Saved as the race that made it ends: at the start of
     the next load, whatever's loaded (`load_track` calls `ta_save_ghost` once the OS has the machine, before any
     file), so it doesn't wait for step 6's flow, and the ghost's buffers aren't yet touched (prepare's file is parked
     over them, `ParkPrepare`). Loaded with its track, before the track's file (`ta_load_ghost`, for a file named
     with a digit), into the cars' bank at `GhHead`, the head then buffer A; `ghost_start` takes it from there, the
     HUD's ghost time with it, so lap 1 has the ghost. Through the main screen at `TrackFileAddr` (OSFILE can't reach
     a bank). Refused, as no ghost: no file, a length not the head's bytes + 4, bytes 0 or over a buffer, time 0. A
     failed save said once by `load_track`'s brk (`GhNew` cleared first, D23's way); a demo race's laps never
     saved (`GmDemo`). In main RAM's code (it calls OSFILE): 443 bytes, 1,266 to 823 free; the load's first 4K 181
     to 168.
     MEASURED: `tools/ta_ghost_check.mjs` now races each track twice on one machine, the second race's ghost the one
     the first saved, from the first frame, its time on the HUD, and each `GHOSTn` decoded against the model: 38,400
     frames, 0 wrong. `tools/ta_save_check.mjs` (not yet in the suite): `GHOST1` saved once a ghost (592 bytes, time
     478), loaded back after a boot and drawn from the start, saved over when beaten, not by a demo race (one making a
     new ghost); 4 spoilt files refused; a read-only disc's error said once ("Disc read only - press a key"); ADFS
     too. The game's discs the same but for the README's commit link, every track's build byte for byte.
   - **5b, the table** (done 2026-11-11): `src/tatable.6502`, 80 entries, 10 a track, a column a field (times' low
     bytes, high bytes, upgrades, names of 10), indexed track * 10 + place, best first, an empty entry's time 0;
     1,040 bytes in the cars' bank below the ghost's head (asserted above every track's slot). As a race ends (the
     frame loop on its way to `load_go`, `ta_race_end`), its best lap (`TaBest`) entered in its track's 10
     (`ta_enter`, D41): before the first it's under, a tie after, the 10th dropped; no lap, nothing; the demo's,
     nothing. Its upgrades 0 and its name 10 zero bytes, until step 6. Saved as `TIMES` (the 1,040 bytes and a
     2-byte sum: a total of the bytes and of the totals) at the next load's start after the ghost (`ta_save`: both
     flags cleared first, so a failed save is said once and neither is tried again), only if it changed. Loaded
     with each track, after its ghost (`ta_load`): until step 6 the game's screens park their files over it between
     races (`ParkPrepare`), so it can't stay resident yet; an empty table if there's no `TIMES`, it's not 1,042
     bytes, or its sum's wrong. Step 6 loads it once, at the boot.
     MEASURED: the cars' bank 3,924 to 2,628 bytes free on track 1, 786 on track 6 (its largest slot; the objects'
     bank's tornado frames and pickups' variants, still in time attack, are 3,100 and more, for when room's wanted);
     main RAM's code 823 to 463. `tools/ta_table_check.mjs` (not yet in the suite): 19 races on tracks 1, 3 and 8 with
     their bests poked (ties, none, past 10), each entered as its model has it, `TIMES` written only when the table
     changed and as the model, the table loaded at each next race's start as the model; back after a boot; 5 spoilt
     files refused; a read-only disc's error said once. With its model's order reversed it fails at race 2; ties
     can't be told apart until entries have names. `tools/ta_save_check.mjs` and `tools/ta_ghost_check.mjs` still
     pass. The game's discs the same but for the README's commit link, every track's build byte for byte.
6. **The front end.** The menu, the upgrades, the name; checks driven key by key as the screens' are now. No attract
   mode or demo race (D51): what only the demo needed goes (the drones and their path, the demo's lap events, `GhNew`'s
   `GmDemo` test). Planned 2026-11-11 in pieces, each tried, the visible ones on Tom's Master (the game's between-race
   code is `game.6502` in the background's bank, the pictures' `front.6502` beside it, each screen's file loaded into
   the main screen and copied up; time attack gets its own in their place):
   - **6a, room**: the objects' bank's tornado frames (`mov_tornado`, 3,609 bytes) and the pickups', oil's, cones'
     and barriers' variants in each track's `ObjSlot` out of time attack's build, as 3c did for code: play the same
     frame by frame (the autopilot's races before and after), the room measured. Where the packed Shared (6c) and
     the menu's code can go.
     **Done for the tornado** (2026-11-11): `tools/gendata.py --ta` makes no tornado keys (its compiled frames a stub,
     `GenTorPiece` zeros), `movers.6502`'s `mov_tornado` and its frames and `mov_all`'s call to it under
     `GenTimeAttack = 0`; `ParkUpgrades` is `ObjSlot` (`&9A00` in the game, as before), so the park moves down with
     the slot until 6b drops it. MEASURED: the objects' bank 4,322 to 7,906 bytes free on track 1, 34 to 3,618 on
     track 5 (its largest slot); main RAM's code 463 to 472. Time attack before and after (the autopilot, each track
     2,400 frames, car state, draw records, HUD text and both screens every frame): the same. The game's discs the
     same but for the README's commit link, every track's build byte for byte. The pickups' and hazards' variants in
     `ObjSlot` (per track) left: their indices are the slot sprites' numbers; not needed for room yet.
   - **6b, the skeleton**: time attack's own between-race code in place of `game.6502`'s flow: the boot to a plain
     menu, in the race's 26 rows and the MOS's font (as the load's row text), each track's best time and the track
     picked as D52 (the driving keys move a highlight, 1-8 pick, Return opens); Return races it; Escape back to the
     menu. Any player's keys drive the car (D53). The game's screens' files (attract, title, select,
     upgrades, circle, prepare) off the disc, the drones and the demo's code out; the table loaded once at the boot
     and kept (nothing parked over it now). Tried on Tom's Master.
     **Done but the drones** (2026-11-11, to be tried on Tom's Master; `docs/img/timeattack-menu-6b.png`):
     `src/tagame.6502` in place of `game.6502` (its image in the fourth bank's first 4K, copied up by `game_go` as
     before): after a race, or at the boot, the title's file (`TRACKF`) is loaded first, so the save's at that load's
     start (the ghost, `TIMES`, and `SCORES`'s keys and sound), its pictures unused; then the menu, black, `TIME
     ATTACK` and 8 rows of `TRACK n` and the track's best (`ta_track_best` reads the table in the cars' bank, main
     RAM's), in the small font (`front_glyph`), a block marking the highlighted track (`GmTrack`, so it stays after
     a race). Keys act once each press: 1-8 race that track, Return the highlighted one, any player's left and right
     move it, round from 8 to 1 (D52); a number or Return first. Any player's keys drive the car (`logic_frame` ORs
     the three players' inputs into car 0's, D53). The select, upgrades, circle, prepare and options files left out
     of time attack's build (16 files on the disc, 88,064 bytes; were 21, 125,696), and front.6502's prepare and
     park code; the table is loaded at every load (the menu's file's and a track's), not yet once at the boot. The
     drones and the demo's code are still in: next, a small piece of their own.
     MEASURED: the first 4K 168 to 2,634 bytes free, the front end's code 34 to 290, main RAM's code 472 to 444.
     `tools/ta_menu_check.mjs` (not yet in the suite): from the boot, track 1 marked; any player's left and right
     move the mark (a key held 40 fields: once; round from 1 to 8 and back); 3 races track 3, player 2's accelerate
     drives, Escape back with `TIMES` saved and its row alone showing a time, the mark on it; Return races the
     marked track; 5, made player 1's right too, races track 5. `ta_save_check` (its demo case gone, D51),
     `ta_table_check` and `ta_ghost_check` still pass, waiting for the menu in the background's bank (its address
     alone is reached in the ADFS ROM while it boots). The game's discs the same but for the README's commit link,
     every track's build byte for byte.
     **The drones and the demo out** (2026-11-11; Tom tried the menu on his Master: "Looks good!"): with no demo
     race (D51), what only it ran is left out of time attack's build: `drone.6502`'s code (its state kept:
     `RcGateLane` is the gates'), the drones' set-up in `race.6502`'s start and the control loop's call, the lap
     events and points (the demo's end), `race_end` and the logic's tests of it and of `GmDemo`, `ghost.6502`'s and
     `ta_race_end`'s `GmDemo` tests. The drones' path in Shared's slot is now `TrackNum` and 995 bytes of room, kept
     in place under the tunes' rings (`TuneRing`, asserted in the slot); its zeros pack to nothing in the track's
     file. The autopilot (`tools/ta_pilot.mjs`) reads the path from `orig/st/SUPER.DAT` as `tools/gen_logic.py`
     does, every track's entries the same as the build's tables (a script, all 8 tracks).
     MEASURED (track 1's build): the fourth bank 1,919 to 2,707 bytes free, main RAM's code 445 to 785, the first 4K
     2,634 to 2,637; the disc 88,064 to 83,456 bytes. Time attack before and after (the autopilot, each track 2,400
     frames, car state, draw records, HUD text and both screens every frame): 19,200 frames, 0 different. The four
     time attack checks pass; the game's discs the same but for the README's commit link, every track's build byte
     for byte; the suite 43 of 43 on agentbox.
     **The table loaded once** (2026-11-11): `ta_load_table` reads `TIMES` at the boot's first load only (the title's
     file's), `TaTableIn` set after its reads (so a disc error tries again) in `LowFree`'s byte that was the demo's
     next track (`GmDemoTrack`, the boot zeroes it), and the table's kept from then on: no load writes the cars' bank
     above every track's slot, and nothing's parked there now. A save that failed (a write-protected disc) leaves the
     race's entry in the table until the machine's off, where before the next load put the disc's back.
     MEASURED: main RAM's code 785 to 776 bytes free. `tools/ta_table_check.mjs` now counts the OSFILE reads of
     `TIMES`: some at the boot, none in the 20 races' loads after (each race's start the table as the model); with
     the flag's test taken out, it fails. The other three checks pass; the game's discs the same but for the README's
     commit link, every track's build byte for byte.
   - **6c, 32 rows**: the front end's screen 32 rows, the race's 26 (D46): the CRTC switched with the palette black,
     and Shared (the `&3000` area's read-only data, which a 32-row screen overwrites) put back before each race from
     a packed copy in a bank. Checked as `boot_check`/`flash_check` do, field by field.
   - **6d, the menu's picture** (D44, D47): layout A, the 8 maps from the select screen, the SUPER SPRINT logo in red
     and yellow (colour 1 switched mid-screen), the text in the ST's small font (`front_glyph`), a file loaded once.
     Against the mock-up (`docs/img/timeattack-menu.png`). Tried.
   - **6e, the track's screen** (D48): its 10 entries; Return races, Escape back to the menu. Tried.
   - **6f, the upgrades** (D49): picked on the track's screen, 5 points over top speed, turbo and traction, as the
     last race's; given to the race as the ST's set-up does, kept in the entry and the ghost's file. Tried.
   - **6g, the name** (D39, D49, D50): after a race that made the table, typed (up to 10), then the track's screen
     with the new entry lit. Ties' order then checkable (`tools/ta_table_check.mjs`). Tried.
   - **6i, the options** (D54): a screen of its own from the menu, mostly text with the logo: the three key sets
     redefined and the sound on or off, as the game's options do, saved as now. Tried.
   - **6h, the turnaround** (D45): measured from Escape to the next race; the same track again loading nothing, if
     the front end's files keep clear of the track's slots and the ghost's buffers.
7. **Close**: the variant's suite, both discs, Tom's Master.
