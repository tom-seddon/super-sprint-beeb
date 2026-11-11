// Time attack's ghosts on the disc (docs/brief-timeattack-2026-11-10.md, step 5; timeattack.6502's ta_save_ghost and
// ta_load_ghost), on build/ta.ssd, each case from a fresh boot, the races driven by the autopilot (tools/ta_pilot.mjs)
// and left by Escape's flag (GmAbandon):
// - saved: track 1 raced past its first lap, then left: GHOST1 written once, at the next load, its time the HUD's
//   ghost time and its bytes the ghost's buffer;
// - loaded: that disc booted again and track 1 raced: the ghost from the first frame, its time on the HUD, its
//   bytes the file's; left with no new ghost: nothing written;
// - beaten: on that machine the ghost's time poked longer (5,000 frames) as the race starts, so lap 1 beats it:
//   GHOST1 written again, its time lap 1's;
// - spoilt: the saved disc with GHOST1 a byte short, its head's bytes one more, its time 0, or its length more
//   than a buffer holds: no ghost (the HUD's time 0, nothing drawn but the car);
// - read only: the disc write-protected, a ghost made and the race left: the OS's error in the HUD's row with
//   " - press a key", a key, the load going on to the title; the next race left with no new ghost: no second try;
// - ADFS: build/ta.adl on a Master with ADFS, a ghost saved, SHIFT-BREAK with the disc as written, and it's back.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_save_check.mjs

import { mkdirSync, writeFileSync } from "node:fs";
import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { makePilot } from "./ta_pilot.mjs";

const { toSsdOrDsd } = await jsbeebModule("disc.js");
const dir = "build/tracks_ta";
const syms = symbols(`${dir}/t0.json`);          // (track 1's: every track's code the same outside the slots)
const Out = "build/ta_save_check";
mkdirSync(Out, { recursive: true });
const Adfs = 8000000;
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
async function boot(disc, writeable = true, model = "Master", hold = undefined) {
    const s = await bootDisc(disc, model, hold);
    const cpu = s._machine.processor;
    const peek = (a) => s.readMemory(a, 1)[0];
    const log = { saves: [], brk: 0, text: "", said: "" };
    cpu.debugInstruction.add((pc) => {
        if (pc === 0xffdd && cpu.a === 0) {           // OSFILE 0: the name's
            const blk = cpu.x | (cpu.y << 8), at = peek(blk) | (peek(blk + 1) << 8);
            let name = ""; for (let i = 0; i < 10 && peek(at + i) !== 13; i++) name += String.fromCharCode(peek(at + i));
            log.saves.push(name);
        } else if (pc === syms["load_track.brk"]) { log.brk++; log.text = ""; }
        else if (pc === syms.row_char && log.brk) log.text += String.fromCharCode(cpu.a);
        else if (pc === syms["load_track.waitkey"]) log.said = log.text;
        return false;
    });
    await toMenu(s);
    const m = { s, cpu, peek, log, bankbg: peek(syms.bankbg), bt: peek(syms.banktrace), disc: () => cpu.fdc.drives[0].disc };
    if (!writeable) m.disc().isWriteable = false;
    return m;
}
const ghostSaves = (m) => m.log.saves.filter((n) => n.startsWith("GHOST"));   // (TIMES too: tools/ta_table_check.mjs's)
const word = (m, a) => m.peek(a) | (m.peek(a + 1) << 8);
const image = (m) => toSsdOrDsd(m.disc());
const ghostFile = (m) => discFiles(image(m)).GHOST1;

// to the attract mode's wait (a key pressed if a load stops for one)
async function toIdle(m) {
    for (let keys = 0; ; keys++) {
        const at = await runToAny(m.s, [[syms["game_resume.idle"], m.bankbg], [syms["load_track.waitkey"]]], 400000000);
        if (at !== syms["load_track.waitkey"]) return;
        if (keys === 3) { say(`a load still stopped for a key after ${keys}: "${m.log.said}"`); process.exit(1); }
        m.s.keyDown("Space");
        await m.s.runFor(400000);
        m.s.keyUp("Space");
    }
}

// track 1 raced FRAMES frames and left; at the start (the first frame drawn): the HUD's ghost time, the ghost's
// bytes and the cars drawn; poke: the ghost's time as the race starts
async function race(m, frames, poke = null) {
    m.s.writeMemory(syms.GmDemo, [0]); m.s.writeMemory(syms.LoadWant, [1]);
    await runTo(m.s, syms.start, 400000000);
    let pilot = null, n = 0, first = null;
    while (n < frames) {
        const at = await runToAny(m.s, [[syms["logic_frame.played"], m.bt], [syms["frame_loop.objects"]]], 8000000);
        if (at === syms["logic_frame.played"]) {
            if (!pilot && poke !== null) m.s.writeMemory(syms.TaGhostLo, [poke & 255, poke >> 8]);
            pilot ??= makePilot(m.s, syms);
            m.s.writeMemory(syms.RcInput, [pilot(), 0, 0]);
        } else {
            first ??= { time: word(m, syms.TaGhostLo), len: word(m, syms.GhLenLo), cars: m.peek(syms.CarCount) };
            n++;
        }
    }
    const end = { time: word(m, syms.TaGhostLo), len: word(m, syms.GhLenLo), news: m.peek(syms.GhNew) };
    m.log.saves = [];
    m.s.writeMemory(syms.GmAbandon, [1]); m.s.writeMemory(syms.LoadWant, [0xff]);
    await toIdle(m);
    return { first, end };
}

