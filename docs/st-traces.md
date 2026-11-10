# The ST's files: traces, dumps and captures

Everything the port knows about the original comes from running it. The ST's game (`orig/st`, with TOS 1.04 from
`orig/`) runs headless in Hatari through `tools/hatari.sh`, and the tracers (`tools/st_*.py`) read its memory and
log its calls through Hatari's debugger. What they write goes in `build/` (git-ignored): `build/gfx`,
`build/trace` and `build/st_screens`. Only these need Hatari. Everything else in `build/` is made from them, and from
the original's files, by the tools here. That includes the models the render checks compare against
(`build/check/model_*.bin`, made by `tools/render_model.py`) and the per-track copies of track 1's logic trace
(`build/trace/logic_tN_room.json`, made by `tools/all_tracks.sh`).

Hatari's runs are deterministic. A fresh clone's files, all made again in Hatari, were the same byte for byte as this
checkout's (2026-11-09, all 88 in the pack below). `docs/stfiles-sha256.txt` holds the hashes of the pack's 120 files
as made here (2026-11-10, with the clean track dumps): `sha256sum -c docs/stfiles-sha256.txt` checks a set.

`tools/hatari.sh` looks for Hatari at `/Users/tom/Applications/Hatari.app/Contents/MacOS/Hatari`. Set `HATARI` to
run another. Hatari 2.6.1 made all of these (2.5.0 or later is needed: `docs/brief-ci-hatari-2026-11-10.md`). A file is made if it's missing and then kept: a newer tracer or
`tools/hatari.sh` doesn't make it again (their timestamps are only the last checkout's), so to make one again after
changing its tracer, delete it.

## What there is

Sizes are this checkout's (2026-11-09); "needs" says what reads them.

| Files | What | Made by | Time | Size | Needs |
|---|---|---|---|---|---|
| `build/gfx/bg_tN.npy`, `maskK_tN.npy` | Each track's background and its three masks, as the ST has them | `make tracks` (`st_dump_tracks.py`) | 5 s a track | 2 MB | for comparison |
| `build/gfx/bgclean_tN.npy`, `maskcleanK_tN.npy` | The same, with the map's "TRACK n" and "DRONE LAP" cells replaced before the ST builds the track (`st_text_cells.py`), so its trees are drawn over clean ground | `make tracks` (`st_dump_tracks.py --clean`) | 5 s a track | 2 MB | `make game` |
| `build/trace/race_tN_r17.json` | Race 17 on track N, every object's draw calls each frame (from `obj_tN_r17.json`, which `st_trace_objects.py` writes, by `st_race.py`) | make, as the build asks | 20 s each | 2.6-6.0 MB each | `make game`, `make check`, `tools/tracks_check.sh` |
| `build/trace/race_t0_r0_script.json` | The logic trace's race, drawn | make | 40 s | 1.4 MB | `make game`, `make check TRACE=logic0` |
| `build/trace/logic_t0_r0.json` | Track 1's race 0, driven by `tools/logic_scripts/t0.json`: every car's variables, the inputs and the random numbers, every frame | make (`st_trace_logic.py`) | 1 min | 50 MB | `make game` (each track's logic data), `logic_check` |
| `build/trace/sound_t0_r0.json`, `sound_t0_r0_oil.json`, `sound_t6_r17.json` | The race's sound effects, as the ST's driver plays them | make (`st_trace_sound.py`) | 40 s each | 1 MB | `make game`, `sound_check`, `sn_check` |
| `build/trace/tunes.json` | The front end's ten tunes | make (`st_trace_tunes.py`) | 35 s | 0.7 MB | `make game`, `tune_check` |
| `build/st_screens/screens.json`, `options.json` and `NAME_0.bin`, `NAME_1.bin` | The front end's screens, captured by playing `tools/game_scripts/screens.json` and `options.json` | make, or `tools/game_traces.sh` | 30 s | 2 MB | `make game`, `st_frontend`, `st_screens` |
| `build/trace/logic_tN_rR.json`, `race_tN_rR.json` (R 1, 2, 4, 17, 50) | The race count's hazards on every track | `make logictrace`, `make hazardtrace` | `hazardtrace` 3 hours | 3 GB | `tools/disc_races.sh`, `tools/tracks_check.sh`, `logic4_*` |
| `build/trace/logic_tN_hCARS.json`, `race_tN_hCARS.json`, `logic_t0_hprobe.json` | Races with two or three humans, steered by `tools/steer_script.py`; the wall probes' race | `tools/human_traces.sh` | 2 hours | 3 GB | `tools/disc_races.sh` |
| `build/trace/game_NAME.json`, `logic_tN_demoR.json` | Whole games (`tools/game_scripts`), the demo race on every track | `tools/game_traces.sh` | | 8 MB and 0.4 GB | `tools/disc_races.sh`'s `game_check`, `attract_check`, the demos |
| `build/trace/w_*/hatari_*.log`, `obj_*.json` | Hatari's logs (with each trace's scripts, in a directory of its own) and the raw object traces | (with the above) | | 3.4 GB | nothing after |

