// Time attack's table (docs/brief-timeattack-2026-11-10.md, step 5b; tatable.6502's ta_enter, timeattack.6502's
// ta_race_end, ta_save_table and ta_load_table) against a model, on build/ta.ssd, each race on a track briefly
// driven by the autopilot (tools/ta_pilot.mjs), its best lap then poked (TaBest) and the race left by Escape's flag:
// - entered: a run of races on tracks 1, 3 and 8, their bests chosen to fill track 1's 10 and go past it (ties,
//   none, slower than all 10): after each, the model's entry (D41: before the first it's under, a tie after, the
//   10th dropped; no lap, nothing; its upgrades the race's, car 0's levels poked into GmTopUp, GmTurbo and GmTraction
//   before it, and the race's car given them, speed * 36 + turbo * 6 + traction; its name typed, step 6g, each race's
//   its own, so ties' order shows), TIMES on the disc as the model (the times, upgrades, names, the sum) and
//   written only if the table changed, after the name (its save's own trip, none at the race's load), and at the next race's start the table in the cars' bank as it, TIMES read
//   only at the boot's first load (its catalogue entry and the file), kept from then on;
// - loaded: the disc as written booted again: the table back at the first race's start;
// - spoilt: that disc with a byte of TIMES changed, two bytes swapped, either byte of its sum changed, or the file
//   a byte short: the table empty at the race's start;
// - read only: the disc write-protected, a race that enters: the OS's error said once, the next race no second try.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_table_check.mjs

import { mkdirSync, writeFileSync } from "node:fs";
import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { makePilot } from "./ta_pilot.mjs";
import { typeName } from "./ta_name.mjs";

const { toSsdOrDsd } = await jsbeebModule("disc.js");
const dir = "build/tracks_ta";
const syms = symbols(`${dir}/t0.json`);
const Out = "build/ta_table_check";
mkdirSync(Out, { recursive: true });
const N = 80, Len = syms.TaTableLen;
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };

