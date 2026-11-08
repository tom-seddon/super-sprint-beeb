// The front end's tunes at the chip (Phase 5, step 9, D11): build/game.ssd run from the title through a demo, fire, the
// select, a race's end poked (a player with 4 wrenches), the circle, the upgrades with their dings, and prepare to race
// with a drone joining (its jingle), the SN76489's writes captured and the chip's state rebuilt a field at a time, at
// each vsync's sound_irq. Every field a tune plays is compared with the converter's own (tools/tune_gen.py's
// tunes_expect.json, from the ST's capture): each channel's attenuation, as SnAtten has the YM level times the master
// (16, or less as a screen's end fades it) / 16, its period where it sounds, and the noise's control and attenuation
// where a channel's on it. A tune's first field is the first vsync after tune_play has it playing. The rings' feeding
// is checked too: the paging at each tune_feed while a tune plays must be the background's bank with ANDY in.
//
// With --off, the sound's off (F9) from the start: no tune may play, and the screens end without a fade.
//
// Exit status: 1 if any field differs, a tune or a screen is missed, or the paging's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/tune_check.mjs [--off]

import { readFileSync } from "node:fs";
import { bootDisc, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const off = process.argv.includes("--off");
const expect = JSON.parse(readFileSync("build/gen/tunes_expect.json"));
const Fixed = ["select", "prepare", "join", "ding"];
const Circle = [0, 1, 2, 3, 4].map((k) => `circle${k}`);
const SnAtten = [15, 13, 13, 11, 11, 9, 9, 7, 7, 5, 5, 3, 3, 1, 1, 0];

const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
const cpu = s._machine.processor, chip = s._soundChip;
const peek = (a) => s.readMemory(a, 1)[0];
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0];
if (off) s.writeMemory(syms.SoundOff, [1]);

let bad = 0;
const say = (t) => { if (bad++ < 25) console.log(t); };

// the hooks: each vsync's sound (with the tune's state as it starts), each tune unpacked and started, each feed's paging
const irqs = [];                        // per sound_irq: the cycle, TuneOn, TuneMaster, TuneLeft
const slots = [null, null];             // the tune unpacked into each slot
const plays = [];                       // per tune_play that started one: the cycle, its name
let pending = null, feeds = 0, wrongPaging = 0;
cpu.debugInstruction.add((pc) => {
    if (pc === syms.sound_irq) irqs.push({ cycle: s.elapsedCycles, on: peek(syms.TuneOn), master: peek(syms.TuneMaster),
        left: peek(syms.TuneLeft) | (peek(syms.TuneLeft + 1) << 8) });
    else if (pc === syms.tune_unpack) {
        const want = s.readMemory(syms.TuneWant, 1)[0], slot = s.readMemory(syms.TuneSlot, 1)[0];
        const circle = s.readMemory(syms.TuneBlk + 1, 1)[0] !== (syms.TuneRing >> 8);
        slots[slot] = circle ? Circle[want] : Fixed[want];
    } else if (pc === syms.tune_play) pending = { slot: cpu.x, cycle: s.elapsedCycles };
    else if (pc === syms["tune_play.done"] && pending) {
        if (peek(syms.TuneOn) & 0x80) plays.push({ cycle: s.elapsedCycles, name: slots[pending.slot] });
        pending = null;
    } else if (pc === syms["tune_feed.fill"] && peek(syms.TuneOn) & 0x80) {
        feeds++;
        if (cpu.romsel !== (bankbg | 0x80)) wrongPaging++;
    }
    return false;
});

// the flow, flash_check's: the title, a demo, the credits, fire; at the select's end a race's end poked
const G = (n) => syms[`game_resume.${n}`];
const got = syms["game_read.got"], fire = syms["game_fire.got"], done = G("credits_shown"), selected = G("selected");
const prepShown = syms["prepare.shown"], prepOver = syms["prepare.over"], race = syms["frame_loop"];
const flow = [[got, bankbg], [done, bankbg], [selected, bankbg], [fire, bankbg], [prepShown, bankbg], [prepOver, bankbg]];
let firing = false, started = false, upgraded = false, partied = 0, inPrepare = false, prepReads = 0, joined = false;
const seen = new Set();
chip.startCapture();
const c0 = s.elapsedCycles;
for (let k = 0; k < 100000; k++) {
    const at = await runToAny(s, seen.has("prepare over") ? [...flow, [race]] : flow, 4000000000);
    if (at === done) firing = true;
    else if (at === selected) {
        seen.add("select over");
        if (!upgraded) {
            upgraded = true;
            s.writeMemory(syms.RcWrench, [4]);
            s.writeMemory(syms.RcLaps, [4, 0, 0, 0]);
            s.writeMemory(syms.RcLapTimeLo, [100, 200, 44, 144]);
            s.writeMemory(syms.RcLapTimeHi, [0, 0, 1, 1]);
            s.writeMemory(syms.GmStage, [1]);
            cpu.pc = G("arrived");
        }
    } else if (at === fire) cpu.a = ++partied > 1 ? 0x80 : 0;
    else if (at === prepShown) { inPrepare = true; seen.add("prepare"); }
    else if (at === prepOver) { inPrepare = false; seen.add("prepare over"); }
    else if (at === got) {
        if (inPrepare) {                // (car 1, a drone, joins at its 60th read)
            const join = !joined && cpu.x === 1 && ++prepReads === 60;
            if (join) joined = true;
            cpu.a = join ? 0x80 : 0;
        } else if (firing && !started && cpu.x === 0) { cpu.a = 0x80; started = true; }
        else cpu.a = upgraded && cpu.x === 0 ? 0x80 : 0;
    } else if (at === race && seen.has("prepare over")) break;
}
const writes = chip.stopCapture();
if (process.env.DEBUG) console.log([...seen], plays.length, irqs.length, slots);

