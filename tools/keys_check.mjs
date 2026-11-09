// The players' keys in jsbeeb (D12, brief step 9): the play build (make beeb TRACE=play, build/sprint.ssd)
// booted to the attract mode, each of the layout's 9 keys held alone, then all 9 together, and the inputs the game
// read for the three players (RcInput, in ANDY: D15) checked, at game_read (the read given as nothing, or fire would
// start a game). Then Escape, f5 and f0's numbers, each put in the table in place of a player's key, as the
// game's own reads of them are of a number alone (D24). The keys are pressed by jsbeeb's own matrix table (its BBC
// key names: CAPS LOCK and the keypad's have no host key of their own), so the game's numbers are checked against
// jsbeeb's. jsbeeb's keyboard has no ghosting, so this proves the key numbers and the reading, not the matrix:
// tools/keys_ghost.py does that on paper, and a real BBC is the test of it.
//
// Exit status: 1 if any input is wrong, else 0.
//
// Usage (from the repo root, after make beeb TRACE=play): node tools/keys_check.mjs

import { andy, bootDisc, ram, runTo, runToAny, symbols } from "./jsbeeb.mjs";

const syms = symbols();
const s = await bootDisc();
// [jsbeeb's BBC key name, player, bit]: the defaults (D12)
const Keys = [["Q", 0, 4], ["W", 0, 8], ["E", 0, 0x80], ["COMMA", 1, 4], ["PERIOD", 1, 8], ["SLASH", 1, 0x80],
    ["NUMPAD5", 2, 4], ["NUMPAD6", 2, 8], ["NUMPAD_DELETE", 2, 0x80]];
await runTo(s, syms["game_resume.idle"], 80000000);    // (the disc copies its banks first: the attract mode now)
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor, table = cpu.model.keys;
const down = (name) => s.keyDownRaw(table[name]), up = (name) => s.keyUpRaw(table[name]);
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
    if (!table[name]) throw new Error(`jsbeeb has no ${name}`);
    down(name);
    const want = [0, 0, 0];
    want[p] = bit;
    check(name, await inputs(), want);
    up(name);
}
for (const [name] of Keys) down(name);
check("all 9", await inputs(), [0x8c, 0x8c, 0x8c]);
for (const [name] of Keys) up(name);
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
