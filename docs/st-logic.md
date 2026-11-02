# Super Sprint (Atari ST): game logic

What the ST version's game logic does, worked out from `orig/st/AUTO/SUPER.PRG`, its data files and Hatari 2.6.1.
It is a spec to write 6502 from, not a translation of the C. Graphics and file formats are covered elsewhere;
this doc only touches them where the logic depends on them.

**How facts were checked.** Each section says which facts were checked in Hatari (breakpoints, per-frame memory
logs, RAM dumps, screenshots). Anything not marked that way comes from reading the code.

## Contents

0. Conventions, tools and a correction
1. The frame
2. Cars
3. Track interaction
4. Car-to-car collisions
5. Drones
6. Race rules
7. Input
8. Sound
9. Game sequence
10. Where the data lives
11. Bugs and quirks
12. Notes for the port

## 0. Conventions, tools and a correction

**Addresses.** `F_xxxxxx` is a function and `G_xxxxxx` a global, at run-time addresses (text at &AA56, a4 = &1F296).
Nearly all game tables are BSS filled at start-up, so their addresses are the same in every run.

**Cars.** There are always 4 cars. Car 0 is blue, car 1 red, car 2 yellow; each can be a human or a drone. Car 3 is
always a drone. Per-car variables are word arrays of 4, indexed by car (`G_01E404[car]`). The upgrade levels are
4 words per car (`G_01E2AC + car*8`).

**Correction to the brief.** `F_00C592` is the real race; it is called from `F_0141B0`, the game. `F_00D1FA` is the
attract-mode demo race; it is called from the main loop `F_013F68`. The two are near copies; the differences are
listed in section 9.

**Tools written for this** (all in `tools/`):

| Tool | Does |
|---|---|
| `logic_lift.py <hex>` or `all` | Turns a Megamax function into rough pseudo-C (symbolic execution per basic block). Good for compiled C. For the hand-written assembler routines (car drawing, `F_00BEEA`, `F_00F092`, the sound interrupt) read the asm instead. |
| `logic_fn.sh <hex>` | Prints one function's asm from `build/super.s`. |
| `logic_init.py [G_xxxxxx ...]` | Splits `INIT.DAT` into the 43 tables `F_0104EC` copies it to, and prints them. |
| `logic_maps.py` | Per-track logic data: `attr`, `walls`, `wallmask`, `prio`, `slots`, `path`, `fixed`, `summary`. Run it with `.venv/bin/python` (it uses PIL for `wallmask`). |
| `logic_mem.py <dump> <hex> <n>` | Prints words from a 1 MB RAM dump. |
| `logic_trace.py <hatari log> 1D30E` | Turns per-frame Hatari `m` dumps into a table of car variables. |
| `logic_snd.py` | Decodes the sound instruments and sequences in `SUPER.DAT`. |
| `logic_fifo.py` | Sends commands to Hatari's `--cmd-fifo` without blocking. |

**Driving the original in Hatari** (checked). Write `w $1F200 0 0` (see the copy protection in section 9) and
`w $1DFFE 3` (left shift held: keyboard accelerate) from a breakpoint at VBL 2000, during the attract mode. A
one-player game starts with the blue car on the keyboard. `$1DFF2` is A (left) and `$1DFF4` is D (right). Poking
`$1DFD2`/`$1DFD3` with `$80` holds fire on joystick 0/1, which brings in the red and yellow cars too. Poked values
stay until a real key or joystick event arrives. `tools/logic_trace.py` reads the output of a breakpoint on
`pc = $CF2A` (the top of the car loop in `F_00C592`) that runs `m $1D30E 2` and `m $1E2A0 400`.

## 1. The frame

### Frame rate (checked)

**The race runs at 50 frames a second on a PAL ST: one frame per VBL.** The game's work for a frame fits in one
20 ms VBL period. The flip `xbios_014D9C` (&14D9C) swaps the two screen pointers (`G_01F248` back buffer,
`G_01F244` front, &21800 and &F8000), adds 1 to the frame counter `G_01D30E`, calls XBIOS Setscreen with the new
front buffer, and then calls Vsync once. Setscreen takes effect at the next VBL and Vsync waits for it.

Measured with a breakpoint on &14D9C that prints the VBL counter `&462`:

| Run | Flips | VBLs per flip |
|---|---|---|
| Attract demo race, VBL 2200 to 2400 | 199 | all 1 |
| One-player race, track 1 | 1,469 | all 1 |
| Three-player race, track 1 | 1,602 | all 1 |
| Three-player race, track 3, with tornado, barriers and 3 hazards | about 2,600 | all 1 except 2 frames of 2 |

There is no frame-time compensation. All speeds are per frame, so a frame that overruns just makes the game run
slower for that frame. A 60 Hz ST would run the game 20% faster (inferred, not tested).

The 3, 4 and 5 VBL gaps seen between flips outside races come from the screen wipe `F_014E34`, which flips
through the same function with `F_010214(2)` waits (2 VBLs each) between steps, and from other front-end screens.
They are not race frames.

**Interrupts.** The game installs no VBL handler of its own; Vsync is TOS's. It installs an MFP Timer D interrupt
at 749.3 Hz for sound (section 8) and its own IKBD handler for keys and joysticks (section 7).

### The race loop (`F_00C592`, real race)

**Set-up, once per race:**
1. `F_015FD6(track, &59E36)`: builds the background picture, the three 1-bit masks and the attribute map (section 3).
2. `F_01C3E4`: tracks 5, 6 and 7's skid marks, lines from per-track tables drawn into the background (found
   in Phase 3; this was listed as part of the HUD). `F_014C1C(0..2)`: HUD and car panels. `F_0102AE`: copies the background. `F_014E34(&G_01DAD8)`: wipe in.
3. `F_00FAD8(track)`: selects the track's drone path (section 5).
4. For each car: start position, speed 0, laps 0, upgrades applied (section 2), drone set-up (section 5).
5. Draw order `G_01E2CC` = {0, 1, 2, 3}.
6. Hazard set-up (section 3): pop-up barriers if `(race + 1) % 3 == 0`; tornado if race > 3 and a coin flip says so;
   then `F_016884` (save the HUD strip), `F_00AE16` (oil-type hazards), `F_00ADDC` (bonus and wrench timers),
   `F_00AFF2` (cones), `F_00AF7A` (gates), `F_00BA9E(0)` (start banner).
7. `G_01D30E` = 0. The fixed objects, gates, cars and banner are drawn into both buffers (2 flips).
8. Start sound `F_0131A8`; "get ready" text (`F_016F4E`, string at `G_01F296`) and a 50 VBL (1 s) pause
   (`F_010214(50)`); engines on (`F_013582(0..2)`).

**Each frame, in this order:**
1. **Erase** last frame's sprites in the back buffer, from the clean background at &59E36:
   cars (`F_0150C4`, in draw order), up to 8 sparks (`F_014BC8`), the banner (`F_014978`), the tornado (`F_01487E`),
   the drone-lap digit (`F_014D72`), the helicopter (`F_014634`). Each buffer keeps its own list of what to erase,
   indexed by `G_01D30E & 1`.
2. **Track objects:** pop-up barriers (`F_00B9A0`), gates (`F_00B1B2`), bonus (`F_00B326`), cones (`F_00B10C`),
   wrench (`F_00B560`).
3. **Car control,** cars 0 to 3 in index order, unless the car is wrecked (`G_01E3D4[car] != 0`):
   humans `F_00DC4C(car)` followed by the engine sound `F_012BA2(car, speed)`; drones `F_00F23C(car)`.
   This is skipped once the race has ended (see section 6).
4. **Lap events:** the first car whose lap count becomes 3 shows banner 1 (`F_00BA9E(1)`, presumably "final lap").
   The first car whose lap count becomes 4 starts the finish: banner 2, engines off, a 170-frame countdown. Banners
   are 12-frame animations (3 frames a step) at the track's banner position, shown for 180 frames; banner 0 is shown
   at the start.
5. **Every 64 frames** (`G_01D30E & 63 == 0`), while no car has finished: 10 points to every car (`F_0167D6`).
6. **HUD** (`F_014310`): one player's score and lap per pair of frames (section 6).
7. **Collisions and car drawing** (`F_00E66A`): sections 3 and 4.
8. **Sparks** (`F_00B718`), **drone lap digit** (`F_014D3A`), **banner** (`F_00BABC`), **tornado** (`F_00B852`),
   **helicopter** (`F_00BD4A`).
