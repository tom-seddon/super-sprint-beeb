// Where the game's cycles go, by label: each instruction's cycles from frame_top to frame_end charged to the
// nearest label at or below it in what's paged there (main RAM's, or the bank ROMSEL selects: the background's,
// the cars', the fourth (the logic's, unprefixed) or the objects'), with the real IRQ. Prints the mean a frame
// over the race and over its slowest frames, and how many frames took over a TV frame. Finer than
// render_profile.mjs's regions: it shows set-up against loops (a routine's local labels each get their own
// line; --routines adds them up by routine). In a game drawn from the logic, the race's start (its 50-field
// pause, logic_frame.wait) is one frame of about 2 million cycles: it's among the slowest, adding about
// 6,600 a frame to logic_frame there.
//
// Usage (from the repo root, after make beeb, e.g. TRACE=logic4):
//     node tools/game_profile.mjs [--worst N] [--top N] [--routines]
//     --worst N: the N slowest frames (default 300); --top N: the N costliest lines each (default 60)

import { readFileSync } from "node:fs";
import { bootDisc, cycles, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => (args.includes(name) ? Number(args[args.indexOf(name) + 1]) : dflt);
const worstN = option("--worst", 300), topN = option("--top", 60), routines = args.includes("--routines");
const syms = symbols();

// each bank's labels, and main RAM's (MainCode, Shared, and the loader's section), from the symbol dump's sections
const kinds = { BgBank: "bg", CarsBank: "cars", TraceBank: "", ObjBank: "obj", MainCode: "main", Shared: "main", Sprint: "main" };
const lists = {};
for (const sec of JSON.parse(readFileSync("build/sprint.json")).assemblies[1].sections) {
    const k = kinds[sec.name];
    if (k === undefined) continue;
    lists[k] ??= [];
    for (const [n, v] of Object.entries(sec.labels || {}))
        if (/^[a-z_0-9.]+$/.test(n) && typeof v.value === "number") lists[k].push([v.value, n]);
}
for (const l of Object.values(lists)) l.sort((a, b) => a[0] - b[0]);
const near = (pc, l) => {
    let lo = 0, hi = l.length - 1, best = "?";
    while (lo <= hi) {
        const m = (lo + hi) >> 1;
        if (l[m][0] <= pc) { best = l[m][1]; lo = m + 1; } else hi = m - 1;
    }
    return routines ? best.replace(/\..*$/, "") : best;
};

const s = await bootDisc();
const cpu = s._machine.processor;
const peek = (a) => s.readMemory(a, 1)[0];
await runTo(s, syms["frame_loop.frame_top"]);
const bank = {};
for (const [k, b] of [["bg", "bankbg"], ["cars", "bankcars"], ["", "banktrace"], ["obj", "bankobj"]]) bank[peek(syms[b])] = k;
const cache = new Map();
const nameOf = (pc) => {
    const key = pc < 0x8000 ? pc : pc + ((cpu.romsel & 0x8f) << 16);
    let v = cache.get(key);
    if (v) return v;
    if (pc >= 0xC000) v = "(MOS)";
    else if (pc < 0x8000) v = near(pc, lists.main);
    else if (pc < 0x9000 && (cpu.romsel & 0x80)) v = "(ANDY)";
    else { const b = bank[cpu.romsel & 15]; v = b === undefined ? "(bank?)" : (b ? b + ":" : "") + near(pc, lists[b]); }
    cache.set(key, v);
    return v;
};

let current = null, last = 0, counts = null;
cpu.debugInstruction.add((pc) => {
    const now = cycles(s);
    if (counts && current) counts[current] = (counts[current] || 0) + now - last;
    current = nameOf(pc);
    last = now;
    return false;
});
const per = [];
for (let n = 0; n < syms["TraceFrames"]; n++) {
    await runTo(s, syms["frame_loop.frame_top"]);
    counts = {};
    const t0 = cycles(s);
    await runTo(s, syms["frame_loop.frame_end"]);
    per.push([cycles(s) - t0, counts]);
    counts = null;
}
function report(list, title) {
    const sum = {};
    for (const [, c] of list) for (const [n, v] of Object.entries(c)) sum[n] = (sum[n] || 0) + v;
    console.log(`${title}: ${list.length} frames, ${(list.reduce((a, [t]) => a + t, 0) / list.length).toFixed(0)} cycles a frame`);
    for (const [n, v] of Object.entries(sum).sort((a, b) => b[1] - a[1]).slice(0, topN))
        console.log(`  ${n.padEnd(34)} ${(v / list.length).toFixed(0).padStart(6)}`);
}
report(per, "the race");
report([...per].sort((a, b) => b[0] - a[0]).slice(0, worstN), `the slowest ${worstN}`);
console.log(`over a TV frame (39936): ${per.filter(([t]) => t > 39936).length}`);
process.exit(0);
