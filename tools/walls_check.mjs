// column_hit (src/walls.6502), a wall probe's side column, against tools/maskb.py's mask B: 3,000 random cars'
// places, columns and lines on the track, each called on the BBC (build/logic.ssd, its bank paged, mask B as
// stored) and compared with the pixels the lines cover. Exit status 1 if any differs.
//
// The race oracles test it only where the traced cars go: a fault in a wall cell found through a row's map
// (the flags mask_cell leaves) passed the hazard race's 2,239 frames; this found it at once.
//
// Usage (from the repo root, after make logic): node tools/walls_check.mjs [TRACK]   (the logic build's track)

import { execFileSync } from "node:child_process";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";
const track = Number(process.argv[2] ?? 0);
const want = execFileSync(".venv/bin/python", ["-c",
    `import sys; sys.path.insert(0, 'tools'); import maskb; ` +
    `sys.stdout.buffer.write(bytes(b for row in maskb.mask_bytes(${track}) for b in row))`]);
const px = (x, y) => (want[y * 40 + (x >> 3)] >> (7 - (x & 7))) & 1;
const syms = symbols("build/logic.json");
const s = await bootDisc("build/logic.ssd");
await runTo(s, syms["test_entry.loaded"]);
const cpu = s._machine.processor;
if (!(cpu.romsel & 0x80)) { console.log("ANDY isn't paged in (ROMSEL's bit 7): mask B isn't where the game has it"); process.exit(1); }
const Stub = 0x7000, Out = 0x7010, f = syms["column_hit"];
s.writeMemory(Stub, [0x20, f & 0xff, f >> 8, 0x8d, Out & 0xff, Out >> 8, 0x4c, (Stub + 6) & 0xff, (Stub + 6) >> 8]);
let bad = 0, n = 0, seed = 1;
const rnd = (m) => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % m; };
for (let k = 0; k < 3000; k++) {
    const x = rnd(300), y = rnd(186), c = rnd(17), lines = rnd(4096);
    s.writeMemory(syms.RcXLo, [x & 255]); s.writeMemory(syms.RcXHi, [x >> 8]); s.writeMemory(syms.RcYLo, [y]);
    const sh = lines << (y & 7);                    // (the lines as the walls' tables have them: to y's place in its cell)
    s.writeMemory(syms["column_hit.lines"], [sh & 255, (sh >> 8) & 255, sh >> 16]);
    cpu.pc = Stub; cpu.a = c; cpu.x = 0; cpu.s = 0xff;
    await runTo(s, Stub + 6, 100000);
    const got = s.readMemory(Out, 1)[0] !== 0;
    let exp = false;
    for (let l = 0; l < 12; l++) if ((lines >> l) & 1 && y + l < 200 && px(x + c, y + l)) exp = true;
    n++;
    if (got !== exp && bad++ < 5) console.log(`x ${x} y ${y} col ${c} lines ${lines.toString(2)}: BBC ${got}, want ${exp}`);
}
console.log(bad ? `${bad} of ${n} wrong` : `all ${n} match`);
process.exit(bad ? 1 : 0);
