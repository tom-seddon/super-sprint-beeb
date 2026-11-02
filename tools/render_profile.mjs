// Where the renderer test's cycles go: each frame's cycles from frame_top to frame_end, split by code
// region (the erase's loop and the rest, the plot's set-up, bands, fast loop, slow loop and its columns),
// in headless jsbeeb with the real IRQ. Prints the mean over the race and over its worst frames.
//
// Usage (from the repo root, after make beeb): node tools/render_profile.mjs [--worst 20] [--list N]
//     --list N: also each of the N worst frames on its own, its number and regions

import { bootDisc, cycles, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const worstN = Number(args[args.indexOf("--worst") + 1] || 20);
const listN = args.includes("--list") ? Number(args[args.indexOf("--list") + 1]) : 0;
const syms = symbols();
const s = await bootDisc();
const cpu = s._machine.processor;
const peek = (a) => s.readMemory(a, 1)[0];
const bank = {};
const frames = syms["TraceFrames"];

// the regions: [name, bank ("bg", "cars" or null for main RAM), start, end (exclusive)]
const L = (n) => syms[n];
const regions = [
    ["erase loop", "bg", L("erase_cars.blocks"), L("erase_cars.back") + 2],
    ["erase rest", "bg", L("erase_cars"), L("EraseBack") + 6],
    ["plot car set-up", "cars", L("plot_car"), L("plot_car.crossing")],
    ["plot fast loop", "cars", L("plot_car.blocks"), L("plot_car.back") + 2],
    ["plot slow loop", "cars", L("slowcol.loop"), L("slowcol.loopend") + 4],
    ["plot slow columns", "cars", L("slowcol"), L("PrioClass")],
    ["plot classify", "cars", L("plot_car.classify"), L("plot_car.draw")],
    ["movers loop", "obj", L("objmov.mov_plot.blocks"), L("objmov.mov_plot.back") + 2],
    ["tornado", "obj", L("mov_tornado"), 0xC000],
    ["movers rest", "obj", L("objmov.mov_plot"), 0xC000],
    ["helicopter loop", "heli", L("helimov.mov_plot.blocks"), L("helimov.mov_plot.back") + 2],
    ["helicopter rest", "heli", L("helimov.mov_plot"), L("walls") ?? 0xC000],
    ...(L("walls") ? [["logic (fourth bank)", "heli", L("walls"), 0xC000]] : []),
    ["objects: copy loops", null, L("obj_bands.p0blocks"), L("CopyBack")],
    ["objects: bands", null, L("obj_bands"), L("CopyBack")],
    ["objects: priority runs", null, L("obj_runs"), L("obj_runs") + 300],
    ["objects (main RAM)", null, L("obj_events"), L("mul_s16") ?? L("obj_events") + 2000],
    ...(L("mul_s16") ? [["sound IRQ (main RAM)", null, L("sound_irq"), L("sound_irq") + 400],
        ["logic (main RAM)", null, L("mul_s16"), 0x2a00]] : []),
    ["plot bands", "cars", L("plot_car.crossing"), L("slowcol")],
    ["main RAM", null, 0, 0x3000],
];
const regionOf = (pc) => {
    for (const [name, b, lo, hi] of regions) {
        if (pc < lo || pc >= hi) continue;
        if (b === null || (cpu.romsel & 15) === bank[b]) return name;
    }
    return "other";
};

let current = null, last = 0, counts = null;
cpu.debugInstruction.add((pc) => {
    const now = cycles(s);
    if (counts && current) counts[current] = (counts[current] || 0) + now - last;
    current = regionOf(pc);
    last = now;
    return false;
});

await runTo(s, syms["frame_loop.frame_top"]);
bank.bg = peek(syms["bankbg"]);
bank.cars = peek(syms["bankcars"]);
bank.obj = peek(syms["bankobj"]);
bank.heli = peek(syms["banktrace"]);
const perFrame = [];
for (let n = 0; n < frames; n++) {
    await runTo(s, syms["frame_loop.frame_top"]);
    counts = {};
    const t0 = cycles(s);
    await runTo(s, syms["frame_loop.frame_end"]);
    perFrame.push({ n, total: cycles(s) - t0, counts });
    counts = null;
}

const names = [...regions.map((r) => r[0]), "other"];
const show = (label, set) => {
    const mean = (f) => set.reduce((a, x) => a + f(x), 0) / set.length;
    console.log(`${label} (${set.length} frames): total ${mean((x) => x.total).toFixed(0)}`);
    for (const k of names) {
        const m = mean((x) => x.counts[k] || 0);
        if (m) console.log(`  ${k.padEnd(18)} ${m.toFixed(0).padStart(6)}`);
    }
};
show("all", perFrame);
show("worst", [...perFrame].sort((a, b) => b.total - a.total).slice(0, worstN));
for (const f of [...perFrame].sort((a, b) => b.total - a.total).slice(0, listN)) {
    const parts = names.filter((k) => f.counts[k] > 500).map((k) => `${k} ${f.counts[k]}`);
    console.log(`frame ${f.n}: ${f.total}: ${parts.join(", ")}`);
}
process.exit(0);
