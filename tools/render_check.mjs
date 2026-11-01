// The renderer test in headless jsbeeb (a Master 128): each frame's work timed with the real IRQ, and the
// screen it drew (the HUD's row and the play area) checked against the model (tools/render_model.py).
//
// Each frame runs from frame_loop.frame_top (the screen to draw chosen) to frame_loop.frame_end (the cars
// drawn): its cycles are the erase, the trace's read and the plot, with any vsync interrupt that lands in
// it. The vsyncs between frame_tops are the TV frames each drawn frame took.
//
// Usage (from the repo root, after make):
//   node tools/render_check.mjs [--frames N] [--model build/check/model_t5.bin] [--dump N]
//       --dump N: write frame N's drawn and expected screens to build/check/frameN-{bbc,model}.bin
//       --json PATH: write each frame's cycles to PATH: work, and its parts (trace: the test's own reading
//           of the race and its HUD events, which the game's logic will replace)

import { readFileSync, writeFileSync } from "node:fs";
import { bootDisc, cycles, ram, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => {
    const i = args.indexOf(name);
    return i >= 0 ? args[i + 1] : dflt;
};
const syms = symbols();
const traceFrames = syms["TraceFrames"];
const want = Number(option("--frames", traceFrames));
const modelPath = option("--model", "build/check/model_t5.bin");
const model = modelPath === "none" ? null : readFileSync(modelPath);
const dump = Number(option("--dump", -1));
const HudAddr = syms["HudAddr"], ScreenBytes = syms["PlayBytes"] + syms["RowBytes"], AccX = syms["AccX"];
const TvFrame = 39936;

const s = await bootDisc();
const peek = (a) => s.readMemory(a, 1)[0];
const work = [], tv = [];
const parts = { erase: [], read: [], plot: [], hud: [], trace: [] };
let wrong = 0, firstWrong = null, lastVsyncs = null;

for (let n = 0; n < want; n++) {
    await runTo(s, syms["frame_loop.frame_top"]);
    const t0 = cycles(s);
    const v = peek(syms["vsyncs"]);
    if (lastVsyncs !== null) tv.push((v - lastVsyncs) & 255);
    lastVsyncs = v;
    await runTo(s, syms["frame_loop.erased"]);
    const t1 = cycles(s);
    await runTo(s, syms["frame_loop.objects"]);
    parts.trace.push(cycles(s) - t1);
    await runTo(s, syms["frame_loop.read"]);
    const t2 = cycles(s);
    await runTo(s, syms["frame_loop.plotted"]);
    const t3 = cycles(s);
    await runTo(s, syms["frame_loop.frame_end"]);
    work.push(cycles(s) - t0);
    parts.erase.push(t1 - t0);
    parts.read.push(t2 - t1);
    parts.plot.push(t3 - t2);
    parts.hud.push(cycles(s) - t3);

    const frame = peek(syms["Frames"]) | (peek(syms["Frames"] + 1) << 8);
    const shadow = (peek(syms["acccon"]) & AccX) !== 0;
    const drawn = ram(s, HudAddr, ScreenBytes, shadow);
    if (model) {
        const i = frame % traceFrames;
        const exp = model.subarray(i * ScreenBytes, (i + 1) * ScreenBytes);
        let bad = 0;
        for (let k = 0; k < ScreenBytes; k++) if (drawn[k] !== exp[k]) bad++;
        if (bad) {
            wrong++;
            if (firstWrong === null) firstWrong = { frame, bad };
        }
        if (frame === dump) {
            writeFileSync(`build/check/frame${frame}-bbc.bin`, drawn);
            writeFileSync(`build/check/frame${frame}-model.bin`, exp);
        }
    }
}

if (option("--json", null)) writeFileSync(option("--json"), JSON.stringify({ work, ...parts }));
const sorted = [...work].sort((a, b) => a - b);
const pct = (p) => sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
const mean = work.reduce((a, b) => a + b, 0) / work.length;
const hist = {};
for (const t of tv) hist[t] = (hist[t] || 0) + 1;
console.log(`frames ${work.length}: work cycles mean ${mean.toFixed(0)}, median ${pct(50)}, 90% ${pct(90)}, ` +
    `99% ${pct(99)}, max ${sorted[sorted.length - 1]}; over a TV frame (${TvFrame}): ` +
    `${work.filter((t) => t > TvFrame).length}`);
if (args.includes("--readframes")) {
    const top = parts.read.map((c, i) => [c, i]).filter(([c]) => c > 1000);
    console.log(`read over 1000 cycles: ${top.map(([c, i]) => `${i}:${c}`).join(" ")}`);
}
if (args.includes("--hudframes")) {
    const top = parts.hud.map((c, i) => [c, i]).filter(([c]) => c > 500);
    console.log(`HUD over 500 cycles: ${top.map(([c, i]) => `${i}:${c}`).join(" ")}`);
}
for (const [k, v] of Object.entries(parts)) {
    const m = v.reduce((a, b) => a + b, 0) / v.length;
    console.log(`  ${k}: mean ${m.toFixed(0)}, max ${Math.max(...v)}`);
}
console.log(`TV frames per drawn frame: ${JSON.stringify(hist)}`);
if (model) console.log(wrong ? `model: ${wrong} frames wrong, the first frame ${firstWrong.frame} (${firstWrong.bad} bytes)`
    : `model: all ${work.length} frames match`);
process.exit(0);
