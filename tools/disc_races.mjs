// The race count's hazards through the game's own disc (Phase 5, step 4): build/game.ssd booted, and each traced
// race (tools/st_trace_logic.py) played on it in turn, every track's reached through its load. A race's
// counter, the generator's state and the drones are put where the last race would have left them (GmRace,
// GmSeed, GmDrone), its scores and sparks as the trace's (LfScores, LfSparks), and the track loaded. The trace's
// forced coins are forced as the tracer forced them, in the A register after the draw; the human's inputs are
// written over the keys' each frame. Then every frame:
// - the logic's whole state against the ST's (tools/logic_compare.mjs, as tools/logic_check.mjs);
// - the screen drawn against the model (tools/render_model.py, from the ST's own draw calls; a race with no model
//   file has only its state checked).
// At a race's end: the race over on the trace's last frame, the counter on one (at most 50), the generator
// kept, and the next track the ST's.
//
// Exit status: 1 if any frame of any race differs, a race ends at the wrong frame, or anything stops, else 0.
//
// Usage (from the repo root, after make game and the traces: tools/disc_races.sh makes the models):
//   node tools/disc_races.mjs [--races 1,2,4,17,50] [--tracks 2,6,5,1,4,7,3,0] [--rotate J] [--show N] [--noscreen]
//   Each race number on each track, unless --rotate J: the tracks once, in turn, the races taken in turn from the
//   Jth on, so one race's hazards are followed by another's (J from 0 to the races' count less 1 covers them all).

