// The sound's starters against the ST's (Phase 4, step 10): build/logic.ssd replays the traced race, and each
// frame the BBC logic's calls of its effect starters (sound.6502's log: the effect, the channel, whether it
// started) are compared with the ST's in the same race (tools/st_trace_sound.py's capture: each conditional
// starter's call, its channel, the priorities it found, and the wreck's and the helicopter's).
//
// Not the ST's (D16): the helicopter's going (F_012D38: the engine on two channels) isn't started on the BBC, so
// the ST's are left out; and the BBC's sweep as a wrecked car is seen again (back) is checked apart: one where
// each wreck's wait reaches CueFrames (collide_car.sweep, the blink's first frame), on its car's channel, and none
// anywhere else; and each car whose wait is CueFrames, read from its state, is one of them.
//
// Which effect and which channel, in which frame, follow from the logic and must match exactly. Whether it
// started depends on the channel's priority, which the ST's driver changes at its own 83 Hz ticks and the
// BBC at the next vsync: those are counted apart, as the timing's difference, not a fault.
//
// Exit status: 1 if any frame's calls (effect, channel) differ, or a blink's sweep's, else 0.
//
// Usage (from the repo root, after make logic): node tools/sound_check.mjs [--capture build/trace/sound_t0_r0.json]

import { readFileSync } from "node:fs";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const args = process.argv.slice(2);
const capture = JSON.parse(readFileSync(args.includes("--capture") ? args[args.indexOf("--capture") + 1] : "build/trace/sound_t0_r0.json"));
const syms = symbols("build/logic.json");
const Names = ["start0", "start1", "start2", "bounce", "bump", "slow", "skid", "wrench", "bonus", "tornado", "wreck", "back"];
const Threshold = { bounce: 1, bump: 2, slow: 1, skid: 1, wrench: 4, bonus: 4, tornado: 3 };
const st = new Map();                    // frame -> [{name, ch, started}]
for (const s of capture.starts) {
    if (s.name === "heli_gone") continue;   // (not the BBC's: D16)
    const name = s.name;
    const ch = s.channel % 3;
    const started = Threshold[name] === undefined || s.prio[ch] < Threshold[name];
    if (!st.has(s.frame)) st.set(s.frame, []);
    st.get(s.frame).push({ name, ch, started });
}
const s = await bootDisc("build/logic.ssd");
const peek = (a) => s.readMemory(a, 1)[0];
const cpu = s._machine.processor;
let blinks = [];                        // this frame's sweeps started at collide_car.sweep: their cars
cpu.debugInstruction.add((pc) => {
    if (pc === syms["collide_car.sweep"]) blinks.push(cpu.x);
    return false;
});
await runTo(s, syms["test_entry.setup_done"]);
let wrong = 0, calls = 0, startedDiffer = 0, backs = 0, cued = 0;
blinks = [];
const last = capture.frames[capture.frames.length - 1].frame - 1;   // (the trace's last race frame)
for (let k = 2; k <= last; k++) {
    try {
        await runTo(s, syms["test_entry.frame_done"], 2000000);
    } catch {
        console.log(`frame ${k}: the BBC never finished it`);
        wrong++;
        break;
    }
    const bbc = [];
    for (let i = 0; i < peek(syms.SndLogCount); i++) {
        const fx = peek(syms.SndLogFx + i), ch = peek(syms.SndLogCh + i);
        // fx_car logs the effect | started << 7; fx_two (the wreck, the helicopter gone: the engine, &81)
        // logs it | &80. The engine's and silence's other calls (&80, &81 from fx_car) aren't the ST's
        // conditional starters'.
        const id = fx & 0x7f;
        const name = fx === 0x81 ? "engine2" : id < Names.length ? Names[id] : "";
        bbc.push({ name, ch, started: !!(fx & 0x80) });
    }
    // the BBC's sweeps: one at each blink's start, on its car's channel, always started; and the cars whose
    // wait is CueFrames now (read from the state, apart from the label) the same ones
    const swept = bbc.filter((c) => c.name === "back").map((c) => `ch${c.ch} ${c.started}`).join(", ");
    const want = blinks.map((car) => `ch${car % 3} true`).join(", ");
    const waits = [0, 1, 2, 3].filter((car) => peek(syms.RcState + car) && peek(syms.RcBounce + car) === syms.CueFrames);
    backs += blinks.length;
    cued += waits.length;
    const at = blinks.join(), seen = waits.join();
    blinks = [];
    if (swept !== want || at !== seen) {
        wrong++;
        if (wrong <= 10) console.log(`frame ${k}: waits at CueFrames ${seen || "-"}, sweeps started ${at || "-"}, wanted ${want || "-"}; swept ${swept || "-"}`);
        continue;
    }
    // the ST's conditional starters and the wreck's
    const mine = bbc.filter((c) => c.name && !c.name.startsWith("start") && c.name !== "back");
    const theirs = st.get(k) ?? [];
    const key = (c) => `${c.name} ch${c.ch}`;
    const a = theirs.map(key).join(", "), b = mine.map(key).join(", ");
    calls += theirs.length;
    if (a !== b) {
        wrong++;
        if (wrong <= 10) console.log(`frame ${k}: ST ${a || "-"}; BBC ${b || "-"}`);
        continue;
    }
    theirs.forEach((t, i) => {
        if (t.started !== mine[i].started) {
            startedDiffer++;
            if (startedDiffer <= 5) console.log(`frame ${k}: ${key(t)} started on the ST ${t.started}, the BBC ${mine[i].started}`);
        }
    });
}
console.log(`${calls} starter calls on the ST; ${wrong ? `${wrong} frames' calls differ` : "every frame's calls match the BBC's"};` +
    ` ${startedDiffer} differ in whether they started (the priorities' timing); ${backs} blinks, each swept (${cued} found by the waits)`);
process.exit(wrong ? 1 : 0);
