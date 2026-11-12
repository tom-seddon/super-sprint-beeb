// Time attack's menu's picture (docs/brief-timeattack-2026-11-10.md, step 6d; D47; tagame.6502), on build/ta.ssd from
// a fresh boot:
// - the screen: the 8 tracks' bests poked into the table (none, under 10 s, over, 99.98 and past it), the menu drawn
//   again (a title's load) and its 32 rows in main RAM byte for byte as a model has them: tools/screens.py's picture
//   (build/gen/tamenu.bin), each track's "TRACK n" in white and its best in yellow, " 9.56", in the small font (the
//   build's table, build/gen/front.6502's SmallFont), and the yellow box round the highlighted track; again once the
//   highlight's moved (the box EOR'd: out of one cell, into the next);
// - as shown, every field from the boot's menu to a race's first frame (the frame buffer, as tools/ta_rows_check.mjs
//   reads it): no green on the logo's lines (colour 1 red there, the interrupt's TaSplit) and no red under them; and
//   while the menu's up, each of its 256 lines' colours as the model's, pixel for pixel counted (two of the frame
//   buffer's a pixel across, two lines a line), colour 1 red to the logo's end and green from there.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_picture_check.mjs

import { readFileSync } from "node:fs";
import { bootDisc, ram, settle, symbols } from "./jsbeeb.mjs";

const syms = symbols("build/tracks_ta/t0.json");
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
const font = readFileSync("build/gen/front.6502", "utf8").match(/^SmallFont = \{([^}]*)\}/m)[1].split(",").map(Number);
const glyph = (ch) => ch === "." ? 10 : ch >= "A" ? 12 + ch.charCodeAt(0) - 65 : Number(ch);
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
let field = 0, steady = 0, checked = 0;
function shown(want) {
    field++;
    for (let y = 0; y < Lines; y++) for (const half of [0, 1]) {
        const row = (Top32 + 2 * y + half) * Width, count = [0, 0, 0, 0, 0, 0];
        for (let x = 0; x < Width; x++) count[kind(fb[row + x])]++;
        if (y < Logo ? count[2] : count[1] || count[5]) {
            say(`field ${field}, line ${y}: ${count[2]} green, ${count[1]} red, ${count[5]} other`);
            return;
        }
        if (!want || half) continue;
        const expect = [0, 0, 0, 0, 0, 0];
        for (let x = 0; x < 320; x++) expect[Rgb[y < Logo ? 0 : 1][want[y * 320 + x]]] += 2;
        if ([1, 2, 3, 4].some((k) => count[k] !== expect[k])) {
            say(`field ${field}, line ${y}: ${[1, 2, 3, 4].map((k) => `${count[k]} ${Names[k]}`).join(", ")}, not ${[1, 2, 3, 4].map((k) => expect[k]).join(", ")}`);
            return;
        }
    }
    if (want) steady++;
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
s.keyDown("Digit6");
if (!await run(4000, null, syms.start)) say("6 raced nothing");
s.keyUp("Digit6");
await run(5, null);                     // (the race's first fields: nothing red, as the logo's lines go)

console.log(bad ? `${bad} wrong` : `the menu's 32 rows as the model (${checked} screens: the picture, the 8 tracks' text and bests, the box moved); ${field} fields from the boot to a race: no green on the logo's lines nor red under them, and ${steady} of the menu's every line's colours as the model's`);
process.exit(bad ? 1 : 0);