import { existsSync, readFileSync } from "node:fs";
import { andy, bootDisc, cycles, ram, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { comparer } from "./logic_compare.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => (args.includes(name) ? args[args.indexOf(name) + 1] : dflt);
const races = option("--races", "1,2,4,17,50").split(",").map(Number);
const tracks = option("--tracks", "2,6,5,1,4,7,3,0").split(",").map(Number);
const show = Number(option("--show", 10));
const screens = !args.includes("--noscreen");

const syms0 = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
const cpu = s._machine.processor;
await runTo(s, syms0["frame_loop.frame_end"], 80000000);    // (the disc copies its banks first)
const banktrace = ram(s, 2, 1)[0];
const peek = (a) => s.readMemory(a, 1)[0];
const word = (a) => peek(a) | (peek(a + 1) << 8);
const NextTrack = [2, 4, 6, 0, 7, 1, 5, 3];                 // G_01D138 (+ 1 in the game's NextTrack1)

// one race on the disc, a line said about it -> 1 if it's wrong
async function race(track, number) {
    const name = `t${track}_r${number}`, label = `track ${track + 1} race ${number}: `;
    const trace = JSON.parse(readFileSync(`build/trace/logic_${name}.json`));
    const frames = trace.frames, last = frames.length - 1, force = trace.force ?? [];
    const syms = symbols(`build/tracks/t${track}.json`);
    const modelPath = `build/check/model_${name}.bin`;
    const model = screens && existsSync(modelPath) ? readFileSync(modelPath) : null;
    const ScreenBytes = syms.PlayBytes + syms.RowBytes;
    const m = frames[1].mem;

    // the state a game would have brought here
    const seed = trace.seed;
    s.writeMemory(syms.GmRace, [number]);
    s.writeMemory(syms.GmSeed, [seed & 255, (seed >> 8) & 255, (seed >> 16) & 255, seed >>> 24]);
    s.writeMemory(syms.GmDrone, [0, 1, 2, 3].map((c) => m[0x1e34c + 2 * c + 1]));
    // (the scores and sparks are Shared's, in both screens: the trace's, as a test build has them)
    const scores = Array.from({ length: 24 }, (_, i) => m[0x1dfa8 + i]);
    const sparks = [];                  // (LfSparks's order: each array's low bytes, then its high bytes if it has them)
    const bytes = (a, st, hi) => Array.from({ length: 8 }, (_, i) => m[a + st * i + (hi ? 0 : 1)]);
    for (const [a, st, words] of [[0x1e070, 2, true], [0x1e080, 2, false], [0x1e090, 2, false], [0x1e0a0, 4, true], [0x1e0a2, 4, true]]) {
        sparks.push(...bytes(a, st, false));
        if (words) sparks.push(...bytes(a, st, true));
    }
    for (const shadow of [false, true]) {
        ram(s, syms.LfScores, 24, shadow).set(scores);
        ram(s, syms.LfSparks, 64, shadow).set(sparks);
    }
    s.writeMemory(syms.LoadWant, [track + 1]);
    const t0 = cycles(s);
    await runTo(s, syms.start, 400000000);
    const fields = Math.round((cycles(s) - t0) / 39936);

    if (number >= 4) {
        await runToAny(s, [[syms["race_setup.tornado_coin"], banktrace]], 8000000);
        if (force.includes("tornado")) cpu.a = 1;
    }
    await runToAny(s, [[syms["pickups_setup.cones_coin"], banktrace]], 8000000);
    if (force.includes("cones")) cpu.a = 10;

    const check = comparer(s, syms, trace, { show, label });
    const played = syms["logic_frame.played"], built = syms["logic_frame.built"], frameEnd = syms["frame_loop.frame_end"];
    const lfFrame = () => word(syms.LfFrame);
    const stops = [[played, banktrace], [built, banktrace], [frameEnd], [syms.load_go]];
    const repeats0 = word(syms.Repeats);
    let screenWrong = 0, firstScreen = null, drawn = 0, problem = null, k = 0, finished = false;
    while (!finished) {
        const at = await runToAny(s, stops, 8000000);
        if (at === played) {
            const f = frames[lfFrame()];
            const b = [0, 0, 0];
            for (const [car, bits] of f?.inputs ?? []) b[car] = bits;
            s.writeMemory(syms.RcInput, b);
        } else if (at === built) {
            k = lfFrame();
            if (k >= 1 && k <= last) check.compare(k);
        } else if (at === frameEnd) {
            const n = word(syms.Frames);
            if (model && (n + 1) * ScreenBytes <= model.length) {
                const shadow = (peek(syms.acccon) & syms.AccX) !== 0;
                const got = ram(s, syms.HudAddr, ScreenBytes, shadow), exp = model.subarray(n * ScreenBytes, (n + 1) * ScreenBytes);
                let bad = 0;
                for (let i = 0; i < ScreenBytes; i++) if (got[i] !== exp[i]) bad++;
                drawn++;
                if (bad) {
                    screenWrong++;
                    firstScreen ??= `${n} (${bad} bytes)`;
                }
            }
            if (k >= last) finished = true;
        } else {
            problem = `over at frame ${k}, the trace's last ${last}`;
            finished = true;
        }
    }

    // the race's end, as it left it for the next
    const rcOver = andy(s, syms.RcOver, 1)[0];
    if (!problem) {
        const want = NextTrack[track] + 1, race1 = Math.min(number + 1, 50), sd = check.seeds[last];
        const got = s.readMemory(syms.GmSeed, 4), gseed = (got[0] | (got[1] << 8) | (got[2] << 16) | (got[3] << 24)) >>> 0;
        const left = [];
        if (!rcOver) left.push("the race not over");
        if (peek(syms.LoadWant) !== want) left.push(`next track ${peek(syms.LoadWant)}, not ${want}`);
        if (peek(syms.GmRace) !== race1) left.push(`race counter ${peek(syms.GmRace)}, not ${race1}`);
        if (gseed !== sd) left.push(`the generator &${gseed.toString(16)}, not &${sd.toString(16)}`);
        if (left.length) problem = left.join(", ");
    }
    const reps = ((word(syms.Repeats) - repeats0) & 0xffff) - 50;    // (less the start's 50-field pause)
    console.log(`${label}loaded in ${fields} fields; ${last} frames: state ${check.wrong ? `WRONG in ${check.wrong}, the first ${check.firstWrong}` : "exact"}; ` +
        `${model ? `screen ${screenWrong ? `WRONG in ${screenWrong}, the first ${firstScreen}` : `exact in ${drawn}`}` : "no model"}; ` +
        `${reps} fields repeated${problem ? `; ${problem}` : ""}`);
    return check.wrong || screenWrong || problem ? 1 : 0;
}

let bad = 0, done = 0;
const rotate = option("--rotate", null);
const list = rotate === null ? races.flatMap((number) => tracks.map((track) => [track, number]))
    : tracks.map((track, i) => [track, races[(i + Number(rotate)) % races.length]]);
for (const [track, number] of list) {
    bad += await race(track, number);
    done++;
}
console.log(bad ? `${bad} of ${done} races wrong` : `all ${done} races exact`);
process.exit(bad ? 1 : 0);