// saved
let m = await boot("build/ta.ssd");
if (ghostFile(m)) say("fresh: a GHOST1 on the disc as built");
let r = await race(m, 600);
let f = ghostFile(m);
const time1 = r.end.time;
if (r.first.time || r.first.len || r.first.cars !== 1) say(`saved: a ghost at the first race's start (time ${r.first.time}, ${r.first.len} bytes, ${r.first.cars} cars)`);
if (!r.end.news || !time1) say(`saved: no new ghost in 600 frames (time ${time1})`);
if (ghostSaves(m).join() !== "GHOST1") say(`saved: the saves ${ghostSaves(m).join() || "none"}, not GHOST1`);
if (!f) say("saved: no GHOST1");
else {
    const d = [...f.data];
    if ((d[0] | (d[1] << 8)) !== time1 || (d[2] | (d[3] << 8)) !== r.end.len || d.length !== 4 + r.end.len)
        say(`saved: GHOST1's head ${d.slice(0, 4)}, ${d.length} bytes, not time ${time1}, ${r.end.len} + 4 bytes`);
}
const saved = Uint8Array.from(image(m));
writeFileSync(`${Out}/saved.ssd`, saved);
const file1 = f ? [...f.data] : [];

// loaded
m = await boot(`${Out}/saved.ssd`);
r = await race(m, 400);
if (r.first.time !== time1 || r.first.len !== file1.length - 4 || r.first.cars !== 2)
    say(`loaded: at the start time ${r.first.time}, ${r.first.len} bytes, ${r.first.cars} cars, not ${time1}, ${file1.length - 4}, 2`);
if (ghostSaves(m).length) say(`loaded: the saves ${ghostSaves(m).join()} with no new ghost`);

// beaten
r = await race(m, 600, 5000);
f = ghostFile(m);
if (!r.end.news || ghostSaves(m).join() !== "GHOST1") say(`beaten: the saves ${ghostSaves(m).join() || "none"}, not GHOST1`);
else if (!f || (f.data[0] | (f.data[1] << 8)) !== r.end.time || r.end.time >= 5000) say(`beaten: GHOST1's time not lap 1's, ${r.end.time}`);
const beaten = r.end.time;

// spoilt
const at = discFiles(saved).GHOST1.data.byteOffset, entry = discFiles(saved).GHOST1.entry;
const spoil = {
    "a byte short": (d) => { d[0x100 + entry + 4]--; },
    "its head's bytes one more": (d) => { d[at + 2]++; },
    "its time 0": (d) => { d[at] = 0; d[at + 1] = 0; },
    "longer than a buffer": (d) => { d[0x100 + entry + 4] = 0xbd; d[0x100 + entry + 5] = 0x0b; },  // 3,005 bytes
};
for (const [what, fn] of Object.entries(spoil)) {
    const d = Uint8Array.from(saved);
    fn(d);
    writeFileSync(`${Out}/spoilt.ssd`, d);
    m = await boot(`${Out}/spoilt.ssd`);
    r = await race(m, 50);
    if (r.first.time || r.first.len || r.first.cars !== 1) say(`spoilt, ${what}: at the start time ${r.first.time}, ${r.first.len} bytes, ${r.first.cars} cars`);
}

// read only
m = await boot("build/ta.ssd", false);
r = await race(m, 600);
const text = m.log.said;
if (m.log.brk !== 1 || ghostSaves(m).join() !== "GHOST1") say(`read only: ${m.log.brk} errors, the saves ${ghostSaves(m).join()}, not 1 and GHOST1`);
if (!/^Disc read only - press a key$/.test(text)) say(`read only: the HUD's row said "${text}"`);
if (ghostFile(m)) say("read only: GHOST1 written");
r = await race(m, 100);
if (ghostSaves(m).length || m.log.brk !== 1) say(`read only: the saves ${ghostSaves(m).join()} and ${m.log.brk} errors after another race, not none and 1`);

// ADFS L
m = await boot("build/ta.adl", true, "MasterADFS", Adfs);
r = await race(m, 600);
const timeA = r.end.time;
if (ghostSaves(m).join() !== "GHOST1" || m.log.brk) say(`ADFS: the saves ${ghostSaves(m).join()}, ${m.log.brk} errors, not GHOST1 and 0`);
m.s.keyDown("ShiftLeft");
m.s.reset(true);
await m.s.runFor(Adfs);
m.s.keyUp("ShiftLeft");
await toMenu(m.s);
r = await race(m, 50);
if (r.first.time !== timeA || r.first.cars !== 2) say(`ADFS: booted again, the start's time ${r.first.time} and ${r.first.cars} cars, not ${timeA} and 2`);

console.log(wrong ? `${wrong} wrong` : `GHOST1 saved once a ghost (${file1.length} bytes, time ${time1}), loaded back and drawn from the start, saved over when beaten (time ${beaten}); 4 spoilt files refused; a read-only disc's error said once ("${text}"); ADFS too`);
process.exit(wrong ? 1 : 0);
