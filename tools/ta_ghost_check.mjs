// Time attack's ghost (docs/brief-timeattack-2026-11-10.md, step 4; src/ghost.6502) against a model, every frame:
// each track's race on the disc driven by the autopilot (tools/ta_pilot.mjs) for FRAMES frames. The player's
// records logged each frame (logic_frame.built); each lap that becomes the ghost (GhLapEnd 2 at ghost_frame) keeps
// its frames' records, from its crossing's frame to the one before the next; each frame after ghost_frame (the
// frame loop's .objects) the draw list against the model's: the player's record and the ghost's, the ghost's lap's
// record k (k the frames since this lap started, the crossing's frame 0) or, its lap done, its first (D43), as car 3
// unless an explosion, first in the list (the player's drawn over it). So the recording's coding and the
// playback's decoding are checked together: what's drawn is what the player was.
//
// Exit status: 1 if any frame's list differs, or no ghost is drawn on any track; else 0.
//
// Each track raced PASSES times (default 2) on the one machine: a race starts with the ghost its track's last race
// saved (step 5: GHOSTn, written at the next load), its lap 1 with it from the first frame and the HUD's ghost time
// its; after each race, GHOSTn on the disc as written decoded and checked against the ghost the model has.
//
// Usage (from the repo root, after make ta): node tools/ta_ghost_check.mjs [DISC DIR [FRAMES]]
//     DISC default build/ta.ssd, DIR (the tracks' symbols) build/tracks_ta, FRAMES 2400; TRACKS=0,1 for some,
//     PASSES=1 for one race each
import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { makePilot } from "./ta_pilot.mjs";
const [disc = "build/ta.ssd", dir = "build/tracks_ta", framesArg] = process.argv.slice(2);
const FRAMES = Number(framesArg || 2400);
const s = await bootDisc(disc);
let syms = symbols(`${dir}/t0.json`);
await runTo(s, syms["game_resume.idle"], 80000000);
const peek = (a) => s.readMemory(a, 1)[0];
const bt = peek(syms.banktrace), bc = peek(syms.bankcars);
const key = (r) => (r ? r.join(",") : "none");
const { toSsdOrDsd } = await jsbeebModule("disc.js");
const written = () => toSsdOrDsd(s._machine.processor.fdc.drives[0].disc);
let wrong = 0, total = 0, anyDrawn = 0;
const TRACKS = (process.env.TRACKS || "0,1,2,3,4,5,6,7").split(",").map(Number);
const PASSES = Number(process.env.PASSES || 2);
const saved = {};                       // each track's ghost as its last race left it: its records and time
// a ghost's file, decoded (ghost.6502's coding): its time and records
function decodeFile(b) {
    const time = b[0] | (b[1] << 8), len = b[2] | (b[3] << 8), recs = [];
    let last = null, i = 4;
    while (i < 4 + len) {
        let c = b[i++];
        if (c === 0xfe) { recs.push(null); last = null; continue; }
        if (c === 0xff) { last = b.slice(i, i + 4); i += 4; recs.push(last); continue; }
        let f = last[3] & 0x7f;
        if (c >= 0xc0) { f = ((c & 0x10) << 2) | (c & 15); c = b[i++]; }
        const x9 = (last[1] | ((last[3] & 0x80) << 1)) + Math.floor(c / 9) - 4, y = last[2] + (c % 9) - 4;
        last = [last[0], x9 & 255, y, f | ((x9 >> 8) << 7)];
        recs.push(last);
    }
    return { time, recs, len, size: b.length };
}
for (let pass = 0; pass < PASSES; pass++) for (const t of TRACKS) {
    syms = symbols(`${dir}/t${t}.json`);
    s.writeMemory(syms.GmDemo, [0]); s.writeMemory(syms.LoadWant, [t + 1]);
    await runTo(s, syms.start, 400000000);
    const log = new Map();
    let pilot = null, frames = 0, lapStart = 0, prevStart = 0, drawn = 0, waited = 0, ghosts = 0, bad = 0, firstBad = "";
    let ghost = saved[t]?.recs ?? null, ghostTime = saved[t]?.time ?? 0, timeChecked = false;
    const stops = [[syms["logic_frame.played"], bt], [syms["logic_frame.built"], bt], [syms.ghost_frame, bc], [syms["frame_loop.objects"]]];
    const lf = () => (peek(syms.LfFrame) | (peek(syms.LfFrame + 1) << 8)) - 1;   // (counted on at the frame's end)
    while (frames < FRAMES) {
        const at = await runToAny(s, stops, 8000000);
        if (at === syms["logic_frame.played"]) { pilot ??= makePilot(s, syms); s.writeMemory(syms.RcInput, [pilot(), 0, 0]); }
        else if (at === syms["logic_frame.built"]) {
            const f = lf() + 1;
            log.set(f, peek(syms.CarCount) ? [peek(syms.CarId), peek(syms.CarXLo), peek(syms.CarY), peek(syms.CarFlags)] : null);
        } else if (at === syms.ghost_frame) {
            const end = peek(syms.GhLapEnd), f = lf();
            if (end) {
                if (end === 2) {
                    ghost = []; for (let g = prevStart; g < f; g++) ghost.push(log.get(g)); ghosts++;
                    ghostTime = peek(syms.TaGhostLo) | (peek(syms.TaGhostHi) << 8);
                }
                lapStart = prevStart = f;
            }
        } else {
            const f = lf();
            if (!timeChecked) {             // the race's start: the HUD's ghost time the saved ghost's
                timeChecked = true;
                const time = peek(syms.TaGhostLo) | (peek(syms.TaGhostHi) << 8);
                if (time !== ghostTime) { bad++; if (!firstBad) firstBad = `the start's ghost time ${time}, not ${ghostTime}`; }
            }
            const player = log.get(f);
            let g = null;
            if (ghost) { const k = f - lapStart; if (k >= ghost.length) waited++; g = ghost[k < ghost.length ? k : 0]; }
            if (g && !(g[0] & 0x80)) g = [3, g[1], g[2], g[3]];
            const want = [];
            if (player) want.push(player);
            if (g) { want.unshift(g); drawn++; }
            const n = peek(syms.CarCount), got = [];
            for (let i = 0; i < n; i++) got.push([peek(syms.CarId + i), peek(syms.CarXLo + i), peek(syms.CarY + i), peek(syms.CarFlags + i)]);
            if (got.map(key).join(" ") !== want.map(key).join(" ")) { bad++; if (!firstBad) firstBad = `frame ${f} (lap from ${lapStart}): want ${want.map(key).join(" ")}, got ${got.map(key).join(" ")}`; }
            total++;
            frames++;
        }
    }
    wrong += bad;
    anyDrawn += drawn;
    if (ghosts) saved[t] = { recs: ghost, time: ghostTime };
    console.log(`pass ${pass + 1}, track ${t + 1}: ${frames} frames, ${ghost && !ghosts ? "the saved ghost, " : ""}${ghosts} ghosts, the ghost drawn on ${drawn}, waiting on ${waited}; ${bad} wrong${firstBad ? ": first " + firstBad : ""}`);
    s.writeMemory(syms.GmAbandon, [1]); s.writeMemory(syms.LoadWant, [0xff]);
    await runTo(s, syms["game_resume.idle"], 400000000);
    // its file (saved at that load's start) the ghost the model has
    const file = discFiles(written())[`GHOST${t + 1}`];
    const want = saved[t];
    if (!want) { if (file) { wrong++; console.log(`  GHOST${t + 1} written with no ghost`); } }
    else if (!file) { wrong++; console.log(`  no GHOST${t + 1}`); }
    else {
        const g = decodeFile([...file.data]);
        if (g.time !== want.time || g.size !== 4 + g.len || g.recs.map(key).join(" ") !== want.recs.map(key).join(" ")) {
            wrong++; console.log(`  GHOST${t + 1} not the ghost: time ${g.time} (${want.time}), ${g.recs.length} records (${want.recs.length})`);
        }
    }
}
console.log(`${total} frames, the ghost drawn on ${anyDrawn}, ${wrong} wrong`);
process.exit(wrong || !anyDrawn ? 1 : 0);
