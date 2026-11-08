// The high scores, lap records, keys and sound saved as SCORES and loaded at the boot (Phase 5, step 10, D23), on
// build/game.ssd, each case from a fresh boot:
// - fresh: no SCORES, so the assembled table and keys, both screens' copies, HiSum their sum; a title's load
//   (TRACKF) with nothing changed writes nothing;
// - changed: a score, its initials and a lap record poked into both copies, the sound off and a key changed, then
//   TRACKF's load writes SCORES once, its bytes the table, keys, sound and sum; another load writes nothing;
// - loaded: the disc jsbeeb wrote booted again: all of it back, in both copies, and nothing written at the next load;
//   then the sound on again, and SCORES saved over;
// - spoilt: that disc with a table byte changed, two bytes swapped, either byte of the sum changed, or the file a byte short: the
//   assembled table and keys, nothing from the file;
// - read only: the disc write-protected, a change, and the load: the OS's error in the HUD's row with " - press a
//   key", a key, TRACKF loaded again, the title reached, and no second try at the next load;
// - ADFS: build/game.adl on a Master with ADFS, a change saved, and SHIFT-BREAK with the disc as written: all back; then
//   saved over and booted again.
// The sum is modelled here from the code's steps (HI_SUM, macros.6502): a total and a total of totals, the carry
// carried, but cleared by the second page's CPY.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/save_check.mjs

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { bootDisc, discFiles, jsbeebModule, ram, runToAny, symbols } from "./jsbeeb.mjs";

const { toSsdOrDsd } = await jsbeebModule("disc.js");
const syms = symbols("build/tracks/t0.json");
const Hsc = [...readFileSync("orig/st/SSPRINT.HSC")];
const Len = syms.HiSumLen, Keys = syms.HiKeys - syms.HiFile, F = 0x46;
const Out = "build/save_check";
mkdirSync(Out, { recursive: true });
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };
const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);

// HI_SUM's steps
function sum(bytes) {
    let a = 0, h = 0, c = 0;
    for (let i = 0; i < Len; i++) {
        if (i > 256) c = 0;
        let t = a + bytes[i] + c;
        a = t & 255; c = t >> 8;
        t = h + a + c;
        h = t & 255; c = t >> 8;
    }
    return [a, h];
}

const Adfs = 8000000;                   // (SHIFT held this long for ADFS: its drive spins up first)

async function boot(disc, writeable = true, model = "Master", hold = undefined) {
    const s = await bootDisc(disc, model, hold);
    const cpu = s._machine.processor;
    const peek = (a) => s.readMemory(a, 1)[0];
    const log = { saves: 0, entries: 0, brk: 0, text: "" };
    cpu.debugInstruction.add((pc) => {
        if (pc === 0xffdd && cpu.a === 0) log.saves++;
        else if (pc === syms.front_save && peek(syms.LoadName + 5) === F) log.entries++;
        else if (pc === syms["load_track.brk"]) { log.brk++; log.text = ""; }
        else if (pc === syms.row_char && log.brk) log.text += String.fromCharCode(cpu.a);
        else if (pc === syms["load_track.waitkey"]) log.said = log.text;   // (what's on the row while it waits)
        return false;
    });
    await runToAny(s, [[syms["game_resume.idle"]]], 400000000);
    if (log.entries !== 1 || log.saves || log.brk) say(`${disc}: the boot's ${log.entries} title loads, ${log.saves} saves, ${log.brk} errors, not 1, 0, 0`);
    log.entries = 0;                    // (from here, the case's own loads)
    const m = { s, cpu, log, bankbg: ram(s, 0, 1)[0], disc: () => cpu.fdc.drives[0].disc };
    if (!writeable) m.disc().isWriteable = false;
    return m;
}

// the state: each screen's HiFile to HiSum, SoundOff and PlayerKeys
const state = (m) => ({
    main: [...ram(m.s, syms.HiFile, Len + 2)],
    shadow: [...ram(m.s, syms.HiFile, Len + 2, true)],
    keys: [...m.s.readMemory(syms.SoundOff, 10)],
});

