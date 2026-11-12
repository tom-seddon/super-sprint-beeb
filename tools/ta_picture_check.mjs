// Time attack's menu's picture (docs/brief-timeattack-2026-11-10.md, step 6d; D47; tagame.6502), on build/ta.ssd from
// a fresh boot:
// - the screen: the 8 tracks' bests poked into the table (none, under 10 s, over, 99.98 and past it), the menu drawn
//   again (a title's load) and its 32 rows in main RAM byte for byte as a model has them: tools/screens.py's picture
//   (build/gen/tamenu.bin), each track's "TRACK n" in white and its best in yellow, " 9.56", in the small font (the
//   build's table, build/gen/front.6502's SmallFont), and the yellow box round the highlighted track; again once the
//   highlight's moved (the box EOR'd: out of one cell, into the next);
// - the track's screen (step 6e, D48), Return on the menu: the logo kept, the track's map moved from its cell to the first
//   cell's place, the rest cleared, "TRACK n" in white under it, and its 10 entries (poked: times, names of every
//   character the font has, a full 10, none and empty entries), each its place in green, time in yellow and name in
//   white, and its upgrades in green (S2 A1 T2), byte for byte; under the map the upgrades' panel (step 6f, D49):
//   SPEED, ACCEL., TRACTION and their levels, the wrench and the upgrades left, RACE, the cursor's item in yellow;
//   the panel driven by keys (right and accelerate) to speed 3, acceleration 2, traction 1: one too many, the count -1
//   and RACE in red (colour 1 switched red for each one's line by the interrupt), the cursor passing over RACE right
//   and left, and Return then racing nothing; then Escape, the menu again as before; then 5, the highlighted track's
//   number: its screen again (the box not copied with the map, the levels kept, the cursor on SPEED as there are too
//   many), traction round to 0, the cursor to RACE, white again, and Return races it; every field of each of the
//   panel's keys, held and let go, the screen before it or after it, nothing half drawn between;
// - as shown, every field from the boot's menu to a race's first frame (the frame buffer, as tools/ta_rows_check.mjs
//   reads it): no green on the logo's lines (colour 1 red there, the interrupt's TaSplit) and no red under them; and
//   while the menu's up, each of its 256 lines' colours as the model's, pixel for pixel counted (two of the frame
//   buffer's a pixel across, two lines a line), colour 1 red to the logo's end and green from there.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_picture_check.mjs

