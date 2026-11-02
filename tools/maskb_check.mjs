// mask_byte (src/walls.6502) against tools/maskb.py's mask B: every one of the track's 8,000 bytes read on the
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
const Stub = 0x7000, Out = 0x7010, mb = syms["mask_byte"];
s.writeMemory(Stub, [0x20, mb & 0xff, mb >> 8, 0x8d, Out & 0xff, Out >> 8, 0x4c, (Stub + 6) & 0xff, (Stub + 6) >> 8]);
let bad = 0;                                         // JSR mask_byte : STA Out : JMP *
for (let y = 0; y < 200; y++)
    for (let c = 0; c < 40; c++) {
        cpu.pc = Stub; cpu.a = c; cpu.y = y; cpu.s = 0xff;
        await runTo(s, Stub + 6, 100000);
        const got = s.readMemory(Out, 1)[0];
        if (got !== want[y * 40 + c] && bad++ < 5) console.log(`column ${c} row ${y}: BBC &${got.toString(16)}, mask B &${want[y * 40 + c].toString(16)}`);
    }
console.log(bad ? `${bad} of 8,000 bytes wrong` : "all 8,000 bytes match");
process.exit(bad ? 1 : 0);
