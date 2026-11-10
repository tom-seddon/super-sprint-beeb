# Brief - can a Linux runner make the ST's files? (for the GitHub Actions build)

> **Status: RUN** (2026-11-10, Linux Mint 22.3: results below). Hatari 2.4.1 can't; 2.6.1 built from source can. For an agent on Tom's Linux PC. Tom, 2026-11-10: "I will have an agent test this on my Linux
> PC. Please ensure there is enough info committed for them to run the correct experiments, and I will have them add
> the results to the notes."

## Why

The plan's "A GitHub Actions build" item (`docs/plan.md`, "After Phase 5"): Tom wants a GitHub Actions workflow that
builds the game and zips `game.ssd` and `game.adl`, named by the commit's UTC date and time and the 5 hex digits the
options screen shows (`super-sprint-20261110-1432-e6e28.zip`, the discs inside named the same way).

The build reads files made by running the ST original in Hatari (`docs/st-traces.md`): track dumps, traced races,
captured screens. They aren't in the repository. Tom: "There's an apt-get package for hatari 2.41, so in principle it
might be possible to run on the CI server and generate the files there." Everything here was made with Hatari
2.6.1 on macOS. **The question: does Hatari 2.4.1 on Linux make the same files?** If it does, the runner can make its
own. If not, it needs `build/stfiles.tar.gz` from somewhere.

What's known: Hatari's runs are deterministic here. A fresh clone's files, all made again, were the same byte for
byte (2026-11-09, `docs/st-traces.md`). So a difference on Linux would be Hatari's version, or the platform, not
chance.

## The reference

`docs/stfiles-sha256.txt`: the SHA-256 of all 120 files in `build/stfiles.tar.gz` as made on Tom's Mac with Hatari
2.6.1, at the commit that added it. `sha256sum -c docs/stfiles-sha256.txt` from the repo root checks a set.

## Experiments, in order

Work in a fresh clone, on a branch of your own, `ci-hatari-<date>`. Don't push or merge: Tom decides.

1. **Set up.** `README.md`'s prerequisites, from apt:
   - make, cc, CMake and Ninja;
   - Python 3.14 (`python3.14`; if the distribution has another, try `make PYTHON3=python3.12 ...` and say so);
   - perl;
   - `hatari` (note the version `hatari --version` gives);
   - Node 22, for step 4.

   Then `git clone --recurse-submodules` and `cd` in. Record the distribution, its version and each tool's.
2. **Make the ST's files with Hatari 2.4.1.** `HATARI=$(which hatari) make stfiles`, timed: about 12 minutes from
   nothing on the Mac. `tools/hatari.sh` runs Hatari headless (SDL's dummy drivers, `--alert-level fatal` so no
   dialogs, a perl alarm as the time limit). If an option isn't in 2.4.1, or a tracer stops or times out, record the
   message and what you changed to get past it. Don't change a tracer's logic: anything that changes what a file
   holds is a finding, not a fix.
3. **Compare.** `sha256sum -c docs/stfiles-sha256.txt`. Report how many of the 120 match, and list the ones that
   don't. For each that doesn't:
   - Say how it differs. A `.npy` is numpy's format: compare the arrays (`np.load`) before blaming Hatari, as another
     numpy may write another header. A `.json` trace: the first frame or field that differs, and in what.
   - Make that file a second time and compare again, to rule out chance on this machine.
4. **Build and check with these files.**
   - `make game`, then `sha256sum build/game.ssd build/game.adl`, with the commit (`git rev-parse HEAD`). Tom or a
     session on his Mac builds the same commit there and compares: the discs should be the same if the files and
     the tools agree.
   - Then the suite, all here: `tools/suite.sh /tmp/suite-out` (`REMOTE` unset; about 40 minutes on the Mac). Report
     `/tmp/suite-out/verdicts.txt`, and for any check that failed, its log's last lines.
