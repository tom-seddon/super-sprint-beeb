// Where the race logic's cycles go (build/logic.ssd, the traced race): every instruction's cycles charged to
// the routine it's in (the nearest top-level routine label at or below its address), from each frame's
// start to its end. Prints each routine's mean a frame.
//
// Usage (from the repo root, after make logic): node tools/logic_profile.mjs [--frames N] [--worst N]
//     --worst N: the same over the N frames that took longest

import { bootDisc, cycles, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => (args.includes(name) ? Number(args[args.indexOf(name) + 1]) : dflt);
const syms = symbols("build/logic.json");
// routines: the top-level labels in lower case (tables are CamelCase), from the symbols
const routines = Object.entries(syms)
    .filter(([n, v]) => /^[a-z_0-9]+$/.test(n) && typeof v === "number" && v >= 0x1100 && !n.startsWith("test_entry"))
    .map(([n, v]) => [v, n]).sort((a, b) => a[0] - b[0]);
const routineOf = (pc) => {
    let lo = 0, hi = routines.length - 1, best = "?";
    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (routines[mid][0] <= pc) { best = routines[mid][1]; lo = mid + 1; } else hi = mid - 1;
    }
    return best;
};

const s = await bootDisc("build/logic.ssd");
const cpu = s._machine.processor;
const frames = Number(option("--frames", syms.LgFrames - 2)), worstN = Number(option("--worst", 0));   // (every race frame)
let current = null, last = 0, counts = null;
cpu.debugInstruction.add((pc) => {
    const now = cycles(s);
    if (counts && current) counts[current] = (counts[current] || 0) + now - last;
    current = routineOf(pc);
    last = now;
    return false;
});
await runTo(s, syms["test_entry.setup_done"]);
const per = [];
for (let k = 0; k < frames; k++) {
    counts = {};
    const t0 = cycles(s);
    await runTo(s, syms["test_entry.frame_done"]);
    per.push([cycles(s) - t0, counts]);
}
function report(list, title) {
    const sum = {};
    for (const [, c] of list) for (const [n, v] of Object.entries(c)) sum[n] = (sum[n] || 0) + v;
    const total = list.reduce((a, [t]) => a + t, 0) / list.length;
    console.log(`${title}: ${list.length} frames, ${total.toFixed(0)} cycles a frame`);
    for (const [n, v] of Object.entries(sum).sort((a, b) => b[1] - a[1]).slice(0, 25))
        console.log(`  ${n.padEnd(28)} ${(v / list.length).toFixed(0).padStart(6)}`);
}
report(per, "the race");
if (worstN) report([...per].sort((a, b) => b[0] - a[0]).slice(0, worstN), `the worst ${worstN}`);
