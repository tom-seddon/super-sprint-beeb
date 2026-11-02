// The players' keys in jsbeeb (D12, brief step 9): the play build (make beeb TRACE=play, build/sprint.ssd)
// booted, each of the layout's 9 keys held alone, then all 9 together, and the inputs the game read for the
// three players (RcInput, in the fourth bank) checked. jsbeeb's keyboard has no ghosting, so this proves the
// key numbers and the reading, not the matrix: tools/keys_ghost.py does that on paper, and a real BBC is the
// test of it.
//
// Exit status: 1 if any input is wrong, else 0.
//
// Usage (from the repo root, after make beeb TRACE=play): node tools/keys_check.mjs

import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const syms = symbols();
const s = await bootDisc();
const peek = (a) => s.readMemory(a, 1)[0];
// [jsbeeb's key name, player, bit]
const Keys = [["KeyZ", 0, 4], ["KeyX", 0, 8], ["ShiftLeft", 0, 0x80], ["KeyV", 1, 4], ["KeyB", 1, 8], ["KeyN", 1, 0x80],
    ["Comma", 2, 4], ["Period", 2, 8], ["Slash", 2, 0x80]];
await runTo(s, syms["frame_loop.frame_end"]);  // (the disc copies its banks first: the game's running now)
const bank = peek(syms.banktrace);
async function inputs() {
    for (let i = 0; i < 3; i++) await runTo(s, syms["frame_loop.frame_end"]);
    return [0, 1, 2].map((p) => s.readMemory(syms.RcInput + p, 1, { bank })[0]);
}

let wrong = 0;
const check = (what, got, want) => {
    const ok = got.every((v, i) => v === want[i]);
    if (!ok) wrong++;
    console.log(`${what}: read ${got.map((v) => "&" + v.toString(16)).join(" ")}${ok ? "" : `, want ${want.map((v) => "&" + v.toString(16)).join(" ")}`}`);
};
check("no key", await inputs(), [0, 0, 0]);
for (const [name, p, bit] of Keys) {
    s.keyDown(name);
    const want = [0, 0, 0];
    want[p] = bit;
    check(name, await inputs(), want);
    s.keyUp(name);
}
for (const [name] of Keys) s.keyDown(name);
check("all 9", await inputs(), [0x8c, 0x8c, 0x8c]);
for (const [name] of Keys) s.keyUp(name);
check("none again", await inputs(), [0, 0, 0]);
console.log(wrong ? `${wrong} wrong` : "every key read as its player's");
process.exit(wrong ? 1 : 0);