5. **If step 3 found differences**, the fallback: ask Tom for `build/stfiles.tar.gz` from his Mac. Unpack it in a
   fresh clone's root with `tar -xmzf` (`-m`: so make doesn't remake the files). Check it with step 3's command (all
   120 should match). Then do step 4 again. That shows whether the runner can work from the pack instead.

## Results

Add them here, under a dated heading. Then change the status line above to RUN, and add one line to the plan's
GitHub Actions item saying what was found. A fault in Hatari 2.4.1 or the tools that could matter elsewhere also goes
in `docs/upstream-notes.md`, saying how it was checked. Commit on your branch, with the measurements in the commit's
body.

### 2026-11-10, Linux Mint 22.3 (agent on Tom's PC)

**In short.** Hatari 2.4.1 (Ubuntu 24.04's, so GitHub's `ubuntu-latest`'s) can't make the build's files: its
memory dumps defeat the race and sound tracers, and the game doesn't build from what it makes. Hatari 2.6.1, built
from source on the same machine, makes all 120 the same as the Mac's, byte for byte, once the tracers read a dump
that follows the debugger's prompt. From those the discs are the Mac pack's, byte for byte, and the whole suite
passes. Three commits on `ci-hatari-2026-11-10` make that work, and make the traces run in parallel: `make -j16
stfiles` from nothing in 45 s.

**1. Set up.** Linux Mint 22.3 (Ubuntu 24.04 "noble" underneath), AMD Threadripper 2990WX, 32 cores, 64 threads,
slow one thread at a time. make 4.3, cc (gcc) 13.3.0, CMake 3.28.3, Ninja 1.11.1, perl 5.38.2, Node 22.20.0,
Hatari 2.4.1 (apt). Python: noble has no 3.14, so `make PYTHON3=python3.12` (3.12.3); the pins all have 3.12
wheels (numpy 2.5.4 needs 3.12 or later, pillow 13.0.0 3.11). For the Linux build, beyond the README:
- `python3.12-venv` (apt): without it `python3 -m venv` fails (no `ensurepip`). Tom installed it.
- `tools/hatari.sh` copied the ST's disc with `cp -R orig/st/ build/stdisk/`: GNU cp copies the directory
  itself (`build/stdisk/st`), so the ST booted to an empty C:, no breakpoint was hit and Hatari exited 0 with
  nothing written. `orig/st/.` copies the contents with both cps (`c103929`).
- For a Hatari built from source: `libsdl2-dev`, `zlib1g-dev` (and `libpng-dev`, optional), and `libreadline-dev`
  (optional to Hatari, but see 3; Tom installed it).

**2. Hatari 2.4.1's files.** `HATARI=$(which hatari) make PYTHON3=python3.12 stfiles`, one at a time: 8 min 22 s
(the Mac: about 12). No option missing, no time limit hit, every tracer exited 0.

**3. Compared.** 105 of 120 match: all 72 track dumps (`.npy`), `tunes.json` and every captured screen's
`*_0.bin`/`*_1.bin`. The 15 that don't are JSON traces, the same 15 again on a second run (7 min 31 s, all 15 the
same as the first), so not chance. Against Tom's pack (`build/stfiles.tar.gz` from the Mac), value by value:
- `race_tN_r17.json` (8) and `race_t0_r0_script.json`: the same frames (the hazard race's 2,240, as the Mac's), but
  no draw calls: 0 of 2,240 frames on track 5 have any, the Mac's all 2,240.
- `sound_t0_r0.json`, `sound_t0_r0_oil.json`, `sound_t6_r17.json`: "starters called: {}", more frames (2,283,
  2,341, 3,171 against 2,252, 2,251, 2,981), differing from frame 76, 29 and 57.
- `logic_t0_r0.json`: every value in both the same (3,774,446), but 861,224 more `mem` bytes on Linux.
- `st_screens/screens.json` and `options.json`: one or two `mem` strings 2 bytes longer.

