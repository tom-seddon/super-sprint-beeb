// BREAK after the game has run: the MOS must make its soft font again (it's in ANDY, which the game takes: D15).
// The game's disc booted to the title's file, a few fields on, then BREAK (a soft reset); ANDY's &8900-&8FFF,
// the MOS's copy of the font, afterwards, against a fresh machine's after power-on. The game sets OSBYTE 200's
// memory-clear bit at its start (entry.6502), so the BREAK clears memory as power-on does.
//
// Exit status: 1 if the font after BREAK isn't the fresh machine's; else 0.
//
// Usage (from the repo root, after make game): node tools/break_check.mjs [--adfs]

import { andy, bootGame, runTo, symbols } from "./jsbeeb.mjs";

const Field = 39936, Font = 0x8900, FontLen = 0x700;
const syms = symbols("build/tracks/t0.json");

const fresh = await bootGame();             // (the disc's boot never gets far in these fields: nothing's touched ANDY)
const want = [...andy(fresh, Font, FontLen)];

const s = await bootGame();
await runTo(s, syms["game_resume.loaded"], 400000000);
await s.runFor(50 * Field);
const clear = s.readMemory(0x258, 1)[0];
const before = [...andy(s, Font, FontLen)];
s.reset(false);                             // BREAK
await s.runFor(100 * Field);
const after = [...andy(s, Font, FontLen)];

const diff = (a) => a.reduce((n, b, i) => n + (b !== want[i]), 0);
console.log(`OSBYTE 200's byte (&258) before BREAK: ${clear}`);
console.log(`the font's bytes unlike a fresh machine's: before BREAK ${diff(before)}, after ${diff(after)} of ${FontLen}`);
process.exit(diff(after) ? 1 : 0);
