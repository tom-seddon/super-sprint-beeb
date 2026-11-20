// The attract mode against the ST's (Phase 5, step 6; D19): build/game.ssd left alone from the ST's seed, each screen's
// order and time measured, and at each demo's end the generator against the ST's, run on by the numbers it drew in
// the same demo (tools/st_trace_game.py's attract script). Nothing else tests demos back to back: what one leaves
// behind (the generator, the coasting phase, the sparks' timers) goes into the next. The ST's waits are its screens'
// F_0140F0 calls, 250, 250, 250, 150 and 325 fields; here a screen's drawing adds a few, so they're allowed
// Slack, the high scores' and lap records' with their wipes out, but for the title's, which adds a wipe out, an unpacking and a wipe in,
// and the wait after the demo, which adds the pictures' load. The title, the high scores and lap records (tables and
// all, against the ST's as tools/st_frontend.py composes them) and the credits are compared byte for byte.
//
// Exit status: 1 if the order, a time, a track or the generator differs, else 0.
//
// Usage (from the repo root, after make game): node tools/attract_check.mjs [DEMOS]   (default 3)

import { readFileSync } from "node:fs";
import { andy, bootDisc, cycles, ram, runToAny, symbols } from "./jsbeeb.mjs";

const Demos = Number(process.argv[2] ?? 3), Slack = 8, Field = 39936;
const Tracks = [0, 2, 6, 5, 1, 4, 7, 3];   // G_01D148, from track 1
const Waits = { title: 250, scores: 250 + 50 + 88, records: 250 + 50, credits: 325 };   // (88: the lap records' unpacking, table and wipe in)
const { events } = JSON.parse(readFileSync("build/trace/game_attract.json"));

// the numbers each demo drew, and the seed before the first
const drawn = [];
let inDemo = false;
for (const e of events) {
    if (e.kind === "point" && e.name === "demo") { inDemo = true; drawn.push([]); }
    else if (e.kind === "point" && e.name === "wait") inDemo = false;
    else if (e.kind === "random" && inDemo) drawn[drawn.length - 1].push(e.value);
}
const Mul = 3141592621n;
const Inv = (() => { let x = 1n; for (let i = 0; i < 6; i++) x = (x * (2n - Mul * x)) & 0xffffffffn; return x; })();
function firstSeed(values) {
    for (let low = 0n; low < 256n; low++) {
        const s = (BigInt(values[0]) << 8n) | low;
        let t = s, ok = true;
        for (const v of values.slice(1)) {
            t = (t * Mul + 1n) & 0xffffffffn;
            if (Number((t >> 8n) & 0xffffffn) !== v) { ok = false; break; }
        }
        if (ok) return ((s - 1n) * Inv) & 0xffffffffn;
    }
    throw new Error("the random numbers aren't one run of TOS's generator");
}
const start = firstSeed(drawn.flat());

const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0];
for (let i = 0n; i < 4n; i++) s.writeMemory(syms.GmSeed + Number(i), [Number((start >> (8n * i)) & 255n)]);
s.writeMemory(syms.GmSeeded, [1]);

const peek = (a) => s.readMemory(a, 1)[0];
const G = (n) => syms[`game_resume.${n}`];
const stops = ["shown", "scores", "records", "demo", "credits_shown"].map((n) => [G(n), bankbg]);
const names = new Map(stops.map(([a], i) => [a, ["title", "scores", "records", "demo", "credits"][i]]));
stops.push([G("credits_over"), bankbg]);    // (the credits' wait over)
names.set(G("credits_over"), "over");
let bad = 0, seed = start, demo = 0, before = "title", t0 = cycles(s);   // (the boot's idle is in the title's wait)
const say = (t) => { console.log(t); bad++; };
const order = ["title", "scores", "records", "demo", "credits"];
while (demo < Demos) {
    const now = names.get(await runToAny(s, stops, 400000000));
    const fields = Math.round((cycles(s) - t0) / Field);
    t0 = cycles(s);
    if (now === "over") {
        if (Math.abs(fields - Waits.credits) > Slack) say(`credits: ${fields} fields, the ST's ${Waits.credits}`);
        console.log(`credits: ${fields} fields`);
        continue;
    }
    const want = order[(order.indexOf(before) + 1) % order.length];
    if (now !== want) say(`after ${before}: ${now}, not ${want}`);
    if (before in Waits && before !== "title" && before !== "credits" && Math.abs(fields - Waits[before]) > Slack) say(`${before}: ${fields} fields, the ST's ${Waits[before]}`);
    if (before !== "demo" && before !== "credits") console.log(`${before}: ${fields} fields`);
    if (now === "title" || now === "scores" || now === "records" || now === "credits") {     // the picture, wiped in whole, in its mode
        const want = readFileSync(`build/gen/${now}.bin`), got = ram(s, syms.PlayAddr, 16000);
        let diff = 0;
        for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
        if (diff) say(`the ${now}: ${diff} bytes differ`);
        if (peek(syms.GmPicture) !== (now === "title" ? 2 : 1)) say(`the ${now} in the wrong mode`);
    }
    if (now === "demo") {
        const track = peek(syms.GmDemoTrack);
        if (track !== Tracks[demo]) say(`demo ${demo}: track ${track + 1}, not ${Tracks[demo] + 1}`);
    }
    if (now === "credits") {        // (the wait after the demo's gone by too: 150 fields, nothing drawn, then the load)
        for (const v of drawn[demo]) seed = (seed * Mul + 1n) & 0xffffffffn;
        const got = BigInt(s.readMemory(syms.GmSeed, 4).reduce((a, b, i) => a + b * 2 ** (8 * i), 0));
        const ok = got === seed;
        if (!ok) say(`demo ${demo}: the generator &${got.toString(16)}, the ST's &${seed.toString(16)}`);
        console.log(`demo ${demo} on track ${Tracks[demo] + 1}, and the wait: ${fields} fields; ${drawn[demo].length} numbers drawn${ok ? ", the generator exact" : ""}`);
        demo++;
    }
    before = now;
}

