// The winner's circle (F_01AC1C, step 8): build/game.ssd, a game started and a race's end reached by pokes with results chosen to try each part of the
// screen, compared byte for byte with tools/circle_model.mjs as it's shown, after every pass of the count and at every field of the celebration:
// each car in each place, drones, all four kinds of figure, a time below 0, an ST limit. It watches every write to the screen while counting: no pixel
// that ends as it began may be written any other way. game_check sees the screens of the traced games.
//
// Exit status: 1 if a screen's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/circle_check.mjs [SHOTDIR]

import { writeFileSync } from "node:fs";
import { bootDisc, ram, runToAny, symbols } from "./jsbeeb.mjs";
import { First, Hold, Steps, screen, sums } from "./circle_model.mjs";

const shots = process.argv[2];
const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
const got = syms["game_read.got"], peek = (a) => s.readMemory(a, 1)[0], peeks = (a, n) => [...s.readMemory(a, n)];
let bad = 0;
const say = (t) => { if (bad++ < 30) console.log(t); };

for (let started = false; ;) {          // a game started, the select ended by fire
    const at = await runToAny(s, [[got, bankbg], [syms["game_resume.selected"], bankbg]], 2000000000);
    if (at !== got) break;
    if (cpu.x === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
}

const digits = (n) => [...String(n).padStart(6, " ")].map((c) => c === " " ? 0x80 : Number(c));
const number = (d) => Number(d.map((c) => c & 0x80 ? 0 : c).join(""));
// each car's laps done, lap end frames, checkpoint and stripes: places by them
const Cases = [
    { name: "white first", track: 0, kind: 0, drone: [0, 0, 0, 1], laps: [4, 3, 2, 1], ends: [[200, 420, 640, 860], [260, 520, 800, 0], [300, 620, 0, 0], [500, 0, 0, 0]], score: [1250, 1250, 73150], frames: 1200 },
    { name: "the drone wins", track: 3, kind: 1, drone: [1, 0, 1, 1], laps: [2, 3, 1, 4], ends: [[300, 640, 0, 0], [250, 500, 780, 0], [700, 0, 0, 0], [200, 400, 600, 800]], score: [0, 990990, 120], frames: 900 },
    { name: "yellow first, green last", track: 7, kind: 2, drone: [0, 0, 0, 1], laps: [3, 0, 4, 2], ends: [[100, 200, 300, 0], [0, 0, 0, 0], [240, 480, 720, 960], [220, 440, 0, 0]], score: [5, 700, 12345], frames: 1100 },
    { name: "a time below 0", track: 5, kind: 3, drone: [0, 1, 0, 1], laps: [4, 2, 3, 1], ends: [[150, 310, 470, 630], [320, 0, 0, 0], [20000, 40000, 60000, 0], [400, 0, 0, 0]], score: [0, 0, 0], frames: 1000 },
];

function poke(c) {
    s.writeMemory(syms.GmStage, [1]);
    s.writeMemory(syms.GmAbandon, [0]);
    s.writeMemory(syms.GmBack, [0]);
    s.writeMemory(syms.GmTrack, [c.track]);
    s.writeMemory(syms.RcFrameLo, [c.frames & 255]);
    s.writeMemory(syms.RcFrameHi, [c.frames >> 8]);
    for (let car = 0; car < 4; car++) {
        s.writeMemory(syms.RcDrone + car, [c.drone[car]]);
        s.writeMemory(syms.RcLaps + car, [c.laps[car]]);
        s.writeMemory(syms.RcCheck + car, [0]);
        s.writeMemory(syms.RcStripesLo + car, [0]);
        s.writeMemory(syms.RcStripesHi + car, [0]);
        s.writeMemory(syms.RcWrench + car, [car]);
        if (car < 3) s.writeMemory(syms.RcScore + car * 6, digits(c.score[car]));
        for (let l = 0; l < 4; l++) {
            s.writeMemory(syms.RcLapTimeLo + car * 4 + l, [c.ends[car][l] & 255]);
            s.writeMemory(syms.RcLapTimeHi + car * 4 + l, [c.ends[car][l] >> 8 & 255]);
        }
    }
}

const G = (n) => syms[`circle_file.${n}`];
const stops = [[syms.circle, bankbg], [syms["circle.count"], bankbg], [syms["circle.passed"], bankbg], [syms["circle.party"], bankbg], [syms["circle.partied"], bankbg],
    [syms["game_resume.after_circle"], bankbg]];
let screens = 0, shot = 0, fieldsSeen = 0, passesSeen = 0, longest = 0;
const compare = (where, st) => {
    const want = screen(st), have = ram(s, syms.PlayAddr, 16000);
    let diff = 0, first = -1;
    for (let i = 0; i < 16000; i++) if (have[i] !== want[i]) { diff++; if (first < 0) first = i; }
    screens++;
    if (diff) say(`${where}: ${diff} bytes differ, the first at row ${Math.floor(first / 640)}, byte ${(first % 640) >> 3}, line ${first & 7}: ${have[first].toString(16)}, not ${want[first].toString(16)}`);
};
// a count's writes: none may disturb a pixel that doesn't change
let step = null, flickers = 0, steps = 0;
cpu.debugWrite.add((a, v) => {
    if (step && a >= syms.PlayAddr && a < syms.PlayAddr + 16000) step.writes.push([a - syms.PlayAddr, v]);
    return false;
});
function stepped(where) {
    if (step) {
        const after = ram(s, syms.PlayAddr, 16000);
        let n = 0;
        for (const [i, v] of step.writes) if ((v ^ step.before[i]) & ~(step.before[i] ^ after[i]) & 255) n++;
        steps++;
        if (n) { flickers++; say(`${where}: ${n} writes to pixels that don't change`); }
    }
    step = { before: Uint8Array.from(ram(s, syms.PlayAddr, 16000)), writes: [] };
}

for (const c of Cases) {
    poke(c);
    cpu.pc = syms["game_resume.arrived"];
    let st = null, want, passes = 0, lastField = 0, field = 0, spark, stepNo = 0, left = 0;
    for (; ;) {
        const at = await runToAny(s, stops, 2000000000);
        if (at === syms["game_resume.after_circle"]) break;
        if (at === syms.circle) {
            // the file's in, the sums done: the kind as this case wants it
            s.writeMemory(syms.GsKind, [c.kind]);
            const order = peeks(syms.GsOrder, 4);
            want = [0, 1, 2, 3].map((car) => sums(c.ends[car], c.laps[car], c.frames, c.track, order.indexOf(car)));
            const key = [0, 1, 2, 3].sort((a, b) => c.laps[b] - c.laps[a]);
            if (key.join() !== order.join()) say(`${c.name}: the order ${order}, not ${key}`);
            spark = peeks(syms.GsSpark, 16);
            st = {
                order, drone: peeks(syms.RcDrone, 4), avg: want.map((w) => w.avg), best: want.map((w) => w.best), shown: [0, 1, 2, 3].map(() => [0, 0, 0]),
                wrench: peeks(syms.RcWrench, 3), score: [0, 1, 2].map((n) => digits(c.score[n])), laps: peeks(syms.RcLaps, 3), frame: First[c.kind], spark,
            };
        } else if (at === syms["circle.count"]) {
            stepped(`${c.name}, pass ${passes}`);
            if (!passes) {
                compare(`${c.name}, shown`, st);
                if (shots) writeFileSync(`${shots}/circle${shot++}.png`, await s.screenshotActive({ scale: 2 }));
            }
            const f = peek(syms.vsyncs);
            if (passes > 1 && ((f - lastField) & 255) !== 2) say(`${c.name}, pass ${passes}: ${(f - lastField) & 255} fields`);
            lastField = f;
        } else if (at === syms["circle.passed"]) {
            passes++;
            passesSeen++;
            for (let car = 0; car < 4; car++) for (let l = 0; l < 3; l++) st.shown[car][l] = Math.min(want[car].points[l], passes * 10);
            st.score = [0, 1, 2].map((n) => digits(c.score[n] + st.shown[n].reduce((a, b) => a + b, 0)));
            compare(`${c.name}, pass ${passes}`, st);
            if (shots && passes === 20) writeFileSync(`${shots}/circle${shot++}.png`, await s.screenshotActive({ scale: 2 }));
        } else if (at === syms["circle.party"]) {
            if (!field) {
                step = null;
                stepNo = 0;
                left = Hold[c.kind][0];
                if (!st.shown.every((v, car) => v.every((n, l) => n === want[car].points[l]))) say(`${c.name}: counted to ${st.shown}`);
            } else {
                left--;
                if (!left) {
                    stepNo++;
                    if (Steps[c.kind][stepNo] === -1) stepNo = 0;
                    if (Steps[c.kind][stepNo] === -2) stepNo--;
                    left = Hold[c.kind][stepNo];
                }
                if (field % 3 === 0) spark = spark.map((n) => (n + 1) % 6);
                st.spark = spark;
                st.frame = First[c.kind] + Steps[c.kind][stepNo];
                compare(`${c.name}, field ${field}`, st);
                fieldsSeen++;
            }
            field++;
        } else if (at === syms["circle.partied"]) {
            if (field !== 200) say(`${c.name}: ${field} fields`);
            if (shots) writeFileSync(`${shots}/circle${shot++}.png`, await s.screenshotActive({ scale: 2 }));
        }
    }
}
console.log(bad ? `${bad} wrong` : `${screens} screens of the circle right: ${passesSeen} passes of 2 fields, ${fieldsSeen} fields of the celebration, ${steps} steps of the count with no flicker`);
process.exit(bad ? 1 : 0);
