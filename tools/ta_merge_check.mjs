// Time attack's merger, MERGE (src/merge.6502; D57, docs/brief-merge-2026-11-15.md), on build/ta.ssd (or with --adfs
// build/ta.adl on a Master with ADFS), driven at its prompts as a person would: *RUN from BASIC's prompt, keys typed,
// the OS's output (jsbeeb's VDU capture) and MODE 7's screen read back. Step 1, the shell (with a ghost saved first,
// so the read goes on):
// - the heading on the screen: double height, SUPER SPRINT in red and TIME ATTACK in yellow on both of its lines, then
//   "Scores and ghosts merge" and the build's version (build/tracks_ta/gen/version.6502's) in green;
// - the read's prompt; a command run there (*CAT: the disc's files, MERGE among them); a bad one (Bad command), back
//   at the prompt; RETURN on an empty line on to the write's prompt; ESCAPE there and N, the prompt again; RETURN, the
//   "Done" line; RETURN, round again to the read's prompt; ESCAPE and Y, back at BASIC's prompt, which works (PRINT)
//   and has its own BRKV back (a bad command BASIC's error, BASIC's prompt after it);
// - step 2, the source read: two discs' files made here and *SAVEd from BASIC (TIMES, its sum as timeattack.6502's
//   ta_sum makes it; ghosts, their heads as ghost.6502's), A's read at RETURN: its TIMES and the right ghosts held in
//   the banks byte for byte (MgHave, MgLenLo, MgLenHi, MgBanks, MgSlotBank, MgSlotHi: build/tracks_ta/t0.json's), the
//   most records (3,000) and the least (1) among them, and those not right said and left out (shorter than its head,
//   its time 0, one record too many, 2 bytes with the buffer's head left stale so &FFFE + 4 wraps to its length);
//   then round again, B swapped in (5 s for the drive's motor to stop first, as a person's swap: DFS reads the
//   catalogue again only then, MEASURED), its spoilt TIMES (the sum) left out and its ghosts held; on ADFS, B
//   without *MOUNT first: "Disc changed" (MEASURED), back at the prompt, nothing held, then *MOUNT and one RETURN
//   reads it (the step run from the prompt); then C, a disc with none: "Nothing to read here.", the prompt again;
// - on a Model B (DFS 1.2, PAGE &1900; and the 1770's DFS and ADFS both, PAGE &1F00, the worst case; Tom: a Model B's
//   test covers a B+'s, which jsbeeb hasn't): MERGE refused with its message, nothing else run (NMOS code to there),
//   and the machine fine after it: the disc catalogued, BASIC working (MERGE loads above a Model B's PAGE, &1900).
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_merge_check.mjs [--adfs]

import { readFileSync } from "node:fs";
import { adfs, discFiles, jsbeebModule, symbols } from "./jsbeeb.mjs";

const { MachineSession } = await jsbeebModule("machine-session.js");
const fdc = await jsbeebModule("fdc.js");
const disc = adfs ? "build/ta.adl" : "build/ta.ssd";
const syms = symbols("build/tracks_ta/t0.json");     // (MERGE's labels among them: its own assembly)
const version = readFileSync("build/tracks_ta/gen/version.6502", "utf8").match(/^VersionAscii = \{([^}]*)\}/m)[1]
    .split(",").map(Number).filter((c) => c).map((c) => String.fromCharCode(c)).join("");
let bad = 0, checked = 0;
const say = (t) => { if (bad++ < 30) console.log(t); };
const want = (what, ok) => (ok ? checked++ : say(`${what}: wrong`));