// fire ends a demo at once (F_00D1FA, at each frame's end), and that car's game starts: the ST's wait after the demo
// reads fire straight after, a tap still held, where this one's read comes too late for it (logic_frame.demo_fire).
// Car 1's fire, a field long: at once, no wait and no credits, then the select with car 1 the human
const banktrace = ram(s, 2, 1)[0];
await runToAny(s, [[G("records"), bankbg]], 400000000);
await runToAny(s, [[G("demo"), bankbg]], 400000000);
for (let f = 0; f < 200; f++) await runToAny(s, [[syms["logic_frame.demo_fire"], banktrace]], 8000000);
const at = s.readMemory(syms.LfFrame, 2), frame = at[0] | (at[1] << 8);
s.writeMemory(syms.RcInput + 1, [0x80]);    // (ANDY's paged in, the logic's)
s._machine.processor.a = 0x80;
const fired = cycles(s);
const next = await runToAny(s, [[G("game"), bankbg], [G("credits_shown"), bankbg]], 400000000);
const after = (cycles(s) - fired) / Field;
if (frame > 210) say(`fire at frame ${frame}`);
if (next !== G("game")) say("fire in the demo: the credits, not a game");
else {
    const car = s._machine.processor.x;
    if (car !== 1) say(`fire in the demo: car ${car}'s game, not car 1's`);
    if (after > 10) say(`fire in the demo: the game ${after.toFixed(1)} fields on`);
    await runToAny(s, [[G("selected"), bankbg]], 1600000000);
    const drones = [...andy(s, syms.RcDrone, 3)];
    if (drones[1] !== 0 || drones[0] === 0 || drones[2] === 0) say(`after the select, the drones ${drones}, not car 1 the human`);
    else console.log(`fire ended the demo at frame ${frame}, car 1's game ${after.toFixed(1)} fields on, car 1 the human after the select`);
}

// a demo's end, each screen's parity (logic frames 200 and 201, poked): the wait after it shows the race's last frame
// or the one before, cars and all, never the bare track (the cars erased from the screen not shown, then the main one
// shown: Tom's Master, 2026-11-20). Against the clean background, read from the bank as the race ends
for (const k of [200, 201]) {
    const t = await bootDisc("build/game.ssd");
    await runToAny(t, [[syms["game_resume.idle"]]], 80000000);
    await runToAny(t, [[G("demo"), bankbg]], 1600000000);
    for (let f = 0; f < k; f++) await runToAny(t, [[syms["logic_frame.demo_fire"], banktrace]], 8000000);
    const last = ram(t, syms.acccon, 1)[0] & 1 ? "main" : "shadow";   // (not drawn yet: it goes to the screen not shown)
    const clean = t.readMemory(syms.PlayAddr + 0x4000, syms.PlayBytes, { bank: bankbg });
    t.writeMemory(syms.LoadWant, [0xff]);
    t._machine.processor.a = 0;
    for (let i = 0; i < 51; i++) await runToAny(t, [[G("idle"), bankbg]], 400000000);
    const shown = ram(t, syms.PlayAddr, syms.PlayBytes, (ram(t, syms.acccon, 1)[0] & 1) === 1);
    let drawn = 0;
    for (let i = 0; i < syms.PlayBytes; i++) if (shown[i] !== clean[i]) drawn++;
    if (drawn < 32) say(`a demo's end with its last frame on ${last}: the bare track in the wait (${drawn} bytes drawn)`);
    else console.log(`a demo's end with its last frame on ${last}: the wait shows the cars (${drawn} bytes drawn)`);
}

console.log(bad ? `${bad} wrong` : `the attract mode's order and times right, ${Demos} demos' generator exact`);
process.exit(bad ? 1 : 0);
