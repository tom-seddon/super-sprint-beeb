// The race logic's check (Phase 4, D9): build/logic.ssd replays the ST's traced race (tools/st_trace_logic.py)
// through the BBC's logic, and every frame each of the ST's per-car variables is compared with the BBC's.
//
// The BBC stops at test_entry.setup_done (compared with the trace's frame 1, the set-up's last flip) and at
// each test_entry.frame_done (race frame k, from 2, with the trace's frame k). Each variable is the ST's word
// at its address (+2 a car) against the BBC's Rc array: a Lo/Hi pair, or a byte (signed or not). Each race
// frame's cycles (the logic's, with no IRQ: the test runs with interrupts off) are measured too.
//
// Exit status: 1 if any compared variable differs in any compared frame, or the BBC stops, else 0.
//
// Usage (from the repo root, after make logic):
//   node tools/logic_check.mjs [--trace build/trace/logic_t0_r0.json] [--until N] [--cars 0,1,2,3]
//       [--vars x8,y8,...] [--show N]
//   --until N: compare frames up to N (default: all)
//   --cars, --vars: only these cars and variables (the names below; default: all); race-wide ones are
//       compared whatever --cars says
//   --show N: print up to N differences (default 20)
//   --from K: start at frame K: after the set-up, the ST's state at frame K - 1 is written into the BBC's
//       (every variable below, every car) and its inputs pointed at frame K's, so a stretch of the race can
//       be checked before everything that leads to it is built

