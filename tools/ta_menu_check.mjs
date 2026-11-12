// Time attack's menu (docs/brief-timeattack-2026-11-10.md, step 6b; tagame.6502; D51-D53), driven key by key on
// build/ta.ssd from a fresh boot:
// - the boot to the menu, track 1 highlighted (its box drawn, no other);
// - the driving keys move the highlight round the cells, right clockwise (1, 5, 6, 7, 8, 4, 3, 2): player 1's right (W),
//   player 2's right (.), player 3's left (keypad 5), left from track 1 to track 2, and right all the way round; a key
//   held 40 fields moves it once;
// - Escape on the menu does nothing;
// - 3 opens track 3's screen (D52: the numbers another way through, Tom, 2026-11-12), with the highlight elsewhere;
//   Return races it (its file loaded: TrackNum 2); in the race player 2's accelerate (/) drives the car (D53); its
//   best poked and Escape: through the title's file to its name (step 6g), the Escape still held there doing nothing
//   (TIMES not saved, nothing typed), AB typed and Return: TIMES saved with it, then track 3's screen (D50); the driving keys and numbers do nothing there either; Escape: the menu,
//   track 3's cell showing a time and the others none, the highlight on track 3;
// - Return opens the highlighted track's screen (D48), Return there races it, Escape back to its screen and again to
//   the menu; player 1's accelerate (E) opens the highlighted one's screen and races it too, and player 2's (/) after
//   Escape, its hold as the screen came up let go first;
// - player 1's right redefined as 5: 5 opens track 5's screen (a number wins over a driving key, D52), Return races it.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_menu_check.mjs

import { bootDisc, discFiles, jsbeebModule, runTo, runToAny, symbols } from "./jsbeeb.mjs";
import { typeName } from "./ta_name.mjs";

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
async function screenKey(key) { s.keyDown(key); await fields(3); s.keyUp(key); await toMenu(); await fields(5); }   // (a screen drawn)
const on = () => peek(syms.TgOn);

// the screen's byte at a line and byte column of the front end's 32 rows (the main screen, shown)
const RowBytes = 640, Front = syms.FrontAddr;
const at = (line, col) => Front + (line >> 3) * RowBytes + col * 8 + (line & 7);
// a track's cell (D47, step 6d): its first byte across and line; its box, yellow along its top and bottom lines
const cell = (t) => [(t >> 2) * 40, syms.TaMenuTop + (t & 3) * syms.TaMenuRow];
const mark = (t) => { const [c0, y0] = cell(t); return [...Array(40)].every((_, c) => (peek(at(y0, c0 + c)) & 0xf0) === 0xf0 && (peek(at(y0 + syms.TaMenuRow - 1, c0 + c)) & 0xf0) === 0xf0); };
const marks = () => [...Array(8)].map((_, t) => mark(t));
// a track's time drawn: any pixel where it goes (its columns, 6 lines)
const timeShown = (t) => { const [c0, y0] = cell(t), x = c0 + (syms.TaMenuTextX >> 2); return [...Array(6)].some((_, i) => { for (let c = x; c < x + 8; c++) if (peek(at(y0 + syms.TgTimeLine + i, c))) return true; return false; }); };
const highlight = () => { const m = marks(); return m.filter(Boolean).length === 1 ? m.indexOf(true) : -1; };

await toMenu();
await fields(5);
if (highlight() !== 0 || peek(syms.GmTrack) !== 0) say(`boot: the highlight ${highlight()}, GmTrack ${peek(syms.GmTrack)}, not 0`);

for (const [key, want, what] of [["KeyW", 4, "player 1's right"], ["Period", 5, "player 2's right"], ["Numpad5", 4, "player 3's left"],
    ["KeyQ", 0, "player 1's left"], ["KeyQ", 1, "left from track 1"], ["KeyW", 0, "right from track 2"]]) {
    await press(key);
    if (highlight() !== want || peek(syms.GmTrack) !== want) say(`${what}: the highlight ${highlight()}, GmTrack ${peek(syms.GmTrack)}, not ${want}`);
}
const round = [];
for (let n = 0; n < 8; n++) { await press("KeyW"); round.push(highlight() + 1); }
if (round.join() !== "5,6,7,8,4,3,2,1") say(`right 8 times from track 1: ${round.join()}, not 5,6,7,8,4,3,2,1`);
await press("KeyW", 40);
if (highlight() !== 4) say(`W held 40 fields: the highlight ${highlight()}, not 4`);
await press("KeyQ");

await press("Escape");
if (on() || peek(syms.LoadWant) || highlight() !== 0) say(`Escape on the menu: TgOn ${on()}, LoadWant ${peek(syms.LoadWant)}, the highlight ${highlight()}`);