import { readFileSync } from "node:fs";
import { bootDisc, discFiles, jsbeebModule, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const syms = symbols("build/tracks_ta/t0.json");
const { toSsdOrDsd } = await jsbeebModule("disc.js");
const Field = 39936, Width = 1024, Top = 128;
const Top32 = Top - 2 * 8 * (syms.FrontVSyncPos - syms.ScreenVSyncPos);   // (the 32 rows' first line in the frame buffer)
const Lines = 256, Logo = syms.TaLogoLines;
let bad = 0;
const say = (t) => { if (bad++ < 30) console.log(t); };

// the model: logical colours, 320 x 256
const at = (y, c) => (y >> 3) * 640 + c * 8 + (y & 7);
function decode(bytes) {
    const l = new Uint8Array(Lines * 320);
    for (let y = 0; y < Lines; y++) for (let c = 0; c < 80; c++) {
        const b = bytes[at(y, c)];
        for (let n = 0; n < 4; n++) l[y * 320 + c * 4 + n] = (b >> (7 - n) & 1) * 2 + (b >> (3 - n) & 1);
    }
    return l;
}
function encode(l) {
    const out = new Uint8Array(20480);
    for (let y = 0; y < Lines; y++) for (let c = 0; c < 80; c++) {
        let b = 0;
        for (let n = 0; n < 4; n++) { const v = l[y * 320 + c * 4 + n]; b |= (v >> 1) << (7 - n) | (v & 1) << (3 - n); }
        out[at(y, c)] = b;
    }
    return out;
}
const picture = readFileSync("build/gen/tamenu.bin");
if (!encode(decode(picture)).every((v, i) => v === picture[i])) throw new Error("the model's MODE 1 bytes aren't the picture's");
const gen = readFileSync("build/gen/front.6502", "utf8"), table = (n) => gen.match(new RegExp(`^${n} = \\{([^}]*)\\}`, "m"))[1].split(",").map(Number);
const font = [...table("SmallFont"), ...table("TaGlyphs"), 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0];   // (then 39 the minus, 40 and 41
// the wrench; 42 the name's cursor, # in text, a block tg_typed draws itself)
const glyph = (ch) => ch === "." ? 10 : ch === "!" ? 11 : ch === "-" ? 39 : ch === "{" ? 40 : ch === "}" ? 41 : ch === "#" ? 42 : ch >= "A" ? 12 + ch.charCodeAt(0) - 65 : Number(ch);
function text(l, s, x, y, ink) {
    for (const ch of s) {
        if (ch !== " ") for (let line = 0; line < 6; line++) for (let j = 0; j < 6; j++)
            if (font[glyph(ch) * 6 + line] >> (7 - j) & 1) l[(y + line) * 320 + x + j] |= ink;
        x += 6;
    }
}
const time = (f) => {
    f = Math.min(f, 4999);
    return `${Math.floor(f / 500) || " "}${Math.floor(f % 500 / 50)}.${Math.floor(f % 50 / 5)}${f % 5 * 2}`;
};
const cell = (t) => [(t >> 2) * 160, syms.TaMenuTop + (t & 3) * syms.TaMenuRow];
function model(times, track) {
    const l = decode(picture);
    for (let t = 0; t < 8; t++) {
        const [x0, y0] = cell(t);
        text(l, `TRACK ${t + 1}`, x0 + syms.TaMenuTextX, y0 + syms.TgTrackLine, 3);
        if (times[t]) text(l, time(times[t]), x0 + syms.TaMenuTextX, y0 + syms.TgTimeLine, 2);
    }
    const [x0, y0] = cell(track);
    for (let y = y0; y < y0 + syms.TaMenuRow; y++) for (let x = x0; x < x0 + 160; x++)
        if (y === y0 || y === y0 + syms.TaMenuRow - 1 || x === x0 || x === x0 + 159) l[y * 320 + x] ^= 2;
    return l;
}
// the track's screen: the picture's lines above the cells, the track's map (its cell's first 84 pixels) in the first
// cell's place, the title and the entries; lit, the place of the entry just made (step 6g): its row all yellow, and if
// typed is given its name that and the cursor (#) after it if shown and there's room
function trackModel(track, entries, levels = [0, 0, 0], cursor = 3, { lit = -1, typed = null, blink = false } = {}) {
    const p = decode(picture), l = new Uint8Array(Lines * 320), [x0, y0] = cell(track), Top = syms.TaMenuTop;
    l.set(p.subarray(0, Top * 320));
    for (let y = 0; y < syms.TaMenuRow; y++) for (let x = 0; x < 4 * syms.TgMapBytes; x++) l[(Top + y) * 320 + x] = p[(y0 + y) * 320 + x0 + x];
    text(l, `TRACK ${track + 1}`, syms.TtTitleX, syms.TtTitleY, 3);
    const left = 5 - levels[0] - levels[1] - levels[2];
    ["SPEED", "ACCEL.", "TRACTION", "RACE"].forEach((label, i) => {
        const y = i < 3 ? syms.TpSpeedY + i * syms.TpStep : syms.TpRaceY, ink = i === 3 && left < 0 ? 1 : i === cursor ? 2 : 3;
        text(l, label, syms.TpX, y, ink);
        if (i < 3) text(l, String(levels[i]), syms.TpValueX, y, ink);
    });
    text(l, "{}", syms.TpX, syms.TpLeftY, 3);
    text(l, String(left), syms.TpX + 18, syms.TpLeftY, left < 0 ? 1 : 3);
    entries.forEach(([t, name, ups = 0], i) => {
        const y = syms.TtRowY + i * syms.TtRowStep, on = i === lit;
        if (on && typed !== null) name = typed + (blink && typed.length < 10 ? "#" : "");
        text(l, String(i + 1).padStart(2), syms.TtPlaceX, y, on ? 2 : 1);
        if (t) {
            text(l, time(t), syms.TtTimeX, y, 2), text(l, name, syms.TtNameX, y, on ? 2 : 3);
            text(l, `S${Math.floor(ups / 36)} A${Math.floor(ups / 6) % 6} T${ups % 6}`, syms.TtUpsX, y, on ? 2 : 1);
        }
    });
    return l;
}

// the frame buffer's colours: 0 black, then red, green, yellow, white; 5 anything else
const s = await bootDisc("build/ta.ssd");
const cpu = s._machine.processor;
const peek = (a) => s.readMemory(a, 1)[0];
const b = s._completeFb8, fb = new Uint32Array(b.buffer, b.byteOffset, b.byteLength / 4);
const Names = ["black", "red", "green", "yellow", "white", "other"];
const kind = (v) => {
    const r = v & 255, g = v >> 8 & 255, bl = v >> 16 & 255, hi = (c) => c > 127;
    if (!r && !g && !bl) return 0;
    if (hi(r) && !g && !bl) return 1;
    if (!r && hi(g) && !bl) return 2;
    if (hi(r) && hi(g) && !bl) return 3;
    if (hi(r) && hi(g) && hi(bl)) return 4;
    return 5;
};
const Rgb = [[0, 1, 3, 4], [0, 2, 3, 4]];   // (logical colours' kinds: over the logo, then under it)
let field = 0, steady = 0, checked = 0, onTrack = false;   // (a track's screen: colour 1 red on its upgrades left's and RACE's lines too)
// a field shown: its colours, and if want's given every line's as want's (a model), or as one of want's (an array:
// before and after a key, nothing half drawn between)
function shown(want) {
    field++;
    const wants = !want ? [] : Array.isArray(want) ? want : [want], ok = wants.map(() => true);
    let first = "";
    for (let y = 0; y < Lines; y++) for (const half of [0, 1]) {
        const row = (Top32 + 2 * y + half) * Width, count = [0, 0, 0, 0, 0, 0];
        for (let x = 0; x < Width; x++) count[kind(fb[row + x])]++;
        const red = y < Logo || onTrack && (y >= syms.TaRedTop && y <= syms.TaRedBottom || y >= syms.TaRaceTop && y <= syms.TaRaceBottom);
        if (red ? count[2] : count[1] || count[5]) {
            say(`field ${field}, line ${y}: ${count[2]} green, ${count[1]} red, ${count[5]} other`);
            return;
        }
        if (half) continue;
        wants.forEach((w, i) => {
            if (!ok[i]) return;
            const expect = [0, 0, 0, 0, 0, 0];
            for (let x = 0; x < 320; x++) expect[Rgb[red ? 0 : 1][w[y * 320 + x]]] += 2;
            if ([1, 2, 3, 4].some((k) => count[k] !== expect[k])) {
                ok[i] = false;
                if (process.env.DBG) console.log(`  want ${i}: line ${y} ${[1, 2, 3, 4].map((k) => count[k])} not ${[1, 2, 3, 4].map((k) => expect[k])}`);
                first ||= `line ${y}: ${[1, 2, 3, 4].map((k) => `${count[k]} ${Names[k]}`).join(", ")}, not ${[1, 2, 3, 4].map((k) => expect[k]).join(", ")}`;
            }
        });
    }
    if (!wants.length) return;
    if (ok.some(Boolean)) steady++;
    else say(`field ${field}, ${wants.length > 1 ? "neither before the key nor after, " : ""}${first}`);
}

// fields run, each shown checked; stopped early at stop (an address in the background's bank, or the race's start)
async function run(fields, want, stop) {
    const id = stop ? s.addBreakpoint("execute", stop, {}) : null;
    try {
        for (let n = 0, left = Field; n < fields;) {
            s.resetBreakpointHits();
            settle(s);
            const before = s.elapsedCycles;
            await s.runFor(left);
            left -= Math.max(s.elapsedCycles - before, 1);
            const hit = s.hitBreakpoint();
            if (hit && hit.address === stop && (stop === syms.start || (cpu.romsel & 15) === peek(syms.bankbg))) return true;
            if (left > 0) continue;
            left = Field;
            n++;
            shown(want);
        }
        return false;
    } finally {
        if (id !== null) s.removeBreakpoint(id);
    }
}
const idle = syms["game_resume.idle"];
const toMenu = async () => { if (!await run(4000, null, idle)) { say("the menu never reached"); process.exit(1); } };
const screen = (what, want) => {
    const got = ram(s, syms.FrontAddr, 20480), w = encode(want);
    let n = 0, first = -1;
    for (let i = 0; i < w.length; i++) if (got[i] !== w[i]) { if (first < 0) first = i; n++; }
    if (n) say(`${what}: ${n} bytes of the screen not the model's (the first &${(syms.FrontAddr + first).toString(16)}: &${got[first].toString(16)}, not &${w[first].toString(16)})`);
    else checked++;
};

await toMenu();
// the bests poked: none (track 2), under 10 s, over, 99.98, past it; the title's file loaded and the menu drawn again
const times = [342, 0, 515, 428, 4999, 553, 6000, 296];
const bc = peek(syms.bankcars), romsel = cpu.romsel;
cpu.romSelect(bc);
for (let t = 0; t < 8; t++) s.writeMemory(syms.TaTimeLo + t * 10, [times[t] & 255]), s.writeMemory(syms.TaTimeHi + t * 10, [times[t] >> 8]);
cpu.romSelect(romsel);
s.writeMemory(syms.LoadWant, ["F".charCodeAt(0) - 48]);
if (!await run(4000, null, syms["game_resume.menu"])) say("the title's load: no menu after it");
await toMenu();
screen("drawn, track 1 highlighted", model(times, 0));
await run(10, model(times, 0));
s.keyDown("KeyW");                      // (player 1's right)
await run(3, null);
s.keyUp("KeyW");
await run(3, null);
if (peek(syms.GmTrack) !== 4) say(`right: GmTrack ${peek(syms.GmTrack)}, not 4`);
screen("the highlight moved to track 5", model(times, 4));
await run(10, model(times, 4));
// the track's screen: Return on track 5, its entries poked (the first as its best on the menu)
const entries = [[times[4], "TOM", 2 * 36 + 6 + 2], [296, "WWWWWWWWWW", 30], [0, "GONE", 5], [553, "", 5], [1000, "A.B!", 43],
    [6000, "0123456789", 0], [2600, "XYZ 81", 180], [515, "CDEFGHIJKL", 215], [0, ""], [428, "MNOPQRSUV", 1]];
cpu.romSelect(bc);
entries.forEach(([t, name, ups = 0], i) => {
    const e = 40 + i, n = [...name].map((c) => c.charCodeAt(0));
    while (n.length < 10) n.push(0);
    s.writeMemory(syms.TaTimeLo + e, [t & 255]), s.writeMemory(syms.TaTimeHi + e, [t >> 8]), s.writeMemory(syms.TaNames + e * 10, n);
    s.writeMemory(syms.TaUps + e, [ups]);
});
cpu.romSelect(romsel);
s.keyDown("Enter");
await run(3, null);
s.keyUp("Enter");
await toMenu();
onTrack = true;
if (peek(syms.TgOn) !== 1) say(`Return: TgOn ${peek(syms.TgOn)}, not 1`);
screen("track 5's screen", trackModel(4, entries));
await run(10, trackModel(4, entries));
// the upgrades: speed 3, acceleration 2, traction 1 (one too many), the cursor passing over RACE, and Return racing
// nothing. Each key's fields, held and let go, either the screen before it or after (D49's rules, as below), nothing
// half drawn between.
const panel = { levels: [0, 0, 0], cursor: 3 };
const key = async (k) => {
    const left = () => 5 - panel.levels.reduce((a, b) => a + b);
    const before = trackModel(4, entries, panel.levels, panel.cursor);
    if (k === "KeyE" && panel.cursor < 3) panel.levels[panel.cursor] = (panel.levels[panel.cursor] + 1) % 6;
    const d = { KeyW: 1, KeyQ: 3 }[k];
    if (d) {
        panel.cursor = (panel.cursor + d) % 4;
        if (panel.cursor === 3 && left() < 0) panel.cursor = (panel.cursor + d) % 4;
    }
    const after = trackModel(4, entries, panel.levels, panel.cursor);
    s.keyDown(k); await run(3, [before, after]); s.keyUp(k); await run(3, [before, after]);
};
for (const k of ["KeyW", "KeyE", "KeyE", "KeyE", "KeyW", "KeyE", "KeyE", "KeyW", "KeyE"]) await key(k);
screen("the upgrades 3, 2, 1: -1 left", trackModel(4, entries, [3, 2, 1], 2));
await run(10, trackModel(4, entries, [3, 2, 1], 2));
await key("KeyW");
screen("-1 left, right from TRACTION: SPEED", trackModel(4, entries, [3, 2, 1], 0));
await key("KeyQ");
screen("-1 left, left from SPEED: TRACTION", trackModel(4, entries, [3, 2, 1], 2));
await key("Enter");
await run(10, null);
if (peek(syms.LoadWant) || peek(syms.TgOn) !== 1) say(`Return with -1 left: LoadWant ${peek(syms.LoadWant)}, TgOn ${peek(syms.TgOn)}`);
s.keyDown("Escape");
await run(3, null);
s.keyUp("Escape");
await toMenu();
onTrack = false;
if (peek(syms.TgOn) !== 0) say(`Escape: TgOn ${peek(syms.TgOn)}, not 0`);
screen("Escape: the menu again", model(times, 4));
await run(10, model(times, 4));
s.keyDown("Digit5");
await run(3, null);
s.keyUp("Digit5");
await toMenu();
onTrack = true;
if (peek(syms.TgOn) !== 1 || peek(syms.GmTrack) !== 4) say(`5: TgOn ${peek(syms.TgOn)}, GmTrack ${peek(syms.GmTrack)}, not track 5's screen`);
panel.cursor = 0;
screen("5: track 5's screen, -1 left", trackModel(4, entries, [3, 2, 1], 0));
await run(10, trackModel(4, entries, [3, 2, 1], 0));
// traction round to 0, the cursor to RACE
await key("KeyQ");
for (let n = 0; n < 5; n++) await key("KeyE");
await key("KeyW");
screen("traction round to 0, the cursor on RACE", trackModel(4, entries, [3, 2, 0], 3));
await run(10, trackModel(4, entries, [3, 2, 0], 3));
s.keyDown("Enter");
if (!await run(4000, null, syms.start)) say("Return on track 5's screen raced nothing");
s.keyUp("Enter");
await run(5, null);                     // (the race's first fields: nothing red, as the logo's lines go)

// the name (step 6g, D39, D49, D50): the race's best poked, Escape: its entry the first of track 5's 10, the row lit,
// the name typed with the cursor after it (Delete, ! by SHIFT and 1, to 10 and an 11th ignored), every field of each key the row before it or after it (the cursor shown
// or not), nothing half drawn; Return: "Saving" in the HUD's row, nothing else lit till the screen's drawn again, no
// file read; TIMES then holding the name; track 5's screen again, the row lit; Escape and 5: the row as the others
const bt = peek(syms.banktrace), Best = 400, Ups = 3 * 36 + 2 * 6;
for (let n = 0; n < 20; n++) await runToAny(s, [[syms["logic_frame.played"], bt]], 8000000);
s.writeMemory(syms.TaBestLo, [Best & 255, Best >> 8]);   // (ANDY's, paged in here)
let named = [[Best, "", Ups], ...entries.slice(0, 9)];
s.keyDown("Escape");
await runToAny(s, [[syms["tg_type.field"], peek(syms.bankbg)]], 400000000);   // (the race's own screen not checked here)
let typed = "";
const naming = (t) => [false, true].map((blink) => trackModel(4, named, [3, 2, 0], 3, { lit: 0, typed: t, blink }));
await run(10, naming(""));              // (Escape still held: nothing typed)
s.keyUp("Escape");
await run(5, naming(""));
for (const [keys, after] of [[["KeyT"], "T"], [["KeyO"], "TO"], [["KeyM"], "TOM"], [["Backspace"], "TO"], [["KeyN"], "TON"],
    [["ShiftLeft", "Digit1"], "TON!"], [["Space"], "TON! "], [["Digit1"], "TON! 1"], [["Digit2"], "TON! 12"], [["Period"], "TON! 12."],
    [["Minus"], "TON! 12.-"], [["KeyZ"], "TON! 12.-Z"], [["KeyQ"], "TON! 12.-Z"]]) {   // (10, the most: Q ignored)
    const want = [...naming(typed), ...naming(after)];
    for (const k of keys) s.keyDown(k);
    await run(3, want);
    for (const k of keys) s.keyUp(k);
    await run(3, want);
    typed = after;
}
await run(40, naming(typed));           // (the cursor on and off)
const names = [];
const hook = (pc) => { if (pc === syms.row_char) names.push(String.fromCharCode(cpu.a)); return false; };
cpu.debugInstruction.add(hook);
s.keyDown("Enter");
let reads = 0, tripFields = 0, said = 0, dark = false;   // (from the screen gone black: the screen's still up till then, 3 fields at most)
const osfile = (pc) => { if (pc === 0xffdd && cpu.a === 0xff) reads++; return false; };
cpu.debugInstruction.add(osfile);
const shownAt = syms["game_resume.shown"], id = s.addBreakpoint("execute", shownAt, {});
for (let left = Field; ;) {             // (to the screen's redraw: the HUD's row alone lit)
    s.resetBreakpointHits();
    settle(s);
    const before = s.elapsedCycles;
    await s.runFor(left);
    const hit = s.hitBreakpoint();
    left -= Math.max(s.elapsedCycles - before, 1);
    if (hit && (cpu.romsel & 15) === peek(syms.bankbg)) break;
    if (left > 0) continue;
    left = Field;
    if (++tripFields === 3) s.keyUp("Enter");
    let out = 0, row = 0;
    for (let i = 0; i < fb.length; i++) if (fb[i] & 0xffffff) { const y = Math.floor(i / Width); if (y >= Top && y < Top + 16) row++; else out++; }
    if (!dark && !out && !row) dark = true;
    if (!dark && tripFields <= 3) continue;
    if (out) say(`the save's trip, field ${tripFields}: ${out} pixels lit outside the HUD's row`);
    if (row) said++;
    if (tripFields > 1000) { say("the save's trip: no screen after 1000 fields"); break; }
}
s.removeBreakpoint(id);
cpu.debugInstruction.remove(hook);
cpu.debugInstruction.remove(osfile);
if (names.join("") !== "Saving" || !said || reads) say(`the save's trip: "${names.join("")}" written, the row lit ${said} fields, ${reads} files read, not "Saving", some and none`);
await toMenu();
named = [[Best, "TON! 12.-Z", Ups], ...entries.slice(0, 9)];
const times5 = discFiles(toSsdOrDsd(cpu.fdc.drives[0].disc)).TIMES;
const name40 = times5 && String.fromCharCode(...times5.data.subarray(3 * 80 + 400, 3 * 80 + 410));
if (!times5 || (times5.data[40] | times5.data[120] << 8) !== Best || name40 !== "TON! 12.-Z") say(`the save: TIMES ${times5 ? `track 5's first ${times5.data[40] | times5.data[120] << 8}, ${JSON.stringify(name40)}` : "none"}, not ${Best} and TON! 12.-Z`);
screen("the name saved: track 5's screen, the new entry lit", trackModel(4, named, [3, 2, 0], 3, { lit: 0 }));
await run(10, trackModel(4, named, [3, 2, 0], 3, { lit: 0 }));
s.keyDown("Escape");
await run(3, null);
s.keyUp("Escape");
await toMenu();
onTrack = false;
await run(5, null);
s.keyDown("Digit5");
await run(3, null);
s.keyUp("Digit5");
await toMenu();
onTrack = true;
screen("Escape and 5: track 5's screen, nothing lit", trackModel(4, named, [3, 2, 0], 3));
await run(10, trackModel(4, named, [3, 2, 0], 3));

console.log(bad ? `${bad} wrong` : `the menu's and the track's screen's 32 rows as the model (${checked} screens: the picture, the 8 tracks' text and bests, the box moved, track 5's screen, its upgrades set and over, the cursor over RACE both ways, the menu again, track 5's by its number, put right, a race's entry named and lit, then not); the name typed field by field, its save's trip "Saving" alone (${tripFields} fields); ${field} fields from the boot to a race: no green on the logo's lines nor red under them, and ${steady} of the menu's every line's colours as the model's`);
process.exit(bad ? 1 : 0);
