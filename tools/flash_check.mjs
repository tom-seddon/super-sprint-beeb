// The screen around a load, field by field, as shown (Phase 5, step 8): build/game.ssd left to run from the title through a
// demo to the credits, then fire, the select, prepare to race and a race's start. Every load lands its file in the main
// screen, so the display has to hide it: nothing may be lit outside the screen's own lines at any time, and from a load's
// start (a frame's grace, for the one being shown) to the next picture's wipe or the race's first frame, nothing below
// the HUD's row, which must say "Loading" at some point. Tom saw each of these on his Master as a flash of junk.
//
// Exit status: 1 if any field shows something it shouldn't, else 0.
//
// Usage (from the repo root, after make game): node tools/flash_check.mjs

import { bootDisc, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, Width = 1024, Top = 128, Hud = 144, Bottom = 544;   // (the frame buffer's lines: two a scan line)
const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
const b = s._completeFb8, fb = new Uint32Array(b.buffer, b.byteOffset, b.byteLength / 4), lines = fb.length / Width;

const lit = (from, to) => {
    let n = 0;
    for (let i = from * Width; i < to * Width; i++) if (fb[i] & 0xffffff) n++;
    return n;
};
const G = (n) => syms[`game_resume.${n}`];
const opens = syms["load_go.load"], closes = [syms.wipe_in, syms.frame_loop], got = syms["game_read.got"], done = G("credits_shown");
const stops = [[opens], [closes[0], bankbg], [closes[1]], [got, bankbg], [done, bankbg]];
for (const [a, bank] of stops) s.addBreakpoint("execute", a, bank === undefined ? {} : { bank });

let bad = 0, field = 0, loads = 0, grace = -1, racing = false, firing = false, started = false, seen = 0, said = false;
const say = (t) => { if (bad++ < 20) console.log(`field ${field}: ${t}`); };
for (let left = Field; ;) {
    s.resetBreakpointHits();
    settle(s);
    const before = s.elapsedCycles;
    await s.runFor(left);
    const hit = s.hitBreakpoint();
    left -= Math.max(s.elapsedCycles - before, 1);
    if (hit) {
        if (hit.address === opens) {
            if (grace < 0) { grace = 2; loads++; said = false; }
        }
        else if (closes.includes(hit.address)) {
            if (grace >= 0 && !said) say("no \"Loading\" seen in that load");
            if (grace >= 0 && hit.address === closes[1]) racing = firing;
            grace = -1;
        } else if (hit.address === done) firing = true;
        else if (hit.address === got) {
            if (firing && !started && cpu.x === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
        }
    }
    if (left > 0) continue;
    left = Field;
    field++;
    const out = lit(0, Top) + lit(Bottom, lines);
    if (out) say(`${out} pixels outside the screen`);
    if (grace > 0) grace--;
    else if (grace === 0) {
        seen++;
        const n = lit(Hud, Bottom);
        if (n) say(`${n} pixels below the HUD's row during a load`);
        if (lit(Top, Hud)) said = true;
    }
    if (racing) break;
    if (field > 20000) { say("never reached a race"); break; }
}
console.log(bad ? `${bad} fields wrong` : `${field} fields, ${loads} loads, ${seen} fields looked at in them: nothing to see`);
process.exit(bad ? 1 : 0);
