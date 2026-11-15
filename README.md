# Super Sprint for the BBC Master 128/Compact

Requires Master 128/Compact. 64 KB of sideways RAM must be available.

Get the latest release here: https://github.com/tom-seddon/super-sprint-beeb/releases/latest

Inside the zip file, there are five files, named similarly to the zip
file: 2 `super-sprint-game` disk image files, 2 `super-sprint-ta` disk
image files, and a README.

# Super Sprint

Use one of the `super-sprint-game` disk images, either the `.ssd` file
(DFS) or `.adl` (ADFS), as appropriate (both contain the same
contents). The disk auto-boots with SHIFT+BREAK.

**The game saves high scores to the disk** - make sure it is write
enabled.

## Instructions

(loosely adapted from the 8-bit instructions)

![Super Sprint title screen](./docs/docimages/game-title.png)

Just another racing game? No - this is THE racing game. SUPER SPRINT
lets one, two or three players compete head to head with a bird's-eye
view over eight gruelling tracks. There's plenty of challenge for your
driving skills, with ramps to jump, opening and closing gates, hidden
shortcuts, over- and underpasses, and banked turns. There are random
obstacles to avoid, and golden spanners to collect which can be traded
for custom car features to enhance your vehicle's performance.

To start the race, press one of the accelerate keys:

| Action | White | Green | Yellow       |
|--------|-------|-------|--------------|
| Left   | `Q`   | `,`   | Pad `5`      |
| Right  | `W`   | `.`   | Pad `6`      |
| Accel  | `E`   | `/`   | Pad `DELETE` |

Change the initial track using the left and right keys, and press
accelerate to select it. Additional players can join on this screen by
pressing their accelerate key.

![Select Track](./docs/docimages/game-tracks.png)

Additional players can also join on the prepare to race screen that
follows. Then the race begins! Each race consists of four laps - beat
the drone cars to qualify for the next one.

![Race](./docs/docimages/game-race.png)

Steer your vehicle using the left and right keys, and control its
speed with the accelerator. Hitting the circuit barriers at low speeds
only causes a delay, but on a high-speed impact your car explodes and
respawns after a delay.

On some tracks there are underpasses where you will be steering blind.
Other circuits feature gates which open and close, allowing brief
access to short cuts. Ramps enable you to leap over obstacles.

Random objects will appear on the track from time to time, to be
collected or avoided:

- *Golden Spanner* - for every 4 spanners collected, you can purchase
  a car upgrade at the end of the race
- *Bonus Score Pad* - shows a number which is added to the score of
  the driver that passes over it
- *Oil Slicks* - causes the car to spin out of control
- *Water Slicks* - causes the car to slow down
- *Tornado* - blows the car off course and into a spin

At the end of the race, the winner's circle is displayed, with the
rank, score, and best lap times for each car.