async function machine(model) {
    const s = new MachineSession(model);
    await s.initialise();
    s.loadDisc(disc);
    await s.boot();
    return s;
}
// (a pause before each key or line, as a person's: the same key twice in a row, RETURN then RETURN, is lost
// otherwise, the OS's scan not seeing it let go between them)
const Gap = 200000;
// a line typed and RETURN (jsbeeb's type() always ends with one), then on till the OS waits for a key: what was
// printed meanwhile, as lines
async function type(s, text) {
    await s.runFor(Gap);
    await s.type(text);
    return lines(s);
}
const lines = async (s) => (await s.runUntilPrompt(20)).screenText.split("\n").map((l) => l.trimEnd());
// a key pressed and let go ("KeyN", "Enter", "Escape"), then on till the OS waits for one
async function press(s, key) {
    await s.runFor(Gap);
    s.keyDown(key);
    await s.runFor(100000);
    s.keyUp(key);
    return lines(s);
}
// MODE 7's screen, the top row first (the OS's hardware scroll undone: &350, the top line's address), 25 rows of 40
function screen(s) {
    const top = s.readMemory(0x350, 2), at = (top[0] | top[1] << 8) - 0x7c00, m = s.readMemory(0x7c00, 1024), rows = [];
    for (let r = 0; r < 25; r++) rows.push(Array.from({ length: 40 }, (_, c) => m[(at + r * 40 + c) & 1023] & 127));
    return rows;
}
const text = (row) => row.map((b) => (b >= 32 ? String.fromCharCode(b) : " ")).join("").trimEnd();
const has = (lines, t) => lines.some((l) => l.trim() === t);
// the screen's last row with anything on it (the cursor's, as the OS waits)
const last = (s) => screen(s).map(text).filter((l) => l.trim()).at(-1)?.trim();
const Red = 1, Green = 2, Yellow = 3, Double = 13;   // (teletext's codes, top bit off)

// time attack's files (tafiles.6502), made here: TIMES, 1,040 bytes and their sum (a total of the bytes and a total of
// the totals, each a byte: timeattack.6502's ta_sum); a ghost, its time, its records' bytes and those
const TableLen = 1040, GhBufLen = 3000;
let seed = 12345;
const random = (n) => Uint8Array.from({ length: n }, () => (seed = (seed * 1103515245 + 12345) >>> 0) >>> 24);
function times({ spoilt = false } = {}) {
    const t = new Uint8Array(TableLen + 2);
    t.set(random(TableLen));
    let total = 0, totals = 0;
    for (let i = 0; i < TableLen; i++) total = (total + t[i]) & 255, totals = (totals + total) & 255;
    t[TableLen] = total, t[TableLen + 1] = spoilt ? totals ^ 1 : totals;
    return t;
}
function ghost(time, records, { length = records + 4, head = null } = {}) {
    const g = new Uint8Array(length);
    g.set(random(length));
    const h = head ?? [time & 255, time >> 8, records & 255, records >> 8];
    g.set(h.slice(0, Math.min(4, length)));
    return g;
}
// files saved on the disc in the drive, from BASIC: each poked at &3000 and *SAVEd
async function save(s, files) {
    for (const [name, data] of Object.entries(files)) {
        s.writeMemory(0x3000, data);
        await type(s, `*SAVE ${name} 3000 +${data.length.toString(16)}`);
    }
}
// a disc put in drive 0 as a person would: a pause for the drive's motor to stop first (DFS reads the catalogue again
// once it has, MEASURED; at once it would go on with the last disc's), and one after; on ADFS then *MOUNT if asked
const Second = 2000000;
async function swap(s, d) {
    await s.runFor(5 * Second);
    s._machine.processor.fdc.loadDisc(0, d);
    await s.runFor(5 * Second);
}
const image = (name) => fdc.discFor(name + disc.slice(-4), new Uint8Array(readFileSync(disc)));   // (its format by its name)
// what MERGE holds: each file's bytes from its slot in the banks, or null
function held(s) {
    const banks = s.readMemory(syms.MgBanks, 2), have = s.readMemory(syms.MgHave, 9);
    const lo = s.readMemory(syms.MgLenLo, 9), hi = s.readMemory(syms.MgLenHi, 9);
    const bank = s.readMemory(syms.MgSlotBank, 9), page = s.readMemory(syms.MgSlotHi, 9);
    return Array.from({ length: 9 }, (_, i) => (have[i] ? s.readMemory(page[i] << 8, lo[i] | hi[i] << 8, { bank: banks[bank[i]] }) : null));
}
const Names = ["TIMES", ...Array.from({ length: 8 }, (_, i) => `GHOST${i + 1}`)];
// MERGE's holding as files has it: a file name's bytes, the rest none
function holds(s, what, files) {
    const got = held(s);
    Names.forEach((n, i) => {
        const w = files[n] ?? null, g = got[i];
        want(`${what}: ${n} ${w ? "held" : "not held"}`, w ? g && g.length === w.length && g.every((b, j) => b === w[j]) : !g);
    });
}

