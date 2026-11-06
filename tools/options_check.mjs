// The options screen (F_0192A6, step 8; D24), driven on build/game.ssd: F1 from the attract mode; the picture, each key's name
// in the MOS's font, and the status line against tools/screens.py's; a name in inverse while its key's held; F2-F4 asking
// for keys, refusing the game's own and those taken, Escape putting them back; the warning against tools/keys_ghost.py's
// model on random layouts; F9; f0 out to the title, the new keys read by the game, through a track's load too. jsbeeb's
// keyboard doesn't ghost, so what a clash looks like on a real keyboard is left to a real keyboard. The key numbers are
// checked against jsbeeb's own keyboard, for the keys it can name.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/options_check.mjs

import { readFileSync } from "node:fs";
import { andy, bootDisc, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, F = { f0: 32, f1: 113, f2: 114, f3: 115, f4: 20, f5: 116, f9: 119, esc: 112 };
const Q = 16, W = 33, E = 34, V = 99, B = 100, N = 85, COMMA = 102, PERIOD = 103, SLASH = 104;
const A = 65, S = 81, D = 50, RETURN = 73, LEFT = 25, SPACE = 98, ONE = 48, TWO = 49, THREE = 17;
const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };
const raw = (n) => [n & 15, n >> 4];
const run = async (fields) => { settle(s); await s.runFor(fields * Field); };
const down = (n) => s.keyDownRaw(raw(n)), up = (n) => s.keyUpRaw(raw(n));
const tap = async (n) => { down(n); await run(4); up(n); await run(4); };

// the keys jsbeeb can name: its keyboard against the table on the disc
const held = () => s.heldKeys().map(([c, r]) => r * 16 + c);

// F1
down(F.f1);
await runToAny(s, [[syms.options_shown, bankbg]], 400000000);
up(F.f1);
await run(4);
const count = syms.OptNames - syms.OptNumbers;
const peek = (a, n = 1) => [...s.readMemory(a, n)];
const table = new Map(peek(syms.OptNumbers, count).map((k, i) => [k, peek(syms.OptNames + i)[0]]));
const words = Buffer.from(peek(syms.OptWords + 1, 200)).toString("latin1").split("\0");
const nameOf = (k) => { const n = table.get(k); return n < 32 ? words[n - 1] : String.fromCharCode(n); };
const named = { KeyQ: "Q", KeyA: "A", KeyZ: "Z", KeyP: "P", KeyL: "L", KeyM: "M", Digit1: "1", Digit5: "5", Digit0: "0", Space: "SPACE", Enter: "RETURN", Comma: ",", Period: ".", Slash: "/",
    ArrowLeft: "\x88", ArrowRight: "\x89", ArrowDown: "\x8a", ArrowUp: "\x8b", Tab: "TAB", CapsLock: "CAPS", ControlLeft: "CTRL", ShiftLeft: "SHIFT", Backspace: "DELETE", Semicolon: ";",
    Numpad0: "PAD 0", Numpad1: "PAD 1", Numpad2: "PAD 2", Numpad3: "PAD 3", Numpad4: "PAD 4", Numpad5: "PAD 5", Numpad6: "PAD 6", Numpad7: "PAD 7", Numpad8: "PAD 8", Numpad9: "PAD 9",
    NumpadAdd: "PAD +", NumpadSubtract: "PAD -", NumpadMultiply: "PAD *", NumpadDivide: "PAD /", NumpadDecimal: "PAD .", NumpadEnter: "PADRET" };
let keysSeen = 0;
for (const [code, want] of Object.entries(named)) {
    s.keyDown(code);
    const got = held();
    s.keyUp(code);
    if (got.length !== 1 || nameOf(got[0]) !== want) say(`jsbeeb's ${code}: number ${got}, named ${got.length ? nameOf(got[0]) : "nothing"}, not ${want}`);
    else keysSeen++;
}

