# Super Sprint for the BBC Master

Super Sprint, from the Atari ST, for the BBC Master 128 and the Master Compact.

## Building

On macOS. Linux should work but hasn't been tried; Windows isn't supported for now. From your package manager
(MacPorts, Homebrew, apt and so on):

* make, a C compiler (`cc`), CMake 3.21 or later and Ninja: the build compiles its own Baron, the assembler, from
  the submodule `rich/baron`, and the ZX02 compressor, from the submodule `reference/beeb-port-kit`
* Python 3.14, as `python3.14`: the build makes its own virtual environment, `.venv`, from `requirements.txt`
* Hatari (2.6.1 here) and perl: the build runs the ST original in Hatari to capture its data. `tools/hatari.sh`
  looks for it at `/Users/tom/Applications/Hatari.app/Contents/MacOS/Hatari`; anywhere else, set `HATARI` to the
  executable (`HATARI=$(which hatari) make game`).

Then:

```
git clone --recurse-submodules https://github.com/tom-seddon/super-sprint-beeb.git
cd super-sprint-beeb
make game
```

The game's two discs are `build/game.ssd` (DFS) and `build/game.adl` (ADFS L). From nothing, about 16 minutes:
most of it is the ST's traces in Hatari, made once and kept in `build/`.

The checks (`tools/suite.sh` and the rest, `CLAUDE.md` "Oracles") also need Node 22.
