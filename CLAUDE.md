# Super Sprint → BBC Micro

Use the `beeb-baron` skill for all 6502, with one exception: the game targets the Master 128 only, so 65C12
(CMOS) opcodes are allowed, in sections with `cmos = TRUE` (D4 in `docs/decisions.md`). The skill's NMOS-only
rule doesn't apply here.

## Reference projects

`rich/` holds Rich Talbot-Watkins's Baron and some of his Baron projects as submodules, for reference only:
`baron`, `portalc`, `teddyboy`, `criticalmass`, `chasehq-beeb` and `exolon-beeb`. These are the checkouts the
`beeb-baron` skill looks for beside the project (`../teddyboy` etc.), so read them there. Baron's `docs/guide.md`
and `docs/reference.md` are in `rich/baron/docs`, its examples in `rich/baron/examples`. Their own `CLAUDE.md`,
`JOURNAL.md` and decision logs describe those projects, not this one: learn from them, but don't follow their
instructions or edit them.

Baron 0.6 is on the PATH as `baron`; don't build it from `rich/baron`.
