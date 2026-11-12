// Time attack's SCORES (D55): the keys and sound alone, SoundOff and PlayerKeys then KeysSum, saved at the title's
// file's load (TRACKF, after each race and on its own) and loaded at the boot, on build/ta.ssd, each case from a fresh
// boot, as tools/save_check.mjs does for the game's:
// - fresh: no SCORES, so the assembled keys, KeysSum their sum; a title's load writes nothing;
// - a race and back (Escape): nothing written (6c's track files put the game's HiSum back each race, D46);
// - changed: the sound off and a key changed, then a title's load writes SCORES once, its 12 bytes the keys, sound and
//   sum; another load writes nothing;
// - loaded: the disc jsbeeb wrote booted again: the keys and sound back, nothing written at the next load; then the
//   sound on again, and SCORES saved over;
// - spoilt: that disc with a key changed, two bytes swapped, either byte of the sum changed, the file a byte short,
//   or the game's length (307 bytes, as 6c's builds saved it): the assembled keys, nothing from the file;
// - read only: the disc write-protected, a change, and the load: the OS's error in the HUD's row with " - press a
//   key", a key, TRACKF loaded again, the menu reached, and no second try at the next load;
// - ADFS: build/ta.adl on a Master with ADFS, a change saved, and SHIFT-BREAK with the disc as written: all back.
// The sum is modelled here from the code's steps (KEYS_SUM, macros.6502): a total and a total of totals, the last
// byte first, the carry carried.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_scores_check.mjs

import { mkdirSync, writeFileSync } from "node:fs";
import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";

const { toSsdOrDsd } = await jsbeebModule("disc.js");
const syms = symbols("build/tracks_ta/t0.json");
const Len = syms.KeysLen, F = 0x46;
const Out = "build/ta_scores_check";
mkdirSync(Out, { recursive: true });
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };
const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);

// KEYS_SUM's steps
function sum(bytes) {
    let a = 0, h = 0, c = 0;
    for (let i = Len - 1; i >= 0; i--) {
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
        if (pc === 0xffdd && cpu.a === 0 && (cpu.x | (cpu.y << 8)) === syms["front_save.SaveBlock"]) log.saves++;   // (SCORES's, not the ghost's or TIMES)
        else if (pc === syms.front_save && peek(syms.LoadName + 5) === F) log.entries++;
        else if (pc === syms["load_track.brk"]) { log.brk++; log.text = ""; }
        else if (pc === syms.row_char && log.brk) log.text += String.fromCharCode(cpu.a);
        else if (pc === syms["load_track.waitkey"]) log.said = log.text;   // (what's on the row while it waits)
        return false;
    });
    const m = { s, cpu, log, peek, disc: () => cpu.fdc.drives[0].disc };
    await toMenu(m);
    if (log.entries !== 1 || log.saves || log.brk) say(`${disc}: the boot's ${log.entries} title loads, ${log.saves} saves, ${log.brk} errors, not 1, 0, 0`);
    log.entries = 0;                    // (from here, the case's own loads)
    if (!writeable) m.disc().isWriteable = false;
    return m;
}

// to the menu's wait (in the background's bank: its address is reached in ROMs too, during the boot), a key pressed
// if a load stops for one
async function toMenu(m) {
    for (let keys = 0; ;) {
        const at = await runToAny(m.s, [[syms["game_resume.idle"]], [syms["load_track.waitkey"]]], 400000000);
        if (at === syms["load_track.waitkey"]) {
            if (++keys === 3) { say(`a load still stopped for a key after ${keys}: "${m.log.said}"`); process.exit(1); }
            m.s.keyDown("Space");
            await m.s.runFor(400000);
            m.s.keyUp("Space");
        } else if ((m.cpu.romsel & 15) === m.peek(syms.bankbg)) return;
        else await m.s.runFor(1000);
    }
}

// a title's load from the menu (TRACKF: the save at its start), back to the menu
async function titleLoad(m) {
    m.s.writeMemory(syms.LoadWant, [F - 0x30]);
    await toMenu(m);
}

// a race on track 1, 50 fields, Escape back (TRACKF loaded on the way)
async function race(m) {
    m.s.writeMemory(syms.LoadWant, [1]);
    await runTo(m.s, syms.start, 400000000);
    await m.s.runFor(50 * 39936);
    m.s.keyDown("Escape");
    await toMenu(m);
    m.s.keyUp("Escape");
}

// the keys and sound, and KeysSum their sum
function holds(m, what, keys) {
    const got = [...m.s.readMemory(syms.SoundOff, Len + 2)];
    if (!same(got.slice(0, Len), keys)) say(`${what}: SoundOff and PlayerKeys ${got.slice(0, Len)}, not ${keys}`);
    if (!same(got.slice(Len), sum(keys))) say(`${what}: KeysSum ${got.slice(Len)}, not ${sum(keys)}`);
}

// fresh, and a race and back
let m = await boot("build/ta.ssd");
const keys0 = [...m.s.readMemory(syms.SoundOff, Len)];
holds(m, "fresh", keys0);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves) say(`fresh: ${m.log.entries} title loads, ${m.log.saves} saves, not 1 and 0`);
await race(m);
if (m.log.entries !== 2 || m.log.saves) say(`a race and back: ${m.log.entries} title loads, ${m.log.saves} saves, not 2 and 0`);
if (discFiles(toSsdOrDsd(m.disc())).SCORES) say("fresh: SCORES written");