// a title's load, from the attract mode's wait: TRACKF, back to the wait (a key pressed if the load stops for one)
async function titleLoad(m) {
    m.s.writeMemory(syms.LoadWant, [F - 0x30]);
    for (let keys = 0; ; keys++) {
        const at = await runToAny(m.s, [[syms["game_resume.idle"], m.bankbg], [syms["load_track.waitkey"]]], 400000000);
        if (at !== syms["load_track.waitkey"]) return;
        if (keys === 3) { say(`a load still stopped for a key after ${keys}: "${m.log.said}"`); process.exit(1); }
        m.s.keyDown("Space");
        await m.s.runFor(400000);
        m.s.keyUp("Space");
    }
}

// what's assembled, and its check: HiSum and both copies
function holds(m, what, table, keys) {
    const st = state(m);
    const want = [...table, ...keys];
    const [a, h] = sum(want);
    if (!same(st.main.slice(0, Len), want)) say(`${what}: the main screen's table or keys aren't the ${table === Hsc ? "assembled" : "saved"} ones`);
    if (!same(st.shadow.slice(0, Keys), table)) say(`${what}: the shadow screen's table isn't`);
    if (!same(st.keys, keys)) say(`${what}: SoundOff and PlayerKeys ${st.keys}, not ${keys}`);
    if (st.main[Len] !== a || st.main[Len + 1] !== h) say(`${what}: HiSum ${st.main.slice(Len)}, not ${[a, h]}`);
}

// fresh
let m = await boot("build/game.ssd");
const keys0 = [...m.s.readMemory(syms.SoundOff, 10)];
holds(m, "fresh", Hsc, keys0);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves) say(`fresh: ${m.log.entries} title loads, ${m.log.saves} saves, not 1 and 0`);
if (discFiles(toSsdOrDsd(m.disc())).SCORES) say("fresh: SCORES written");

// changed: entry 1 (the best) 5,250 by TOM, track 3's lap record 1, the sound off, player 1's left A
const table1 = [...Hsc];
table1.splice(6, 6, 0, 0, 5, 2, 5, 0);
const names = syms.HiNames - syms.HiFile, laps = syms.LapRecords - syms.HiFile;
table1.splice(names + 3, 3, 19 + 11, 14 + 11, 12 + 11);   // (GsInLetter + 11: T, O, M)
table1.splice(laps + 2 * 2, 2, 0, 1);
const keys1 = [...keys0];
keys1[0] = 1;
keys1[1] = 65;
for (const shadow of [false, true]) ram(m.s, syms.HiFile, Keys, shadow).set(table1);
m.s.writeMemory(syms.SoundOff, keys1);
await titleLoad(m);
if (m.log.entries !== 2 || m.log.saves !== 1 || m.log.brk) say(`changed: ${m.log.entries} title loads, ${m.log.saves} saves, ${m.log.brk} errors, not 2, 1, 0`);
let image = toSsdOrDsd(m.disc());
const file = discFiles(image).SCORES;
const want1 = [...table1, ...keys1, ...sum([...table1, ...keys1])];
if (!file) say("changed: no SCORES");
else if (!same([...file.data], want1)) say(`changed: SCORES ${file.data.length} bytes, not the ${want1.length} wanted`);
holds(m, "changed", table1, keys1);
await titleLoad(m);
if (m.log.saves !== 1) say(`changed: ${m.log.saves} saves after another load, not 1`);
writeFileSync(`${Out}/saved.ssd`, image);

// loaded
m = await boot(`${Out}/saved.ssd`);
holds(m, "loaded", table1, keys1);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves) say(`loaded: ${m.log.entries} title loads, ${m.log.saves} saves, not 1 and 0`);
// and saved over: the sound on again
const keys2 = [0, ...keys1.slice(1)];
m.s.writeMemory(syms.SoundOff, [0]);
await titleLoad(m);
const again = discFiles(toSsdOrDsd(m.disc())).SCORES;
const want2 = [...table1, ...keys2, ...sum([...table1, ...keys2])];
if (m.log.saves !== 1 || !again || !same([...again.data], want2)) say(`saved over: ${m.log.saves} saves, SCORES ${again ? "not as wanted" : "gone"}`);