9. **Flip** (`xbios_014D9C`).
10. **Keys:** F8 pauses (silence, then a busy wait for F8 again), F10 abandons the race (returns 1).

The race ends when the 170-frame countdown reaches 0 (section 6). The demo race `F_00D1FA` uses a 50-frame countdown.

## 2. Cars

### State per car

| Global | Meaning | Units and range |
|---|---|---|
| `G_01E42C`, `G_01E424` | x, y | Pixels, top-left of the car's 16 x 12 sprite box. Legal range x 2 to 301, y 2 to 185 |
| `G_01E3FC`, `G_01E3F4` | x, y | 1/8 pixel (x * 8). The pixel values are these divided by 8 |
| `G_01E3CC`, `G_01E3C4` | Previous x, y | 1/8 pixel. For humans, before this frame's move; for drones, after it (a quirk) |
| `G_01E3EC`, `G_01E3E4`, `G_01E3DC` | Last safe x, y, direction | 1/8 pixel; used to put a wrecked car back |
| `G_01E41C` | Facing direction | 0 to 15, 0 = up, clockwise, 22.5° a step |
| `G_01E414` | Travel direction | 0 to 15. The direction the car moves in when not accelerating |
| `G_01E404` | Speed | 0 to top speed, in "speed units" (see below) |
| `G_01E374` | Top speed | Speed units |
| `G_01E36C` | Divisor | 40 for drones; 40 - 5 * turbo level for humans |
| `G_01E364` | Steering threshold | Speed units |
| `G_01E35C` | Speed cap during a jump | Speed units (11 * divisor / 4) |
| `G_01E40C` | Steering timer | 0 to the steering delay |
| `G_01E2EC`, `G_01E2E4` | Target velocity x, y | speed * direction vector |
| `G_01E2FC`, `G_01E2F4` | Smoothed velocity x, y | Same units |
| `G_01E3B4` | Bounce timer, or wreck timer | Frames |
| `G_01E3AC` | Car-to-car immunity timer | Frames |
| `G_01E37C` | Spin counter, or jump step frame counter, or wreck animation counter | Frames |
| `G_01E384` | Jump sequence position | Index into `G_01D1FC`/`G_01D1CE` |
| `G_01E3A4` | Flags | See below |
| `G_01E39C` | Latches for track cells | See section 3 |
| `G_01E3D4` | State | 0 racing, 1 crash pending, 2 wrecked |
| `G_01E354` | Laps completed | 0 to 4 |
| `G_01E38C` | Last checkpoint passed | 0 to 3 |
| `G_01E394` | Stripes crossed since the last checkpoint | For ranking |
| `G_01E32C` | Frame number at the end of each lap | 4 words per car |
| `G_01E324` | Wrenches held | |
| `G_01E34C` | Drone flag | 0 human, 1 drone |
| `G_01E2AC/AE/B0/B2 + car*8` | Upgrade levels: super traction, higher top speed, turbo acceleration, increase score | 0 to 5 |

Drone-only variables are in section 5.

**Flags `G_01E3A4`:**

