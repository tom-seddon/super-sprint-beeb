# Super Sprint for the BBC Master

A BBC Master port of Atari ST Super Sprint.

Code by Claude Code, with occasional direction from Tom Seddon.

# Instructions (as-was from Claude)

## Building

On macOS, and on Linux (Mint 22.3, 2026-11-10: `docs/brief-ci-hatari-2026-11-10.md`); Windows isn't supported for
now. From your package manager (MacPorts, Homebrew, apt and so on):

* make, a C compiler (`cc`), CMake 3.21 or later and Ninja: the build compiles its own Baron, the assembler, from
  the submodule `rich/baron`, and the ZX02 compressor, from the submodule `reference/beeb-port-kit`
* Python 3.14, as `python3.14`: the build makes its own virtual environment, `.venv`, from `requirements.txt`.
  3.12 works too, with `make PYTHON3=python3.12` (and on Ubuntu, apt's `python3.12-venv`)
* Hatari 2.5.0 or later (2.6.1 here; Ubuntu 24.04's 2.4.1 won't do: build 2.6.1 from source) and perl: the build runs
  the ST original in Hatari to capture its data. `tools/hatari.sh` looks for it at
  `/Users/tom/Applications/Hatari.app/Contents/MacOS/Hatari`; anywhere else, set `HATARI` to the executable
  (`HATARI=$(which hatari) make game`).

Then:

```
git clone --recurse-submodules https://github.com/tom-seddon/super-sprint-beeb.git
cd super-sprint-beeb
make game
```

The game's two discs are `build/game.ssd` (DFS) and `build/game.adl` (ADFS L). From nothing, about 16 minutes:
most of it is the ST's traces in Hatari, made once and kept in `build/`. Where Hatari doesn't run, the game builds
from those files made on a machine where it does, packed and copied: `docs/st-traces.md`, which also says what each
of the ST's files is, what makes it and what reads it.

The checks (`tools/suite.sh` and the rest, `CLAUDE.md` "Oracles") also need Node 22.

## For AI agents

Start with `CLAUDE.md`: how the project builds, how it's checked, and where everything else is. Where the port
stands is in `docs/plan.md`, the decisions in `docs/decisions.md`, the work done in `JOURNAL.md`. Please don't edit
this README: Tom writes it.