// the chip's state after each vsync's writes (sn_check's)
const fields = [];
const st = { n: [0, 0, 0], att: [15, 15, 15], noise: null, natt: 15 };
let latch = 0, w = 0;
const ir = irqs.filter((q) => q.cycle >= c0);
for (let i = 0; i < ir.length; i++) {
    const end = i + 1 < ir.length ? ir[i + 1].cycle : Infinity;
    while (w < writes.length && writes[w].cycle < end) {
        const v = writes[w++].value;
        if (v & 0x80) {
            latch = (v >> 5) & 3;
            const typ = (v >> 4) & 1;
            if (latch === 3) { if (typ) st.natt = v & 15; else st.noise = v & 7; }
            else if (typ) st.att[latch] = v & 15;
            else st.n[latch] = (st.n[latch] & 0x3f0) | (v & 15);
        } else if (latch < 3) st.n[latch] = (st.n[latch] & 15) | ((v & 0x3f) << 4);
    }
    fields.push({ ...ir[i], n: [...st.n], att: [...st.att], noise: st.noise, natt: st.natt });
}

// each tune started: its fields compared from the first vsync after, while it plays
const counts = {};
for (let p = 0; p < plays.length; p++) {
    const { name, cycle } = plays[p];
    const want = expect[name];
    if (!want) { say(`a tune started from slot with nothing known in it`); continue; }
    let f = fields.findIndex((q) => q.cycle > cycle);
    const next = p + 1 < plays.length ? plays[p + 1].cycle : Infinity;
    let i = 0, wrong = 0, faded = 0;
    const masters = [];
    for (; f >= 0 && f < fields.length && i < want.length && fields[f].cycle < next && fields[f].on & 0x80; f++, i++) {
        const g = fields[f], m = g.master;
        if (m < 16) { faded++; masters.push(m); }
        const row = want[i];
        let ok = true, noisy = null;
        for (let c = 0; c < 3; c++) {
            const [v, lvl, onNoise] = row[c];
            const att = SnAtten[(lvl * m) >> 4];
            if (onNoise) { noisy = { v, att }; ok &&= g.att[c] === 15; }
            else ok &&= g.att[c] === att && (att === 15 || g.n[c] === v);
        }
        if (noisy) ok &&= g.natt === noisy.att && (noisy.att === 15 || g.noise === (noisy.v | 4));
        else ok &&= g.natt === 15;
        if (!ok && wrong++ < 3)
            say(`${name}, field ${i}: chip ${JSON.stringify({ n: g.n, att: g.att, noise: g.noise, natt: g.natt })}, ` +
                `want ${JSON.stringify(row)} at master ${m}`);
    }
    // the fade, F_013306's: the master down 1 every 5 fields (each step's 5 fields, the last ones seen while it played)
    for (let a = 0; a < masters.length; ) {
        let b = a;
        while (b < masters.length && masters[b] === masters[a]) b++;
        const first = a === 0 && masters[a] !== 15, last = b === masters.length;
        if ((b - a !== 5 && !(last && b - a < 5)) || first || (b < masters.length && masters[b] !== masters[a] - 1)) {
            say(`${name}: the fade's master ${masters[a]} for ${b - a} fields`); wrong++; break;
        }
        a = b;
    }
    const ended = i === want.length ? "whole" : f < fields.length && fields[f].cycle >= next ? "until the next" : "faded out";
    counts[name] = (counts[name] ?? 0) + 1;
    console.log(`${name}: ${i} of ${want.length} fields ${ended}${faded ? `, ${faded} of them fading` : ""}, ${wrong} wrong`);
    if (wrong) bad++;
}
if (wrongPaging) say(`${wrongPaging} of ${feeds} feeds with the paging wrong`);
const wanted = off ? {} : { select: 1, circle: 1, ding: 4, prepare: 1, join: 1 };
for (const [n, k] of Object.entries(wanted)) {
    const have = n === "circle" ? Circle.reduce((a, c) => a + (counts[c] ?? 0), 0) : counts[n] ?? 0;
    if (have < k) say(`${n}: played ${have} times, wanted ${k}`);
}
if (off && plays.length) say(`${plays.length} tunes played with the sound off`);
if (!seen.has("prepare over")) say("never reached prepare's end");
console.log(bad ? `${bad} wrong` : `${plays.length} tunes, ${fields.length} fields, ${feeds} feeds: all right`);
process.exit(bad ? 1 : 0);
