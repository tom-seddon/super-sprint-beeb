// The race logic's 16-bit arithmetic (src/arith.6502) against the 68000's (D9): div_s16 against divs.w's
// quotient (rounded towards 0) for divisors 1-127, mul_s16 and mul_dir against muls.w's low word, each over
// numbers across the whole range and every one near 0. Run on the BBC (build/logic.ssd); exit status 1 if any
// differs.
//
// The race oracles reach only the numbers the traced races make; this reaches the rest (the long divide, a
// negative product's wrap).
//
// Usage (from the repo root, after make logic): node tools/arith_check.mjs

import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const syms = symbols("build/logic.json");
const s = await bootDisc("build/logic.ssd");
await runTo(s, syms["test_entry.loaded"]);
const cpu = s._machine.processor, num = syms["num"];
const Stub = 0x7000;
const s16 = (v) => (v << 16) >> 16;
const nums = [];
for (let v = -32768; v < 32768; v += 97) nums.push(v);
for (let v = -600; v <= 600; v++) nums.push(v);
nums.push(32767, -32767, 255, 256, -255, -256, 4095, -4096);

let bad = 0, n = 0;
async function check(name, a, v, want) {
    const f = syms[name];
    s.writeMemory(Stub, [0x20, f & 0xff, f >> 8, 0x4c, (Stub + 3) & 0xff, (Stub + 3) >> 8]);  // JSR f : JMP *
    s.writeMemory(num, [v & 255, (v >> 8) & 255]);
    cpu.pc = Stub; cpu.a = a & 255; cpu.s = 0xff;
    cpu.p.n = (a & 0x80) !== 0; cpu.p.z = (a & 255) === 0;                // (as the callers' LDA leaves them)
    await runTo(s, Stub + 3, 100000);
    const b = s.readMemory(num, 2), got = s16(b[1] << 8 | b[0]);
    n++;
    if (got !== want && bad++ < 5) console.log(`${name}(${v}, ${a}): BBC ${got}, want ${want}`);
}
for (let d = 1; d < 128; d += d < 45 ? 1 : 7)
    for (const v of nums) await check("div_s16", d, v, s16(Math.trunc(v / d)));
for (const m of [-127, -40, -11, -8, -7, -6, -3, -1, 0, 1, 2, 3, 4, 6, 7, 8, 11, 40, 127])
    for (const v of nums) await check("mul_s16", m, v, s16(v * m));
for (const m of [-8, -7, -6, -3, 0, 3, 6, 7, 8])                           // DirX and DirY's steps
    for (const v of nums) await check("mul_dir", m, v, s16(v * m));
console.log(bad ? `${bad} of ${n} wrong` : `all ${n} match`);
process.exit(bad ? 1 : 0);
