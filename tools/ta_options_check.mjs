// Time attack's options (docs/brief-timeattack-2026-11-10.md, step 6i; D54; options.6502 as time attack builds it),
// driven on build/ta.ssd as tools/options_check.mjs drives the game's: F1 from the menu; the screen byte for byte
// against a model (the menu's picture above its cells, the rest cleared; each key set's SET n, Fn TO CHANGE in its
// colour and LEFT, RIGHT, ACCEL. in white in the small font; each key's name in the MOS's font in the player's
// colour, in inverse while held; the status line as the game's, the build's version in its right end); F2-F4 asking
// for keys, refusing the game's own and those taken, Escape putting them back; the warning against tools/keys_ghost.py's
// model on random layouts; F9 and the sound's field; F0 out to the menu, F1 and Escape out again, the highlight
// kept; the new keys driving the race's car.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make ta): node tools/ta_options_check.mjs

import { readFileSync } from "node:fs";
import { andy, bootDisc, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, F = { f0: 32, f1: 113, f2: 114, f3: 115, f4: 20, f5: 116, f9: 119, esc: 112 };
const Q = 16, W = 33, E = 34, COMMA = 102, PERIOD = 103, SLASH = 104, PAD5 = 123, PAD6 = 26, PADDEL = 75;   // (the defaults, D12)
const A = 65, S = 81, D = 50, RETURN = 73, LEFT = 25, SPACE = 98;
const syms = symbols("build/tracks_ta/t0.json");
const s = await bootDisc("build/ta.ssd");
const cpu = s._machine.processor, peek = (a, n = 1) => [...s.readMemory(a, n)];
// to address a in the background's bank (its address alone is reached in ROMs too, during the boot)
async function toBg(a) {
    for (;;) {
        await runToAny(s, [[a]], 400000000);
        if ((cpu.romsel & 15) === peek(syms.bankbg)[0]) return;
        await s.runFor(1000);
    }
}
await toBg(syms["game_resume.idle"]);
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };
const raw = (n) => [n & 15, n >> 4];
const run = async (fields) => { settle(s); await s.runFor(fields * Field); };
const down = (n) => s.keyDownRaw(raw(n)), up = (n) => s.keyUpRaw(raw(n));
const tap = async (n) => { down(n); await run(4); up(n); await run(4); };
const same = (what, got, want) => { if (got.join() !== want.join()) say(`${what}: ${got}, not ${want}`); };

// F1
await run(5);
down(F.f1);
await toBg(syms.options_shown);
up(F.f1);
await run(4);
const count = syms.OptNames - syms.OptNumbers;
const table = new Map(peek(syms.OptNumbers, count).map((k, i) => [k, peek(syms.OptNames + i)[0]]));
const words = Buffer.from(peek(syms.OptWords + 1, 200)).toString("latin1").split("\0");
const nameOf = (k) => { const n = table.get(k); return n < 32 ? words[n - 1] : String.fromCharCode(n); };

