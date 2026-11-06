// The select screen's dial (F_0198B6, step 8): build/game.ssd, a game started and right held, every one of the 16 positions
// compared with tools/screens.py's as it comes round, with the rectangle round its track and nowhere else. game_check only
// sees the positions its traces end on.
//
// Exit status: 1 if a position's wrong or never seen, else 0.
//
// Usage (from the repo root, after make game): node tools/select_check.mjs

import { readFileSync } from "node:fs";
import { bootDisc, ram, runToAny, symbols } from "./jsbeeb.mjs";

const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
const got = syms["game_read.got"], shown = syms["select.shown"], peek = (a) => s.readMemory(a, 1)[0];
const dial = readFileSync("build/gen/select_dial.bin"), base = readFileSync("build/gen/select.bin");
const lineAt = (y) => (y >> 3) * 640 + (y & 7);
const Rects = [[28, 34, 87], [53, 34, 87], [53, 88, 141], [53, 145, 199], [28, 145, 199], [3, 145, 199], [3, 88, 141], [3, 34, 87]];
let bad = 0;
const say = (t) => { console.log(t); bad++; };
for (let started = false; ;) {
    const at = await runToAny(s, [[got, bankbg], [shown, bankbg]], 2000000000);
    if (at === shown) break;
    if (!started && cpu.x === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
}
function compare(p) {
    const screen = ram(s, syms.PlayAddr, 16000);
    let diff = 0;
    for (let l = 0; l < 44; l++) for (let c = 0; c < 16; c++) if (screen[lineAt(94 + l) + (32 + c) * 8] !== dial[p * 704 + l * 16 + c]) diff++;
    if (diff) say(`position ${p}: ${diff} bytes of the dial wrong`);
    Rects.forEach(([col, top], t) => {
        const on = screen[lineAt(top) + (col + 5) * 8] ^ base[lineAt(top) + (col + 5) * 8];
        if ((on === 0xf0) !== (t === p >> 1)) say(`position ${p}: track ${t}'s rectangle ${on ? "on" : "off"}`);
    });
}
const seen = new Set();
let last = -1;
for (let i = 0; i < 400 && seen.size < 16; i++) {
    await runToAny(s, [[got, bankbg]], 40000000);
    const p = peek(syms.SelShown);
    if (p !== last && !seen.has(p)) { compare(p); seen.add(p); }
    last = p;
    s.writeMemory(syms.GsCount, [160]);  // (the time doesn't run out)
    cpu.a = cpu.x === 0 ? 8 : 0;
}
if (seen.size < 16) say(`only ${seen.size} positions seen`);
console.log(bad ? `${bad} wrong` : "all 16 positions of the dial right, the rectangle with them");
process.exit(bad ? 1 : 0);
