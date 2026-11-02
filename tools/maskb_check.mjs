// mask_row and row_byte (src/walls.6502) against tools/maskb.py's mask B: every one of the track's 8,000 bytes read on the
// BBC, from build/logic.ssd's logic bank, and compared (D13). Exit status 1 if any differs.
//
// Usage (from the repo root, after make logic): node tools/maskb_check.mjs [TRACK]   (the trace's track, 0)

import { execFileSync } from "node:child_process";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const track = Number(process.argv[2] ?? 0);
const want = execFileSync(".venv/bin/python", ["-c",
    `import sys; sys.path.insert(0, 'tools'); import maskb; ` +
    `sys.stdout.buffer.write(bytes(b for row in maskb.mask_bytes(${track}) for b in row))`]);
const syms = symbols("build/logic.json");
const s = await bootDisc("build/logic.ssd");
await runTo(s, syms["test_entry.loaded"]);           // the logic's bank filled and paged in, before the race's
                                                     // set-up draws the gates and barriers into it
const cpu = s._machine.processor;
if (!(cpu.romsel & 0x80)) { console.log("ANDY isn't paged in (ROMSEL's bit 7): mask B isn't where the game has it"); process.exit(1); }
const Stub = 0x7000, Out = 0x7010, mr = syms["mask_row"], rb = syms["row_byte"];
s.writeMemory(Stub, [0x20, mr & 0xff, mr >> 8, 0xa9, 0, 0x20, rb & 0xff, rb >> 8, 0x8d, Out & 0xff, Out >> 8,
    0x4c, (Stub + 11) & 0xff, (Stub + 11) >> 8]);
let bad = 0;                                         // JSR mask_row : LDA #c : JSR row_byte : STA Out : JMP *
for (let y = 0; y < 200; y++)
    for (let c = 0; c < 40; c++) {
        s.writeMemory(Stub + 4, [c]);
        cpu.pc = Stub; cpu.y = y; cpu.s = 0xff;
        await runTo(s, Stub + 11, 100000);
        const got = s.readMemory(Out, 1)[0];
        if (got !== want[y * 40 + c] && bad++ < 5) console.log(`column ${c} row ${y}: BBC &${got.toString(16)}, mask B &${want[y * 40 + c].toString(16)}`);
    }
console.log(bad ? `${bad} of 8,000 bytes wrong` : "all 8,000 bytes match");
process.exit(bad ? 1 : 0);
