// The race logic's draw calls against the ST's (Phase 4, step 8): each frame, what build/logic.ssd's logic
// draws (the barriers F_014A80 and gates F_014A04 as it noted them, the slots' sprites F_0149B4, the cars
// F_01519C and explosions F_0152E0 in draw order, the sparks F_014B1C, the banner F_0148BE, the tornado and the
// helicopter F_01440E/F_0144AA, as their state says) against the calls
// tools/st_trace_objects.py logged from the ST in the same race. The renderer is driven by these.
//
// Exit status: 1 if any frame's calls differ, else 0.
//
// Usage (from the repo root, after make logic): node tools/logic_draws.mjs [--race build/trace/race_t0_r0_script.json]
//     [--until N] [--show N]

import { readFileSync } from "node:fs";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => (args.includes(name) ? args[args.indexOf(name) + 1] : dflt);
const syms = symbols("build/logic.json");
const race = JSON.parse(readFileSync(option("--race", "build/trace/race_t0_r0_script.json")));
const byFrame = new Map(race.map((f) => [f.frame, f]));
const until = Number(option("--until", race[race.length - 1].frame));
const show = Number(option("--show", 10));
const s = await bootDisc("build/logic.ssd");
const peek = (a) => s.readMemory(a, 1)[0];
const word = (n, i) => peek(syms[`${n}Lo`] + i) | (peek(syms[`${n}Hi`] + i) << 8);
const signed = (v) => (v >= 32768 ? v - 65536 : v);

// the ST's calls, as strings, in order (each call's own arguments only)
function st(f) {
    const out = [];
    for (const [n, w] of f.calls) {
        if (n === "barrier") out.push(`barrier ${w[0]} ${w[1]}`);
        else if (n === "gate") out.push(`gate ${w[0]} ${w[1]}`);
        else if (n === "tornado") out.push(`tornado ${w[0]} ${signed(w[1])} ${signed(w[2])}`);
        else if (n === "slot") out.push(`slot ${w[0]} ${w[1]} ${w[2]}`);
        else if (n === "car") out.push(`car ${w[0]}`);
        else if (n === "explosion") out.push(`explosion ${w[0]} ${w[1]}`);
        else if (n === "spark") out.push(`spark ${w[0]}`);
        else if (n === "small") out.push(`banner ${w[0]} ${w[1]} ${w[2]}`);
        else if (n === "heli2" || n === "heli3") out.push(`${n} ${w[0]} ${signed(w[1])} ${signed(w[2])}`);
    }
    return out;
}

// the BBC's, from the logic's state after its frame
function bbc() {
    const out = [];
    for (let i = 0; i < peek(syms.RcHazDrawCount); i++) {     // a gate's or barrier's screen offset: y * 160 + column * 4
        const what = peek(syms.RcHazDrawWhat + i), j = peek(syms.RcHazDrawIdx + i);
        if (what & 0x80) out.push(`barrier ${what & 0x7f} ${peek(syms.BarY + j) * 160 + peek(syms.BarCol + j) * 4}`);
        else out.push(`gate ${what} ${peek(syms.GateY + j) * 160 + peek(syms.GateCol + j) * 4}`);
    }
    for (let i = 0; i < peek(syms.RcSlotCount); i++)
        out.push(`slot ${peek(syms.RcSlotSprite + i)} ${peek(syms.RcSlotX + i)} ${peek(syms.RcSlotY + i)}`);
    for (let k = 0; k < 4; k++) {
        const c = peek(syms.RcOrder + k);
        const e = peek(syms.RcExplFrame + c);
        out.push(e === 0xff ? `car ${c}` : `explosion ${c} ${e}`);
    }
    for (let i = 0; i < 8; i++) if (peek(syms.RcSparkFrame + i) !== 42) out.push(`spark ${i}`);
    if (peek(syms.RcBannerOn) === 1) out.push(`banner ${peek(syms.RcBannerFrame)} ${syms.GenBannerX ?? syms.LgBannerX} ${syms.GenBannerY ?? syms.LgBannerY}`);
    if (peek(syms.RcTornado)) out.push(`tornado ${peek(syms.RcTorFrame)} ${signed(word("RcTorX", 0))} ${signed(word("RcTorY", 0))}`);
    if (peek(syms.RcHeliDrawn))
        out.push(`${peek(syms.RcHeliVariant) & 2 ? "heli3" : "heli2"} ${peek(syms.RcHeliFrame)} ${signed(word("RcHeliX", 0))} ${signed(word("RcHeliY", 0))}`);
    return out;
}

await runTo(s, syms["test_entry.setup_done"]);
let wrong = 0, shown = 0, first = null, n = 0;
for (let k = 2; k <= until; k++) {
    try {
        await runTo(s, syms["test_entry.frame_done"], 2000000);
    } catch {
        console.log(`frame ${k}: the BBC never finished it`);
        wrong++;
        break;
    }
    const f = byFrame.get(k);
    if (!f) continue;
    n++;
    const a = st(f).join("; "), b = bbc().join("; ");
    if (a !== b) {
        wrong++;
        first ??= k;
        if (shown++ < show) console.log(`frame ${k}:\n  ST  ${a}\n  BBC ${b}`);
    }
}
console.log(wrong ? `${wrong} of ${n} frames' calls differ, the first ${first}` : `all ${n} frames' calls match`);
process.exit(wrong ? 1 : 0);
