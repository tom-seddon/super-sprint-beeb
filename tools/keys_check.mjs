// The players' keys in jsbeeb (D12, brief step 9): the play build (make beeb TRACE=play, build/sprint.ssd)
// booted to the attract mode, each of the layout's 9 keys held alone, then all 9 together, and the inputs the game
// read for the three players (RcInput, in ANDY: D15) checked, at game_read (the read given as nothing, or fire would
// start a game). Then Escape, f5 and f0's numbers, each put in the table in place of a player's key, as the
// game's own reads of them are of a number alone (D24). jsbeeb's keyboard has no ghosting, so this proves the
// key numbers and the reading, not the matrix: tools/keys_ghost.py does that on paper, and a real BBC is the
// test of it.
//
// Exit status: 1 if any input is wrong, else 0.
//
// Usage (from the repo root, after make beeb TRACE=play): node tools/keys_check.mjs

import { andy, bootDisc, ram, runTo, runToAny, symbols } from "./jsbeeb.mjs";

const syms = symbols();
const s = await bootDisc();
// [jsbeeb's key name, player, bit]
const Keys = [["KeyQ", 0, 4], ["KeyW", 0, 8], ["KeyE", 0, 0x80], ["KeyV", 1, 4], ["KeyB", 1, 8], ["KeyN", 1, 0x80],
    ["Comma", 2, 4], ["Period", 2, 8], ["Slash", 2, 0x80]];
await runTo(s, syms["game_resume.idle"], 80000000);    // (the disc copies its banks first: the attract mode now)
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
async function inputs() {
    let got;
    for (let i = 0; i < 6; i++) {
        await runToAny(s, [[syms["game_read.got"], bankbg]], 8000000);
        got = [...andy(s, syms.RcInput, 3)];
        cpu.a = 0;
    }
    return got;
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
for (const [name, number] of [["Escape", syms.KeyEscape], ["F5", syms.KeyF5], ["F10", syms.KeyF0]]) {
    const keep = s.readMemory(syms.PlayerKeys, 1);
    s.writeMemory(syms.PlayerKeys, [number]);
    s.keyDown(name);
    check(`${name} (${number})`, await inputs(), [syms.PlayerBit && s.readMemory(syms.PlayerBit, 1)[0], 0, 0]);
    s.keyUp(name);
    s.writeMemory(syms.PlayerKeys, [...keep]);
}
console.log(wrong ? `${wrong} wrong` : "every key read as its player's");
process.exit(wrong ? 1 : 0);