![Winner's Circle](./docs/docimages/game-winner.png)

Press accelerate to continue. If a player has accumulated 4 or more
spanners, they can spend 4 spanners on a car upgrade:

- *Super Traction* (5 levels)
- *Higher Top Speed* (5 levels)
- *Turbo Acceleration* (5 levels)
- *Increase Score* (no limit)

![Upgrade](./docs/docimages/game-upgrades.png)

At the end of the game, if you qualified for the high score table,
enter your name: use left/right to pick each letter and accelerate to
select it.

## Options

Press `f1` during the initial sequence to access the options screen.

Follow the prompts to change the assigned keys for each car. **The
defaults are recommended** - they have been chosen to avoid ghost
keypresses or clashing keys when playing on a Master 128 or Compact.

(If you change keys, experiment with the new keys on the options
screen. When pressing a key, it will be highlighted - watch for keys
that become stuck or unavailable when doing this. Choose different
keys when this happens; it's an unavoidable hardware issue for which
there is no workaround.)

If playing on an emulator, you may have to experiment to find keys
that work well for multiple players.

----

# Super Sprint (Time Attack)

Use one of the `super-sprint-ta` disk images, either the `.ssd` file
(DFS) or `.adl` (ADFS), as appropriate (both contain the same
contents). The disk auto-boots with SHIFT+BREAK.

**The game saves lap times and ghost cars to the disk** - make sure it
is write enabled.

Super Sprint (Time Attack) puts a fresh spin on the Super Sprint
experience. Drive timed laps to beat the current track record. Once a
record is set, you race against a ghost car that repeatedly drives the
best lap, to try to beat it.

(If you fail: there are 10 times per track, so you might still make
the top 10.)

![Main Menu](./docs/docimages/ta-tracks.png)

From the main menu, select the track you want to race. Press `1`-`8`
to select the track, or use left/right to select and accelerate to
confirm. (You can use any of the sets of keys from the normal game,
whichever you're most used to.)

| Action | Set 1 | Set 2 | Set 3        |
|--------|-------|-------|--------------|
| Left   | `Q`   | `,`   | Pad `5`      |
| Right  | `W`   | `.`   | Pad `6`      |
| Accel  | `E`   | `/`   | Pad `DELETE` |

The track screen shows the current high scores for the selected track,
and lets you pick a limited number of upgrades for the next race.

![Track Screen](./docs/docimages/ta-track.png)

Use left/right to move the highlight between the options.

`SPEED`, `ACCEL.` and `TRACTION` are the current upgrade levels. Press
accelerate to cycle between the upgrade level, `0` to `5`. You can
have up to 5 upgrades overall; if this is exceeded, change the numbers
until you're within budget again.

(Each lap time on the table shows the upgrades the player used for
that lap: `S` for speed, `A` for acceleration, and `T` for traction.)

Choose `RACE` to race.

![Race](./docs/docimages/ta-race.png)

In the race, you always race as the white car, and the ghost, when
present, always races as the black car. Your current time is shown at
the top left, then `BEST` (your best time this session), then `GHOST`
(the ghost's time).

Once you're done, press `ESCAPE` to get back to the track screen. If
you made it on to the best lap times table, enter your name so it can
be saved to disk for posterity! (And if you're number 1, your best lap
will be saved as the ghost car for future races.)

## Options

Press `f1` from the main menu to select the options screen, letting
you redefine keys and toggle sound.

## Merge

Use the merge program to back up or merge your Super Sprint (Time
Attack) lap times with another set.

Run the merge program with `*MERGE` from the disk.

You'll get a `*` prompt, allowing you to issue `*` commands to select
the Super Sprint (Time Attack) files you want to merge from - select
filing system, change drive, mount disk, and so on.

You can issue as many as required. Once ready, press Return on a blank
line, and the lap times and ghost cars will be loaded.

Now you'll get further `*` prompts, to let you locate the Super Sprint
(Time Attack) files to merge into, as above.

Again, press Return on a blank line. The best 10 lap times from both
sets will be determined, and the corresponding ghost car, and the
results written to the disk.

----

# Other BBC Notes

- the game is supplied as DFS and ADFS disk images, but it is intended
  to be compatible with other filing systems, and should run off ADFS
  hard disk. Copy the files to the filing system of interest, and
  `*RUN !BOOT` to start the game
- for best results, create a physical ADFS disk from the supplied disk
  image, as the files are arranged to shorten the load times

----

# Credits

Atari ST version created by State of the Art.

Programming: Nalin Sharma, Martin Green, Jon Steele

Graphics: Chris Gibbs

Sound: Mark Tisdale

BBC Micro version written by Claude Code (with occasional input from Tom Seddon).

----

# Building

(Claude did pretty much all of this. You'd be mostly on your own
here.)

```
git clone --recurse-submodules https://github.com/tom-seddon/super-sprint-beeb.git
cd super-sprint-beeb
make game && make ta
```

The results are:

* Super Sprint: `build/game.ssd` (DFS); `build/game.adl` (ADFS)
* Super Sprint (Time AttacK): `build/ta.ssd` (DFS); `build/ta.adl` (ADFS)

## For AI agents

Start with `CLAUDE.md`: how the project builds, how it's checked, and where everything else is. Where the port
stands is in `docs/plan.md`, the decisions in `docs/decisions.md`, the work done in `JOURNAL.md`. Please don't edit
this README: Tom writes it.