{
    const s = await machine(adfs ? "MasterADFS" : "Master");
    if (adfs) await type(s, "*MOUNT");                  // (as booting the disc would have: power-on mounts nothing)
    await save(s, { GHOST1: ghost(300, 10) });          // (something to read, so RETURN goes on)
    const out = await type(s, "*RUN MERGE");
    const rows = screen(s);
    const head = Array.from({ length: 26 }, (_, i) => rows[0][i]);
    const heading = [Double, Red, ..."SUPER SPRINT".split("").map((c) => c.charCodeAt(0)), Yellow,
        ..."TIME ATTACK".split("").map((c) => c.charCodeAt(0))];
    want("the heading's first line", heading.every((b, i) => head[i] === b));
    want("the heading's second line", heading.every((b, i) => rows[1][i] === b));
    want(`the heading's version line ("${text(rows[2])}")`, text(rows[2]) === ` Scores and ghosts merge      v ${version}`
        && rows[2][29] === Green);
    want("the read's prompt", has(out, "Read from:type * commands, change") && has(out, "discs, then press RETURN.")
        && last(s) === "*");
    let o = await type(s, "CAT");
    want("*CAT at the prompt", o.some((l) => /\bMERGE\b/.test(l)) && last(s) === "*");
    o = await type(s, "FOO");
    const shown = screen(s).map(text), at = shown.findLastIndex((l) => l === "Bad command");
    want("a bad command: its error, then the prompt", at > 0 && last(s) === "*");
    want("a bad command: no blank line before its error", shown[at - 1] === "*FOO");
    o = await type(s, "");
    want("RETURN: the write's prompt", has(o, "Read: GHOST1") && has(o, "Write to:type * commands, change") && last(s) === "*");
    o = await press(s, "Escape");
    want("ESCAPE: asked", last(s) === "Quit? (Y/N)");
    o = await press(s, "KeyN");
    want("N: the prompt again", last(s) === "*" && screen(s).map(text).some((l) => l.trim() === "Quit? (Y/N) N"));
    o = await type(s, "");
    want("RETURN: done", has(o, "Done.Press RETURN to merge again."));
    o = await press(s, "Enter");
    want("RETURN: round again", has(o, "Read from:type * commands, change") && last(s) === "*");
    await press(s, "Escape");
    o = await press(s, "KeyY");
    want(`Y: BASIC's prompt (${JSON.stringify(last(s))})`, last(s) === ">");
    o = await type(s, "PRINT 6*7");
    want("BASIC after the quit", has(o, "42") && last(s) === ">");
    o = await type(s, "*FOO");
    want("BASIC's BRKV back", has(o, "Bad command") && last(s) === ">");
    s.destroy?.();
}
// Step 2, the source read: two discs' files, made and saved (B's first, A's after it, A's the disc MERGE runs from);
// A read at once; round again, B swapped in and read; then C, a disc with none
{
    const s = await machine(adfs ? "MasterADFS" : "Master");
    const mount = async () => adfs && type(s, "*MOUNT");
    await mount();
    const A = s._machine.processor.fdc.drives[0]._disc, B = image("b"), C = image("c");
    const a = {
        TIMES: times(),
        GHOST1: ghost(478, 600),
        GHOST2: ghost(500, 500, { length: 300 }),            // (shorter than its head says)
        GHOST3: ghost(1500, GhBufLen),                       // (the most)
        GHOST4: ghost(0, 20, { head: [0, 0, 0xfe, 0xff] }),  // (its time 0; and its head left for GHOST6)
        GHOST5: ghost(900, GhBufLen + 1),                    // (one too many)
        GHOST6: ghost(0, 0, { length: 2, head: [1, 2] }),    // (2 bytes: the buffer's head stale, &FFFE + 4 = 2)
        GHOST8: ghost(321, 1),                               // (the least)
    };
    const b = { TIMES: times({ spoilt: true }), GHOST2: ghost(450, 800), GHOST7: ghost(777, 1234) };
    await swap(s, B);
    await mount();
    await save(s, b);
    await swap(s, A);
    await mount();
    await save(s, a);
    await type(s, "*RUN MERGE");
    let o = await type(s, "");
    for (const n of ["GHOST2", "GHOST4", "GHOST5", "GHOST6"]) want(`A: ${n} said and left out`, has(o, `${n}: not a ghost, left out`));
    want(`A: what was read said (${JSON.stringify(o.filter((l) => l.includes("Read:")))})`, has(o, "Read: TIMES GHOST1 GHOST3 GHOST8"));
    want("A: on to the write's prompt", has(o, "Write to:type * commands, change") && last(s) === "*");
    holds(s, "A", { TIMES: a.TIMES, GHOST1: a.GHOST1, GHOST3: a.GHOST3, GHOST8: a.GHOST8 });
    await type(s, "");
    o = await press(s, "Enter");
    want("round again: the read's prompt", has(o, "Read from:type * commands, change") && last(s) === "*");
    await swap(s, B);
    if (adfs) {
        o = await type(s, "");                          // (MEASURED: ADFS refuses a changed disc till *MOUNT)
        want(`B, no *MOUNT: ADFS's error, the prompt again (${JSON.stringify(o.filter((l) => l.trim()))})`,
            has(o, "Disc changed") && last(s) === "*");
        holds(s, "B, no *MOUNT", {});
        await mount();                                  // (then one RETURN reads it: the step run again)
    }
    o = await type(s, "");
    want("B: TIMES said and left out", has(o, "TIMES: not a table, left out"));
    want(`B: what was read said (${JSON.stringify(o.filter((l) => l.includes("Read:")))})`, has(o, "Read: GHOST2 GHOST7"));
    holds(s, "B", { GHOST2: b.GHOST2, GHOST7: b.GHOST7 });
    await type(s, "");
    await press(s, "Enter");
    await swap(s, C);
    await mount();
    o = await type(s, "");
    want("C: nothing to read, the read's prompt again", has(o, "Nothing to read here.") && last(s) === "*");
}
if (!adfs) for (const model of ["B-DFS1.2", "B1770"]) {
    const s = await machine(model);
    let o = await type(s, "PRINT ~PAGE");               // (MERGE loaded at or above it, so the DFS's workspace is kept)
    const page = parseInt(o.filter((l) => /^[0-9A-F]+$/.test(l.trim())).at(-1), 16), load = discFiles(disc).MERGE.load;
    want(`MERGE's load, &${load.toString(16)}, above the Model B's (${model}) PAGE, &${page.toString(16)}`, page >= 0xe00 && load >= page);
    o = await type(s, "*RUN MERGE");
    want(`a Model B (${model}) refused (${JSON.stringify(o.slice(-3))})`, has(o, "MERGE needs a Master 128 or Compact") && o.at(-1) === ">");
    o = await type(s, "*CAT");                          // (the DFS's workspace, under PAGE, left alone by the load)
    want(`the Model B's (${model}) disc after it (${JSON.stringify(o.slice(-3))})`, o.some((l) => /\bMERGE\b/.test(l)) && o.at(-1) === ">");
    o = await type(s, "PRINT 6*7");
    want(`the Model B's (${model}) BASIC after it`, has(o, "42") && o.at(-1) === ">");
}

console.log(bad ? `${bad} wrong` : `MERGE right${adfs ? " (ADFS)" : ""}: ${checked} checked (the heading, version ${version}; the read's ` +
    `and write's prompts, *CAT and a bad command at them, RETURN on, ESCAPE and N, round again, ESCAPE and Y to BASIC, ` +
    `which works and has its BRKV back; the source read from two discs, a swap between, ${adfs ? "\"Disc changed\" till *MOUNT, " : ""}` +
    `the right files held byte for byte and 5 wrong ones left out, then a disc with none${adfs ? "" : "; Model Bs refused, unharmed"})`);
process.exit(bad ? 1 : 0);
