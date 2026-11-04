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
import { comparer, index, PerCar, Race, stride, stWord } from "./logic_compare.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => {
    const i = args.indexOf(name);
    return i >= 0 ? args[i + 1] : dflt;
};

const syms = symbols("build/logic.json");
const trace = JSON.parse(readFileSync(option("--trace", "build/trace/logic_t0_r0.json")));
const frames = trace.frames;
const until = Math.min(Number(option("--until", frames.length - 1)), frames.length - 1);
const cars = option("--cars", "0,1,2,3").split(",").map(Number);
const only = option("--vars", null)?.split(",");
const show = Number(option("--show", 20));
const from = Number(option("--from", 2));
for (const v of only ?? []) if (!["seed", "maskb", "map"].includes(v) && ![...PerCar, ...Race].some(([n]) => n === v)) throw new Error(`no variable ${v}`);

const s = await bootDisc("build/logic.ssd");
const peek = (a) => s.readMemory(a, 1)[0];
const checker = comparer(s, syms, trace, { cars, only, show });
const { compare, seeds } = checker;
const work = [];

let stopped = null;                     // the frame the BBC never finished (a path not built yet traps)
await runTo(s, syms["test_entry.setup_done"]);
if (from > 2) {
    const m = frames[from - 1].mem;
    for (const vr of [...PerCar, ...Race]) {
        const [, a, b, kind] = vr;
        const n = Race.includes(vr) ? 1 : 4;
        for (let c = 0; c < n; c++) {
            const v = stWord(m, a + (Race.includes(vr) ? 0 : stride(vr) * c)), i = index(vr, c);
            if (kind === "b") s.writeMemory(syms[b] + i, [m[a + stride(vr) * c]]);
            else if (kind === "w") {
                s.writeMemory(syms[`${b}Lo`] + i, [v & 0xff]);
                s.writeMemory(syms[`${b}Hi`] + i, [v >> 8]);
            } else s.writeMemory(syms[b] + i, [v & 0xff]);
        }
    }
    const sd = seeds[from - 1];
    s.writeMemory(syms.RcSeed, [sd & 0xff, (sd >> 8) & 0xff, (sd >> 16) & 0xff, (sd >>> 24) & 0xff]);
    // the inputs as runs (build/lgen/inputs.rle, as the test has them): the run holding race frame from - 2,
    // its inputs as read, the frames left in it, the next run's place, and the race's frames left
    const rle = readFileSync("build/lgen/inputs.rle");
    let at = 0, frame = 0;
    while (frame + rle[at] <= from - 2) frame += rle[at], at += 4;
    const next = syms["Inputs"] + at + 4, left = syms.LgFrames - 2 - (from - 2);
    s.writeMemory(syms.RcInput, [...rle.subarray(at + 1, at + 4)]);
    s.writeMemory(syms["test_entry.ileft"], [rle[at] - (from - 2 - frame)]);
    s.writeMemory(syms["test_entry.iptr"], [next & 0xff, next >> 8]);
    s.writeMemory(syms["test_entry.left"], [left & 0xff, left >> 8]);
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
    `${only ? only.length : checker.count} variables`);
console.log(`logic cycles a frame: mean ${mean.toFixed(0)}, max ${sorted[sorted.length - 1] ?? 0} ` +
    `(the test's own loop, about 60, included)`);
console.log(checker.wrong ? `${checker.wrong} frames wrong, the first frame ${checker.firstWrong}`
    : `all ${(stopped ? stopped - 1 : until) - (from > 2 ? from - 1 : 0)} frames match`);
if (stopped) console.log(`stopped at frame ${stopped}`);
process.exit(checker.wrong || stopped ? 1 : 0);
