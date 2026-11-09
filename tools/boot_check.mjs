// The screen from SHIFT-BREAK to the title, field by field, as shown: "Loading" in the HUD's row must be up soon
// after the boot starts (the boot puts it there, in the shadow screen, before the files load: boot.6502), and from
// then until the title's file has loaded nothing may change: every field the same row, nothing lit anywhere else.
// Before it, the OS's MODE 7 and its prompt; at the load's end the display goes off, and once it's off nothing may
// be lit until the title's file has loaded (so no "Loading" gone and back). After it, the screen cleared and the
// title wiped in, as after any load.
// The loader's "Loading" in the main screen (entry.6502), shown from game_go, and the title's load redrawing it
// (loadcode.6502) must not show either.
//
// Exit status: 1 if "Loading" comes late or not at all, if any field after it differs, or if the title's file
// never loads; else 0.
//
// Usage (from the repo root, after make game): node tools/boot_check.mjs [--adfs] [--show FIELD OUT.png]

import { writeFileSync } from "node:fs";
import { adfs, gameArgs, gameDisc, jsbeebModule, ram, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, Width = 1024, Top = 128, Hud = 144;   // (the frame buffer's lines: two a scan line)
const show = gameArgs[0] === "--show" ? [Number(gameArgs[1]), gameArgs[2]] : null;
const Soon = 15;                                        // fields from !BOOT's start (its loading and the
                                                        // OS's start-up, SHIFT held, come before: the harness's)
const syms = symbols("build/tracks/t0.json");
const { MachineSession } = await jsbeebModule("machine-session.js");
const s = new MachineSession(adfs ? "MasterADFS" : "Master");
await s.initialise();
s.loadDisc(gameDisc);
s.keyDown("ShiftLeft");
s.reset(true);
const hold = adfs ? 8000000 : 2000000, cpu = s._machine.processor;
const b = s._completeFb8, fb = new Uint32Array(b.buffer, b.byteOffset, b.byteLength / 4), lines = fb.length / Width;
const title = syms["game_resume.loaded"];
s.addBreakpoint("execute", title);
s.addBreakpoint("execute", syms.boot_entry);

const lit = (from, to) => {
    let n = 0;
    for (let i = from * Width; i < to * Width; i++) if (fb[i] & 0xffffff) n++;
    return n;
};
let bad = 0, field = 0, first = -1, row = null, shift = true, done = false, booted = -1, gone = false;
const say = (t) => { if (bad++ < 20) console.log(`field ${field}: ${t}`); };
for (let left = Field; ;) {
    s.resetBreakpointHits();
    settle(s);
    const before = s.elapsedCycles;
    await s.runFor(left);
    const hit = s.hitBreakpoint();
    left -= Math.max(s.elapsedCycles - before, 1);
    if (hit && hit.address === syms.boot_entry && booted < 0) booted = field;
    if (hit && hit.address === title && (cpu.romsel & 15) === ram(s, 0, 1)[0]) done = true;  // (the game's, in bankbg: not a ROM's)
    if (left > 0 && !done) continue;
    left = Field;
    field++;
    if (shift && field * Field >= hold) { s.keyUp("ShiftLeft"); shift = false; }
    if (done) break;
    if (show && field === show[0]) writeFileSync(show[1], await s.screenshotActive({ scale: 2 }));
    const outside = lit(0, Top) + lit(Hud, lines), inside = lit(Top, Hud);
    if (first < 0) {
        if (inside && !outside) { first = field; row = fb.slice(Top * Width, Hud * Width); }
        else if (field > 3000) { say("no \"Loading\" alone in the HUD's row"); break; }
        continue;
    }
    if (outside) say(`${outside} pixels outside the HUD's row`);
    if (!inside && !outside) { gone = true; continue; }     // (the display off at the load's end)
    if (gone) { say("the HUD's row lit again after it went off"); continue; }
    const now = fb.subarray(Top * Width, Hud * Width);
    let differ = 0;
    for (let i = 0; i < now.length; i++) if (now[i] !== row[i]) differ++;
    if (differ) say(`${differ} pixels of the HUD's row changed`);
    if (field > 6000) { say("the title's file never loaded"); break; }
}
if (booted < 0) say("!BOOT never ran");
else if (first - booted > Soon) say(`"Loading" ${first - booted} fields after !BOOT started: more than ${Soon}`);
if (!done && first >= 0 && bad === 0) say("the title's file never loaded");
console.log(`${adfs ? "ADFS" : "DFS"}: !BOOT from field ${booted}, "Loading" from ${first}, the title's file loaded at ${field}${bad ? `; ${bad} fields wrong` : ": nothing else seen"}`);
process.exit(bad ? 1 : 0);
