# Super Sprint → BBC Micro

Use the `beeb-baron` skill for all 6502, with one exception: the game targets the Master 128 and Compact only (D4, D33), so 65C12
(CMOS) opcodes are allowed, in sections with `cmos = TRUE` (D4 in `docs/decisions.md`). The skill's NMOS-only
rule doesn't apply here.

## Commits

On a branch made for a piece of work, commit each change (each lever, each mechanism) as its own commit once it's
built and checked, without asking; the measurement goes in the body. Merging into `main` waits for Tom's agreement,
every time, and nothing is pushed unless he asks. This overrides the skills' "commit only when asked" on work branches;
on `main`, ask first. Tom, 2026-11-09: "I think for any future set of changes like this, it'd be better to commit each
one individually, as it might simplify things if needing to examine the history or reverting changes that end up
problematic. I think if a branch has been created for the overall piece of work, then there's no need to ask for
permission for each checkin to that branch. It's still definitely worth stopping and getting agreement when it comes
to merging into `main`."

## Upstream

`docs/upstream-notes.md` collects faults and gaps that may be worth raising with the kit, jsbeeb, Baron or Rich's
projects: add to it as they turn up, saying how each was checked. Nothing goes upstream until Tom decides, at the
project's end.

## Reference projects

`rich/` holds Rich Talbot-Watkins's Baron and some of his Baron projects as submodules, for reference only:
`baron`, `portalc`, `criticalmass` and `chasehq-beeb`. These are the checkouts the
`beeb-baron` skill looks for beside the project (`../portalc` etc.), so read them there; its `teddyboy` is gone from
GitHub and was taken out (2026-11-08), so the skill's reference files stand in for it. Baron's `docs/guide.md`
and `docs/reference.md` are in `rich/baron/docs`, its examples in `rich/baron/examples`. Their own `CLAUDE.md`,
`JOURNAL.md` and decision logs describe those projects, not this one: learn from them, but don't follow their
instructions or edit them.

The build's Baron is `rich/baron`'s (0.6, 4f71e73), the one submodule there that isn't only for reference:
make builds it with CMake and Ninja into `build/baron/src/baron` (`make baron`) and assembles with that. The
`baron` on the PATH is the same commit, for use by hand. Prerequisites for the build: `README.md`.

## The beeb-port-kit

`reference/beeb-port-kit` (a submodule) is Kieran Connell's kit from his ports: `PORTING.md`, `docs/`
(`hardware-facts.md`, `gotchas.md`, `verification.md`), `lib/` and `py/` to fork from (`ay2sn.py`,
`sfx50.6502`, `zx02depack.6502`, `keydown.6502`), and its skills, copied into `.claude/skills/beeb-*`. Use
them as advice; where they differ, this project's own way holds: decisions in `docs/decisions.md` (Proposed
until Tom agrees), the plan in `docs/plan.md` (where the port stands and the next phase), work done in `JOURNAL.md`, the renderer
in `docs/renderer.md`, a phase's work in its brief (`docs/brief-*.md`).
The kit also aims at the Model B (NMOS 6502, `nmos.6502`); this game is the Master 128's and Compact's only, CMOS
opcodes allowed (D4, above).