// spoilt
const at = file.data.byteOffset;
const spoil = {
    "a table byte": (d) => { d[at + 30] ^= 1; },
    "two bytes swapped": (d) => { [d[at + 8], d[at + 9]] = [d[at + 9], d[at + 8]]; },
    "the sum's first byte": (d) => { d[at + Len] ^= 0x80; },
    "the sum's second byte": (d) => { d[at + Len + 1] ^= 0x80; },
    "a byte short": (d) => { d[0x100 + file.entry + 4]--; },
};
for (const [what, f] of Object.entries(spoil)) {
    const d = Uint8Array.from(image);
    f(d);
    if (what === "two bytes swapped" && d[at + 8] === d[at + 9]) throw new Error("two bytes the same");
    writeFileSync(`${Out}/spoilt.ssd`, d);
    m = await boot(`${Out}/spoilt.ssd`);
    holds(m, `spoilt, ${what}`, Hsc, keys0);
}

// read only
m = await boot("build/game.ssd", false);
for (const shadow of [false, true]) ram(m.s, syms.HiFile, Keys, shadow).set(table1);
await titleLoad(m);
const text = m.log.said;
if (m.log.brk !== 1 || m.log.saves !== 1 || m.log.entries !== 2) say(`read only: ${m.log.brk} errors, ${m.log.saves} saves, ${m.log.entries} title loads, not 1, 1, 2`);
if (!/^Disc read only - press a key$/.test(text)) say(`read only: the HUD's row said "${text}"`);
if (discFiles(toSsdOrDsd(m.disc())).SCORES) say("read only: SCORES written");
await titleLoad(m);
if (m.log.saves !== 1 || m.log.brk !== 1) say(`read only: ${m.log.saves} saves and ${m.log.brk} errors after another load, not 1 and 1`);

// ADFS L: build/game.adl on a Master with ADFS, a change saved, then SHIFT-BREAK with the disc as written
m = await boot("build/game.adl", true, "MasterADFS", Adfs);
for (const shadow of [false, true]) ram(m.s, syms.HiFile, Keys, shadow).set(table1);
m.s.writeMemory(syms.SoundOff, keys1);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves !== 1 || m.log.brk) say(`ADFS: ${m.log.entries} title loads, ${m.log.saves} saves, ${m.log.brk} errors, not 1, 1, 0`);
m.s.keyDown("ShiftLeft");
m.s.reset(true);
await m.s.runFor(Adfs);
m.s.keyUp("ShiftLeft");
await runToAny(m.s, [[syms["game_resume.idle"]]], 400000000);
holds(m, "ADFS, booted again", table1, keys1);
if (m.log.saves !== 1 || m.log.brk) say(`ADFS: ${m.log.saves} saves, ${m.log.brk} errors by the boot again, not 1 and 0`);
m.s.writeMemory(syms.SoundOff, [0]);    // (saved over, and booted again)
await titleLoad(m);
m.s.keyDown("ShiftLeft");
m.s.reset(true);
await m.s.runFor(Adfs);
m.s.keyUp("ShiftLeft");
await runToAny(m.s, [[syms["game_resume.idle"]]], 400000000);
holds(m, "ADFS, saved over", table1, keys2);
if (m.log.saves !== 2 || m.log.brk) say(`ADFS: ${m.log.saves} saves, ${m.log.brk} errors, not 2 and 0`);

console.log(wrong ? `${wrong} wrong` : `SCORES saved once a change, ${want1.length} bytes, loaded back and saved over, on DFS and ADFS; 5 spoilt files refused; a read-only disc's error said once ("${text}")`);
process.exit(wrong ? 1 : 0);