import { readFileSync } from "node:fs";
import { bootDisc, cycles, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => {
    const i = args.indexOf(name);
    return i >= 0 ? args[i + 1] : dflt;
};

// [name, the ST's address, the BBC's array, kind]: w a Lo/Hi pair, s a signed byte, u an unsigned one
const PerCar = [
    ["x8", 0x1e3fc, "RcX8", "w"], ["y8", 0x1e3f4, "RcY8", "w"], ["x", 0x1e42c, "RcX", "w"], ["y", 0x1e424, "RcY", "w"],
    ["px8", 0x1e3cc, "RcPX8", "w"], ["py8", 0x1e3c4, "RcPY8", "w"],
    ["safex8", 0x1e3ec, "RcSafeX8", "w"], ["safey8", 0x1e3e4, "RcSafeY8", "w"], ["safedir", 0x1e3dc, "RcSafeDir", "u"],
    ["dir", 0x1e41c, "RcDir", "u"], ["travel", 0x1e414, "RcTravel", "u"], ["speed", 0x1e404, "RcSpeed", "w"],
    ["top", 0x1e374, "RcTop", "w"], ["cap", 0x1e35c, "RcCap", "w"], ["thresh", 0x1e364, "RcThresh", "w"],
    ["div", 0x1e36c, "RcDiv", "u"], ["steer", 0x1e40c, "RcSteer", "s"],
    ["tvx", 0x1e2ec, "RcTVX", "w"], ["tvy", 0x1e2e4, "RcTVY", "w"], ["svx", 0x1e2fc, "RcSVX", "w"], ["svy", 0x1e2f4, "RcSVY", "w"],
    ["offx", 0x1e30c, "RcOffX", "w"], ["offy", 0x1e304, "RcOffY", "w"],
    ["bounce", 0x1e3b4, "RcBounce", "u"], ["immune", 0x1e3ac, "RcImmune", "u"], ["spin", 0x1e37c, "RcSpin", "u"],
    ["jump", 0x1e384, "RcJump", "u"], ["bits", 0x1e3a4, "RcBits", "w"], ["latch", 0x1e39c, "RcLatch", "w"],
    ["state", 0x1e3d4, "RcState", "u"], ["laps", 0x1e354, "RcLaps", "u"], ["check", 0x1e38c, "RcCheck", "u"],
    ["stripes", 0x1e394, "RcStripes", "w"], ["drone", 0x1e34c, "RcDrone", "u"], ["order", 0x1e2cc, "RcOrder", "u"],
];
const Race = [["phase", 0x1d178, "RcPhase", "u"], ["frame", 0x1d30e, "RcFrame", "w"], ["push", 0x1e2a0, "RcPush", "u"]];

const syms = symbols("build/logic.json");
const trace = JSON.parse(readFileSync(option("--trace", "build/trace/logic_t0_r0.json")));
const frames = trace.frames;
const until = Math.min(Number(option("--until", frames.length - 1)), frames.length - 1);
const cars = option("--cars", "0,1,2,3").split(",").map(Number);
const only = option("--vars", null)?.split(",");
const show = Number(option("--show", 20));
const from = Number(option("--from", 2));
for (const v of only ?? []) if (![...PerCar, ...Race].some(([n]) => n === v)) throw new Error(`no variable ${v}`);
const wanted = (list) => list.filter(([n]) => !only || only.includes(n));

const s = await bootDisc("build/logic.ssd");
const peek = (a) => s.readMemory(a, 1)[0];
const stWord = (m, a) => (m[a] << 8) | m[a + 1];
function bbc(name, kind, car) {
    if (kind === "w") return peek(syms[`${name}Lo`] + car) | (peek(syms[`${name}Hi`] + car) << 8);
    const b = peek(syms[name] + car);
    return kind === "s" && b >= 0x80 ? b | 0xff00 : b;
}

let wrong = 0, shown = 0, firstWrong = null;
const work = [];
function compare(k) {
    const m = frames[k].mem;
    let bad = 0;
    const one = (label, st, bb) => {
        if (st === bb) return;
        bad++;
        if (shown++ < show) console.log(`frame ${k} ${label}: ST ${st} (&${st.toString(16)}), BBC ${bb} (&${bb.toString(16)})`);
    };
    for (const [n, a, b, kind] of wanted(PerCar))
        for (const c of cars) one(`car ${c} ${n}`, stWord(m, a + 2 * c), bbc(b, kind, c));
    for (const [n, a, b, kind] of wanted(Race)) one(n, stWord(m, a), bbc(b, kind, 0));
    if (bad) {
        wrong++;
        if (firstWrong === null) firstWrong = k;
    }
}

let stopped = null;                     // the frame the BBC never finished (a path not built yet traps)
await runTo(s, syms["test_entry.setup_done"]);
if (from > 2) {
    const m = frames[from - 1].mem;
    for (const [, a, b, kind] of [...PerCar, ...Race]) {
        const n = Race.some(([, ra]) => ra === a) ? 1 : 4;
        for (let c = 0; c < n; c++) {
            const v = stWord(m, a + 2 * c);
            if (kind === "w") {
                s.writeMemory(syms[`${b}Lo`] + c, [v & 0xff]);
                s.writeMemory(syms[`${b}Hi`] + c, [v >> 8]);
            } else s.writeMemory(syms[b] + c, [v & 0xff]);
        }
    }
    const inputs = syms["Inputs"] + (from - 2) * 3;
    s.writeMemory(syms["test_entry.iptr"], [inputs & 0xff, inputs >> 8]);
} else compare(1);
for (let k = from; k <= until; k++) {
    const t0 = cycles(s);
    try {
        await runTo(s, syms["test_entry.frame_done"], 2000000);
    } catch {
        stopped = k;
        console.log(`frame ${k}: the BBC never finished it, pc &${s._machine.processor.pc.toString(16)}`);
        break;
    }
    work.push(cycles(s) - t0);
    compare(k);
}

const sorted = [...work].sort((a, b) => a - b);
const mean = work.reduce((a, b) => a + b, 0) / Math.max(1, work.length);
console.log(`frames ${from > 2 ? from : 1}-${until} (${from > 2 ? "" : "the set-up and "}${work.length} race frames), cars ${cars.join(",")}, ` +
    `${only ? only.length : PerCar.length + Race.length} variables`);
console.log(`logic cycles a frame: mean ${mean.toFixed(0)}, max ${sorted[sorted.length - 1] ?? 0} ` +
    `(the test's own loop, about 60, included)`);
console.log(wrong ? `${wrong} frames wrong, the first frame ${firstWrong}`
    : `all ${(stopped ? stopped - 1 : until) - (from > 2 ? from - 1 : 0)} frames match`);
if (stopped) console.log(`stopped at frame ${stopped}`);
process.exit(wrong || stopped ? 1 : 0);