// 3 opens track 3's screen, Return races it
await screenKey("Digit3");
if (on() !== 1 || peek(syms.GmTrack) !== 2 || peek(syms.LoadWant) || highlight() !== -1) say(`3 on the menu: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, LoadWant ${peek(syms.LoadWant)}, the highlight ${highlight()}, not track 3's screen`);
s.keyDown("Enter");
await runTo(s, syms.start, 400000000);
s.keyUp("Enter");
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
await runToAny(s, [[syms["tg_type.field"], peek(syms.bankbg)]], 400000000);   // (the entry's name, step 6g)
await fields(10);
const disc = () => discFiles(toSsdOrDsd(cpu.fdc.drives[0].disc));
if (disc().TIMES || peek(syms.TaNew) !== 21 || peek(syms.TgLen)) say(`Escape held at the name: TIMES ${disc().TIMES ? "saved" : "not saved"}, TaNew ${peek(syms.TaNew)}, ${peek(syms.TgLen)} typed, not none, 21 and 0`);
s.keyUp("Escape");
await typeName(s, "AB");
await toMenu();
await fields(5);
const times = disc().TIMES;
if (!times || (times.data[20] | (times.data[100] << 8)) !== 564 || String.fromCharCode(...times.data.subarray(240 + 200, 240 + 203)) !== "AB\0") say("the name: TIMES not saved with track 3's best 564 and AB");
if (on() !== 1 || peek(syms.GmTrack) !== 2 || highlight() !== -1) say(`after the name: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, the highlight ${highlight()}, not track 3's screen`);
for (const key of ["KeyW", "KeyQ", "Digit5"]) await press(key);
if (on() !== 1 || peek(syms.GmTrack) !== 2 || peek(syms.LoadWant)) say(`W, Q, 5 on track 3's screen: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, LoadWant ${peek(syms.LoadWant)}`);
await screenKey("Escape");
if (on() || highlight() !== 2) say(`Escape on track 3's screen: TgOn ${on()}, the highlight ${highlight()}, not the menu's track 3`);
const shown = [...Array(8)].map((_, t) => timeShown(t));
if (shown.join() !== [false, false, true, false, false, false, false, false].join()) say(`Escape: times shown on rows ${shown.map((v, t) => v ? t + 1 : "").join("")}, not 3`);

// Return opens the highlighted's screen (right from track 3: track 2), and races it
await press("KeyW");
await screenKey("Enter");
if (on() !== 1 || peek(syms.GmTrack) !== 1 || peek(syms.LoadWant)) say(`Return on the menu: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, LoadWant ${peek(syms.LoadWant)}, not track 2's screen`);
s.keyDown("Enter");
await runTo(s, syms.start, 400000000);
s.keyUp("Enter");
if (peek(syms.TrackNum) !== 1) say(`Return: track ${peek(syms.TrackNum) + 1} loaded, not 2`);
s.keyDown("Escape");
await toMenu();
s.keyUp("Escape");
await fields(5);
if (on() !== 1 || peek(syms.GmTrack) !== 1) say(`Escape from track 2's race: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, not its screen`);
await screenKey("Escape");

// accelerate opens and races the highlighted: player 1's (E) from track 1
await press("KeyW");
if (highlight() !== 0) say(`right from track 2: the highlight ${highlight()}, not 1`);
await screenKey("KeyE");
if (on() !== 1 || peek(syms.GmTrack) !== 0) say(`E on the menu: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, not track 1's screen`);
s.keyDown("KeyE");
await runTo(s, syms.start, 400000000);
s.keyUp("KeyE");
if (peek(syms.TrackNum) !== 0) say(`E: track ${peek(syms.TrackNum) + 1} loaded, not 1`);
// player 2's (/), held through Escape: nothing till it's let go, then track 1 again
s.keyDown("Slash");
s.keyDown("Escape");
await toMenu();
s.keyUp("Escape");
await fields(20);
if (peek(syms.LoadWant) || on() !== 1) say(`/ held from the race: LoadWant ${peek(syms.LoadWant)}, TgOn ${on()}`);
s.keyUp("Slash");
await fields(3);
s.keyDown("Slash");
await runTo(s, syms.start, 400000000);
s.keyUp("Slash");
if (peek(syms.TrackNum) !== 0) say(`/: track ${peek(syms.TrackNum) + 1} loaded, not 1`);
s.keyDown("Escape");
await toMenu();
s.keyUp("Escape");
await fields(5);
await screenKey("Escape");

// a number over a driving key
s.writeMemory(syms.PlayerKeys + 1, [19]);   // (player 1's right: the 5 key, tools/screens.py's matrix)
await screenKey("Digit5");
if (on() !== 1 || peek(syms.GmTrack) !== 4) say(`5 as a driving key too: TgOn ${on()}, GmTrack ${peek(syms.GmTrack)}, not track 5's screen`);
s.keyDown("Enter");
await runTo(s, syms.start, 400000000);
s.keyUp("Enter");
if (peek(syms.TrackNum) !== 4) say(`5 as a driving key too, then Return: track ${peek(syms.TrackNum) + 1} loaded, not 5`);

console.log(wrong ? `${wrong} wrong` : "the menu: highlight by any player's left and right round the cells (held: once), Return, accelerate (E) and the numbers (3, 5: a driving key too) open the track's screen, Return and accelerate race from it (/: a hold from the race ignored), player 2's keys drive, Escape back to the track's screen with TIMES saved, again to the menu with the new best shown");
process.exit(wrong ? 1 : 0);
