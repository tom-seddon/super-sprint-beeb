// Time attack's 32-row front end and the race's 26 rows (docs/brief-timeattack-2026-11-10.md, step 6c; D46;
// tagame.6502's tg_rows), field by field as shown (the frame buffer, as tools/flash_check.mjs reads it), on
// build/ta.ssd from a fresh boot: to the menu, 3 raced, Escape back to the menu, Return races the highlighted track (3):
// - from the first menu on, nothing lit outside the 32 rows' lines, nor outside the 26 rows' but while the menu's
//   shown;
// - the menu, from its start (two fields' grace: the one being shown and tg_rows's wait for a vsync) until it's all
//   drawn (game_resume.shown): nothing lit; then shown in 32 rows: its heading lit on its lines there (TgHeading from
//   the 32 rows' top), and nothing on the lines it would have in the race's 26;
// - leaving it for a race (game_resume.go, the same grace) to the race's first frame: nothing lit below the HUD's
//   row, which says "Loading" at some point;
// - at each race's start, Shared (SharedOrg to SharedEnd) in both screens as the track's build has it: its file puts
//   back what the menu's 32 rows overwrote.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_rows_check.mjs

import { bootDisc, discFiles, ram, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, Width = 1024;
const Top = 128, Hud = 144, Bottom = 544;               // (the race's 26 rows, in the frame buffer's lines: two a scan line)
const syms = symbols("build/tracks_ta/t0.json");
const Top32 = Top - 2 * 8 * (34 - syms.ScreenVSyncPos);  // (32 rows: the sync 3 rows later, R7 34, so the display 3 rows higher)
const Bottom32 = Top32 + 2 * 8 * 32;
const s = await bootDisc("build/ta.ssd");
const cpu = s._machine.processor;
const b = s._completeFb8, fb = new Uint32Array(b.buffer, b.byteOffset, b.byteLength / 4), lines = fb.length / Width;
const lit = (from, to) => {
    let n = 0;
    for (let i = from * Width; i < to * Width; i++) if (fb[i] & 0xffffff) n++;
    return n;
};

const G = (n) => syms[`game_resume.${n}`];
const at = { menu: G("menu"), shown: G("shown"), go: G("go"), start: syms.start, frame: syms.frame_loop };
const Keys = [["Digit3", 2], ["Enter", 2]];             // (each from the menu: the key, and the track it races)

let bad = 0, field = 0;
const say = (t) => { if (bad++ < 20) console.log(`field ${field}: ${t}`); };
let state = "boot", grace = 0, said = false, menus = 0, races = 0, sharedChecked = 0, shownFields = 0, raceFields = 0;
const shared = (n) => {
    const sprint = discFiles(`build/tracks_ta/t${n}.ssd`).SPRINT.data;
    return sprint.subarray(syms.SharedOrg - 0x3000, syms.SharedEnd - 0x3000);
};
const same = (a, want) => a.length === want.length && a.every((v, i) => v === want[i]);

for (const a of Object.values(at)) s.addBreakpoint("execute", a, {});
// (the menu's in the background's bank: its addresses are reached in ROMs too, during the boot)
const ours = (a) => a === at.start || a === at.frame || (cpu.romsel & 15) === ram(s, syms.bankbg, 1)[0];

for (let left = Field; ;) {
    s.resetBreakpointHits();
    settle(s);
    const before = s.elapsedCycles;
    await s.runFor(left);
    const hit = s.hitBreakpoint();
    left -= Math.max(s.elapsedCycles - before, 1);
    if (hit && ours(hit.address)) {
        const a = hit.address;
        if (a === at.menu) { state = "drawing"; grace = 2; menus++; }
        else if (a === at.shown) { state = "menu"; shownFields = 0; }
        else if (a === at.go) { state = "loading"; grace = 2; said = false; }
        else if (a === at.start && state === "loading") {
            const n = ram(s, syms.TrackNum, 1)[0], want = shared(n);
            const main = ram(s, syms.SharedOrg, want.length), shadow = ram(s, syms.SharedOrg, want.length, true);
            if (!same(main, want) || !same(shadow, want)) say(`race ${races + 1} (track ${n + 1}): Shared not as built at its start (main ${same(main, want)}, shadow ${same(shadow, want)})`);
            else sharedChecked++;
        } else if (a === at.frame && state === "loading") {
            if (!said) say("no \"Loading\" seen on the way to the race");
            state = "race"; raceFields = 0; races++;
        }
    }
    if (left > 0) continue;
    left = Field;
    field++;

    // the field just shown (from the first menu: the boot's screens are tools/boot_check.mjs's)
    if (state === "boot") continue;
    const out = lit(0, Top32) + lit(Bottom32, lines);
    if (out) say(`${out} pixels outside the 32 rows' lines`);
    const out26 = lit(Top32, Top) + lit(Bottom, Bottom32);
    if (out26 && state !== "menu") say(`${out26} pixels outside the 26 rows' lines, ${state}`);
    if (grace > 0) grace--;
    else if (state === "drawing") {
        const n = lit(0, lines);
        if (n) say(`${n} pixels lit while the menu's drawn`);
    } else if (state === "loading") {
        const n = lit(Hud, lines);
        if (n) say(`${n} pixels below the HUD's row on the way to a race`);
        if (lit(Top, Hud)) said = true;
    } else if (state === "menu") {
        if (++shownFields === 3) {
            const head = Top32 + 2 * syms.TgHeading;
            if (!lit(head, head + 12)) say("the menu's heading not on its 32 rows' lines");
            const head26 = Top + 2 * (syms.TgHeading - 8 * (syms.HudAddr - syms.FrontAddr) / 640);
            if (lit(head26, head26 + 12)) say("the menu's heading where the race's 26 rows would show it");
            const key = Keys[menus - 1];
            if (!key) break;
            s.keyDown(key[0]);
        } else if (shownFields === 6) {
            for (const [k] of Keys) s.keyUp(k);
        }
    } else if (state === "race" && ++raceFields === 100) {
        if (races === Keys.length) break;
        s.keyDown("Escape");
    } else if (state === "race" && raceFields === 103) s.keyUp("Escape");
    if (field > 5000) { say(`stuck: ${state}, ${menus} menus, ${races} races`); break; }
}
if (menus !== 2 || races !== 2) say(`${menus} menus and ${races} races, not 2 and 2`);
console.log(bad ? `${bad} fields wrong` : `${field} fields: ${menus} menus drawn black and shown in 32 rows, ${races} races reached through "Loading" in the 26, Shared as built in both screens at each race's start (${sharedChecked} checked); nothing lit out of place`);
process.exit(bad ? 1 : 0);
