// The game's disc booted from power-on with RAM full of junk, as a real machine's is, not jsbeeb's zeroed or &FF
// RAM: main, ANDY, HAZEL, shadow and the sideways RAM banks seeded after the hard reset, before the MOS's first
// instruction, then SHIFT-BREAK's boot run until the title's file has loaded, and on for After fields, the game's
// field counter going all the while. A boot that never loads the title's file, or whose game stops, failed.
//
// jsbeeb's boots all keep the same time: its disc turns from power-on in step with the fields, near enough, and every
// load waits for the disc. A real drive's turning has nothing to do with the fields, so each seed also turns the disc
// to a random place as !BOOT starts, as SPRINT does and as each load_track does, and waits a while (up to about a
// field and a half, in a loop at Delay) at the first two: the loads, the fields and the interrupts fall differently.
// (The Master's MOS clears main, shadow and HAZEL RAM at power-on but not ANDY or the banks: measured, jsbeeb 2.18.0.)
//
// Exit status: 1 if any seed's boot failed; else 0.
//
// --ram 0,1,2,3: the sideways RAM in those banks, not the Master's 4-7 (cartridges'; the rest ROM sockets, empty).
//
// Usage (from the repo root, after make game): node tools/seed_check.mjs [--adfs] [--ram BANKS] [RUNS] [FIRST] [--show DIR]

import { mkdirSync, writeFileSync } from "node:fs";
import { adfs, gameArgs, gameDisc, jsbeebModule, ram, settle, symbols } from "./jsbeeb.mjs";

const Field = 39936;
const option = (name) => (gameArgs.includes(name) ? gameArgs[gameArgs.indexOf(name) + 1] : null);
const args = gameArgs.filter((a, i) => !a.startsWith("--") && !gameArgs[i - 1]?.startsWith("--"));
const show = option("--show"), ramBanks = option("--ram")?.split(",").map(Number);
const After = 500, Delay = 0x0A00;          // (fields on after the title's file; the MOS's serial buffer, unused)
const runs = Number(args[0] ?? 40), first = Number(args[1] ?? 1);
const syms = symbols("build/tracks/t0.json");
const { MachineSession } = await jsbeebModule("machine-session.js");
const s = new MachineSession(adfs ? "MasterADFS" : "Master");
await s.initialise();
s.loadDisc(gameDisc);
const cpu = s._machine.processor;
if (ramBanks) for (let bank = 0; bank < 16; bank++) cpu.model.swram[bank] = ramBanks.includes(bank);
if (ramBanks && cpu.model.swram.some((r, bank) => r !== ramBanks.includes(bank))) throw new Error("jsbeeb's banks can't be changed");
const hold = adfs ? 8000000 : 2000000, limit = adfs ? 2500 : 1500;
const title = syms["game_resume.loaded"];
s.addBreakpoint("execute", title);
const Waits = [syms.boot_entry, syms.entry];                // (!BOOT's start, then SPRINT's)
for (const w of [...Waits, syms.load_track]) s.addBreakpoint("execute", w);
const drive = cpu.fdc._drives[0];
if (show) mkdirSync(show, { recursive: true });

// a seed's junk: 0-3 one byte everywhere (&00, &FF, &A5, &5A), on from 4 a PRNG's (mulberry32)
function junk(seed) {
    const fill = [0x00, 0xff, 0xa5, 0x5a][seed];
    if (fill !== undefined) return () => fill;
    let a = seed * 0x9e3779b9;
    return () => {
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) & 0xff;
    };
}

let failed = 0;
for (let seed = first; seed < first + runs; seed++) {
    const next = junk(seed), mem = cpu.ramRomOs;
    s.keyDown("ShiftLeft");
    s.reset(true);
    for (let i = 0; i < cpu.romOffset; i++) mem[i] = next();
    cpu.model.swram.forEach((isRam, bank) => {
        if (!isRam) return;
        const at = cpu.romOffset + bank * 16384;
        for (let i = 0; i < 16384; i++) mem[at + i] = next();
    });
    const waits = Waits.map(() => [1 + next() % 48, next()]);   // loops of about 1,280 cycles, and spare
    const turn = () => (drive.positionFraction = (next() << 8 | next()) / 65536);
    let field = 0, done = false, shift = true, at = 0, delayed = 0;
    for (let left = Field; field < limit && !(done && field >= at + After); ) {
        s.resetBreakpointHits();
        settle(s);
        const before = s.elapsedCycles;
        await s.runFor(left);
        const hit = s.hitBreakpoint();
        left -= Math.max(s.elapsedCycles - before, 1);
        if (hit && hit.address === syms.load_track) turn();
        if (hit && hit.address === Waits[delayed] && delayed < Waits.length) {
            turn();
            const [loops, spare] = waits[delayed++], back = hit.address;  // LDY #spare:LDX #loops: DEY:BNE:DEX:BNE: JMP back
            [0xa0, spare, 0xa2, loops, 0x88, 0xd0, 0xfd, 0xca, 0xd0, 0xfa, 0x4c, back & 255, back >> 8]
                .forEach((b, i) => (mem[Delay + i] = b));
            cpu.pc = Delay;
            if (process.env.DEBUG) console.log(`  wait at &${back.toString(16)}, field ${field}, cycle ${s.elapsedCycles}`);
            continue;
        }
        if (hit && hit.address === title && !done && (cpu.romsel & 15) === ram(s, 0, 1)[0]) { done = true; at = field; }
        if (left > 0) continue;
        left = Field;
        field++;
        if (shift && field * Field >= hold) { s.keyUp("ShiftLeft"); shift = false; }
    }
    if (shift) s.keyUp("ShiftLeft");
    let going = false;
    if (done) {
        const v = cpu.ramRomOs[syms.vsyncs];
        settle(s);
        await s.runFor(Field * 3);
        going = cpu.ramRomOs[syms.vsyncs] !== v;
    }
    const pc = cpu.pc.toString(16).padStart(4, "0"), sel = cpu.romsel.toString(16), acc = cpu.acccon.toString(16);
    console.log(`seed ${seed}, banks ${[...cpu.ramRomOs.subarray(0, 4)]}: ${done && going ? `title's file loaded at field ${at}, going at ${field}` : `FAILED: ${done ? `loaded at ${at}, stopped by field ${field}` : `not loaded by field ${field}`}, PC &${pc}, ROMSEL &${sel}, ACCCON &${acc}`}`);
    if (!(done && going)) {
        failed++;
        if (show) writeFileSync(`${show}/seed${seed}.png`, await s.screenshotActive({ scale: 2 }));
    }
}
console.log(`${adfs ? "ADFS" : "DFS"}: ${runs - failed} of ${runs} seeds booted to the title's file`);
process.exit(failed ? 1 : 0);
