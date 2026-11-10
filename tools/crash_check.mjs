// The crash handler (src/crash.6502) on build/game.ssd: a BRK made to happen, and the screen it leaves read back. A BRK
// put in LowFree's spare bytes and jumped to, on two machines booted afresh: at the title, and in the attract mode's
// demo race at a frame whose ACCCON shows one screen and writes the other. Each time: BRKV the game's, the CPU kept in
// the handler, ACCCON's D and X off, the CRTC's registers MODE 7's, the Video ULA in teletext, and row 2 saying the
// BRK's address and the build's version (build/gen/version.6502), the rest of the screen spaces.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/crash_check.mjs [--show DIR]

import { readFileSync, writeFileSync } from "node:fs";
import { bootDisc, ram, runToAny, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936, Brk = 0x0ab0;              // (LowFree's spare bytes, below LowCodeOrg: memory.6502)
const show = process.argv.includes("--show") ? process.argv[process.argv.indexOf("--show") + 1] : null;
const syms = symbols("build/tracks/t0.json");
const version = (readFileSync("build/gen/version.6502", "latin1").match(/"(.*)"/) || [, ""])[1];
const want = `  BRK at &${Brk.toString(16).toUpperCase().padStart(4, "0")}${version ? `, build ${version}` : ""}`.padEnd(40);
const Crtc = [63, 40, 51, 0x24, 30, 2, 25, 27, 0x93, 18, 0x20, 0x13, 0x28, 0x00];
let wrong = 0;
const say = (t) => { console.log(t); wrong++; };

async function crash(what, s) {
    const cpu = s._machine.processor, brkv = s.readMemory(0x202, 2);
    if (brkv[0] + brkv[1] * 256 !== syms.crash) say(`${what}: BRKV &${(brkv[0] + brkv[1] * 256).toString(16)}, not the handler's`);
    const before = cpu.acccon;
    s.writeMemory(Brk, [0x00, 0x01]);
    cpu.pc = Brk;
    settle(s);
    await s.runFor(20 * Field);
    if (cpu.pc < syms.crash || cpu.pc >= syms.CrashCrtc) say(`${what}: the CPU at &${cpu.pc.toString(16)}, not in the handler`);
    if (cpu.acccon & 5) say(`${what}: ACCCON &${cpu.acccon.toString(16)}, D or X on`);
    const regs = [...cpu.video.regs.slice(0, 14)];
    if (regs.join() !== Crtc.join()) say(`${what}: the CRTC ${regs}, not MODE 7's`);
    if (cpu.video.ulactrl !== 0x4b) say(`${what}: the Video ULA &${cpu.video.ulactrl.toString(16)}, not teletext's &4b`);
    const screen = Buffer.from(ram(s, 0x7c00, 1000)).toString("latin1"), row = screen.slice(80, 120);
    if (row !== want) say(`${what}: row 2 "${row}", not "${want}"`);
    if ((screen.slice(0, 80) + screen.slice(120)).trim()) say(`${what}: more than row 2 on the screen`);
    if (show) writeFileSync(`${show}/crash_${what.replace(/ /g, "_")}.png`, await s.screenshotActive({ scale: 2 }));
    console.log(`${what}: ACCCON &${before.toString(16)} at the BRK; row 2 "${row.trim()}"`);
}

const title = await bootDisc("build/game.ssd");
await runToAny(title, [[syms["game_resume.idle"]]], 80000000);
await crash("the title", title);

const race = await bootDisc("build/game.ssd"), cpu = race._machine.processor;
let apart = false;
for (let i = 0; i < 6000 && !apart; i++) {
    await runToAny(race, [[syms.frame_loop]], 400000000);
    apart = (cpu.acccon & 1) !== ((cpu.acccon >> 2) & 1);
}
if (apart) await crash("the demo race", race);
else say("the demo race: no frame with ACCCON's D and X apart");

console.log(wrong ? `${wrong} wrong` : "the crash handler right: at the title, and in a race showing one screen and writing the other");
process.exit(wrong ? 1 : 0);
