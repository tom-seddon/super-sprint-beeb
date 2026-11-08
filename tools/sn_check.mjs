// The sound at the chip (Phase 4, step 10): the game built from the logic (make beeb TRACE=logic0) plays the traced
// race in headless jsbeeb with its SN76489's writes captured; the writes are cut into fields at each vsync's
// sound_irq and the chip's state rebuilt per field (each channel's period and attenuation, the noise's). Each
// effect the ST started in the race (tools/st_trace_sound.py's capture) is then looked for on its channel: its
// fields (build/lgen/sound.6502, tools/sound_gen.py's) in order, from within 3 fields after the vsync that ended
// its frame. A tone field is its period and attenuation; a noise field, the noise's control and attenuation.
// The sweep that isn't the ST's (back, D16) is looked for the same way at each wreck's blink (collide_car.sweep),
// on its car's channel.
//
// Exit status: 1 if any effect isn't found, else 0.
//
// Usage (from the repo root, after make beeb TRACE=logic0): node tools/sn_check.mjs [--fields OUT.json] [--capture C.json]
//     --capture: the ST's capture of the race built (default build/trace/sound_t0_r0.json; the hazard race,
//         TRACE=logic4: build/trace/sound_t4_r17_hz.json)
//     --fields: each field's chip state, for tools/sound_wav.py to render (what the BBC plays, to listen to)

import { readFileSync, writeFileSync } from "node:fs";
import { bootDisc, cycles, runTo, symbols } from "./jsbeeb.mjs";

const syms = symbols();
const capture = JSON.parse(readFileSync(process.argv.includes("--capture") ? process.argv[process.argv.indexOf("--capture") + 1] : "build/trace/sound_t0_r0.json"));
const Names = ["start0", "start1", "start2", "bounce", "bump", "slow", "skid", "wrench", "bonus", "tornado", "wreck", "back"];
const Threshold = { bounce: 1, bump: 2, slow: 1, skid: 1, wrench: 4, bonus: 4, tornado: 3 };

// the effects' fields, from sound.6502: .Fx_<name> then EQUB lines of 3 bytes a field
const fx = {};
let cur = null;
const src = readFileSync("build/lgen/sound.6502", "utf8");
for (const line of src.split("\n")) {
    const m = /^\.Fx_(\w+)/.exec(line);
    if (m) { cur = fx[m[1]] = []; continue; }
    if (cur && /^\s+EQUB &/.test(line)) {
        const b = line.trim().slice(5).split(",").map((v) => parseInt(v.trim().slice(1), 16));
        for (let i = 0; i < b.length; i += 3)
            cur.push({ n: b[i] | ((b[i + 1] & 3) << 8), att: (b[i + 1] >> 2) & 15, noise: b[i + 1] & 0x40 ? (b[i + 2] & 3) | 4 : null, natt: b[i + 2] >> 4 });
        cur = null;
    }
}

const s = await bootDisc();
const cpu = s._machine.processor;
const chip = s._soundChip;
const irqAt = [];
const blinks = [];                      // each blink's start: its car and the frame
const frameEnd = [];                     // per drawn frame: the vsyncs before its end
cpu.debugInstruction.add((pc) => {
    if (pc === syms.sound_irq) irqAt.push(cycles(s));
    else if (pc === syms["collide_car.sweep"]) blinks.push({ name: "back", channel: cpu.x, frame: frameEnd.length });
    return false;
});
await runTo(s, syms["frame_loop.frame_top"]);
chip.startCapture();
const c0 = cycles(s);
const base = irqAt.length;               // (the vsyncs before the capture aren't fields)
const last = capture.frames[capture.frames.length - 1].frame;
for (let k = 0; k < last; k++) {
    await runTo(s, syms["frame_loop.frame_end"]);
    frameEnd.push(irqAt.length - base);
}
const writes = chip.stopCapture();
// the chip's write cycles are the CPU's (MEASURED: each field's first write about 220 cycles after its IRQ)
const fields = [];
const st = { n: [0, 0, 0], att: [15, 15, 15], noise: null, natt: 15 };
let latch = 0, w = 0;
const irqs = irqAt.filter((t) => t >= c0).map((t) => t - c0);
for (let i = 0; i < irqs.length; i++) {
    const end = i + 1 < irqs.length ? irqs[i + 1] : Infinity;
    while (w < writes.length && writes[w].cycle - c0 < end) {
        const v = writes[w++].value;
        if (v & 0x80) {
            latch = (v >> 5) & 3;
            const typ = (v >> 4) & 1;
            if (latch === 3) { if (typ) st.natt = v & 15; else st.noise = v & 7; }
            else if (typ) st.att[latch] = v & 15;
            else st.n[latch] = (st.n[latch] & 0x3f0) | (v & 15);
        } else if (latch < 3) st.n[latch] = (st.n[latch] & 15) | ((v & 0x3f) << 4);
    }
    fields.push({ n: [...st.n], att: [...st.att], noise: st.noise, natt: st.natt });
}

if (process.argv.includes("--fields")) writeFileSync(process.argv[process.argv.indexOf("--fields") + 1], JSON.stringify(fields));

// each effect the ST started, and each blink's sweep, looked for
let found = 0, missing = 0;
for (const x of [...capture.starts, ...blinks]) {
    const ch = x.channel % 3;
    const started = Threshold[x.name] === undefined || x.prio[ch] < Threshold[x.name];
    if (!started || !fx[x.name]) continue;
    const frameIndex = x.frame;          // the drawn frames start at the set-up's (frame 0)
    const from = frameEnd[frameIndex] ?? 0;
    const want = fx[x.name];
    let ok = false;
    for (let f0 = from - 1; f0 <= from + 3 && !ok; f0++) {
        ok = want.every((e, i) => {
            const g = fields[f0 + i];
            if (!g) return false;
            // a noise field: the SN has one noise channel, the loudest effect's (D11), so where two overlap the
            // quieter's is played by the louder's: its own, or one louder
            if (e.noise !== null) return g.att[ch] === 15 && ((g.noise === e.noise && g.natt === e.natt) || g.natt < e.natt);
            return g.att[ch] === e.att && (e.att === 15 || g.n[ch] === e.n);
        });
    }
    if (ok) found++;
    else {
        missing++;
        if (missing <= 5) console.log(`frame ${x.frame}: ${x.name} on channel ${ch} not found in fields ${from - 1}-${from + 3 + want.length}`);
    }
}
console.log(`${irqs.length} fields, ${writes.length} chip writes; the ST's started effects and ${blinks.length} blinks' sweeps: ${found} found, ${missing} not`);
process.exit(missing ? 1 : 0);
