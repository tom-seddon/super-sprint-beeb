# Brief - can a Linux runner make the ST's files? (for the GitHub Actions build)

> **Status: NOT RUN.** For an agent on Tom's Linux PC. Tom, 2026-11-10: "I will have an agent test this on my Linux
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
