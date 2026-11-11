// Time attack's ghost (docs/brief-timeattack-2026-11-10.md, step 4; src/ghost.6502) against a model, every frame:
// each track's race on the disc driven by the autopilot (tools/ta_pilot.mjs) for FRAMES frames. The player's
// records logged each frame (logic_frame.built); each lap that becomes the ghost (GhLapEnd 2 at ghost_frame) keeps
// its frames' records, from its crossing's frame to the one before the next; each frame after ghost_frame (the
// frame loop's .objects) the draw list against the model's: the player's record and the ghost's, the ghost's lap's
// record k (k the frames since this lap started, the crossing's frame 0) or, its lap done, its first (D43), as car 3
// unless an explosion, ordered by y + 255 on top, the ghost after on a tie. So the recording's coding and the
// playback's decoding are checked together: what's drawn is what the player was.
//
// Exit status: 1 if any frame's list differs, or no ghost is drawn on any track; else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_ghost_check.mjs [DISC DIR [FRAMES]]
//     DISC default build/ta.ssd, DIR (the tracks' symbols) build/tracks_ta, FRAMES 2400; TRACKS=0,1 for some
import { bootDisc, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { makePilot } from "./ta_pilot.mjs";
const [disc = "build/ta.ssd", dir = "build/tracks_ta", framesArg] = process.argv.slice(2);
const FRAMES = Number(framesArg || 2400);
const s = await bootDisc(disc);
let syms = symbols(`${dir}/t0.json`);
await runTo(s, syms["game_resume.idle"], 80000000);
const peek = (a) => s.readMemory(a, 1)[0];
const bt = peek(syms.banktrace), bc = peek(syms.bankcars);
const key = (r) => (r ? r.join(",") : "none");
const sortKey = (r) => r[2] + (!(r[0] & 0x80) && (r[3] & 0x40) ? 255 : 0);
let wrong = 0, total = 0, anyDrawn = 0;
const TRACKS = (process.env.TRACKS || "0,1,2,3,4,5,6,7").split(",").map(Number);
for (const t of TRACKS) {
    syms = symbols(`${dir}/t${t}.json`);
    s.writeMemory(syms.GmDemo, [0]); s.writeMemory(syms.LoadWant, [t + 1]);
    await runTo(s, syms.start, 400000000);
    const log = new Map();
    let pilot = null, frames = 0, lapStart = 0, prevStart = 0, ghost = null, drawn = 0, waited = 0, ghosts = 0, bad = 0, firstBad = "";
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
                if (end === 2) { ghost = []; for (let g = prevStart; g < f; g++) ghost.push(log.get(g)); ghosts++; }
                lapStart = prevStart = f;
            }
        } else {
            const f = lf();
            const player = log.get(f);
            let g = null;
            if (ghost) { const k = f - lapStart; if (k >= ghost.length) waited++; g = ghost[k < ghost.length ? k : 0]; }
            if (g && !(g[0] & 0x80)) g = [3, g[1], g[2], g[3]];
            const want = [];
            if (player) want.push(player);
            if (g) { if (player && sortKey(g) < sortKey(player)) want.unshift(g); else want.push(g); drawn++; }
            const n = peek(syms.CarCount), got = [];
            for (let i = 0; i < n; i++) got.push([peek(syms.CarId + i), peek(syms.CarXLo + i), peek(syms.CarY + i), peek(syms.CarFlags + i)]);
            if (got.map(key).join(" ") !== want.map(key).join(" ")) { bad++; if (!firstBad) firstBad = `frame ${f} (lap from ${lapStart}): want ${want.map(key).join(" ")}, got ${got.map(key).join(" ")}`; }
            total++;
            frames++;
        }
    }
    wrong += bad;
    anyDrawn += drawn;
    console.log(`track ${t + 1}: ${frames} frames, ${ghosts} ghosts, the ghost drawn on ${drawn}, waiting on ${waited}; ${bad} wrong${firstBad ? ": first " + firstBad : ""}`);
    s.writeMemory(syms.GmAbandon, [1]); s.writeMemory(syms.LoadWant, [0xff]);
    await runTo(s, syms["game_resume.idle"], 400000000);
}
console.log(`${total} frames, the ghost drawn on ${anyDrawn}, ${wrong} wrong`);
process.exit(wrong || !anyDrawn ? 1 : 0);
