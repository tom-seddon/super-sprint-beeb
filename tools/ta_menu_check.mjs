// Time attack's menu (docs/brief-timeattack-2026-11-10.md, step 6b; tagame.6502; D51-D53), driven key by key on
// build/ta.ssd from a fresh boot:
// - the boot to the menu, track 1 highlighted (its mark drawn, no other);
// - the driving keys move the highlight: player 1's right (W), player 2's right (.), player 3's left (keypad 5), and
//   left from track 1 to track 8; a key held 40 fields moves it once;
// - 3 races track 3 (its file loaded: TrackNum 2); in the race player 2's accelerate (/) drives the car (D53); its
//   best poked and Escape: back to the menu through the title's file (TIMES saved at its load's start), track 3's
//   row showing a time and the others none, the highlight on track 3;
// - Return races the highlighted track; Escape back;
// - player 1's right redefined as 5: 5 races track 5 (a number wins over a driving key, D52).
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_menu_check.mjs

import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";

const { toSsdOrDsd } = await jsbeebModule("disc.js");
const syms = symbols("build/tracks_ta/t0.json");
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };
const s = await bootDisc("build/ta.ssd");
const cpu = s._machine.processor;
const peek = (a) => s.readMemory(a, 1)[0];

async function toMenu() {
    for (;;) {
        await runToAny(s, [[syms["game_resume.idle"]]], 400000000);
        if ((cpu.romsel & 15) === peek(syms.bankbg)) return;
        await s.runFor(1000);
    }
}
const fields = (n) => s.runFor(n * 39936);
async function press(key, hold = 3) { s.keyDown(key); await fields(hold); s.keyUp(key); await fields(3); }

// the screen's byte at a line and byte column of the front end's 32 rows (the main screen, shown)
const RowBytes = 640, Front = syms.FrontAddr;
const at = (line, col) => Front + (line >> 3) * RowBytes + col * 8 + (line & 7);
const mark = (t) => [...Array(6)].every((_, i) => peek(at(syms.TgRow0 + t * 16 + i, syms.TgMarkCol)) === 0xff);
const marks = () => [...Array(8)].map((_, t) => mark(t));
// a row's time drawn: any pixel in its box (the time's columns, 6 lines)
const timeShown = (t) => [...Array(6)].some((_, i) => { for (let c = syms.TgTimeX >> 2; c < (syms.TgTimeX >> 2) + 8; c++) if (peek(at(syms.TgRow0 + t * 16 + i, c))) return true; return false; });
const highlight = () => { const m = marks(); return m.filter(Boolean).length === 1 ? m.indexOf(true) : -1; };

await toMenu();
await fields(5);
if (highlight() !== 0 || peek(syms.GmTrack) !== 0) say(`boot: the highlight ${highlight()}, GmTrack ${peek(syms.GmTrack)}, not 0`);

for (const [key, want, what] of [["KeyW", 1, "player 1's right"], ["Period", 2, "player 2's right"], ["Numpad5", 1, "player 3's left"],
    ["KeyQ", 0, "player 1's left"], ["KeyQ", 7, "left from track 1"], ["KeyW", 0, "right from track 8"]]) {
    await press(key);
    if (highlight() !== want || peek(syms.GmTrack) !== want) say(`${what}: the highlight ${highlight()}, GmTrack ${peek(syms.GmTrack)}, not ${want}`);
}
await press("KeyW", 40);
if (highlight() !== 1) say(`W held 40 fields: the highlight ${highlight()}, not 1`);
await press("KeyQ");

// 3 races track 3
s.keyDown("Digit3");
await runTo(s, syms.start, 400000000);
s.keyUp("Digit3");
if (peek(syms.TrackNum) !== 2) say(`3: track ${peek(syms.TrackNum) + 1} loaded, not 3`);
const bt = peek(syms.banktrace);
s.keyDown("Slash");                     // (player 2's accelerate)
for (let n = 0; n < 60; n++) await runToAny(s, [[syms["logic_frame.built"], bt]], 8000000);
s.keyUp("Slash");
const speed = peek(syms.RcSpeedLo) | (peek(syms.RcSpeedHi) << 8);
if (!speed || speed > 0x7fff) say(`player 2's accelerate: car 0's speed ${speed}`);
await runToAny(s, [[syms["logic_frame.played"], bt]], 8000000);
s.writeMemory(syms.TaBestLo, [0x34, 0x02]);   // (ANDY's, paged in here: a best of 564 fields, 11.28)
s.keyDown("Escape");
await toMenu();
s.keyUp("Escape");
await fields(5);
const times = discFiles(toSsdOrDsd(cpu.fdc.drives[0].disc)).TIMES;
if (!times || (times.data[20] | (times.data[100] << 8)) !== 564) say("Escape: TIMES not saved with track 3's best 564");
if (highlight() !== 2) say(`Escape: the highlight ${highlight()}, not track 3`);
const shown = [...Array(8)].map((_, t) => timeShown(t));
if (shown.join() !== [false, false, true, false, false, false, false, false].join()) say(`Escape: times shown on rows ${shown.map((v, t) => v ? t + 1 : "").join("")}, not 3`);

// Return races the highlighted
await press("KeyW");
s.keyDown("Enter");
await runTo(s, syms.start, 400000000);
s.keyUp("Enter");
if (peek(syms.TrackNum) !== 3) say(`Return: track ${peek(syms.TrackNum) + 1} loaded, not 4`);
s.keyDown("Escape");
await toMenu();
s.keyUp("Escape");
await fields(5);

// a number over a driving key
s.writeMemory(syms.PlayerKeys + 1, [19]);   // (player 1's right: the 5 key, tools/screens.py's matrix)
s.keyDown("Digit5");
await runTo(s, syms.start, 400000000);
s.keyUp("Digit5");
if (peek(syms.TrackNum) !== 4) say(`5 as a driving key too: track ${peek(syms.TrackNum) + 1} loaded, not 5`);

console.log(wrong ? `${wrong} wrong` : "the menu: highlight by any player's left and right (held: once), 3, Return and 5 (a driving key too) race their tracks, player 2's keys drive, Escape back with TIMES saved and the new best shown");
process.exit(wrong ? 1 : 0);
