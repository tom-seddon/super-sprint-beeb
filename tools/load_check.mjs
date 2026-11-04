// The game's loads (Phase 5, 3c): build/game.ssd booted, and each track's file loaded in turn (LoadWant poked
// at the frame loop's end, as the race's end sets it), then, at start (the load done, nothing drawn yet),
// every slot compared with that track's own play build's (build/game_slots.json, tools/make_game.py): the
// banks' (each read in its bank), ANDY's, and Shared in both screens. Outside the slots every track's build
// is the same (tools/track_slots.py), so a track loaded right is that track's build. Then a few hundred
// frames of its race, each load timed in fields, and the field's length: 10 vsyncs in 10 fields' cycles (the
// MOS's colour flashing, if left on, rewrites the Video ULA during a load and halves the CRTC's clock). The
// MOS's flash counter (&251) must be 0 too: one still counting fires on a later load. And the System VIA's
// DDRB &CF, as MOS 3.20 sets it once at reset: PB6 and PB7 drive the CMOS chip, where the filing system reads
// its seek time (at &0F, seen on Tom's Master, the disc stepped at the wrong rate).
//
// Exit status: 1 if any slot's byte differs, a load never finishes or the fields run slow, else 0.
//
// Usage (from the repo root, after make game): node tools/load_check.mjs [TRACKS]   (indexes, default all 8,
// in the ST's order from track 1's: 2 6 5 1 4 7 3 0)

import { readFileSync } from "node:fs";
import { andy, bootDisc, cycles, ram, runTo, settle, symbols } from "./jsbeeb.mjs";

const syms = symbols("build/tracks/t0.json");
const want = JSON.parse(readFileSync("build/game_slots.json"));
const order = process.argv.length > 2 ? process.argv.slice(2).map(Number) : [2, 6, 5, 1, 4, 7, 3, 0];
const s = await bootDisc("build/game.ssd");
await runTo(s, syms["frame_loop.frame_end"], 80000000);   // (the disc copies its banks first)
const banks = [...ram(s, 0, 4)];                           // bankbg, bankcars, banktrace, bankobj
const role = { BgBank: 0, CarsBank: 1, TraceBank: 2, ObjBank: 3 };

let bad = 0;
for (const n of order) {
    s.writeMemory(syms.LoadWant, [n + 1]);
    const t0 = cycles(s);
    try {
        await runTo(s, syms.start, 400000000);
    } catch (e) {
        console.log(`track ${n + 1}: the load never finished (${e.message})`);
        bad++;
        continue;
    }
    const fields = Math.round((cycles(s) - t0) / 39936);
    let wrong = 0;
    const out = [];
    for (const slot of want[n]) {
        const w = Buffer.from(slot.bytes, "hex");
        const copies = slot.section === "Shared" ? [ram(s, slot.address, w.length), ram(s, slot.address, w.length, true)]
            : slot.section === "Andy" ? [andy(s, slot.address, w.length)]
            : [s.readMemory(slot.address, w.length, { bank: banks[role[slot.section]] })];
        let diff = 0;
        for (const got of copies) for (let i = 0; i < w.length; i++) if (got[i] !== w[i]) diff++;
        if (diff) out.push(`${slot.name} ${diff} wrong`);
        wrong += diff;
    }
    bad += wrong ? 1 : 0;
    console.log(`track ${n + 1}: loaded in ${fields} fields; ${want[n].length} slots ${wrong ? "WRONG: " + out.join(", ") : "all as its build"}`);
    for (let f = 0; f < 300; f++) await runTo(s, syms["frame_loop.frame_end"], 4000000);
    settle(s);
    const v0 = ram(s, syms.vsyncs, 1)[0];
    await s.runFor(399360);
    const vs = (ram(s, syms.vsyncs, 1)[0] - v0 + 256) % 256, flash = ram(s, 0x251, 1)[0];
    const ddrb = s._machine.processor.sysvia.ddrb;
    if (vs !== 10 || flash !== 0 || ddrb !== 0xcf) {
        console.log(`track ${n + 1}: ${vs} vsyncs in 10 fields, the MOS's flash counter ${flash}, DDRB &${ddrb.toString(16)}`);
        bad++;
    }
}
console.log(bad ? `${bad} of ${order.length} tracks wrong` : `all ${order.length} tracks load right`);
process.exit(bad ? 1 : 0);