// the model: the menu's picture above its cells, the small font's words in logical colours, then MODE 1's bytes
const Lines = 256, at = (y, c) => (y >> 3) * 640 + c * 8 + (y & 7);
const picture = readFileSync("build/gen/tamenu.bin");
const gen = readFileSync("build/gen/front.6502", "utf8"), tableOf = (n) => gen.match(new RegExp(`^${n} = \\{([^}]*)\\}`, "m"))[1].split(",").map(Number);
const small = [...tableOf("SmallFont"), ...tableOf("TaGlyphs")];
const glyph = (ch) => ch === "." ? 10 : ch >= "A" ? 12 + ch.charCodeAt(0) - 65 : Number(ch);
const logical = new Uint8Array(Lines * 320);
for (let y = 0; y < syms.TaMenuTop; y++) for (let c = 0; c < 80; c++) {
    const b = picture[at(y, c)];
    for (let n = 0; n < 4; n++) logical[y * 320 + c * 4 + n] = (b >> (7 - n) & 1) * 2 + (b >> (3 - n) & 1);
}
function text(str, x, y, ink) {
    for (const ch of str) {
        if (ch !== " ") for (let line = 0; line < 6; line++) for (let j = 0; j < 6; j++)
            if (small[glyph(ch) * 6 + line] >> (7 - j) & 1) logical[(y + line) * 320 + x + j] |= ink;
        x += 6;
    }
}
const Col = (car) => 8 + car * 104, Ink = [3, 1, 2];   // (a player's column, D54's layout; white, green, yellow)
for (let car = 0; car < 3; car++) {
    text(`SET ${car + 1}`, Col(car), syms.OptHeadY, Ink[car]);
    text(`F${car + 2} TO CHANGE`, Col(car), syms.OptChangeY, Ink[car]);
    ["LEFT", "RIGHT", "ACCEL."].forEach((w, row) => text(w, Col(car), (syms.OptKeyRow + row * 2) * 8 + 1, 3));
}
const base = new Uint8Array(20480);
for (let y = 0; y < Lines; y++) for (let c = 0; c < 80; c++) {
    let b = 0;
    for (let n = 0; n < 4; n++) { const v = logical[y * 320 + c * 4 + n]; b |= (v >> 1) << (7 - n) | (v & 1) << (3 - n); }
    base[at(y, c)] = b;
}
// (each status line with the build's version in its right end, green: tools/version.py's; the game's lines' bytes, a row's)
const version = readFileSync("build/gen/options_version.bin");
const lines = Object.fromEntries(["on", "off", "clash"].map((n) => [n, readFileSync(`build/gen/options_${n}.bin`).map((b, i) => b | version[i])]));
const romFont = (() => {        // the MOS's font, from ROM 15
    const out = [], keep = cpu.romsel;
    cpu.romSelect(15);
    for (let c = 32; c < 256; c++) out[c] = peek(0xb900 + (c - 32) * 8, 8);
    cpu.romSelect(keep);
    return out;
})();
const expand = (n) => (n << 4) | n, Masks = [0xff, 0xff, 0xff, 0x0f, 0x0f, 0x0f, 0xf0, 0xf0, 0xf0];
function field(slot, key, inverse) {    // the 112 bytes of a key's name
    const out = new Uint8Array(112), name = key === undefined ? "" : nameOf(key), mask = Masks[slot];
    for (let i = 0; i < name.length; i++)
        for (let y = 0; y < 8; y++) {
            const g = romFont[name.charCodeAt(i)][y];
            out[i * 16 + y] = expand(g >> 4) & mask;
            out[i * 16 + 8 + y] = expand(g & 15) & mask;
        }
    return inverse ? out.map((b) => b ^ mask) : out;
}
const fieldAt = (slot) => (syms.OptKeyRow + (slot % 3) * 2) * 640 + ((Col(Math.floor(slot / 3)) + 44) >> 2) * 8;
const keysNow = () => peek(syms.PlayerKeys, 9);
function screen(what, line, inverse = []) {
    const want = Buffer.from(base), keys = keysNow();
    keys.forEach((k, i) => Buffer.from(field(i, k, inverse.includes(i))).copy(want, fieldAt(i)));
    lines[line].copy(want, 31 * 640);
    const got = ram(s, syms.FrontAddr, 20480);
    let diff = 0, first = -1;
    for (let i = 0; i < 20480; i++) if (got[i] !== want[i]) { diff++; if (first < 0) first = i; }
    if (diff) say(`${what}: ${diff} bytes differ (the first &${(syms.FrontAddr + first).toString(16)}: &${got[first].toString(16)}, not &${want[first].toString(16)})`);
}

screen("the options", "on");
same("the keys to start with", keysNow(), [Q, W, E, COMMA, PERIOD, SLASH, PAD5, PAD6, PADDEL]);

// the markers
down(W);
await run(3);
screen("W held", "on", [1]);
up(W);
await run(3);
screen("W up", "on");
const nine = keysNow();
nine.forEach(down);
await run(3);
screen("all 9 held", "on", [0, 1, 2, 3, 4, 5, 6, 7, 8]);
nine.forEach(up);
await run(3);
screen("all 9 up", "on");

// redefining
await tap(F.f2);
for (const k of [A, S, D]) await tap(k);
same("F2's keys", keysNow(), [A, S, D, COMMA, PERIOD, SLASH, PAD5, PAD6, PADDEL]);
screen("the new keys", "on");
await tap(F.f3);
await tap(A);                           // taken
await tap(F.f5);                        // the game's own
await tap(F.esc);
same("Escape, and what was refused", keysNow(), [A, S, D, COMMA, PERIOD, SLASH, PAD5, PAD6, PADDEL]);
screen("Escape", "on");
if (peek(syms.TgOn)[0] !== 0) say("Escape while asking for keys: the options left");
await tap(F.f4);
for (const k of [RETURN, LEFT, SPACE]) await tap(k);
same("F4's keys", keysNow(), [A, S, D, COMMA, PERIOD, SLASH, RETURN, LEFT, SPACE]);
screen("words and an arrow", "on");
await tap(F.f4);
for (const k of [0x4b, 0x7a, 0x3c]) await tap(k);
same("the keypad's keys", keysNow(), [A, S, D, COMMA, PERIOD, SLASH, 0x4b, 0x7a, 0x3c]);
screen("the keypad", "on");
await tap(F.f4);
for (const k of [RETURN, LEFT, SPACE]) await tap(k);