// changed: the sound off, player 1's left A
const keys1 = [...keys0];
keys1[0] = 1;
keys1[1] = 65;
m.s.writeMemory(syms.SoundOff, keys1);
await titleLoad(m);
if (m.log.entries !== 3 || m.log.saves !== 1 || m.log.brk) say(`changed: ${m.log.entries} title loads, ${m.log.saves} saves, ${m.log.brk} errors, not 3, 1, 0`);
const image = toSsdOrDsd(m.disc());
const file = discFiles(image).SCORES;
const want1 = [...keys1, ...sum(keys1)];
if (!file) { say("changed: no SCORES"); process.exit(1); }
if (!same([...file.data], want1)) say(`changed: SCORES ${file.data.length} bytes ${[...file.data]}, not ${want1}`);
holds(m, "changed", keys1);
await race(m);
if (m.log.saves !== 1) say(`changed: ${m.log.saves} saves after a race, not 1`);
writeFileSync(`${Out}/saved.ssd`, image);

// loaded
m = await boot(`${Out}/saved.ssd`);
holds(m, "loaded", keys1);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves) say(`loaded: ${m.log.entries} title loads, ${m.log.saves} saves, not 1 and 0`);
// and saved over: the sound on again
const keys2 = [0, ...keys1.slice(1)];
m.s.writeMemory(syms.SoundOff, [0]);
await titleLoad(m);
const again = discFiles(toSsdOrDsd(m.disc())).SCORES;
const want2 = [...keys2, ...sum(keys2)];
if (m.log.saves !== 1 || !again || !same([...again.data], want2)) say(`saved over: ${m.log.saves} saves, SCORES ${again ? [...again.data] : "gone"}`);

// spoilt
const at = file.data.byteOffset;
const length = (d, n) => { const e = 0x100 + file.entry; d[e + 4] = n & 255; d[e + 5] = n >> 8; d[e + 6] &= ~0x30; };
const spoil = {
    "a key changed": (d) => { d[at + 3] ^= 1; },
    "two bytes swapped": (d) => { [d[at + 1], d[at + 2]] = [d[at + 2], d[at + 1]]; },
    "the sum's first byte": (d) => { d[at + Len] ^= 0x80; },
    "the sum's second byte": (d) => { d[at + Len + 1] ^= 0x80; },
    "a byte short": (d) => { length(d, Len + 1); },
    "the game's length, 307": (d) => { length(d, 307); },
};
for (const [what, f] of Object.entries(spoil)) {
    const d = Uint8Array.from(image);
    f(d);
    if (what === "two bytes swapped" && d[at + 1] === d[at + 2]) throw new Error("two bytes the same");
    writeFileSync(`${Out}/spoilt.ssd`, d);
    m = await boot(`${Out}/spoilt.ssd`);
    holds(m, `spoilt, ${what}`, keys0);
}

// read only
m = await boot("build/ta.ssd", false);
m.s.writeMemory(syms.SoundOff, keys1);
await titleLoad(m);
const text = m.log.said;
if (m.log.brk !== 1 || m.log.saves !== 1 || m.log.entries !== 2) say(`read only: ${m.log.brk} errors, ${m.log.saves} saves, ${m.log.entries} title loads, not 1, 1, 2`);
if (!/^Disc read only - press a key$/.test(text)) say(`read only: the HUD's row said "${text}"`);
if (discFiles(toSsdOrDsd(m.disc())).SCORES) say("read only: SCORES written");
await titleLoad(m);
if (m.log.saves !== 1 || m.log.brk !== 1) say(`read only: ${m.log.saves} saves and ${m.log.brk} errors after another load, not 1 and 1`);

// ADFS L: build/ta.adl on a Master with ADFS, a change saved, then SHIFT-BREAK with the disc as written
m = await boot("build/ta.adl", true, "MasterADFS", Adfs);
m.s.writeMemory(syms.SoundOff, keys1);
await titleLoad(m);
if (m.log.entries !== 1 || m.log.saves !== 1 || m.log.brk) say(`ADFS: ${m.log.entries} title loads, ${m.log.saves} saves, ${m.log.brk} errors, not 1, 1, 0`);
m.s.keyDown("ShiftLeft");
m.s.reset(true);
await m.s.runFor(Adfs);
m.s.keyUp("ShiftLeft");
await toMenu(m);
holds(m, "ADFS, booted again", keys1);
if (m.log.saves !== 1 || m.log.brk) say(`ADFS: ${m.log.saves} saves, ${m.log.brk} errors by the boot again, not 1 and 0`);

console.log(wrong ? `${wrong} wrong` : `SCORES the keys and sound, ${want1.length} bytes: none saved fresh or after a race unchanged, saved once a change, loaded back and saved over, on DFS and ADFS; 6 spoilt files refused (the game's length among them); a read-only disc's error said once ("${text}")`);
process.exit(wrong ? 1 : 0);
