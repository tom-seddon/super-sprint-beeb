# Brief - time attack's scores and ghosts merger (2026-11-15)

> **Status: step 1 built (the shell), to be tried on Tom's Master.** Branch `ta-merge`, off `main` at d4908fc. Decision D57. Built in small steps,
> each tried on Tom's Master before the next (as time attack was).
>
> Figures say **MEASURED** (a build's listing or a tool run, named), **COUNTED** (off the source or a listing)
> or **ESTIMATED** (arithmetic on top).

## 1. What Tom asked for

The plan's item (Tom, 2026-11-12): "a program that merges a player's tables and ghosts with another set, so the disc
ends up with the best 10 per track across both sets (`TIMES`) and the ghosts that go with them (`GHOST1`-`GHOST8`).
That's the basic idea, anyway. I need to think a bit more about the UX though so that it works ok across all filing
systems."

Tom, 2026-11-15: "The user has two disks: the so-called source disk, with updated time attack ghost/score files, and
the so-called destination disk, that they want updated time attack ghost/score files to be written to. The source
disk's scores will be merged with the destination disk's, saved, and destination disk's ghost files updated
accordingly." Then: run from the source (or an Econet area, or whatever); a chance to type `*` commands and swap discs;
the source's files read into sideways RAM; the destination chosen the same way; its files read, merged with the copy
held, and the results written. "The idea is that you'd run this from the source disk, then write to the destination
disk, so there's only 1 disk swap. But - it should also be possible to use it for score backup. In which case, you've
got a non-time attack disk that just has some time attack files on it. So the tool should give you the option of
swapping disks before doing the read, so you can merge it from your backup into your time attack disk." On telling
the two cases apart (by a SCORES file on the destination, or an option): "Not sure what the right thing is here."

Agreed 2026-11-15 ("Yes, sounds good", then on the screen: "That sounds good"; on memory: "since the game assumes 4
banks free, I think it's OK for the tool to assume 4 banks free too"): §2-§5, D57.

## 2. The flow

Neither detection nor an option: the same steps for both, the swap before the read skippable.

1. Run it (`*RUN MERGE`, or `*MERGE`) from wherever it is: time attack's disc, a backup disc, a network.
2. **Read from**: a `*` prompt. Any commands (`*DRIVE 1`, `*MOUNT`, `*DIR`, Econet's), discs changed; RETURN on an
   empty line reads. RETURN straight away reads the disc it ran from: the one-swap case.
3. The source's `TIMES` and `GHOST1`-`GHOST8` read and checked (§4), and what was found said: "Read: TIMES, GHOST1
   GHOST3 GHOST5".
4. **Write to**: the same prompt.
5. The destination's files read and checked, the merge made (§3), and what would change said, a line a track:
   "Track 3  +2 entries, ghost replaced", or "no change".
6. "Write these? (Y/N)". Y writes only what changed: the ghosts, then `TIMES` (the game's order). Nothing changed:
   nothing written, and it says so.
7. "Done": RETURN goes round again from 2.

So: a backup is run it from time attack's disc, RETURN, swap to the backup, RETURN. A restore (or scores carried to a
new release's disc, its table empty) is run it, swap to the backup, RETURN, swap back, RETURN. A disc merged with
itself changes nothing (§3's duplicates).

Not by `SCORES`: the game's discs write a `SCORES` of their own (high scores, lap records, keys), and a backup made
with `*COPY` may hold one, so it doesn't tell the discs apart.

An error (`Disc read only`, `Bad command`, `Not found`) is printed and goes back to the prompt it came from, what was
read still held, so it can be put right and tried again. ESCAPE at a prompt asks before quitting.

## 3. The merge

- **A track's table**: both discs' entries, less the duplicates, the best 10 kept, in order of time. An entry is a
  duplicate when its time, upgrades and name are all another's (so a backup made twice, or a disc merged with itself,
  adds nothing; two separate laps alike in all three count as one, which is rare). On a tie the destination's first,
  as D41 keeps an older entry above a newer.
- **A track's ghost**: whichever's faster by its file's time (its first two bytes); the destination's on a tie. So the
  best entry's lap normally stays the ghost (D41).
- `SCORES` (time attack's keys and sound, D55) isn't touched.

## 4. The files

As the game reads and writes them (`timeattack.6502`):

- `TIMES`: 1,042 bytes, the table's 1,040 (80 entries a column a field: time low, time high, upgrades, then the 10-byte
  names; `tatable.6502`) and its sum (`ta_sum`). Refused, as the game does, if its length or sum is wrong.
- `GHOSTn`: its time (2 bytes), its records' bytes (2), its records. Refused if its length isn't the records' bytes
  + 4, those 0 or more than 3,000 (`GhBufLen`), or its time 0.

A refused source file is said and skipped; a refused destination file is said and treated as missing (as the game
would treat it), so it's replaced. Missing files are no entries, no ghost.

## 5. The screen and memory

MODE 7, a transcript: a heading (double height, red and yellow, the game's version on it as the options screen has
it), then each step's prompt and result scrolling up, as the OS prints them; a `*` command's output scrolls past like
any other. The text through OSWRCH, lines through OSWORD 0, commands through OSCLI, errors through BRKV (back to the
prompt, the stack reset). `src/crash.6502` already puts up MODE 7.

Mock-up (40 columns):

```
 SUPER SPRINT TIME ATTACK  (double height)
 Scores and ghosts merge          v e6118

 Read from: type * commands, change
 discs, then press RETURN.
 *DRIVE 1
 *
 Read: TIMES, GHOST1 GHOST3 GHOST5

 Write to: type * commands, change
 discs, then press RETURN.
 *
 Track 1   no change
 Track 3   +2 entries, ghost replaced
 Track 5   +1 entry
 Write these? (Y/N) Y
 Written: TIMES, GHOST3
 Done. Press RETURN to merge again.
```

Memory: a set is at most 25,074 bytes (COUNTED: `TIMES` 1,042 and 8 ghosts of 3,004). The source's held in sideways
RAM, which the tool may assume as the game does (4 banks free; found as `boot.6502` finds them, its message if
they're not there). A file's read into main RAM, OSFILE being unable to reach a bank, and copied across, as the game
does. The destination's read one file at a time beside it. The code in main RAM from `&E00` or so, under the MODE 7
screen at `&7C00`.

## 6. Where it lives

`MERGE` on time attack's discs (`build/ta.ssd`, `build/ta.adl`), Baron 6502, CMOS, assembled on its own like
`boot.6502`; the game's discs unchanged. The formats' code (`ta_sum`, the length checks) shared with
`timeattack.6502` where it can be, so the two can't drift. Run after BREAK: the game has the machine while it runs.
`disc/README-pc.txt` and `disc/README.txt` (Tom's) to mention it.

## 7. Checks

A jsbeeb oracle, `tools/ta_merge_check.mjs`, in `tools/ta_checks.sh`: discs made with given `TIMES` and ghosts (the
cases below), MERGE run and driven by its prompts, the disc in the drive changed between them (jsbeeb loads a new image
into a drive), and the files written read back off the image and compared with a model of §3
(`tools/ta_merge_model.mjs`, written from this brief, not from the 6502):

- into an empty disc (a backup) and from one (a restore); a disc with itself (nothing written);
- duplicates, ties both ways, more than 10, a track on one side only;
- ghosts faster, slower, tied, missing on either side;
- refused files on either side (length, sum, a ghost's head);
- a write-protected destination: the error, back at the prompt, then written once it's allowed;
- `*` commands at both prompts (`*DRIVE`, `Bad command`), on DFS and ADFS (`*MOUNT` after a swap: whether ADFS wants
  it is to be MEASURED).

And the game reading what MERGE wrote: `ta_table_check`'s and `ta_save_check`'s readers on a merged disc.

## 8. Open (Tom)

- The name, `MERGE` (7 characters at most on DFS).
- Whether MERGE copies itself onto a destination that lacks it, so a backup disc carries the tool (the restore then
  one swap too). Not planned unless wanted.
- The wording on screen: the mock-up's is a start.

## 9. The steps

Each tried on Tom's Master before the next; each its commit, the brief's status kept up.

1. The shell: MODE 7, the heading, the two prompts with `*` commands and errors back to the prompt, ESCAPE; built
   onto time attack's discs. Nothing read or written.
   **Built** (4a5eea3, 2026-11-15): `src/merge.6502`, its own assembly after `sprint.6502`, only when
   `GenTimeAttack`: 670 bytes at `&E00` (MEASURED, the listing), NMOS code (a Model B gets "MERGE needs a Master 128
   or Compact"). `tools/ta_merge_check.mjs` (DFS and `--adfs`, in `ta_checks.sh`): the heading on the screen, the
   prompts, `*CAT` and a bad command at them, RETURN on, ESCAPE and N, round again, ESCAPE and Y back to BASIC with its
   BRKV; seen to fail with BRKV left on the quit. All 13 of time attack's checks pass (397 s); the game's discs the
   same. On ADFS the check `*MOUNT`s first, power-on having mounted nothing; whether a swap wants `*MOUNT` again is
   step 2's to measure.
2. The source read: files checked and held in sideways RAM, what was found said.
3. The merge and what would change, the destination read; nothing written yet. The model and the oracle's first
   cases.
4. The writes, the confirmation, round again; the write-protected case; the oracle's every case, in `ta_checks.sh`.
5. Tom's READMEs' reminders (what to say about MERGE), the plan and journal.