| Bit | Meaning |
|---|---|
| &0001 | Elevated: on the bridge or ramp level |
| &0002 | Hit by another car this frame; bits &000C hold that car's number |
| &0010, &0020 | Set by the oil and yellow patches (with their latches), cleared when a spin ends |
| &0040 | On a "nudge" cell stretch (track 2's ramp approaches). Turns off car-to-car collisions and flips the auto-straighten parity |
| &0400 | Airborne: in a scripted jump |
| &0800 | Passed over a safe landing cell during the jump |
| &1000, &2000 | Set by cell types 5 and 7 (&14, &1C), cleared by a ground cell (&08). The steering reads them: &1000 (and airborne) stops the straightening, &2000 makes the delay 1 less (corrected in Phase 4 from F_00BEEA's asm: an earlier reading had these as &0010 and &0020) |
| &8000 | Set with &0001, never read |

### Direction vectors

`G_01E280` (x) and `G_01E260` (y), 16 words each, from `INIT.DAT` (checked in RAM):

| Dir | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dx | 0 | 3 | 6 | 7 | 8 | 7 | 6 | 3 | 0 | -3 | -6 | -7 | -8 | -7 | -6 | -3 |
| dy | -7 | -6 | -6 | -3 | 0 | 3 | 6 | 6 | 7 | 6 | 6 | 3 | 0 | -3 | -6 | -6 |

Vertical moves are 7/8 of horizontal ones (pixel aspect). Diagonals are 6 + 6.

### Movement (humans `F_00DC4C`, drones `F_00F23C`; checked)

Each frame:
1. Target velocity: `vx = speed * dx[d]`, `vy = speed * dy[d]`. `d` is the facing direction when accelerating, or
   the travel direction `G_01E414` when not.
2. Smoothing: `svx = (svx + vx) / 2`, `svy = (svy + vy) / 2` (signed division, rounding towards 0).
3. Position: `x8 += svx / divisor`, `y8 += svy / divisor` (rounding towards 0; no remainder is kept).
4. Pixel position: `x = x8 / 8`, `y = y8 / 8`.

All arithmetic is 16-bit and signed.

**What this means in pixels.** With divisor 40, a human car's top speed of 110 gives 22/8 = 2.75 pixels a frame
horizontally (137 pixels a second), 19/8 vertically and 16/8 + 16/8 diagonally. A first-race drone at speed 72 does
503/40 = 12/8 = 1.5 pixels a frame vertically. Checked: steady `svx` is -659 at direction 10 and speed 110.

**Grip.** There is no tyre model and no skid state. What feels like grip comes from three things: the smoothing
(a new velocity takes effect over 2 to 3 frames, so the car slides a little on every turn), coasting in the old
travel direction when accelerate is released, and the steering delay above the traction threshold. The spins in
this section and the sparks after a bounce are the only "skid" effects.

### Acceleration and top speed (checked)

- **Accelerate held:** speed += 2 a frame, up to the top speed. The travel direction becomes the facing direction.
- **Not held:** the car coasts in its travel direction. Speed drops by up to 2 a frame, set by a 7-frame cycle
  `G_01D178` (0 to 6, advanced in `F_00E66A`) and the table `G_01D17A[level][phase]`:
  - 1 is taken off unless `G_01D17A[turbo][phase]` is 1;
  - another 1 is taken off if `G_01D17A[traction][phase]` is 1.

  | Level | `G_01D17A` row | Ones in 7 |
  |---|---|---|
  | 0 | 0 0 0 0 0 0 0 | 0 |
  | 1 | 1 0 0 0 0 0 0 | 1 |
  | 2 | 1 0 0 1 0 0 0 | 2 |
  | 3 | 1 0 1 0 0 1 0 | 3 |
  | 4 | 1 0 1 0 1 0 1 | 4 |
  | 5 | 1 0 1 1 1 0 1 | 5 |

  So a car with no upgrades loses 1 a frame (checked: 53 to 4 in 49 frames). Turbo makes coasting longer; traction
  brakes harder (k/7 a frame extra).
- Speed never goes below 0.

### Steering (checked)

Input bits: 4 = left, 8 = right, &80 = accelerate. Left and right share one timer, `G_01E40C`.

The **steering delay** `n` depends on the speed `v` and the divisor `D` (all integer):
- if `v < G_01E364`: `n = 5 - v / D`;
- otherwise: `n = 3 + v / D`;
- minus 1 if flag &2000 (never set), and at least 1.

For a car with no upgrades (D = 40, threshold 80) that is 5 below speed 40, 4 from 40 to 79, and 5 again from 80.

- **Right held:** if the timer has reached `n`: travel direction = facing, facing += 1, timer = 0, and if
  accelerate is held, speed -= `n`. Otherwise the timer goes up by 1.
- **Left held:** if the timer is 0 or less: travel direction = facing, facing -= 1, timer = `n`, and speed -= `n` if
  accelerating. Otherwise the timer goes down by 1.
- So holding one way turns one step every `n + 1` frames (every 6 frames at low speed: checked, frames 844, 850,
  856). Reversing turns at once, because the timer is already at the other end.
- Turning while accelerating costs `n` speed each step, which the +2 a frame wins back within a few frames.
- When coasting, the travel direction is the facing direction before the last step, so the car drifts.
- **Neither held (auto-straighten):** only if no spin is running, the speed is below `11 * D / 4` (the level-0 top
  speed) and the facing direction is odd (even if flag &0040 is set; never if flags &1400 are set). The timer creeps on: if it is at or below `n / 2` it counts down and
  turns left when it reaches 0; otherwise it counts up and turns right when it reaches `n`. So a car left on a
  diagonal-between direction settles on one of the 8 main directions.
- No input is read while the bounce timer `G_01E3B4` is running (10 frames after a wall bounce).

### The upgrades

Applied at the start of each race in `F_00C592` (levels 0 to 5, `D` = divisor):

| Upgrade | Level word | Effect |
|---|---|---|
| Turbo acceleration | `G_01E2B0` | `D = 40 - 5 * level` (40, 35, 30, 25, 20, 15). Every speed constant scales with D, so this is a pure acceleration boost: 2 speed units a frame is 16/D eighths of a pixel a frame. Time from 0 to top speed: 55 frames at level 0, about 21 at level 5. Also cuts coasting losses (table above). |
| Higher top speed | `G_01E2AE` | `top = 11 * D / 4 + level * 5 * D / 40`. Top velocity is (22 + level)/8 pixels a frame horizontally: 2.75 to 3.375. |
| Super traction | `G_01E2AC` | `G_01E364 = top * 8 / 11 + level * 4 * D / 40`: steering stays quick up to a higher speed: 80 at level 0 (73% of top speed), plus 4 a level with D = 40. Also extra coasting brake (table above). |
| Increase score | `G_01E2B2` | Nothing in the race. Buying it adds 3,000 points (section 9). |

Also `G_01E35C = 11 * D / 4` (the level-0 top speed) caps the speed during a jump.

Drones have no upgrades: D = 40 and their own top speed (section 5).

### Spins (hazards, tornado, head-on crashes)

`G_01E37C` > 0 starts a spin (32 frames for oil and head-on hits, 28 for the tornado). For a human, each frame:
spin counter -= 1, speed += 1 (and at least 10), input ignored, and on odd counts facing += 1. So 32 frames turn
the car through a full circle while it slides on in its travel direction. At the end flags &0030 are cleared.
Drones do the same turning, but stop as soon as the facing direction equals their path direction.

### Jumps (scripted moves, flag &0400)

Started by ramp cells (section 3). `G_01E384` picks a sequence; `G_01D1FC` gives the frames per step and
`G_01D1CE` the facing change at the start of each step (from `F_012276`):

| Start | Frames per step | Facing change per step | Total |
|---|---|---|---|
| 0 | 3, 6, 7, 5, 4, 1 | +1, -1, -1, -1, -1, +1 | 26 frames |
| 8 | 3, 6, 7, 5, 4, 1 | -1, +1, +1, +1, +1, -1 | 26 frames |
| 16 | 7, 15, 3, 3, 2, 1 | +1, -1, -1, -1, +1, +1 | 31 frames |

During the jump: speed += 1 a frame up to `G_01E35C`; steering is ignored; accelerate counts only in the first 3
steps; the car is drawn over everything and has no wall collisions. At the end: if flag &0800 is set (the car
passed over a landing cell), sparks and a bump sound; otherwise the car crashes (`G_01E3D4` = 1). Flags &0C00 are
then cleared. Drones never run the sequence: they stay airborne until they reach a "ground" cell.

## 3. Track interaction

The track logic uses four per-track structures, all rebuilt by `F_015FD6` at the start of each race.
Mask layout: 320 x 200, 1 bit a pixel, 40 bytes a line, bit 7 of byte 0 is pixel 0. They sit at `G_01F238` = &61B36:

| Name here | Address | Built by | Meaning |
|---|---|---|---|
| Mask A | &61B36 | `F_015C24`, from the finished background | 0 where the background colour is 3, 4 or 7; 1 elsewhere |
| Mask B, walls | &63A76 (+&1F40) | `F_015C7E` clears to 0, `F_015426` draws | 1 = wall or off the road; 0 = road |
| Mask C, priority | &659B6 (+&3E80) | `F_015C7E` sets to all 1, `F_0158D4` clears | 0 = scenery in front of cars on the ground |
| Attribute map | &678F6 (`G_01EB20`) | `F_015CA2`, then hazards | 40 x 25 bytes, one per 8 x 8 cell |

### Walls: mask B and how cars hit it (checked)

**Making it** (`F_015426`). The data is in `SUPER.DAT` at &27B06 (3,000 bytes; loaded to &51006, `G_01D30A`), as
signed big-endian words:
- word `track` = the word index where that track's data starts;
- there: a count N, then a polyline start point (x, y) and further points, each joined to the last with a line
  (`F_015590`, a DDA starting with half the major length as its error, both ends drawn). A word &FFFF ends a
  polyline: it and the next word are skipped, the next pair starts a new polyline, and N counts all of these words
  in pairs;
- then a count of fill seeds and the seeds (x, y). `F_01572E` flood-fills from each seed, so the areas outside
  the track become 1.

`tools/logic_maps.py wallmask 0 out.png build/logic/attract2600.bin 63A76` rebuilds track 1's mask from the file and
compares it with the mask in a RAM dump: **0 pixels differ** for track 1. For track 3 the only 15 pixels that differ
are the gate's, which the game writes in while the race runs. Each track has 1 to 5 polylines (40 to 107 points)
and 1 to 5 seeds. Walls in the middle of the road (track 3's barriers, for example) are single-pixel lines, not
filled shapes; the probes still catch them.

**Testing it.** Wall collisions are pixel-exact against the car's shape:
1. When `F_01519C` draws a car (inside `F_00E66A`), it ANDs each line of the car's opacity (32 bits, rotated by
   x & 15) with mask B and stores the 12 results in `G_01E434` (12 longs). Airborne cars store zeros.
2. `F_00C4F6(car)` probes that buffer with 4 tests from `G_01E160` (16 bytes per facing direction, `INIT.DAT`+&1E8):
   two whole lines (top and bottom of the car) and two columns (left and right side), giving a 4-bit code: 1 top
   line touches a wall, 2 bottom line, 4 left column, 8 right column. The columns are tested on the lines from the
   top probe line down to the line above the bottom one.

   | Dir | Top line | Bottom line | Left column | Right column |
   |---|---|---|---|---|
   | 0 | 1 | 6 | 4 | 12 |
   | 1 | 1 | 10 | 3 | 14 |
   | 2 | 2 | 9 | 3 | 15 |
   | 3 | 3 | 9 | 4 | 16 |
   | 4 | 4 | 9 | 3 | 16 |
   | 5 | 4 | 10 | 1 | 16 |
   | 6 | 3 | 10 | 1 | 15 |
   | 7 | 3 | 11 | 3 | 13 |
   | 8 | 2 | 11 | 4 | 12 |
   | 9 | 3 | 11 | 2 | 12 |
   | 10 | 3 | 10 | 1 | 14 |
   | 11 | 4 | 10 | 0 | 14 |
   | 12 | 4 | 9 | 0 | 14 |
   | 13 | 3 | 9 | 0 | 12 |
   | 14 | 2 | 8 | 0 | 12 |
   | 15 | 1 | 10 | 2 | 13 |

   Lines are 0 to 11 from the top of the sprite box; columns are counted from its left edge (the probe masks are
   shifted by x & 15 along with the sprite). Column 16 is used, so the cars are up to 17 pixels wide.
3. The code becomes a push direction through `G_01E140` (`INIT.DAT`+&2E8):

   | Code | 0 | 1 | 2 | 4 | 5 | 6 | 8 | 9 | 10 | 3, 7, 11 to 15 |
   |---|---|---|---|---|---|---|---|---|---|---|
   | Result | none | 8 (push down) | 0 (up) | 4 (right) | 6 | 2 | 12 (left) | 10 | 14 | &80 = wreck |

   So the push is in screen terms, away from the touching side. Touching on opposite sides at once (squeezed)
   wrecks the car.

**Bouncing** (`F_00E66A`; checked). If there is a push direction `p`, the car is not already bouncing and not
wrecked:
- The car goes back to its previous position.
- Travel direction = `p`. Smoothed velocity = `2 * (10 + speed) * vector[p]` (an impulse).
- Speed = `speed / 4 + D / 2` (checked: 110 becomes 47, 48 becomes 32).
- Bounce timer = 10 frames for humans (no input), 5 for drones.
- Sparks (`F_00BE4A`) and the bump sound.
- **Wreck instead** if `p` is exactly opposite the facing direction and the speed equals the top speed (a head-on
  hit while flat out).

If there was no wall, no bounce running, the car is on the ground and not on a nudge stretch, the position and
facing are saved as the "last safe" place (drones save it every frame).

The car also wrecks if it leaves the area x 2 to 301, y 2 to 185.

### The attribute map

40 x 25 bytes, one per 8 x 8 cell, at `G_01EB20`. **Built** by `F_015CA2(track)` from `INIT.DAT`: `G_01EE02`
(`INIT.DAT`+&A48) gives each track's first record (0, 29, 100, 139, 194, 226, 313, 357, 422) in `G_01E488`
(`INIT.DAT`+&A5A, 422 records of 4 bytes): x cell, y cell, length (bit 7 set: a horizontal run, else vertical),
attribute byte ORed into each cell. `tools/logic_maps.py attr <track>` prints the runs and the map. Checked: the
decoded maps for tracks 1 and 3 equal the maps in RAM apart from the pickups and patches placed at run time.

**Reading it** (`F_00BEEA`, hand-written asm). Two probe points per car, at the front corners: the car's (x, y)
plus `G_01E0C0[dir]` (4 words per direction: dx1, dy1, dx2, dy2; `INIT.DAT`+&308). For direction 0 they are (4, 1)
and (11, 1). Each probe reads the cell under it.

**Byte format:** bit 7 is a "stripe" flag; bits 0-1 are the class; bits 2-6 the type.

- **Stripe (bit 7).** Stripes are lines across the road, every few cells. Each time a car on the ground moves onto
  a stripe (latch `G_01E39C` bit 7), `G_01E394` goes up by 1. With the lap and checkpoint, this ranks the cars.
- If both probes read 0 apart from bit 7, the latches in `G_01E39C` are cleared (bits &FF7F) and nothing else
  happens. So each cell type acts once per visit.
- Otherwise each probe's 7-bit value is handled in turn (the first probe, then the second):

**Class 0, level and ramp cells** (`v & 3 == 0`, type `v >> 2`):

| Byte | Type | Effect |
|---|---|---|
| &04 | 1, up | Elevated (flags &8001). Placed at the foot of each bridge ramp |
| &08 | 2, ground | Back on the ground: clears flags &0001, &0040, &0200, &0400, &1000, &2000 |
| &0C | 3, landing | If airborne, sets &0800: the jump will land safely |
| &10 | 4, ramp | If elevated, facing 8 to 15 and not already latched: airborne (&0400), jump sequence 0, speed at least 15. If already airborne: counts as a landing |
| &20 | 8, ramp | The same for facing 0 to 7, sequence 8 |
| &24 | 9, long ramp | If facing exactly 12: airborne and elevated (&0401), sequence 16 |
| &18 | 6, nudge | Flag &0040; facing 12 becomes 13, facing 4 becomes 3 |
| &14, &1C | 5, 7 | Set flags &1000, &2000 (latched): the steering reads them (corrected in Phase 4) |

When type 4, 8 or 9 starts a jump, the second probe is not looked at.

**Class 1, objects** (`v & 3 == 1`; ignored while airborne):

| Byte | Type | Effect |
|---|---|---|
| &01 | 0, water (blue patch) | Speed halved. Slow sound |
| &05 | 1, oil (black patch) | Speed at least 10; 32-frame spin. Skid sound |
| &09 | 2, (yellow patch) | Speed halved, at least 10; 32-frame spin. Slow sound |
| &0D | 3, wrench | One wrench to the car; the cell pair is cleared. One pickup a frame (`G_01EB56`) |
| &11 | 4, bonus | Bonus to the car (`G_01EB60`); the cell pair is cleared |
| &15 to &21 | 5 to 8, cones | Speed 0, cone `type - 5` knocked over (`G_01EBA8`), cell pair cleared, sparks |

Patches act once per visit: oil and the yellow patch latch in both `G_01E39C` and `G_01E3A4` (bits &10, &20 of the low bytes), water in `G_01E39C` only (&08). A finish line makes laps `(laps AND 3) + 1` (F_00BEEA). The patch colours come from a
screenshot of track 3 in Hatari.

**Class 2, checkpoints** (`v & 3 == 2`, number `n = (v >> 2) & 7`, 1 to 4): if `n` is one more than the last
checkpoint `G_01E38C`, it becomes the last checkpoint and the stripe count resets. Checkpoint 4 is the finish line:
lap count + 1, the frame number goes in `G_01E32C[car*4 + lap]`, and the last checkpoint goes back to 0.
Checkpoints passed out of order do nothing, so short cuts and reversing don't count.

**Class 3, bridge edges** (`v & 3 == 3`; only for elevated cars):

| Byte | Effect for an elevated car |
|---|---|
| &07, &27, &47, &67 | Wall on the bridge: push direction `(v >> 3) & 15` (0, 4, 8, 12) |
| &0B | Use mask B (ground walls) as normal here |
| &03 | Off the edge: wreck |

**An elevated car ignores mask B** unless one of its probes is on a class 3 cell, or on a hazard. So bridges and
ramps are walled only by the attribute map, and the ground walls underneath don't apply.

### The overpass, bridges and draw priority

Tracks 2, 4, 6 and 8 (indices 1, 3, 5, 7) have bridges. Track 2 has a jump over a gap and track 6 a long jump
(the ramp &24). The rules that make it work:
- **Level:** cells &04 set "elevated", &08 clear it.
- **Walls:** see above.
- **Collisions between cars:** only cars on the same level collide (section 4).
- **Drawing order:** every frame `F_00EF9E` sorts the cars by y, plus 255 for elevated cars, into `G_01E2CC`. Cars
  are drawn in that order, so elevated cars are drawn last.
- **Masking:** a car on the ground is hidden where mask C is 0, so it goes under the bridge. Elevated and airborne
  cars ignore mask C.

**Mask C** (`F_0158D4`, data `G_01EE14`, `INIT.DAT`+&83A, 526 bytes): 8 pairs (count, first record), then 6-byte
records: x / 8, y, width (high nibble: 16-pixel groups; low nibble: extra pixels), height, and a 16-bit
little-endian colour set. Inside the rectangle, every pixel whose background colour is in the set is cleared in
mask C. `tools/logic_maps.py prio <track>` prints them. Gates and barriers also write mask C.

### What the car drawing does with the masks (`F_01519C`)

Sprites are at `G_01E484` (&2E256, `SUPER.DAT`+&4D56), 256 bytes each, index `car * 16 + facing`, plus 64 for a
drone. Each line is 4 longs, one per plane, each 32 pixels wide; the code rotates them right by x & 15 and writes
two 16-pixel groups, so a car can be up to 17 pixels wide. 12 lines are drawn. Colour 8 is the transparent colour,
so the unused part of each 32-pixel line must be colour 8 in the data. For each line:
1. Opacity = not colour 8.
2. If not airborne: the line's opacity AND mask B goes to `G_01E434` (collisions); the sprite's plane 3 is ANDed
   with mask A; and, if not elevated, the opacity is ANDed with mask C.
3. The sprite is drawn into the back buffer through the opacity.

So **mask A takes plane 3 out of the car's pixels** where the background is colour 3, 4 or 7. The screen address
and height are kept in `G_01E464[frame & 1][car]` for erasing.

### Hazards, pickups and their timing

All random numbers come from `F_00ADB8(n)` = ((XBIOS Random & &FFFF) >> 1) mod n. "Race" means the race counter
`G_01EBC2` (0 for the first race of a game; see section 6).

**Slots.** Pickups and hazards go in 20 slots per track: `G_01EC48` (`INIT.DAT`+&60), 2 bytes each (x cell,
y cell; x always even). Each object takes 2 cells side by side (16 x 8 pixels) and is drawn opaque into both
screens and the clean background with `F_0149B4(sprite, x cell, y cell)`, from sprite data at `G_01EBDC` + &CC0.
Sprite &15 is plain road, used to remove an object.

| Object | Set up | How many and where | Behaviour |
|---|---|---|---|
| Water, oil, yellow patch (`F_00AE16`) | Race start | `random(race / 6 + 1)`, at most 3: none in races 0 to 5. Type of the first is `random(3)`, then the next types in turn. First slot `random(20)`, then + 3 + `random(4)` (mod 20) | Fixed for the race. Sprites &10, &11, &12 |
| Cones (`F_00AFF2`) | Race start | Only from race 16, and then half the time: 4 cones, random free slots | Disappear when hit. Sprite &14 |
| Wrench (`F_00B560`) | Race start | One at a time, a random slot of 20 | Appears 275 to 524 frames after the start, and again that long after each pickup. Stays until picked up. Sprite &13 |
| Bonus (`F_00B326`) | Race start | One at a time, a random slot of the first 15 | First 250 frames after the start. Grows over 4 sprites (12 frames each), stays 500 frames, shrinks, then 250 frames until the next. Value `random(4)`: 100, 150, 200 or 250 points (`G_01DF72`). Sprites 0 to 15 (value * 4 + size) |
| Gates (`F_00AF7A`, `F_00B1B2`) | Per track | Tracks 3 (1 gate), 5 (3), 8 (1); positions in `G_01ED98` | 5 positions (0 to 4); 6 frames a step; waits 84 + 90 * gate number frames at each end (the first wait is 48 * (gate number + 1)). Each gate is updated on 2 frames in 6. Drawn 48 x 16 by `F_014A04`, which also writes masks B and C, so a closed gate is a wall. Checked in Hatari |
| Pop-up barriers (`F_00B97C`, `F_00B9A0`) | Races where `(race + 1) % 3 == 0` | 3 per track (`G_01EC00`, `G_01EC30`) | At rest all three show sprite frame 3 (studs in the road, seen in a Hatari screenshot). One at a time steps to frame 0 (8 frames a step), stays there 75 frames, steps back, and 30 frames later the next one starts. Frame 0 is presumably fully up. 16 x 8, drawn by `F_014A80`, which writes masks B and C |
| Tornado (`F_00B7E6`, `F_00B852`) | Race > 3, half the time | One, at x 20 to 219, y 20 to 119 | Moves 1 pixel every 4 frames in a random direction (each axis -1, 0 or +1), new direction every 150 to 199 frames, jitters every 8 frames, bounces at x 0/300 and y -16/200. A car within 7 pixels in x and 8 in y of (x, y + 12), not airborne and not spinning, spins for 28 frames |

`tools/logic_maps.py fixed` lists the gates and barriers per track; `slots <track>` lists the slots.

### Wrecks and the helicopter

A car is wrecked (`F_00BB4E`, `G_01E3D4` = 2) by: leaving the screen area, being squeezed between walls, hitting a
wall head-on at top speed, driving off a bridge edge (&03), or a jump without a landing.
- The wreck animation plays (`F_0152E0`, frame `G_01E37C / 4`, up to 25) for a time set by where the car was: the
  helicopter flies in from the farther side, horizontally (4 pixels a frame, wait = horizontal distance / 4, 40 to
  80 frames) or vertically (2 pixels a frame, wait = vertical distance / 2, 50 to 100 frames).
- Only one helicopter flies at a time; a second wreck just waits.
- At the end `F_00ED28` puts the car back at its last safe place and facing, at speed 0, with flags kept only for
  &3180.

## 4. Car-to-car collisions

`F_00F038` (in `F_00E66A`) clears flags &000E on all cars and tests all 6 pairs (`F_00F092`). A pair collides if:
- neither is airborne or on a nudge stretch (flags &0440);
- |dx| ≤ 7 and |dy| ≤ 7 pixels (positions are the sprite corners);
- both are on the same level (flag &0001);
- their facing directions differ.

Then, with `d` = |facing1 - facing2| (0 to 15, not wrapped):
- `d` < 5 or `d` > 11 (roughly the same way: side swipes and shunts): both cars get flag &0002 and the other car's
  number in bits &000C.
- 7 ≤ `d` ≤ 9 (head-on) and both speeds ≥ 60: both spin for 32 frames (if not already spinning).
- Anything else: nothing.

**Response** (in `F_00E66A`, per car, when the immunity timer `G_01E3AC` is 0 and flag &0002 is set): clear &0002;
immunity 25 frames; travel direction = the other car's facing direction; smoothed velocity =
`11 * D * vector / 2` (twice top speed); drone path offset reduced by that velocity; speed * 3/4; back to the
previous position; bump sound. So each car is shoved the way the other car faces, and the shove fades as the
smoothing halves it each frame (about 2 frames of top-speed travel).

## 5. Drones

**How many.** Car 3 always, plus every colour no human is playing. In a game, a human who finishes behind any
drone becomes a drone (section 9). All drones use the same driver, `F_00F23C`. Drones are drawn grey (sprite set +64).

**Paths.** Data in `SUPER.DAT` at &2CE3A (7,100 bytes, loaded to &5633A, `G_01E2A6`). `F_00FAD8(track)` uses
`G_01D158` (start byte offsets 0, &2A2, &554, &826, &C78, &FAA, &13FC, &17CE) and `G_01D168` (entries 84, 86, 90, 138,
102, 138, 122, 124); both are set in `F_012276`. Each track's data is a count word then entries of 4 words:
x * 8, y * 8, length, direction word. `tools/logic_maps.py path <track>` prints them.

- Entries come in two interleaved **lanes**: even entries are lane 0, odd entries lane 1. Where a track has only one
  line, the lane-1 entries are zero and unused.
- An entry is a straight **segment**: start point, direction (bits 0-3) and length. The end point is
  start + length * vector (in eighths of a pixel), so length is roughly in pixels.
- **Direction word flags:** &0100 is a fork; &02nn picks a lane by gate `nn`; &04nn skips `nn` entries.

**Driving** (each frame, if not bouncing):
1. Travel direction = the current segment's direction.
2. "Passed the end?" (`F_00FA2E`): by quadrant `((dir + 2) & 15) >> 2`: up when y ≤ end y, right when x ≥ end x,
   down when y ≥ end y, left when x ≤ end x.
3. Speed += 2 up to the drone's top speed.
4. If passed: index += 2 (mod the entry count), then: fork: odd-numbered cars go on 2 more, even-numbered cars 3 more
   (changing lane); gate: + `G_01EB6E[gate]` (2, or 3 from when the gate leaves position 0 until 12 frames before
   it leaves position 4; checked); skip: + `nn`. `F_00FB14` then makes the new segment's start point the car's
   position and clears the path offset, so the drone snaps onto its line at every segment start.
5. Facing = travel direction (drones turn instantly), except during a spin.
6. Velocity: target = speed * vector + offset / 20, where the **path offset** (`G_01E30C`, `G_01E304`) is the
   drone's displacement from its line times D. Each frame the offset loses that 1/20. Then smoothing and movement as
   for humans.

**Being knocked off the line.** While bouncing (5 frames), a drone coasts in its travel direction and adds the
negative of each frame's movement to the offset. Car-to-car shoves do the same. Afterwards the offset term steers it
back towards the line (1/20 of the offset a frame), and the snap at the next segment start removes whatever is
left. Segments are often only 9 pixels long, so drones rarely stay off their line for long.

**Start.** A drone starts at its grid position but with x from the path's first entry (all tracks start the path
next to the grid), speed `car * 10`, and the y difference to the path in its offset. So the drones fan back onto
the line in the first second.

**Difficulty.** Only the top speed changes (checked in Hatari: 64, 68, 72 for cars 1-3 in race 0 on track 1, and 84
for car 3 in race 20 on track 3):

`top = 60 - 4 * track + 4 * car + race`, with `race` = `G_01EBC2` (capped at 50).

For comparison a human's top is 110 (2.75 pixels a frame), so a first-race drone on track 1 is at 55% to 65% of a
human's top speed, and drones only match humans after about 40 races. There is no catch-up during a race; the
values are fixed at the start. `race` goes up 1 after each race, but not when a drone wins (section 9). The other
things that grow with `race` are the hazards (section 3).

**Attract demo** (`F_00D1FA`): all 4 cars are drones with the player colours (`G_01E34C` = 0); top speed
`110 - 4 * track + 4 * car`; they start on lap 2, so the demo is 2 laps.

**Dead code:** `F_00F92E` (no callers) is an older "end of segment" test using `G_01E2DC`/`G_01E2D4`.

## 6. Race rules

**Laps.** 4 laps. A lap counts when the car crosses checkpoints 1, 2, 3 and then 4 (the finish) in order. The HUD
shows laps completed (0 to 3). Checkpoint runs per track (x, y, length in cells; v vertical, h horizontal):

| Track (index) | Checkpoint 1 | 2 | 3 | 4, finish |
|---|---|---|---|---|
| 1 (0) | 9,18 5v | 31,18 5v | 32,12 6h | 21,3 5v |
| 2 (1) | 32,16 7h | 13,1 4v | 8,20 4v | 27,20 4v |
| 3 (2) | 7,19 4v | 7,13 4v | 32,19 4v | 26,2 5v |
| 4 (3) | 12,13 5v | 11,8 5v | 27,19 5v | 17,2 5v |
| 5 (4) | 16,19 5v | 27,19 4v | 29,2 5v | 20,2 5v |
| 6 (5) | 8,19 5v | 20,14 4v | 31,9 4v | 9,1 4v |
| 7 (6) | 28,1 4v | 13,2 5v | 9,14 4v | 21,19 4v |
| 8 (7) | 26,1 3v | 16,13 3v | 6,1 4v | 16,21 3v |

**The end.** When the first car completes lap 4, banner 2 shows and the engines stop. Cars keep moving
for 4 more frames, then freeze; 165 frames later (170 in all, 3.4 s) the race returns. Any other car that also
completed lap 4 in those frames is put back to lap 3 with checkpoint 5 and stripe count 99, so there is exactly one
winner. The race time is the winner's finishing frame. There is no time limit.

**Positions** are ranked by lap * 100,000 + checkpoint * 10,000 + stripes (in `F_01AC1C`); on a tie a human is
placed ahead of a drone. The HUD uses the same order (`F_014286`: lap << 13 + checkpoint << 10 + stripes) to make
the leader's panel blink.

**Scoring.** Scores are 6 BCD digits per car at `G_01DFA8 + car * 6` (&80 = leading blank).
- 10 points to every car (drones too) every 64 frames while no one has finished (checked: all 4 cars had 140 at
  frame 928).
- Bonus pickups: 100 to 250.
- Wrenches: kept for upgrades, not points.
- After the race (winner's circle): 1,000 / 500 / 250 / 0 for places 1 to 4, plus an average-lap and a best-lap
  bonus of `max(0, (15 + track) * 50 - lap frames)` each, rounded down to 10. So the par lap is 15 + track seconds.
  Lap records (`SSPRINT.HSC`, frames): 286, 378, 414, 417, 275, 485, 511, 662.

**HUD in the race** (screenshot `build/logic/r3_7000.png`): top line, for each colour "BLUE CAR", a wrench
icon and count, "LAP", then the score and lap number; bottom line "TRACK n" and "DRONE LAP n". `F_014310` redraws
one player's panel per pair of frames (frame mod 6). Every 24 frames the leader is worked out; if it is a human, that
panel is blanked for 12 of each 24 frames. `F_014D3A` draws car 3's lap digit at screen offset &7998. Wrench counts
are drawn by `F_014C8C` when they change.

**Tracks.** 8 tracks (indices 0 to 7, shown as TRACK 1 to 8). After each race the next is `G_01D138[track]` =
{2, 4, 6, 0, 7, 1, 5, 3}, a single cycle 0, 2, 6, 5, 1, 4, 7, 3, 0. The first track is chosen on the select screen
(section 9).

**Per-track data** (`tools/logic_maps.py summary`, `fixed`):

| Track | Grid x, y, y step, facing | Drone top (race 0, cars 0-3) | Gates | Barriers | Bridges, jumps | Path entries | Lap record |
|---|---|---|---|---|---|---|---|
| 1 | 162, 27, 9, left | 60 64 68 72 | - | 16,88 32,80 48,72 | - | 84 | 286 (5.7 s) |
| 2 | 214, 160, 6, right | 56 60 64 68 | - | 256,128 272,128 288,128 | bridge with a jump over a gap | 86 | 378 |
| 3 | 202, 17, 9, left | 52 56 60 64 | 96,52 | 208,112 224,112 240,112 | - | 90 | 414 |
| 4 | 130, 17, 9, left | 48 52 56 60 | - | 32,60 16,69 16,78 | bridge | 138 | 417 |
| 5 | 154, 17, 9, left | 44 48 52 56 | 80,52 112,100 80,140 | 176,155 192,164 208,173 | - | 102 | 275 |
| 6 | 66, 8, 8, left | 40 44 48 52 | - | 32,48 16,57 16,66 | bridges and a long jump | 138 | 485 |
| 7 | 158, 152, 8, right | 36 40 44 48 | - | 96,155 112,164 128,173 | - | 122 | 511 |
| 8 | 118, 168, 6, right | 32 36 40 44 | 208,92 | 16,112 16,120 32,128 | bridge | 124 | 662 |

Cars start at the grid x and at y + car * step, facing as shown (`G_01EDA8`, `INIT.DAT`+0, 4 words per track); a
y of 186 or more is set to 178. The banner position per track is `G_01EBE0`/`G_01EBF0`.

## 7. Input

From the input write-up (checked in Hatari where stated).

**Keyboard handler.** `xbios_010BDC` (run through Supexec from `F_010CA0`) turns off key click and repeat (conterm
&484) and installs its own ACIA handler at &10C08 with Mfpint(6). `F_010CA0` sends IKBD command &14 (joystick event
mode; the mouse is off).
- A byte &FE or &FF starts a joystick packet; the next byte goes to `G_01DFD2` (joystick 0, the mouse port) or
  `G_01DFD3` (joystick 1). Joystick bits: 1 up, 2 down, 4 left, 8 right, &80 fire.
- Other bytes are scancodes (&76 and up are ignored). A press sets `G_01DFD4[scancode]` to 3; a release clears bit
  0. Everything tests bit 0.

**Controls.** `F_010CF2(device)` returns joystick-style bits:

| Device | Source | Left (4) | Right (8) | Accelerate (&80) |
|---|---|---|---|---|
| 0 | Keyboard | A, Z or L (&1E, &2C, &26) | D, X or ' (&20, &2D, &28) | Left shift, right shift or Alternate (&2A, &36, &38) |
| 1 | Mouse | always 0 | | |
| 2 | Joystick 0 | `G_01DFD2` | | |
| 3 | Joystick 1 | `G_01DFD3` | | |

Up and down are never used. Only one keyboard player is possible.

`G_01DFCC` holds the device for cars 0, 1 and 2: 0, 2, 3 from `INIT.DAT`+&388 (blue keyboard, red joystick 0, yellow
joystick 1). The options screen (F1) steps each with F2, F3, F4 through 0, 2, 3; F9 toggles sound (`G_01D312`);
F10 leaves only if all three devices differ.

**Function keys.** `F_010DAA` returns 1 to 10 for the first of F1 to F10 held (scancodes &3B to &44) and clears it.
Attract mode: F1 options. Race: F8 pause (busy wait, no Vsync, until F8 again), F10 abandon (back to the attract
mode, no results, no high scores). Winner's circle: F5 shortens the celebration. Esc ends the "prepare to race"
countdown. Keypad - and + (`F_00EE9C`, &4A, &4E) change `G_01D22A`; nothing calls it (dead debug code).

## 8. Sound

From the sound write-up. Checked in Hatari: the Timer D rate, the YM registers in the attract race, the engine
formulas in a real race, the wall bounce effect and the winner's circle noise setting. The rest is from the code.

### The driver

- All sound is the YM2149, driven by the game's own interrupt. No XBIOS Dosound.
- Set-up `F_0136C4` (from main): YM registers via `F_0135D8` (tones 0, volumes 0, envelope period &02BC = 700, shape
  &0C, noise period 31, mixer &F8); key click and bell off; the instrument table (`SUPER.DAT`+&30F66, 35 records of
  60 bytes) to `G_01F250`; the sequences (`SUPER.DAT`+&3179A, 10,000 bytes) to `G_01F260`; instrument 0 on all
  three channels.
- Interrupt: Xbtimer(timer D, ÷16, data 205, handler &139A6) = **749.3 Hz**. Every 9th tick (**83.25 Hz**, checked)
  the sequencer runs and the volumes are written (YM 8, 9, 10). On every tick each channel's pitch counter counts
  down; when it runs out it reloads from the instrument's rate and a new tone period is written.
- **Channel state** (30 bytes each, from `G_01F254`): pitch step, tone period, wobble counter, pitch tick counter,
  volume (0-255), 3 envelope segment counters, segment index, pitch reload.
- **Instrument** (60 bytes, +0 to +&21 used): step, period, wobble count, rate, start volume, 3 segment lengths,
  start segment, loop flag, 3 volume changes per tick, sweep flag, noise flag (0 = noise on), priority (+&20).
- **Pitch:** sweep 1: period += step each pitch tick, step sign flips after 2 then every 4 ticks (triangle vibrato).
  Sweep 0: the output alternates period ± step each tick (the engine growl). YM frequency = 125,000 / period Hz.
- **Volume:** each envelope tick adds the current segment's change; a segment lasts its length in ticks. Output =
  volume * master (`G_01F264`, normally 16) >> 8, so 0 to 15. After segment 3: loop or silence. A volume of 256 or
  more gives 16, the YM's hardware envelope bit (the helicopter uses this on purpose).
- **Sequencer** (`F_013BF4`): 3 tracks with stop flag `G_01F286[t]`, wait `G_01F27E[t]`, pointer `G_01F282[t]`.
  Commands: 0-2 start instrument (next word) on that channel (sets the noise bit and the channel priority
  `G_01F25C`); 3-5 set a period (next word) and restart the envelope; 6 wait N (N + 1 ticks); 7 or more end.
  Track 0 addresses all 3 channels (tunes); tracks 1 and 2 play on channels B and C.
- Starting an effect: master = 16, point track `car % 3` at the sequence. Some starters only play if the channel's
  priority is below a threshold.

### Engine (one channel per human car)

- Race start: instrument 0 on all 3 channels (`F_013582`). Instrument 0: step 900, period 3000, rate 18, sweep 0,
  volume 0, looping, priority 0.
- Each frame, for each human car still racing, `F_012BA2(car, speed)`, only if the channel's priority is 0 (no
  effect playing):
  - speed > 20: volume += 8 up to 200 + speed / 8; period = 3000 - 4 * speed; pitch rate = 18 - speed / 8.
  - speed ≤ 20: volume -= 8 while above 130.
- So the engine is a square wave switching between (3000 - 4v) ± 900 every 19 - v/8 Timer D ticks. At speed 34
  that is periods 3764/1964 (33/64 Hz) switching at 50 Hz; at 110, 3460/1660 (36/75 Hz) at 125 Hz.
- Drones have no engine sound. The attract demo has none at all (checked: volumes 0).

### Effects

| Event | Starter | Seq | Plays if priority < | Sound | Ticks |
|---|---|---|---|---|---|
| Race start | `F_0131A8` | &F2 | always | Instrument 25 on all 3 channels: period 200 ± 2 (625 Hz), level 15 decaying | 81 |
| Wall bounce | `F_0130A0` | &4A | 1 | Instrument 4: period 1500 swept by 600, a low bonk | 4 |
| Car-to-car bump, jump landing | `F_013032` | &0E | 2 | Instrument 2: period 333 swept by 123, a warble | 4 |
| Water, yellow patch, cone | `F_012F4A` (via `F_00AD5A`) | &B4 | 1 | Instrument 9: noise + tone, period 1000 swept by 34 | 47 |
| Oil | `F_012FB8` (via `F_00AD7E`) | &12E | 1 | Instrument 19: noise + tone, period 533 swept by 43, a skid | 49 |
| Wrench | `F_012E00` | &1C | 4 | Instrument 3: rising notes, periods 256, 188, 128, 94, 84 | 73 |
| Bonus | `F_012EDC` | &58 | 4 | Instruments 6-8: 3 notes (263, 188, 128) 3 times, fading (echo) | 129 |
| Tornado | `F_012E6E` | &A6 | 3 | Instrument 5: noise + tone, a whoosh | 91 |
| Wreck | `F_012C74` | &00 | always | On channels car%3 and the next: instrument 20 (noise crash), then instrument 1 (helicopter: period 1000 on the hardware envelope, 11.2 Hz chop, priority 7) | 36, then until stopped |
| Helicopter gone | `F_012D38` | &13C | always | Instrument 0 (engine) back on those 2 channels | 0 |
| Finish, pause, abandon | `F_013284` x 3 | &EC | always | Instrument 15: silence | 0 |

Instrument priorities: 2 is 2, 3 is 4, 4 is 1, 5 is 3, 6-8 are 4, 9 is 1, 19 is 3, 1 is 7, 0/15/20/25 are 0.

Front end: player select tune &1E64 (12 s), prepare to race tune &A14 (7.7 s) and a join jingle &150, winner's
circle one of 5 random tunes (&D46, &1188, &14B6, &171C, &1A8A, 10 to 13 s), upgrade screen tune &1E64 and a "ding"
(instrument 16) per purchase. Tunes set the noise period to 5 (drums) and fade out over 16 steps of 5 VBLs if a
screen ends early. Unused: `F_0134B6`, `F_01310E`, `F_013214`, `F_013026`.

**Sound quirks:** every effect ends with instrument 0, which resets the engine volume to 0, so a slow car stays
silent until it speeds up. After a pause the engines run instrument 15's state (no growl) and go silent about 36 s
later. After a tune fades out early, the noise period stays at 5 into the next race.

### SN76489 plan

- Same formula f = 125,000 / N, but N is 10 bits. Divide the engine periods by 4 (N = (3000 - 4v ± 900) / 4,
  190 to 975) and the helicopter's by 2. Transcode the sequences at build time into bytes with periods already
  converted; move bass notes above 1023 up an octave.
- Run the envelopes and sequencer in the 50 Hz vsync IRQ and scale waits and lengths by 50 / 83.25 = 0.6, or keep
  the data by running a VIA timer at about 83 Hz.
- The engine's ± flip at 50 to 125 Hz needs a faster tick: a VIA T1 at 250 to 300 Hz that only flips engine periods,
  or accept a flip per vsync (25 Hz).
- Volume: keep 0-255 and output `15 - (volume >> 4)` as attenuation.
- One tone channel per human car as on the ST; effects take it by the same priority thresholds. The noise effects
  (instruments 5, 9, 19, 20, 24) play their tone part on the car's channel and their noise part on the shared noise
  channel (highest priority wins). Noise period 31 maps to about rate N/1024, 5 to N/512.
- Helicopter: no hardware envelope, so ramp the attenuation in software (a sawtooth at about 11 Hz) on one channel.

## 9. Game sequence

From the sequence write-up; checked in Hatari where stated.

**Start-up** (`F_013F68`): loads `INIT.DAT` (unpacked into 43 tables by `F_0104EC`), `SUPER.DAT`, `SUPER1.DAT` and
`SSPRINT.HSC`; installs the keyboard handler and the sound timer; constants from `F_012276`; copy protection
`xbios_01090E` (reads the boot sector of drive A and looks for "SOA" at bytes 8-10; on failure `G_01F200` = 1, the
game ends after one race and the high scores are never saved; the port should leave this out).

**Attract loop** (for ever; each change uses the dot wipe `F_014E34`, 8 steps out and 8 in, patterns from
`G_01DD82`):
1. Title (palette `G_01DD62`), wait 250 VBLs.
2. High-score table (`F_0172EA`, 30 entries), wait 250.
3. Lap records (`F_01BF34`, all 8 tracks, frames / 5 shown as seconds), wait 250.
4. Demo race `F_00D1FA(track)`, tracks in the order 0, 2, 6, 5, 1, 4, 7, 3 (`G_01D148`). It ends 50 frames after a
   car finishes, or on fire or F1.
5. Wait 150.
6. Credits picture (`F_014196`), wait 325.

During every wait (`F_0140F0`): F1 opens options (`F_0192A6`); fire on any player's control starts a game with
that car (`F_0141B0(car)`). Either skips back to the title afterwards.

**A game** (`F_0141B0`):
1. **Select screen** `F_0198B6`: every car becomes a drone with a blank score, no upgrades and no wrenches, then
   the starting car becomes human. A 16-position dial moves 2 positions per left or right press. The start track is
   `dial >> 1` (0 to 7); the difficulty `dial >> 2` gives 0 to 3 starting wrenches to cars 0-2 (easy, medium 1 wrench,
   hard 2, very hard 3). So tracks 1 and 2 are easy and 7 and 8 very hard. About 10 s, or until fire. Other players
   join by pressing accelerate.
2. **Prepare to race** `F_018776` (also before the first race; checked): 3 panels, "press accelerate to play" on
   empty ones; 8 s, or Esc, or early once all three are playing. A drone colour whose control presses accelerate
   joins: score blank, upgrades cleared (wrenches already 0). Joining and continuing are free. Then high-score
   entry (`F_017A42`) for each colour that is a drone at that point and has a score.
3. **Race** `F_00C592(track)`. F10 returns 1: back to the attract mode.
4. **Winner's circle** `F_01AC1C` (checked against a screenshot): lap times from `G_01E32C`, finishing order (section
   6), place and lap bonuses counted up 10 at a time, lap records for humans, 200 frames of celebration (random
   animation, F5 to shorten). If a drone won, `G_01EBC2` goes down by 1 (so the race count doesn't advance).
   Then the **elimination** (checked): going down the order, the first drone found turns every car from that place
   down into a drone, which loses its wrenches and upgrades. A human must finish ahead of every drone; a lone human
   against 3 drones must win.
5. **Upgrades** `F_01A0D6` / `F_01A130(car)`: for each human with 4 or more wrenches. A dial picks one of: higher top
   speed, increase score, turbo acceleration, super traction (`G_01D03C` = {1, 3, 2, 0}); about 9.5 s, fire to pick.
   Each purchase costs 4 wrenches and adds 1 level (up to 5); "increase score" adds 3,000 points instead.
6. Prepare to race again (rejoins, high scores), then `F_01BBAA` restores the drones' running scores for display.
7. Next track `G_01D138[track]`; race counter `G_01EBC2` + 1, at most 50.
8. **Game over** when cars 0, 1 and 2 are all drones (or the protection failed). `F_010760` saves `SSPRINT.HSC`.

**High scores.** `SSPRINT.HSC`, 295 bytes: 31 x 6 BCD score digits (entry 0 unused), 31 x 3 initials (letter code
+ &0B; codes 1-26 letters, 27 space), 8 big-endian lap records in frames. Initials are entered with left, right
and accelerate, 30 s.

**Differences between the demo race `F_00D1FA` and the real one `F_00C592`:** the demo makes every car a drone
driven by `F_00F23C` but drawn in player colours; laps start at 2; top speed `110 - 4 * track + 4 * car`; no engine
sounds; no "get ready" pause; a 50-frame end; fire or F1 ends it.

## 10. Where the data lives

All of these were found by matching RAM dumps and pointer globals (`F_0102F8` sets up the pointers; `SUPER.DAT`
loads at &29500, so file offset = address - &29500).

| Data | File | Offset | Size | RAM | Global |
|---|---|---|---|---|---|
| Car sprites (4 colours + drones, 16 directions, 256 bytes each) | `SUPER.DAT` | &4D56 | &8000 | &2E256 | `G_01E484` |
| Tile maps and tiles (see the graphics side) | `SUPER.DAT` | &CD56 | &13880 | &36256 | `G_01EDEA` |
| Object sprites: gates (+&180), pickups (+&CC0), barriers (+&1740) | `SUPER.DAT` | &205D6 | &7530 | &49AD6 | `G_01EBDC` |
| Wall vectors (mask B) | `SUPER.DAT` | &27B06 | 3,000 | &51006 | `G_01D30A` |
| Drone paths | `SUPER.DAT` | &2CE3A | 7,100 | &5633A | `G_01E2A6` |
| Sound instruments | `SUPER.DAT` | &30F66 | 2,100 | copied | `G_01F250` |
| Sound sequences | `SUPER.DAT` | &3179A | 10,000 | copied | `G_01F260` |
| Track start grid | `INIT.DAT` | &0 | 64 | | `G_01EDA8` |
| Gate count, gate positions | `INIT.DAT` | &40, &50 | 16, 16 | | `G_01ED88`, `G_01ED98` |
| Pickup slots | `INIT.DAT` | &60 | 320 | | `G_01EC48` |
| Direction vectors x, y | `INIT.DAT` | &1A8, &1C8 | 32, 32 | | `G_01E280`, `G_01E260` |
| Wall probe table | `INIT.DAT` | &1E8 | 256 | | `G_01E160` |
| Wall code to push direction | `INIT.DAT` | &2E8 | 32 | | `G_01E140` |
| Attribute probe points | `INIT.DAT` | &308 | 128 | | `G_01E0C0` |
| Bonus values, 10-point addend | `INIT.DAT` | &394, &38E | 24, 6 | | `G_01DF72`, `G_01DF8A` |
| Priority rectangles (mask C) | `INIT.DAT` | &83A | 526 | | `G_01EE14` |
| Attribute runs, per-track index | `INIT.DAT` | &A5A, &A48 | 1,688, 18 | | `G_01E488`, `G_01EE02` |
| Banner position x, y | `INIT.DAT` | &10F2, &1102 | 16, 16 | | `G_01EBE0`, `G_01EBF0` |
| Barrier sprite kinds, positions | `INIT.DAT` | &1112, &112A | 24, 48 | | `G_01EC30`, `G_01EC00` |
| Trees (x, y, size) per track | `INIT.DAT` | &116A, &115A, &1162 | 462, 8, 8 | | `G_01F022`, `G_01F1F8`, `G_01F1F0` |

`tools/logic_init.py` prints every `INIT.DAT` table with its offset. Constants that are in the code rather than the
files (`F_012276`): jump sequences `G_01D1FC`/`G_01D1CE`, coasting table `G_01D17A`, path offsets `G_01D158` and
counts `G_01D168`, next-track tables `G_01D148` and `G_01D138`.

## 11. Bugs and quirks

- **Cars facing exactly the same way never collide,** and nor do cars 5, 6, 10 or 11 steps apart, or head-on cars
  below speed 60 (`F_00F092`).
- **Two car-to-car hits in one frame OR the car numbers together** in flag bits &000C, so the shove can take the
  direction of the wrong car (`F_00F092`, `F_00E66A`).
- **Drones are not moved back on a wall bounce:** their "previous position" is stored after the move
  (`F_00F23C`).
- **Drones teleport:** at every segment start they snap to the path, however far they were knocked off it.
- **Drones never run the jump sequence;** once airborne they stay airborne (no walls, no hazards, drawn on top)
  until a "ground" cell.
- **An elevated car on a hazard cell** gets ground wall collisions that frame (`F_00BEEA` only cancels them when no
  other action happened).
- **Cell types 5 and 7** (&14, &1C) set flags &1000 and &2000, which change the steering (an earlier reading of this doc had them unread).
- **Ramp types 4, 8 and 9** skip the second probe for that frame.
- **Track 8 attribute data** has a stripe run at cell (34, 30), outside the 25-row map; it ORs &80 into 5 bytes
  after the map (`G_01DF4A`, the HUD strip save), which is overwritten later. One stripe is missing.
- **Track 8 grid:** car 3's y would be 186 and is clamped to 178, 2 pixels from car 2.
- **The race end:** only the first car to finish gets lap 4; anyone else finishing within the 4 extra frames is
  put back. Everyone else is frozen where they are.
- **The leader blink** compares all 4 cars, but car 3 has no panel, so when the drone leads nothing blinks.
- **`G_01DFC0[3]`** (car 3's "last lap shown") is never updated, so the lap-3 and lap-4 events for car 3 rely on
  their one-shot flags.
- From the sequence write-up: an upgrade already at level 5 still costs 4 wrenches; "increase score" can be bought
  for ever; a player who rejoins loses their high-score entry; the "mouse and joystick" message can never appear.
- From the sound write-up: effects reset the engine volume; the pause leaves the engines on instrument 15; the
  noise period can stay at 5 into a race.
- **Dead code:** `F_00F92E`, `F_00EE9C`, some sound starters.

## 12. Notes for the port

- **Frame rate.** The ST runs the logic and the drawing at 50 Hz; the BBC aims for the same (D2). If it draws at 25 fps, run the car logic
  twice per drawn frame: it is cheap (a few thousand cycles per car), and every constant, timer and table then stays
  as it is. Halving the rate instead would need every per-frame constant changed (speeds, smoothing, timers,
  spin and jump tables, the 64-frame scoring, sound).
- **Wall collisions** need mask B at full resolution, because the 4 probes use the car's real shape. 8,000 bytes per
  track, but it can be rebuilt at load time from the vectors (3,000 bytes for all 8 tracks) with a line draw and a
  flood fill. A cheaper port could AND a fixed per-direction car shape instead of the sprite's opacity, with the same
  probe table.
- **The attribute map** is 1,000 bytes per track, from 4-byte runs (422 runs for all 8 tracks, 1,688 bytes).
- **Mask C** (priority) is only needed where there are bridges, trees or other foreground; a list of rectangles per
  track would do.
- **Mask A** only affects how plane 3 of the car sprites is drawn; it may not matter in 4 colours.
- **Drone paths:** 7,100 bytes for all tracks; positions could be bytes (pixels) instead of words (1/8 pixels) if the
  snap to the segment start is done in pixels.
- **Arithmetic:** speeds fit in a byte (0 to 135), velocities in 16 bits, positions in 16 bits (1/8 pixel). The
  divisions by D (15 to 40) and by 20 and 8 happen per car per frame; a reciprocal table per D would avoid a divide.