// to the menu's wait in the background's bank (its address alone is reached in ROMs too, during a boot)
async function toMenu(s) {
    const cpu = s._machine.processor;
    for (;;) {
        await runToAny(s, [[syms["game_resume.idle"]]], 400000000);
        if ((cpu.romsel & 15) === s.readMemory(syms.bankbg, 1)[0]) return;
        await s.runFor(1000);
    }
}
async function boot(disc, writeable = true) {
    const s = await bootDisc(disc);
    const cpu = s._machine.processor;
    const peek = (a) => s.readMemory(a, 1)[0];
    const log = { saves: [], reads: 0, brk: 0, text: "", said: "" };
    cpu.debugInstruction.add((pc) => {
        if (pc === 0xffdd && (cpu.a === 0 || cpu.a === 5 || cpu.a === 255)) {
            const blk = cpu.x | (cpu.y << 8), at = peek(blk) | (peek(blk + 1) << 8);
            let name = ""; for (let i = 0; i < 10 && peek(at + i) !== 13; i++) name += String.fromCharCode(peek(at + i));
            if (cpu.a === 0) log.saves.push(name);
            else if (name === "TIMES") log.reads++;
        } else if (pc === syms["load_track.brk"]) { log.brk++; log.text = ""; }
        else if (pc === syms.row_char && log.brk) log.text += String.fromCharCode(cpu.a);
        else if (pc === syms["load_track.waitkey"]) log.said = log.text;
        return false;
    });
    await toMenu(s);
    if (!log.reads) say(`${disc}: TIMES not read by the menu`);
    const m = { s, cpu, peek, log, bankbg: peek(syms.bankbg), bt: peek(syms.banktrace), bc: peek(syms.bankcars), disc: () => cpu.fdc.drives[0].disc };
    if (!writeable) m.disc().isWriteable = false;
    return m;
}
// a bank's bytes (romSelect for the moment, as tools/jsbeeb.mjs's andy)
function paged(m, romsel, fn) {
    const r = m.cpu.romsel;
    try { m.cpu.romSelect(romsel); return fn(); } finally { m.cpu.romSelect(r); }
}
const tableNow = (m) => paged(m, m.bc, () => [...m.s.readMemory(syms.TaTable, Len)]);
async function toIdle(m, name = "") {
    for (let keys = 0; ; keys++) {
        const at = await runToAny(m.s, [[syms["game_resume.idle"], m.bankbg], [syms["tg_type.field"], m.bankbg], [syms["load_track.waitkey"]]], 400000000);
        if (at === syms["tg_type.field"]) {     // (the entry's name: the race's load saved nothing)
            if (m.log.saves.length) say(`the saves ${m.log.saves.join()} before the name`);
            await typeName(m.s, name); keys--; continue;
        }
        if (at !== syms["load_track.waitkey"]) return;
        if (keys === 3) { say(`a load still stopped for a key: "${m.log.said}"`); process.exit(1); }
        m.s.keyDown("Space"); await m.s.runFor(400000); m.s.keyUp("Space");
    }
}
// track t raced 30 frames, its best then best, and left; the table at the race's start (ghost_frame's first)
async function race(m, t, best, ups = [0, 0, 0], name = "") {
    const sy = symbols(`${dir}/t${t}.json`);
    m.s.writeMemory(sy.GmTopUp, [ups[0]]); m.s.writeMemory(sy.GmTurbo, [ups[1]]); m.s.writeMemory(sy.GmTraction, [ups[2]]);
    m.s.writeMemory(sy.GmDemo, [0]); m.s.writeMemory(sy.LoadWant, [t + 1]);
    await runTo(m.s, sy.start, 400000000);
    await runToAny(m.s, [[sy.ghost_frame, m.bc]], 8000000);
    const start = [...m.s.readMemory(sy.TaTable, Len)];
    let pilot = null;
    for (let n = 0; n < 30; n++) {
        await runToAny(m.s, [[sy["logic_frame.played"], m.bt]], 8000000);
        pilot ??= makePilot(m.s, sy);
        m.s.writeMemory(sy.RcInput, [pilot(), 0, 0]);
    }
    const given = paged(m, m.bt | 0x80, () => [sy.RcTopUp, sy.RcTurbo, sy.RcTraction].map((a) => m.s.readMemory(a, 1)[0]));
    if (!same(given, ups)) say(`track ${t + 1}: the race's car given upgrades ${given.join(" ")}, not ${ups.join(" ")}`);
    paged(m, m.bt | 0x80, () => m.s.writeMemory(sy.TaBestLo, [best & 255, best >> 8]));
    m.log.saves = [];
    m.s.writeMemory(sy.GmAbandon, [1]); m.s.writeMemory(sy.LoadWant, [0xff]);
    await toIdle(m, name);
    return start;
}

// the model: entries [time, upgrades, name] by track * 10 + place
const empty = () => [...Array(N)].map(() => ({ time: 0, ups: 0, name: Array(10).fill(0) }));
const nameBytes = (name) => [...Array(10)].map((_, i) => i < name.length ? name.charCodeAt(i) : 0);
function enter(model, t, best, [s, tu, r] = [0, 0, 0], name = "") {
    if (!best) return false;
    const e = model.slice(t * 10, t * 10 + 10);
    const p = e.findIndex((x) => !x.time || best < x.time);
    if (p < 0) return false;
    e.splice(p, 0, { time: best, ups: s * 36 + tu * 6 + r, name: nameBytes(name) });
    model.splice(t * 10, 10, ...e.slice(0, 10));
    return true;
}
function bytes(model) {
    const b = Array(Len).fill(0);
    model.forEach((x, i) => { b[i] = x.time & 255; b[N + i] = x.time >> 8; b[2 * N + i] = x.ups; x.name.forEach((c, j) => { b[3 * N + i * 10 + j] = c; }); });
    return b;
}
function sum(b) { let a = 0, h = 0; for (const v of b) { a = (a + v) & 255; h = (h + a) & 255; } return [a, h]; }
const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const show = (b, t) => [...Array(10)].map((_, p) => b[t * 10 + p] | (b[N + t * 10 + p] << 8)).join(" ");

// entered
let m = await boot("build/ta.ssd");
const model = empty();
const runs = [[0, 500], [0, 400], [0, 600], [0, 0], [0, 450], [0, 450], [2, 555], [0, 700], [0, 300], [0, 800],
    [0, 900], [7, 444], [0, 1000], [0, 350], [0, 1100], [0, 2000], [0, 250], [2, 333], [0, 450]];