// the warning, against the model's: a key ghosts if its row and column are joined through the others
function ghosts(keys) {
    return keys.some((key, i) => {
        const others = keys.filter((_, j) => j !== i), seen = new Set([`r${key >> 4}`]);
        for (let grew = true; grew;) {
            grew = false;
            for (const k of others) {
                const r = `r${k >> 4}`, c = `c${k & 15}`;
                if (seen.has(r) !== seen.has(c)) { seen.add(r); seen.add(c); grew = true; }
            }
        }
        return seen.has(`c${key & 15}`);
    });
}
const usable = [...table].filter(([, n]) => n).map(([k]) => k);
let seed = 12345, clashes = 0, tried = 0;
const random = (n) => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) % n;
const start = keysNow();
for (let i = 0; i < 40; i++) {
    const pool = [...usable], keys = [];
    const narrow = i % 2 ? pool.filter((k) => (k >> 4) >= 3 && (k >> 4) <= 5 && (k & 15) < 5) : pool;
    while (keys.length < 9) keys.push(narrow.splice(random(narrow.length), 1)[0]);
    s.writeMemory(syms.PlayerKeys, keys);
    await tap(F.f9);
    await tap(F.f9);
    const c = ghosts(keys), row = ram(s, syms.FrontAddr + 31 * 640, 640), line = lines[c ? "clash" : "on"];
    if (row.some((v, j) => v !== line[j])) say(`layout ${keys}: the status line wrong, ${c ? "a clash" : "no clash"} wanted`);
    clashes += c;
    tried++;
}
if (!clashes || clashes === tried) say(`the layouts tried: ${clashes} of ${tried} clash`);
s.writeMemory(syms.PlayerKeys, start);
await tap(F.f9);
await tap(F.f9);

// the sound: its field runs only with it on
async function fieldRuns() {
    const id = s.addBreakpoint("execute", syms.sound_irq);
    s.resetBreakpointHits();
    settle(s);
    await s.runFor(4 * Field);
    const hit = !!s.hitBreakpoint();
    s.removeBreakpoint(id);
    return hit;
}
if (!(await fieldRuns())) say("the sound's field not running with the sound on");
await tap(F.f9);
same("F9", peek(syms.SoundOff), [1]);
screen("sound off", "off");
if (await fieldRuns()) say("the sound's field running with the sound off");
await tap(F.f9);
same("F9 again", peek(syms.SoundOff), [0]);
screen("sound on", "on");

// out: F0 to the menu, the highlight where it was; in again and out by Escape
const menuShown = async (what) => {
    await toBg(syms["game_resume.shown"]);
    if (peek(syms.TgOn)[0] !== 0 || peek(syms.GmTrack)[0] !== 0) say(`${what}: TgOn ${peek(syms.TgOn)}, GmTrack ${peek(syms.GmTrack)}, not the menu's track 1`);
};
down(F.f0);
await run(4);
up(F.f0);
await menuShown("F0");
await run(10);
down(F.f1);
await toBg(syms.options_shown);
up(F.f1);
await run(4);
screen("in again", "on");
down(F.esc);
await run(4);
up(F.esc);
await menuShown("Escape");
await run(10);

// the new keys drive: track 1's screen and its race (Return, then Return), S (player 1's right now) held
await tap(RETURN);
await toBg(syms["game_resume.idle"]);
await run(5);
down(RETURN);
await runToAny(s, [[syms.frame_loop]], 800000000);
up(RETURN);
same("the keys after a track's load", keysNow(), [A, S, D, COMMA, PERIOD, SLASH, RETURN, LEFT, SPACE]);
const banktrace = peek(syms.banktrace)[0];
down(S);
for (let n = 0; n < 3; n++) await runToAny(s, [[syms["logic_frame.built"], banktrace]], 8000000);
same("S, a redefined key, read as the car's", [...andy(s, syms.RcInput, 1)], [8]);
up(S);

console.log(wrong ? `${wrong} wrong` : `the options right: the screen as the model (F1 from the menu, F0 and Escape back to it), ${tried} layouts, ${clashes} with a clash, the new keys driving`);
process.exit(wrong ? 1 : 0);
