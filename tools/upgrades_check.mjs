// The upgrades' screen (F_01A130, step 8): build/game.ssd, a game started and the circle's end reached by pokes with a state chosen to
// try each part of the screen, every pass compared byte for byte with tools/upgrades_model.mjs: the panels, levels, "TAKEN", the
// dial's 16 positions, the boxes flashing and full, what's bought, and the figures as they're paid for, with no flicker. It waits for
// fire past the ST's 158 passes (D27). game_check sees the screens of the traced games.
//
// Exit status: 1 if a screen's wrong or a position's never seen, else 0.
//
// Usage (from the repo root, after make game): node tools/upgrades_check.mjs [SHOTDIR]

import { writeFileSync } from "node:fs";
import { bootDisc, ram, runToAny, symbols } from "./jsbeeb.mjs";
import { box_full, screen } from "./upgrades_model.mjs";

const shots = process.argv[2];
const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
const got = syms["game_read.got"], peek = (a) => s.readMemory(a, 1)[0], peeks = (a, n) => [...s.readMemory(a, n)];
let bad = 0;
const say = (t) => { if (bad++ < 30) console.log(t); };

// a game started, the select ended by fire
for (let started = false; ;) {
    const at = await runToAny(s, [[got, bankbg], [syms["game_resume.selected"], bankbg]], 2000000000);
    if (at !== got) break;
    if (cpu.x === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
}

const digits = (n) => { const t = String(n).padStart(6, " "); return [...t].map((c) => c === " " ? 0x80 : Number(c)); };
const Cases = [
    // both players, the second then the first in turn: nothing bought yet, and one with everything
    { name: "first upgrades", wrench: [4, 5, 0], drone: [0, 0, 1], score: [2100, 1530, 73170], laps: [4, 3, 2], levels: [[0, 0, 0, 0], [1, 2, 3, 0], [0, 0, 0, 0]], walk: true },
    { name: "full boxes", wrench: [9, 0, 12], drone: [0, 1, 0], score: [0, 999999, 120], laps: [1, 0, 9], levels: [[5, 5, 2, 0], [0, 0, 0, 0], [5, 0, 5, 3]], walk: false, wait: 170 },
    { name: "score bought", wrench: [0, 8, 4], drone: [1, 0, 0], score: [1, 12345, 98999], laps: [0, 2, 3], levels: [[0, 0, 0, 0], [0, 4, 1, 0], [2, 2, 2, 2]], walk: false, dial: 8 },
];

function poke(c) {
    s.writeMemory(syms.GmStage, [1]);
    for (let car = 0; car < 3; car++) {
        s.writeMemory(syms.RcWrench + car, [c.wrench[car]]);
        s.writeMemory(syms.RcDrone + car, [c.drone[car]]);
        s.writeMemory(syms.RcScore + car * 6, digits(c.score[car]));
        s.writeMemory(syms.RcLaps + car, [c.laps[car]]);
        s.writeMemory(syms.RcTraction + car, [c.levels[car][0]]);
        s.writeMemory(syms.RcTopUp + car, [c.levels[car][1]]);
        s.writeMemory(syms.RcTurbo + car, [c.levels[car][2]]);
        s.writeMemory(syms.GmScoreUp + car, [c.levels[car][3]]);
    }
}
let shownLevels;                        // (the levels drawn: a purchase isn't, as on the ST)
function state(car) {
    const n = [0, 1, 2];
    return {
        car, drone: n.map((c) => peek(syms.RcDrone + c)), wrench: n.map((c) => peek(syms.RcWrench + c)),
        score: n.map((c) => peeks(syms.RcScore + c * 6, 6)), laps: n.map((c) => peek(syms.RcLaps + c)),
        level: shownLevels, dial: peek(syms.UpShown), lit: peeks(syms.UpLit, 4),
    };
}
let screens = 0, shot = 0, lastField = -1, longest = 0, moving = 0, longestWait = 0;
const compared = new Set(), bought = [0, 0, 0, 0];
let before;
async function check(where, car) {
    const st = state(car), want = screen(st), have = ram(s, syms.PlayAddr, 16000);
    let diff = 0, first = -1;
    for (let i = 0; i < 16000; i++) if (have[i] !== want[i]) { diff++; if (first < 0) first = i; }
    screens++;
    compared.add(st.dial);
    if (diff) say(`${where}: ${diff} bytes differ, the first at row ${Math.floor(first / 640)}, byte ${(first % 640) >> 3}, line ${first & 7}: dial ${st.dial}, lit ${st.lit}`);
    return st;
}
const stops = [[got, bankbg], [syms["upgrade.shown"], bankbg], [syms["upgrade.chosen"], bankbg], [syms["upgrade.over"], bankbg],
    [syms["upgrade.pay"], bankbg], [syms["game_resume.after_upgrades"], bankbg]];

// A payment's figures mustn't flicker: over each step, no pixel of the panels that ends as it began may be written any other way, or the
// display can catch it. A figure taken away and drawn again fails this, however quickly it's done.
const Panels = 3 * 640;
let step = null, flickers = 0, steps = 0;
cpu.debugWrite.add((a, v) => {
    if (step && a >= syms.PlayAddr && a < syms.PlayAddr + Panels) step.writes.push([a - syms.PlayAddr, v]);
    return false;
});
function stepped(where) {
    if (step) {
        const after = ram(s, syms.PlayAddr, Panels);
        let bad = 0;
        for (const [i, v] of step.writes) if ((v ^ step.before[i]) & ~(step.before[i] ^ after[i]) & 255) bad++;
        steps++;
        if (bad) { flickers++; say(`${where}: ${bad} writes to pixels that don't change`); }
    }
    step = { before: Uint8Array.from(ram(s, syms.PlayAddr, Panels)), writes: [] };   // (a copy: ram's a view)
}
for (const c of Cases) {
    poke(c);
    cpu.pc = syms["game_resume.after_circle"];
    let car = -1, passes = 0, held = 0;
    for (; ;) {
        const at = await runToAny(s, stops, 2000000000);
        if (at === syms["game_resume.after_upgrades"]) break;
        if (at === syms["upgrade.shown"]) {
            car = peek(syms.GsCar);
            passes = 0;
            held = 0;
            shownLevels = [peek(syms.RcTraction + car), peek(syms.RcTopUp + car), peek(syms.RcTurbo + car)];
            const st = await check(`${c.name}, car ${car} shown`, car);
            const full = box_full(st).map(Number);
            if (full.join() !== st.lit.join()) say(`${c.name}: boxes lit at the start ${st.lit}, full ${full}`);
            if (shots) writeFileSync(`${shots}/up${shot++}.png`, await s.screenshotActive({ scale: 2 }));
        } else if (at === got) {
            if (cpu.x !== car) { cpu.a = 0; continue; }
            const field = peek(syms.vsyncs), gone = (field - lastField) & 255;
            if (passes > 1) {           // (the first's from the screen's wipe)
                if (gone < 3) say(`${c.name}, pass ${passes}: ${gone} fields`);
                longest = Math.max(longest, gone);
                if (gone > 3) moving++;
                if (process.env.PASSES) console.log(c.name, passes, gone, peek(syms.UpShown));
            }
            lastField = field;
            if (passes) {               // (as the last pass left it)
                const st = await check(`${c.name}, car ${car} pass ${passes}`, car);
                const on = st.dial >> 2, full = box_full(st);
                st.lit.forEach((l, b) => { if (b !== on && !!l !== full[b]) say(`${c.name}, pass ${passes}: box ${b} ${l ? "lit" : "dark"}, dial ${st.dial}`); });
                if (full[on] && !st.lit[on]) say(`${c.name}, pass ${passes}: the box the dial's on is full but dark`);
                if (shots && passes === 3) writeFileSync(`${shots}/up${shot++}.png`, await s.screenshotActive({ scale: 2 }));
            }
            passes++;
            longestWait = Math.max(longestWait, passes);
            // left held, the dial goes on stopping at 2, 6, 10, 14; the walk sees all 16, then fire
            if (c.walk && car === 0 && compared.size < 16 && held < 200) { cpu.a = 8; held++; } else if (passes > (c.wait ?? 3)) cpu.a = 0x80; else cpu.a = (c.dial ?? 0) && passes === 1 ? 8 : 0;
        } else if (at === syms["upgrade.pay"]) {
            stepped(`${c.name}, car ${car} paying`);
        } else if (at === syms["upgrade.chosen"] || at === syms["upgrade.over"]) {
            if (at === syms["upgrade.over"]) { stepped(`${c.name}, car ${car} paying`); step = null; }
            const st = await check(`${c.name}, car ${car} ${at === syms["upgrade.over"] ? "paid" : "chosen"}`, car);
            if (at === syms["upgrade.chosen"]) {
                if (!st.lit[st.dial >> 2]) say(`${c.name}: what's chosen isn't lit`);
                before = { score: Number(st.score[car].map((d) => d & 0x80 ? 0 : d).join("")), wrench: st.wrench[car], chose: st.dial >> 2 };
            } else {
                const score = Number(st.score[car].map((d) => d & 0x80 ? 0 : d).join(""));
                if (st.wrench[car] !== before.wrench - 4) say(`${c.name}: wrenches ${before.wrench} to ${st.wrench[car]}`);
                if (score !== before.score + (before.chose === 1 ? 3000 : 0)) say(`${c.name}: score ${before.score} to ${score}, quarter ${before.chose}`);
                bought[before.chose]++;
            }
            if (shots && at === syms["upgrade.over"]) writeFileSync(`${shots}/up${shot++}.png`, await s.screenshotActive({ scale: 2 }));
        }
    }
}
if (compared.size < 16) say(`only ${compared.size} positions seen`);
if (!bought[1]) say("no score bought");
if (!steps) say("no payment seen");
if (longestWait <= 158) say(`it never waited past the ST's time: ${longestWait} passes`);
if (longest > 4) say(`a pass of ${longest} fields`);
console.log(bad ? `${bad} wrong` : `${screens} screens of the upgrades right, a pass 3 fields, ${moving} of them 4 (the dial moving); ${steps} payments, no flicker; ${longestWait} passes waited`);
process.exit(bad ? 1 : 0);