All one cause: Hatari 2.4.1's `m ADDR N` prints whole 16-byte lines (`m $1D30E 2` gives 16 bytes), and the
tracers tell their dumps apart by how many bytes come back (`len(bs) == 2`, `st_trace_objects.py:86`,
`st_trace_sound.py:95`) and store all of them. Hatari's release notes, 2.5.0 (2024-04-18): "memdump command
always outputs only requested number of items". So 2.5.0 or later. Not a tracer bug to fix: they're right for the
Hatari they're written for.

Then 2.6.1 on Linux, to tell the version from the platform: built from Hatari's source
(`https://github.com/hatari/hatari/archive/refs/tags/v2.6.1.tar.gz`, SHA-256 `75f09c8deddb511b8c1574b84c507743097db9abc6edbb078f942efa8677547e`, CMake + Ninja,
Release). The track dumps matched, but the race traces failed ("0 flips", `st_race.py`'s IndexError). Every
breakpoint that isn't a trace drops Hatari into its debugger loop, which prints the prompt `> ` and reads stdin
(`/dev/null`). 2.5.0 and later honour `:quiet` for a breakpoint's file, so the first dump after it lands on the
prompt's line, `> 0001D30E: 00 51`, and `^ADDR:` missed it: 56,919 dumps in one object trace, among them every
flip's frame counter. With GNU readline and without readline alike. (2.4.1 ignores `:quiet`: its prompt is
followed by "Reading debugger commands...", harmless.) The Mac's 2.6.1 prints no prompt there, as its files show.
`7c2e218` lets every dump pattern take a leading `> `, which changes nothing where there's no prompt; with it,
**2.6.1 on Linux made all 120 the same as the Mac's.**

**4. Built and checked**, all with 2.6.1's files, at `7c2e218`:
- `make game`: `build/game.ssd` `9eb8ffa0502d8aa7cfa61e44918d752552f2f14d979105419101b9115a64af05`, `build/game.adl`
  `82c89a72e9759a5fc8d6625add7484962f33e52f31019b38b4c960fa83205658`: the same as the Mac pack's (5, below) at the
  same commit. (The discs carry the commit, so only the same commit compares.)
- The suite's other traces, made with 2.6.1 in parallel (`0dc5c09`): `make -j8 logictrace` 1 min 49 s; `make -j8
  hazardrace RACE=1|2|4|50`, the four at once, 4 min 1 s (`make hazardtrace`: about 3 hours one at a time on the
  Mac); `JOBS=16 tools/human_traces.sh` 7 min 8 s (about 2 hours at 3); `JOBS=8 tools/game_traces.sh` 2 min 6 s.
  These ran side by side, with `make game`. 13 GB in `build/trace`.
- `MACHINES=24 MODELS=16 tools/suite.sh /tmp/suite-out`: **42 of 42 pass, `done 0`**, in 9 min 32 s (the Mac:
  about 40). The disc's 88 races "all 8 races exact" eleven times; its 32 jobs all status 0.
- 2.4.1's files: `make game` fails, every track: `sound_gen.py`, "no clean instance of ['bounce', 'bump', 'slow',
  'skid', 'wrench', 'bonus', 'tornado', 'wreck']". (And `tools/all_tracks.sh`, when every track fails, then says
  `build/tracks/slots.txt: Directory nonexistent`: it still exits 1.)

**5. The pack.** Unpacked with `tar -xmzf` in a fresh clone: all 120 match. `HATARI=/usr/bin/false make
PYTHON3=python3.12 game` built both discs, calling no tracer: 2 min 15 s at `1df726f`, 1 min 22 s at `7c2e218`
(the hashes above). The suite wasn't run on the pack alone: it reads traces the pack doesn't hold (the hazard,
human and whole-game traces, made in 4 above).

**For the runner**, then: `ubuntu-latest`'s Hatari won't do. Either build Hatari 2.6.1 from source (about a
minute here with Ninja; `libsdl2-dev zlib1g-dev libreadline-dev`) and make the files (`make -j stfiles`), or
unpack a `build/stfiles.tar.gz` made on the Mac (a release asset, say). Python: `actions/setup-python` can give
3.14; on apt's 3.12, `python3.12-venv` and `PYTHON3=python3.12`.