// what the screen should hold
const frame = readFileSync("build/gen/options.bin"), lines = Object.fromEntries(["on", "off", "clash"].map((n) => [n, readFileSync(`build/gen/options_${n}.bin`)]));
const font = (c) => peek(0xb900 + (c - 32) * 8, 8);
const romFont = (() => {        // the MOS's font, from ROM 15
    const out = [];
    const keep = cpu.romsel;
    cpu.romSelect(15);
    for (let c = 32; c < 256; c++) out[c] = font(c);
    cpu.romSelect(keep);
    return out;
})();
const expand = (n) => (n << 4) | n, Masks = [0xff, 0xff, 0xff, 0x0f, 0x0f, 0x0f, 0xf0, 0xf0, 0xf0];
function field(slot, key, inverse) {    // the 96 bytes of a key's name
    const out = new Uint8Array(96), name = key === undefined ? "" : nameOf(key), mask = Masks[slot];
    for (let i = 0; i < name.length; i++)
        for (let y = 0; y < 8; y++) {
            const g = romFont[name.charCodeAt(i)][y];
            out[i * 16 + y] = expand(g >> 4) & mask;
            out[i * 16 + 8 + y] = expand(g & 15) & mask;
        }
    return inverse ? out.map((b) => b ^ mask) : out;
}
const fieldAt = (slot) => (2 + (slot % 3)) * 640 + (Math.floor(slot / 3) * 27 + 10) * 8;
const keysNow = () => peek(syms.PlayerKeys, 9);
function screen(what, line, inverse = []) {
    const want = Buffer.from(frame), keys = keysNow();
    keys.forEach((k, i) => Buffer.from(field(i, k, inverse.includes(i))).copy(want, fieldAt(i)));
    lines[line].copy(want, 24 * 640);
    const got = ram(s, syms.PlayAddr, 16000);
    let diff = 0;
    for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
    if (diff) say(`${what}: ${diff} bytes differ`);
}
const same = (what, got, want) => { if (got.join() !== want.join()) say(`${what}: ${got}, not ${want}`); };

screen("the options", "on");
same("the keys to start with", keysNow(), [Q, W, E, V, B, N, COMMA, PERIOD, SLASH]);

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
same("F2's keys", keysNow(), [A, S, D, V, B, N, COMMA, PERIOD, SLASH]);
screen("the new keys", "on");
await tap(F.f3);
await tap(A);                           // taken
await tap(F.f5);                        // the game's own
await tap(F.esc);
same("Escape, and what was refused", keysNow(), [A, S, D, V, B, N, COMMA, PERIOD, SLASH]);
screen("Escape", "on");
await tap(F.f4);
for (const k of [RETURN, LEFT, SPACE]) await tap(k);
same("F4's keys", keysNow(), [A, S, D, V, B, N, RETURN, LEFT, SPACE]);
screen("words and an arrow", "on");
await tap(F.f4);
for (const k of [0x4b, 0x7a, 0x3c]) await tap(k);
same("the keypad's keys", keysNow(), [A, S, D, V, B, N, 0x4b, 0x7a, 0x3c]);
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
    const c = ghosts(keys), row = ram(s, syms.PlayAddr + 24 * 640, 640), line = lines[c ? "clash" : "on"];
    if (row.some((v, j) => v !== line[j])) say(`layout ${keys}: the status line wrong, ${c ? "a clash" : "no clash"} wanted`);
    clashes += c;
    tried++;
}
if (!clashes || clashes === tried) say(`the layouts tried: ${clashes} of ${tried} clash`);
s.writeMemory(syms.PlayerKeys, start);
await tap(F.f9);
await tap(F.f9);

// the sound: its field runs only with it on (the attract mode's demos are silent, so the chip wouldn't show it)
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

// out, the keys kept, through the title and a demo's load
down(F.f0);
await run(4);
up(F.f0);
await runToAny(s, [[syms["game_resume.shown"], bankbg]], 800000000);
await runToAny(s, [[syms["game_resume.demo"], bankbg]], 1600000000);
await runToAny(s, [[syms.frame_loop]], 800000000);
same("the keys after a track's load", keysNow(), [A, S, D, V, B, N, RETURN, LEFT, SPACE]);
const banktrace = ram(s, 2, 1)[0];
down(S);
await runToAny(s, [[syms["logic_frame.demo_fire"], banktrace]], 8000000);
await runToAny(s, [[syms["logic_frame.demo_fire"], banktrace]], 8000000);
same("S, a redefined key, read as the car's", [...andy(s, syms.RcInput, 3)], [8, 0, 0]);
up(S);

console.log(wrong ? `${wrong} wrong` : `the options right: ${keysSeen} keys against jsbeeb's, ${tried} layouts, ${clashes} with a clash`);
process.exit(wrong ? 1 : 0);