All of it together is about 11 GB here, most of it for the checks. The game's build needs about 89 MB, 2.5 MB packed.

## Building the game where Hatari doesn't run

On a machine where it runs (this one), from the repo root:

```
make stfiles                # makes any of the build's ST files that are missing, about 12 minutes from nothing
make build/stfiles.tar.gz   # packs them: 88 files, 2.5 MB
```

The pack holds `build/gfx/bg_t?.npy`, `mask?_t?.npy`, `bgclean_t?.npy` and `maskclean?_t?.npy`; `build/trace/race_t?_r17.json`, `race_t0_r0_script.json`,
`logic_t0_r0.json`, `sound_t0_r0.json`, `sound_t0_r0_oil.json`, `sound_t6_r17.json` and `tunes.json`; and
`build/st_screens/screens.json`, `options.json` and every `*_0.bin` and `*_1.bin` there. The paths are relative to
the repo root.

Copy `build/stfiles.tar.gz` to the other machine. In a clone there, before the first `make`:

```
tar -xmzf stfiles.tar.gz    # in the repo root: the files land in build/
make game
```

`-m` matters. It gives the files the time they were unpacked, not the time they were made. Without it they're older
than a fresh clone's tools (git gives files the time of the checkout), and make would try to make them again in
Hatari.

Tested on agentbox (2026-11-09). A fresh clone of `repo-baron`, the pack unpacked, then `HATARI=/usr/bin/false
make game`, so that any call to Hatari would fail. No `baron` on its PATH, and no Hatari it can run. The build took
1 min 8 s, called no tracer, and made `game.ssd` 37fd99f7f367a9ff1a9370dd66efd107df2d78a9 and `game.adl`
3fc4c18e5d23e4964d9a9673818d35dcb1c76d88, the same as this machine's.

## Running the checks on another machine

`tools/suite.sh OUT` runs every check on this machine, reading the files in the table above. Two ways to send
work elsewhere, both for Tom's laptop and his machine agentbox during development, neither needed:

- `tools/suite_remote.sh OUT` runs the whole suite on REMOTE (default agentbox). It copies this working tree there
  with rsync (not `.git`, `build/` or `.venv`), and the ST's files: `build/gfx`, `build/st_screens`, the JSON in
  `build/trace` (not the raw object traces or `tools/all_tracks.sh`'s copies) and `build/prof/seeds.txt`, with their
  times kept. That's about 7 GB the first time, and only what's changed after. There the suite builds its own
  `.venv`, Baron, discs and models, with `HATARI=/usr/bin/false`. Then OUT comes back, with the discs it built. It
  needs the README's prerequisites there, and Node, but not a Hatari that runs.
- `REMOTE=host tools/suite.sh OUT` sends just `tools/disc_races.sh`'s jobs (the 72 traced races on the disc, the
  games, the attract mode and the front end's checks), through `tools/remote.sh`. That copies what they read: the
  discs, the tools, the logic traces of every traced race and the games, and the models, made here. Those jobs need
  only Node and jsbeeb there.