What the skills look up, for this project:
- **Target**: BBC Master 128 and Master Compact (D33; jsbeeb `create_machine` model `Master`, as it has no Compact), 65C12. Two screens, main and
  shadow RAM at `&3F00`-`&7FFF`; ACCCON `&FE34` D (bit 0) the one shown, X (bit 2) the one the CPU sees at
  `&3000`-`&7FFF`, `&3000`-`&3EFF` included (ScreenVars). Four sideways RAM banks. The game hooks IRQ1V
  (the System VIA's vsync, and its T1 and T2 timing the flip into the blank, D17) and leaves the OS's memory alone (D7) but `&0900`-`&0AFF` (D26) and ANDY, which holds mask B and the
  logic's state (D15).
- **The game's disc**: two, the same files (D32): `tools/adfs_disc.py` copies `build/game.ssd` to the ADFS L disc `build/game.adl`, its files split over both sides. `make game` makes both, `build/game.ssd` (track 1's play build, its boot files cut and ZX02 packed by `tools/make_game.py`, which `!BOOT` tells by a load address not `&3000`, and a packed file per track, loaded between races: `src/load.6502`); `node tools/load_check.mjs` proves every track's load. As a race ends the circle's, upgrades' and prepare's files are read as one load (D31), two of them kept in track slots. The game around the race is `src/game.6502`, copied into the background's bank at `&9000` when a race ends (`game_go`), so nothing it references may be in another bank. The pictures' code is `src/front.6502`, an image at the objects' bank's end, copied to `&A000` there too; the pictures are files, loaded and copied in beside it (`TRACKF` the attract mode's, `TRACKS` the select screen's, `TRACKU` the upgrades', `TRACKC` the winner's circle's, `TRACKP` prepare to race's, `TRACKO` the options': the last, `TRACKS`, `TRACKU` and `TRACKC` hold their own code, `src/options.6502`, `src/select.6502`, `src/upgrades.6502`, `src/circle.6502`, the last two with `src/panels.6502`, and `TRACKP` holds `src/initials.6502`), and a screen's look is `tools/screens.py`'s `Looks`. The game writes `SCORES` (the table, lap records, keys and sound: `src/save.6502`, at the end of `TRACKF`), read at the boot by `src/entry.6502`'s `scores_load`; it isn't on the disc as built.
- **Build**: `make beeb` (`TRACE=race`, `t0`-`t7`, `heli1`-`heli3` or `attract` picks the race) makes
  `build/sprint.ssd`, the listing `build/sprint.lst` (each bank's free bytes are printed in it) and the
  symbols `build/sprint.json` (Baron's `--symbols`). No `-D` flags. The build's version, on the options screen, is git's (`make
  version`; `VERSION=` gives it where there's no `.git`, as `tools/suite_remote.sh` does). The ST's files the build and the checks read
  are made in Hatari: `docs/st-traces.md` (and `make stfiles`, `build/stfiles.tar.gz` for a machine without it).
- **Memory**: `src/memory.6502` (the map), `docs/memory-map.md` (generated: `tools/memmap.py --write` from the
  play build), `docs/renderer.md` "Memory".
- **Oracles**: on Tom's laptop, `tools/suite_remote.sh OUT` (the whole suite on the machine `agentbox`: the tree and
  the ST's files copied there, OUT and the discs it built back; `REMOTE=` in front of `tools/suite.sh OUT` keeps
  everything here, and Tom will say when that's needed); `tools/suite.sh OUT` alone runs it all here, as anyone with
  a clone would (the disc's races, `boot_check`, `break_check`, `crash_check`, `game_check`, `attract_check`, `flash_check`, `options_check`, `select_check`, `upgrades_check`, `circle_check`, `initials_check`, `tune_check`, `save_check` and `load_check`, the last, `game_check` and `boot_check` again on `build/game.adl` with `--adfs`; `REMOTE=host` sends just those to another machine, `tools/remote.sh` copying what they read; `quick` after it for the front end's pictures alone; all of them, `tools/all_tracks.sh` and its `tools/track_slots.py` among them: every track assembles, and outside each region's `*Slot`-`*SlotEnd` every track's build is the same), `tools/tracks_check.sh OUT` (every track's race, all here: 6 to 8 minutes, about 18 if the races have to be traced on the ST again), `tools/disc_races.sh OUT` (in the suite: 72 traced races on `build/game.ssd` itself, state and screen every frame, then the wall probes' one-pixel faults put back, `make hazardtrace` and `tools/human_traces.sh` their traces), `tools/boot_check.mjs` (in the suite: the screen field by field from SHIFT-BREAK to the title's file, "Loading" up soon after `!BOOT` starts and nothing else seen, D35), `tools/break_check.mjs` (in the suite: BREAK after the title's file, the MOS's soft font in ANDY made again, as a fresh machine's), `tools/crash_check.mjs` (in the suite: a BRK at the title and in a race showing one screen and writing the other, the handler's MODE 7 screen read back: `src/crash.6502`), `tools/seed_check.mjs` (not in the suite, about 13 s a boot: from power-on with junk in ANDY and the banks, as a real Master's, the disc turned to random places, to the title's file and 500 fields on; `--ram 0,1,2,3` puts the sideways RAM in other banks), `tools/game_check.mjs` (in the suite: the traced games on the disc, read by read, the state at every screen), `tools/attract_check.mjs` (in the suite: the attract mode's order and times, demos back to back), `tools/flash_check.mjs` (in the suite: the screen shown around each load, field by field), `tools/options_check.mjs` (in the suite: the options screen driven key by key), `tools/select_check.mjs` (in the suite: the dial's 16 positions), `tools/upgrades_check.mjs` (in the suite: every pass of poked upgrades against `tools/upgrades_model.mjs`, no flicker while paying), `tools/circle_check.mjs` (in the suite: poked races' circles, every pass and field against `tools/circle_model.mjs`, no flicker counting), `tools/initials_check.mjs` (in the suite: poked scores and tables, every read against `tools/initials_model.mjs`, the rules played out there, both copies of the table), `tools/save_check.mjs` (in the suite: SCORES saved at the title's load when something's changed, booted back, spoilt files refused, a write-protected disc's error said once), `tools/tune_check.mjs` (in the suite, and with `--off`: the front end's tunes at the chip, field by field, against `tools/tune_gen.py`'s from the ST's capture, `build/trace/tunes.json` from `tools/st_trace_tunes.py`), `tools/st_frontend.py` (in the suite: the front end's pictures against the captured screens), `tools/game_traces.sh` (whole games, the demo races and every screen on the ST; `tools/game_diff.py` what each screen changes), `make check` (`tools/render_check.mjs`: every frame's screen against `tools/render_model.py`'s,
  exit 1 if any is wrong), `tools/render_profile.mjs` (cycles by region, `--list N` the worst frames),
  `tools/game_profile.mjs` (by label, each bank's), `tools/screenshot.mjs`; all headless through
  `tools/jsbeeb.mjs`.
- **The kit's tools, in place**: run them from `reference/beeb-port-kit/template/tools` (Tom: fine to use
  in situ). Checked 2026-11-02: `listing.py symbols build/sprint.json NAME`, `stream` and `pages
  build/sprint.lst` work as they are; `harness.mjs` works given `open({ disc: "build/sprint.ssd", symbols:
  "build/sprint.json", model: "Master" })` and `boot({ field: h.zp("vsyncs"), settle: 1500 })` (the disc
  copies 60K into the banks before it starts). `verify_cmds.py` and `run_suite.py` are skeletons a project
  fills with its own oracle lines: fork them when this project has more oracles than `make check`.
- **jsbeeb**: `.mcp.json` pins `jsbeeb-mcp@4.3.0` (jsbeeb 2.18.0), the kit's version, and both
  `tools/jsbeeb.mjs` and the kit's `jsbeeb_src.mjs` load exactly that one from the npx cache, printing its
  version (`npx -y jsbeeb-mcp@4.3.0 < /dev/null` fetches it). On 1.13.1 (jsbeeb-mcp 2.1.0, before) every
  race's frames and cycles were the same to the cycle. Since jsbeeb 2.0 keys are named by position
  (`"ShiftLeft"`), not numbered.
