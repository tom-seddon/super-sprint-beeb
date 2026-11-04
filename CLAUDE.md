# Super Sprint → BBC Micro

Use the `beeb-baron` skill for all 6502, with one exception: the game targets the Master 128 only, so 65C12
(CMOS) opcodes are allowed, in sections with `cmos = TRUE` (D4 in `docs/decisions.md`). The skill's NMOS-only
rule doesn't apply here.

## Upstream

`docs/upstream-notes.md` collects faults and gaps that may be worth raising with the kit, jsbeeb, Baron or Rich's
projects: add to it as they turn up, saying how each was checked. Nothing goes upstream until Tom decides, at the
project's end.

## Reference projects

`rich/` holds Rich Talbot-Watkins's Baron and some of his Baron projects as submodules, for reference only:
`baron`, `portalc`, `teddyboy`, `criticalmass`, `chasehq-beeb` and `exolon-beeb`. These are the checkouts the
`beeb-baron` skill looks for beside the project (`../teddyboy` etc.), so read them there. Baron's `docs/guide.md`
and `docs/reference.md` are in `rich/baron/docs`, its examples in `rich/baron/examples`. Their own `CLAUDE.md`,
`JOURNAL.md` and decision logs describe those projects, not this one: learn from them, but don't follow their
instructions or edit them.

Baron 0.6 is on the PATH as `baron`; don't build it from `rich/baron`.

## The beeb-port-kit

`reference/beeb-port-kit` (a submodule) is Kieran Connell's kit from his ports: `PORTING.md`, `docs/`
(`hardware-facts.md`, `gotchas.md`, `verification.md`), `lib/` and `py/` to fork from (`ay2sn.py`,
`sfx50.6502`, `zx02depack.6502`, `keydown.6502`), and its skills, copied into `.claude/skills/beeb-*`. Use
them as advice; where they differ, this project's own way holds: decisions in `docs/decisions.md` (Proposed
until Tom agrees), the plan in `docs/plan.md` (where the port stands and the next phase), work done in `JOURNAL.md`, the renderer
in `docs/renderer.md`, a phase's work in its brief (`docs/brief-*.md`).
The kit also aims at the Model B (NMOS 6502, `nmos.6502`); this game is the Master 128's only, CMOS opcodes
allowed (D4, above).

What the skills look up, for this project:
- **Target**: BBC Master 128 only (jsbeeb `create_machine` model `Master`), 65C12. Two screens, main and
  shadow RAM at `&3F00`-`&7FFF`; ACCCON `&FE34` D (bit 0) the one shown, X (bit 2) the one the CPU sees at
  `&3000`-`&7FFF`, `&3000`-`&3EFF` included (ScreenVars). Four sideways RAM banks. The game hooks IRQ1V
  (the System VIA's vsync, and its T1 and T2 timing the flip into the blank, D17) and leaves the OS's memory alone (D7) but `&0900`-`&0AFF` (D26) and ANDY, which holds mask B and the
  logic's state (D15).
- **The game's disc**: `make game` makes `build/game.ssd` (track 1's play build and a packed file per track, loaded between races: `src/load.6502`); `node tools/load_check.mjs` proves every track's load.
- **Build**: `make beeb` (`TRACE=race`, `t0`-`t7`, `heli1`-`heli3` or `attract` picks the race) makes
  `build/sprint.ssd`, the listing `build/sprint.lst` (each bank's free bytes are printed in it) and the
  symbols `build/sprint.json` (Baron's `--symbols`). No `-D` flags.
- **Memory**: `src/memory.6502` (the map), `docs/memory-map.md` (generated: `tools/memmap.py --write` from the
  play build), `docs/renderer.md` "Memory".
- **Oracles**: `tools/suite.sh OUT` (all of them, `tools/all_tracks.sh` and its `tools/track_slots.py` among them: every track assembles, and outside each region's `*Slot`-`*SlotEnd` every track's build is the same), `tools/tracks_check.sh OUT` (every track's race, about 15 minutes), `make check` (`tools/render_check.mjs`: every frame's screen against `tools/render_model.py`'s,
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