let file = null, tablesChecked = 0;
const readsAtBoot = m.log.reads;
const Ups = [[0, 0, 0], [2, 1, 2], [5, 0, 0], [0, 5, 0], [0, 0, 5], [1, 1, 1], [3, 2, 0], [0, 4, 1]];   // (each race's, in turn)
const Names = ["RACE 1", "TWO", "", "4", "FIVE.", "SIX-6", "SEVEN!", "EIGHT 8", "NINE 99", "TEN CHARS1", "E11", "E12", "E13",   // (and its name)
    "E14", "E15", "E16", "E17", "E18", "E19"];
for (let i = 0; i <= runs.length; i++) {
    const [t, best] = runs[i] ?? [0, 0];
    const ups = Ups[i % Ups.length], name = Names[i % Names.length];
    const start = await race(m, t, best, ups, name);
    if (i && !same(start, bytes(model))) say(`entered: the table loaded at race ${i + 1}'s start not the model's (track 1: ${show(start, 0)} for ${show(bytes(model), 0)})`);
    else if (i) tablesChecked++;
    if (i === runs.length) break;
    const changed = enter(model, t, best, ups, name);
    const want = bytes(model);
    file = discFiles(toSsdOrDsd(m.disc())).TIMES;
    if (m.log.saves.join() !== (changed ? "TIMES" : "")) say(`entered: race ${i + 1} (track ${t + 1}, ${best}): the saves ${m.log.saves.join() || "none"}, the table ${changed ? "changed" : "the same"}`);
    if (!file && changed) say(`entered: no TIMES after race ${i + 1}`);
    else if (file && !same([...file.data], [...want, ...sum(want)])) say(`entered: TIMES after race ${i + 1} not the model's (track 1: ${show([...file.data], 0)} for ${show(want, 0)})`);
}
if (m.log.reads !== readsAtBoot) say(`entered: TIMES read ${m.log.reads - readsAtBoot} times after the boot, by ${runs.length + 1} races' loads`);
const saved = Uint8Array.from(toSsdOrDsd(m.disc()));
writeFileSync(`${Out}/saved.ssd`, saved);
const final = bytes(model);

// loaded
m = await boot(`${Out}/saved.ssd`);
let start = await race(m, 0, 0);
if (!same(start, final)) say(`loaded: the table at the start not the saved one (track 1: ${show(start, 0)})`);

// spoilt
const f = discFiles(saved).TIMES, at = f.data.byteOffset;
const spoil = {
    "a byte": (d) => { d[at + 5] ^= 1; },
    "two bytes swapped": (d) => { [d[at + 0], d[at + 1]] = [d[at + 1], d[at + 0]]; },
    "the sum's first byte": (d) => { d[at + Len] ^= 0x80; },
    "the sum's second byte": (d) => { d[at + Len + 1] ^= 0x80; },
    "a byte short": (d) => { d[0x100 + f.entry + 4]--; },
};
for (const [what, fn] of Object.entries(spoil)) {
    const d = Uint8Array.from(saved);
    fn(d);
    if (what === "two bytes swapped" && d[at] === d[at + 1]) throw new Error("two bytes the same");
    writeFileSync(`${Out}/spoilt.ssd`, d);
    m = await boot(`${Out}/spoilt.ssd`);
    start = await race(m, 0, 0);
    if (start.some((v) => v)) say(`spoilt, ${what}: the table at the start not empty`);
}

// read only
m = await boot("build/ta.ssd", false);
await race(m, 0, 500);
const text = m.log.said;
if (m.log.brk !== 1 || m.log.saves.join() !== "TIMES") say(`read only: ${m.log.brk} errors, the saves ${m.log.saves.join()}, not 1 and TIMES`);
if (!/^Disc read only - press a key$/.test(text)) say(`read only: the HUD's row said "${text}"`);
await race(m, 0, 0);
if (m.log.saves.length || m.log.brk !== 1) say(`read only: the saves ${m.log.saves.join()} and ${m.log.brk} errors after another race, not none and 1`);

console.log(wrong ? `${wrong} wrong` : `${runs.length} races entered as the model, each its name typed (ties in order: track 1's 10: ${show(final, 0)}; track 3's: ${show(final, 2)}), TIMES saved when changed, read only at the boot and the table kept through every load (${tablesChecked} checked), back after a boot; 5 spoilt files refused; a read-only disc's error said once`);
process.exit(wrong ? 1 : 0);
