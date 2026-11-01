# The ST version's graphics and data files

What the Atari ST version of *Super Sprint* stores and draws, from its code (`build/super.s`, made by
`tools/st_disasm.py`) and checked in Hatari 2.6.1 (TOS 1.04, `tools/hatari.sh`) on 2026-11-01. Addresses are
where TOS 1.04 loads the program under Hatari: text at `&AA56`, `a4` = `&1F296` (checked in the debugger).
`G_xxxxxx` names a global by its address, `F_xxxxxx` a function. The game logic is in `docs/st-logic.md`.

## The program

- `AUTO\SUPER.PRG`: Megamax C. 283 functions found, 70,696 of its 72,908 text bytes decode as code.
- Far calls go through a table of 101 `JMP abs.l` at the start of the text (`jsr n(a5)`, a5 = the text's
  start); near calls are `jsr d16(pc)`. Globals are `d16(a4)`: the BSS below `a4`, the initialised data above
  (the start-up code at `&ACB4` moves the data up by the BSS's length, 11,124 bytes).
- Start-up (`F_01031C`) allocates one block of `&4BAF0` (310,000) bytes at `&21800` and carves it up: the
  second screen, then `SUPER.DAT`'s pieces, then the clean background and the masks. The first screen is
  TOS's own at `&F8000`.

## Loading (traced with `--trace gemdos,xbios`)

| Order | File | Bytes | Loaded at | What happens to it |
|---|---|---|---|---|
| 1 | `INIT.DAT` | 5,139 | `&59E36` | Read first, into what becomes the background buffer: used early, then overwritten |
| 2 | `SUPER1.DAT` | 17,024 | `&61B36` | Into what becomes the masks: used early (front end), then overwritten |
| 3 | `SUPER.DAT` | 212,650 | `&29500` | Everything for the race and screens, in fixed blocks (below) |
| 4 | `SSPRINT.HSC` | 295 | `&1D314`.. | High scores, three reads (16, 93 and 186 bytes) |

The program also calls `Floprd` for drive A's first sector into `&59E36` (a disc check). With the game run
from a folder it reads nothing and the game carries on.

## Memory during a race

| Address | Bytes | What |
|---|---|---|
| `&F8000` | 32,000 | Screen 1 (TOS's) |
| `&21800` | 32,000 | Screen 2. The game flips between them with `Setscreen` (`F_014DDC`/`F_014D9C`) |
| `&29500` | 212,650 | `SUPER.DAT` |
| `&59E36` | 32,000 | The clean background (`G_01F23C`, `G_01F240`): tiles, trees, the HUD's frame. Sprites are erased from it. |
| `&61B36` | 8,000 | Mask 0, "solid": 0 where the background is colour 3, 4 or 7 (`F_015C24`) |
| `&63A76` | 8,000 | Mask 1, the road: 0 on the road (`F_015426`) |
| `&659B6` | 8,000 | Mask 2, priority: 0 where scenery is in front of cars (`F_0158D4`); the HUD's digits are also written here during the race |

Each mask is 1 bit a pixel, 40 bytes a line, 200 lines.

## `SUPER.DAT`

`F_01031C` sets a pointer to each block, at fixed offsets. Offsets are into the file.

| Offset | Bytes | Pointer | Contents |
|---|---|---|---|
| `&0000` | 3,488 | `G_01F234` | Front end (not decoded) |
| `&0DA0` | 9,120 | `G_01F230` | Front end (not decoded) |
| `&3140` | 7,190 | `G_01F22C` | Front end (not decoded) |
| `&4D56` | 32,768 | `G_01E484` | **Cars**: 128 frames of 256 bytes |
| `&CD56` | 80,000 | `G_01EDEA` | **Maps and tiles**: 10 bytes of header, 11 maps from `&CD60` (`G_01EDEE`), then the four tile sets |
| `&205D6` | 30,000 | `G_01EBDC` | **Object sprites** (catalogue below) |
| `&27B06` | 3,000 | `G_01D30A` | Road outlines, as line segments and fill seeds, per track |
| `&286BE` | 3,520 | `G_01DF4E` | Not decoded |
| `&2947E` | 2,000 | `G_01F228` | Not decoded |
| `&29C4E` | 12,300 | `G_01F220` | Not decoded |
| `&2CC5A` | 480 | `G_01F21C` | Not decoded |
| `&2CE3A` | 7,100 | `G_01E2A6` | Not decoded |
| `&2E9F6` | 8,000 | `G_01F218` | Not decoded |
| `&30936` | 13,684 | `G_01F210` etc. | Read into the background buffer's space and used by the front end before the first race overwrites it |

The blocks marked "not decoded" are left to the logic spec (paths, track data) or later phases.

## Track backgrounds (`F_015A24`)

Each track is a 40 × 25 map of 16-bit words, one per 8 × 8 cell: 2,000 bytes a map. There are 11 maps:
tracks 1-8, then the title picture, the Winner's Circle and a track select screen (those three use other
palettes). `tools/st_tracks.py` decodes them.

- **Bit 15 clear: a copy.** The word is a byte offset in the screen; the 8 × 8 cell already drawn there is
  copied. 57% to 75% of a track's cells are copies (437 to 751 of 1,000).
- **Bit 15 set: a tile.** Bits 0-10 are its number, bits 11-12 its type t, bit 13 flips it vertically, bit 14
  horizontally.
  - Type t < 3 stores t + 1 bitplanes (8 bytes each, a byte a row) and then a word. The word's set bits are the
    colours the tile uses: pixel value k is the k-th set bit counting down from bit 15. So a tile of 2 colours
    takes 10 bytes, of 4 colours 18, of 8 colours 26.
  - Type 3 is 4 full planes, 32 bytes.

| Tile set | Offset | Bytes a tile | Highest used |
|---|---|---|---|
| 0 (2 colours) | `&12350` | 10 | 605 |
| 1 (4 colours) | `&13AFC` | 18 | 1,157 |
| 2 (8 colours) | `&18C68` | 26 | 1,114 |
| 3 (16 colours) | `&1FDA6` | 32 | 64 |

`F_015FD6(track, buffer)` builds a track, in this order: clear the road mask (`F_015C7E`); draw the tiles
(`F_015A24`); draw the road outlines into the road mask and fill them (`F_015426`); make the priority mask
from a list of rectangles and colours per track at `G_01EE14` (`F_0158D4`); draw the trees and other
decorations from tables into the background (`F_015F40` via `F_015D94`); make the solid mask from the
background's colours (`F_015C24`); then `F_015CA2` (not decoded). It takes about 60 frames (1.2 s) on the ST.

The finished backgrounds and masks for all 8 tracks were dumped from Hatari at the moment `F_015FD6` returns
(breakpoint at `&D20A`, with the track number patched into the race function's argument at `&217A4`): see
`docs/img/st-tracks.png`. The decoded maps alone lack the trees.

**For the port:** the ST map's bottom row has "TRACK n" and "DRONE LAP" in its tiles, and the top rows hold
the grandstands where the ST prints its HUD. With the HUD in its own row (D6), those text cells need
repainting with grass. The rest converts as it is.

## Colours

The race palette (`G_01DAD8`, the same for all 8 tracks; set by `F_014E34`):

| Index | ST RGB | Use | Share of the 8 tracks' pixels |
|---|---|---|---|
| 0 | `000` | Outlines | 1.2% |
| 1 | `126` | Blue car's trim | 0.0% |
| 2 | `500` | Dark red: gates, trim | 0.1% |
| 3 | `222` | Dark grey: shadows, the road's shading | 6.5% |
| 4 | `550` | Dark yellow | 1.7% |
| 5 | `040` | Dark green: grass, trees | 4.2% |
| 6 | `345` | Slate: stands, kerb edges | 1.1% |
| 7 | `555` | Light grey: kerbs | 2.7% |
| 8 | `333` | **Road**; transparent in sprites | 56.2% |
| 9 | `147` | Blue car's body | 0.0% |
| 10 | `703` | Pink: the red car's body, arrows, gates | 0.2% |
| 11 | `444` | Grey: a drone-driven player's car | 0.5% |
| 12 | `773` | Light yellow: yellow car's body, stripes | 3.0% |
| 13 | `153` | Green: grass, and car 3's body | 14.8% |
| 14 | `567` | Pale blue: kerb highlights | 3.9% |
| 15 | `777` | White | 3.9% |

## Cars (`F_01519C`)

- 128 frames at `SUPER.DAT+&4D56`, 256 bytes each. Frame = car × 16 + direction, plus 64 for a second set
  (`G_01E34C[car]` set). Frames 0-63 are cars 0-3: blue, red, yellow and green (car 3 is always a drone).
  Frames 64-127 are the same cars in grey with their colour as stripes, for a player's car that a drone
  drives (`docs/st-logic.md`).
- **16 directions.** Frame 0 points up, 4 right, 8 down, 12 left.
- A frame is 16 rows of four longwords (planes 0-3), 32 pixels wide: the car is in the left 16, the rest is room
  for the shift. 12 rows are drawn. The car itself is 16 × 12.
- **Colour 8 is transparent**: the mask is NOT plane 3 OR plane 0 OR plane 1 OR plane 2.
- The plotter shifts with `ror.l` (0-15 pixels), then:
  - unless the car's state word (`G_01E3A4[car]`) has bit 10 set, it records which of the car's pixels lie on
    the road mask (to `G_01E434`, for collisions), and clears plane 3 where mask 0 is 0;
  - unless bit 0 or bit 10 is set, it hides the car where mask 2 (priority) is 0. That is how cars go under
    bridges and behind the HUD. So bit 0 means "on the upper level", bit 10 "drawn over everything".
- Car colours: car 0 blue, body 9 and trim 1; car 1 red, body 10 with 2, 4 and 12; car 2 yellow, body 12 with
  4; car 3 green, body 13 with 5. Frames 64-127 have grey bodies (11) with the car's colour as stripes. All
  use 0, 3, 7, 11, 14 and 15 for the outline, wheels, windows and highlights.
- A first version of `tools/st_sprites.py` read the planes in the order 0-3 and so got the colours wrong
  (yellow and red swapped, car 3 grey, the second set green). The colours a car draws on screen in a Hatari
  dump settled it.
- Erasing: `F_0150C4` copies a 32-pixel-wide, 12-line block back from the clean background (the position is
  remembered per screen in `G_01E464`).

## Object sprites (block at `SUPER.DAT+&205D6`)

Found from the functions that read `G_01EBDC`. Offsets are into the block. Sizes are from the code. The
names are guesses from looking at the frames (`tools/st_sprites.py`) and the callers. Only the explosion (rendered in the plotter's own format) and the bonus markers (seen in the
block at about that offset) are confirmed. The others need checking when the hazards are ported.

| Offset | Format | Drawn by | What |
|---|---|---|---|
| `&0000` | 16 × 16, 4 planes, 128 bytes a frame | `F_0147A0` (race) | Tornado frames |
| `&0180` | 48 × 16 blocks, `&240` bytes each, copied unmasked to the screen and the background | `F_014A04` | Gates and other fixed scenery that changes |
| `&0CC0` | 16 × 8, 64 bytes a frame, copied unmasked to both | `F_0149B4` | Bonus markers ("5", "10", "100", "150", "250") |
| `&1240` | 32 bytes a frame | `F_014B1C` | Small objects |
| `&1740` | 8 rows of 6 words, 32 bytes a frame | `F_014A80` | Small objects (oil, wrench) |
| `&1BC0` | 16 × 8 masked, 64 bytes a frame | `F_0148BE` | Small objects |
| `&24C0` | `&2D0`-byte frames of 36 rows of 32 pixels (flying vertically, `F_01440E`), or `&410`-byte frames of 26 rows of 64 from `&3B40` (sideways, `F_0144AA`) | `F_0146DA` composes them | The helicopter that brings a new car |
| `&5BC0` | 16 × 14, 112 bytes a frame, 26 frames | `F_0152E0` | The crash explosion |
| `&6720` | `&150` bytes a frame | `F_014C1C` | HUD car icons |
| `&6F00` | 48 bytes a character, 10 | `F_014C8C` | HUD's large digits |
| `&70E0` | 16 × 16, 128 bytes | `F_015D94` (set-up) | Trees |
| `&72E0` | 32 bytes a frame | `F_015E30` (set-up) | Small decorations |

## Speed

- **The race runs at 50 fps**, one flip per VBL (`docs/st-logic.md` §1 has the measurements). A first count
  from a Hatari trace said 16.7 fps: that was a mistake. Hatari collapses repeated identical trace lines unless
  given `--msg-repeat`, so most of the race's flips were missing from the count, and the 3- and 4-VBL gaps
  left were the screen wipe's. With `--msg-repeat`, the last 199 flips of the attract race each have exactly
  one `Vsync`.
- Over 600 VBLs of the attract race the CPU spent 70% of its time in the game's code and 30% in TOS (mostly
  waiting in `Vsync`): about 112,000 of the 160,000 68000 cycles in each 20 ms frame.
- The biggest single costs: the car plotter `F_01519C` 15%, `F_00F23C` 8.9% (the drones' driving: in the
  attract race all four cars are drones), the sound driver 5%, `F_0157D8` 4.9%, `F_01603C` 4.2%.
- The sound driver runs on MFP timer D: `F_013954` calls `Xbtimer(3, 3, &CD, &139A6)`, which is
  2,457,600 / 16 / 205 = 749 Hz. The handler at `&139A6` steps a sequencer every 9th tick (83 Hz) and three
  channel routines (`F_013AB6`, `F_013B20`, `F_013B8A`) on their own counters.
