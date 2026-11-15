// Time attack's merger, MERGE (src/merge.6502; D57, docs/brief-merge-2026-11-15.md), on build/ta.ssd (or with --adfs
// build/ta.adl on a Master with ADFS), driven at its prompts as a person would: *RUN from BASIC's prompt, keys typed,
// the OS's output (jsbeeb's VDU capture) and MODE 7's screen read back. Step 1, the shell:
// - the heading on the screen: double height, SUPER SPRINT in red and TIME ATTACK in yellow on both of its lines, then
//   "Scores and ghosts merge" and the build's version (build/tracks_ta/gen/version.6502's) in green;
// - the read's prompt; a command run there (*CAT: the disc's files, MERGE among them); a bad one (Bad command), back
//   at the prompt; RETURN on an empty line on to the write's prompt; ESCAPE there and N, the prompt again; RETURN, the
//   "Done" line; RETURN, round again to the read's prompt; ESCAPE and Y, back at BASIC's prompt, which works (PRINT)
//   and has its own BRKV back (a bad command BASIC's error, BASIC's prompt after it);
// - on a Model B (DFS 1.2, and the 1770's DFS): MERGE refused with its message, nothing else run (NMOS code to there),
//   and the machine fine after it: the disc catalogued, BASIC working (MERGE loads above a Model B's PAGE, &1900).
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_merge_check.mjs [--adfs]

import { readFileSync } from "node:fs";
import { adfs, discFiles, jsbeebModule } from "./jsbeeb.mjs";

const { MachineSession } = await jsbeebModule("machine-session.js");
const disc = adfs ? "build/ta.adl" : "build/ta.ssd";
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

{
    const s = await machine(adfs ? "MasterADFS" : "Master");
    if (adfs) await type(s, "*MOUNT");                  // (as booting the disc would have: power-on mounts nothing)
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
    want("RETURN: the write's prompt", has(o, "Write to:type * commands, change") && last(s) === "*");
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
if (!adfs) for (const model of ["B-DFS1.2", "B1770"]) {     // (jsbeeb has no B+)
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

console.log(bad ? `${bad} wrong` : `MERGE's shell right${adfs ? " (ADFS)" : ""}: ${checked} checked (the heading, version ${version}; the read's ` +
    `and write's prompts, *CAT and a bad command at them, RETURN on, ESCAPE and N, round again, ESCAPE and Y to BASIC, ` +
    `which works and has its BRKV back${adfs ? "" : "; Model Bs refused, unharmed"})`);
process.exit(bad ? 1 : 0);
