// What the logic oracles compare (tools/logic_check.mjs, on build/logic.ssd, and tools/disc_races.mjs, on the
// game's disc): every variable of the BBC's race against a trace's frame (tools/st_trace_logic.py), the
// generator's state, the gates' and barriers' boxes of mask B and the attribute map.

// [name, the ST's address, the BBC's array, kind]: w a Lo/Hi pair, s a signed byte, u an unsigned one
export const PerCar = [
    ["x8", 0x1e3fc, "RcX8", "w"], ["y8", 0x1e3f4, "RcY8", "w"], ["x", 0x1e42c, "RcX", "w"], ["y", 0x1e424, "RcY", "w"],
    ["px8", 0x1e3cc, "RcPX8", "w"], ["py8", 0x1e3c4, "RcPY8", "w"],
    ["safex8", 0x1e3ec, "RcSafeX8", "w"], ["safey8", 0x1e3e4, "RcSafeY8", "w"], ["safedir", 0x1e3dc, "RcSafeDir", "u"],
    ["dir", 0x1e41c, "RcDir", "u"], ["travel", 0x1e414, "RcTravel", "u"], ["speed", 0x1e404, "RcSpeed", "w"],
    ["top", 0x1e374, "RcTop", "w"], ["cap", 0x1e35c, "RcCap", "w"], ["thresh", 0x1e364, "RcThresh", "w"],
    ["div", 0x1e36c, "RcDiv", "u"], ["steer", 0x1e40c, "RcSteer", "s"],
    ["tvx", 0x1e2ec, "RcTVX", "w"], ["tvy", 0x1e2e4, "RcTVY", "w"], ["svx", 0x1e2fc, "RcSVX", "w"], ["svy", 0x1e2f4, "RcSVY", "w"],
    ["offx", 0x1e30c, "RcOffX", "w"], ["offy", 0x1e304, "RcOffY", "w"],
    ["bounce", 0x1e3b4, "RcBounce", "u"], ["immune", 0x1e3ac, "RcImmune", "u"], ["spin", 0x1e37c, "RcSpin", "u"],
    ["jump", 0x1e384, "RcJump", "u"], ["bits", 0x1e3a4, "RcBits", "w"], ["latch", 0x1e39c, "RcLatch", "w"],
    ["state", 0x1e3d4, "RcState", "u"], ["laps", 0x1e354, "RcLaps", "u"], ["check", 0x1e38c, "RcCheck", "u"],
    ["stripes", 0x1e394, "RcStripes", "w"], ["drone", 0x1e34c, "RcDrone", "u"], ["order", 0x1e2cc, "RcOrder", "u"],
    ["wrench", 0x1e324, "RcWrench", "u"],
    ["pathidx", 0x1e3bc, "RcPathIdx", "u"], ["endx8", 0x1e31c, "RcEndX8", "w"], ["endy8", 0x1e314, "RcEndY8", "w"],
    // (G_01E2DC and G_01E2D4, a drone's moves since its segment's start, aren't kept: only dead code reads them, D14)
    // the scores: 6 bytes a car in both
    ...[0, 1, 2, 3, 4, 5].map((i) => [`score${i}`, 0x1dfa8 + i, "RcScore", "b", 6, (c) => c * 6 + i]),
    // the frame each lap ended: 4 words a car in the ST, car * 4 + lap in the BBC
    ...[0, 1, 2, 3].map((i) => [`lap${i}`, 0x1e32c + 2 * i, "RcLapTime", "w", 8, (c) => c * 4 + i]),
];
export const Race = [["phase", 0x1d178, "RcPhase", "u"], ["frame", 0x1d30e, "RcFrame", "w"], ["push", 0x1e2a0, "RcPush", "u"],
    ["hazards", 0x1eb54, "RcHazards", "u"], ["wrenchtaken", 0x1eb56, "RcWrenchTaken", "u"],
    ["wrenchy", 0x1eb58, "RcWrenchY", "u"], ["wrenchx", 0x1eb5a, "RcWrenchX", "u"],
    ["wrenchphase", 0x1eb5c, "RcWrenchPhase", "u"], ["wrenchtimer", 0x1eb5e, "RcWrenchTimer", "w"],
    ["bonustaken", 0x1eb60, "RcBonusTaken", "u"], ["bonuscell", 0x1eb62, "RcBonusCell", "w"],
    ["bonusy", 0x1eb64, "RcBonusY", "u"], ["bonusx", 0x1eb66, "RcBonusX", "u"],
    ["bonussprite", 0x1eb68, "RcBonusSprite", "u"], ["bonusphase", 0x1eb6a, "RcBonusPhase", "u"],
    ["bonustimer", 0x1eb6c, "RcBonusTimer", "w"],
    // the hazards (step 11): the oil-type hazards' places, the gates, the barriers, the tornado, the cones
    ...[0, 1, 2].flatMap((i) => [[`haztype${i}`, 0x1eb36 + 2 * i, "RcHazType", "u", 0, () => i],
        [`hazrow${i}`, 0x1eb40 + 2 * i, "RcHazRow", "u", 0, () => i], [`hazcol${i}`, 0x1eb4a + 2 * i, "RcHazCol", "u", 0, () => i]]),
    ...[0, 1, 2].flatMap((i) => [[`gatelane${i}`, 0x1eb6e + 2 * i, "RcGateLane", "u", 0, () => i],
        [`gatetimer${i}`, 0x1eb74 + 2 * i, "RcGateTimer", "w", 0, () => i],
        [`gatepos${i}`, 0x1eb7a + 2 * i, "RcGatePos", "u", 0, () => i],
        [`gatestep${i}`, 0x1eb80 + 2 * i, "RcGateStep", "s", 0, () => i]]),
    ["gatecount", 0x1eb86, "RcGateCount", "u"],
    ["baridx", 0x1eb8e, "RcBarIdx", "u"], ["barframe", 0x1eb90, "RcBarFrame", "u"], ["bardir", 0x1eb92, "RcBarDir", "s"],
    ["bartimer", 0x1eb94, "RcBarTimer", "u"], ["baron", 0x1eb96, "RcBarOn", "u"],
    ["tordy", 0x1eb98, "RcTorDY", "s"], ["tordx", 0x1eb9a, "RcTorDX", "s"], ["torframe", 0x1eb9e, "RcTorFrame", "u"],
    ["tory", 0x1eba0, "RcTorY", "w"], ["torx", 0x1eba2, "RcTorX", "w"], ["tortimer", 0x1eba4, "RcTorTimer", "w"],
    ["tornado", 0x1eba6, "RcTornado", "u"], ["cones", 0x1ebb0, "RcCones", "u"],
    ...[0, 1, 2, 3].flatMap((i) => [[`conehit${i}`, 0x1eba8 + 2 * i, "RcConeHit", "u", 0, () => i],
        [`conerow${i}`, 0x1ebb2 + 2 * i, "RcConeRow", "u", 0, () => i], [`conecol${i}`, 0x1ebba + 2 * i, "RcConeCol", "u", 0, () => i]]),
    ["helicar", 0x1eb28, "RcHeliCar", "u"], ["helitimer", 0x1eb2a, "RcHeliTimer", "w"],
    ["helivariant", 0x1eb2c, "RcHeliVariant", "u"], ["helistate", 0x1eb2e, "RcHeliState", "w"],
    ["heliframe", 0x1eb30, "RcHeliFrame", "u"], ["heliy", 0x1eb32, "RcHeliY", "w"], ["helix", 0x1eb34, "RcHeliX", "w"],
    ["bannerframe", 0x1eb88, "RcBannerFrame", "u"], ["bannertime", 0x1eb8a, "RcBannerTime", "u"],
    ["banneron", 0x1eb8c, "RcBannerOn", "u"],
    // the 8 sparks, each its own entry: [name, address, array, kind, (unused), its index]
    ...[0, 1, 2, 3, 4, 5, 6, 7].flatMap((i) => [[`spark${i}timer`, 0x1e070 + 2 * i, "RcSparkTimer", "w", 0, () => i],
        [`spark${i}end`, 0x1e080 + 2 * i, "RcSparkEnd", "u", 0, () => i],
        [`spark${i}frame`, 0x1e090 + 2 * i, "RcSparkFrame", "u", 0, () => i],
        [`spark${i}x`, 0x1e0a0 + 4 * i, "RcSparkX", "w", 0, () => i], [`spark${i}y`, 0x1e0a2 + 4 * i, "RcSparkY", "w", 0, () => i]])];

export const stWord = (m, a) => (m[a] << 8) | m[a + 1];
// a variable's 5th and 6th fields, if any: the ST's stride a car (2 if not), the BBC's index for a car
export const stride = (v) => v[4] ?? 2;
export const index = (v, c) => (v[5] ? v[5](c) : c);

// the generator's state at each frame's end: the trace's seed run on once for each number drawn
export function traceSeeds(trace) {
    const seeds = [];
    let seed = BigInt(trace.seed);
    for (const f of trace.frames) {
        for (let i = 0; i < f.random.length; i++) seed = (seed * 3141592621n + 1n) & 0xffffffffn;
        seeds.push(Number(seed));
    }
    return seeds;
}

// A comparer for a machine s (ANDY paged in when compare runs), its build's symbols and a trace.
// options: cars, only (variables' names), show (differences printed); `label` starts each line printed.
// compare(k) compares trace frame k; wrong and firstWrong are the frames that differed.
export function comparer(s, syms, trace, { cars = [0, 1, 2, 3], only = null, show = 20, label = "" } = {}) {
    const frames = trace.frames, seeds = traceSeeds(trace);
    const wanted = (list) => list.filter(([n]) => !only || only.includes(n));
    const peek = (a) => s.readMemory(a, 1)[0];
    const stValue = (m, a, kind) => (kind === "b" ? m[a] : stWord(m, a));
    function bbc(name, kind, car) {
        if (kind === "w") return peek(syms[`${name}Lo`] + car) | (peek(syms[`${name}Hi`] + car) << 8);
        const b = peek(syms[name] + car);
        return kind === "s" && b >= 0x80 ? b | 0xff00 : b;
    }
    // a byte of mask B as D13 stores it (walls.6502's row_byte): its row's fill outside its span, else its map's.
    // Mask B is in ANDY (D15), which a read of &8000-&8FFF gets only while ROMSEL's bit 7 is set: checked
    const MaskB = 0x63a76;              // the ST's (G_01F238 + &1F40), 40 bytes a line
    const AttrMap = 0x678f6;            // the ST's attribute map (G_01EB20's), 40 x 25
    function mbByte(col, y) {
        if (!(s._machine.processor.romsel & 0x80)) throw new Error("mask B read with ANDY out (ROMSEL's bit 7 clear)");
        const r = y >> 3;
        if (col < peek(syms.MbLo + r)) return peek(syms.MbLeft + r);
        if (col >= peek(syms.MbEnd + r)) return peek(syms.MbRight + r);
        const n = peek(((peek(syms.MbMapL + r) | (peek(syms.MbMapH + r) << 8)) + col) & 0xffff);
        if (n === 0 || n === 0xff) return n;
        return peek((((peek(syms.MbCellL + r) | (peek(syms.MbCellH + r) << 8)) + n * 8) & 0xffff) + (y & 7));
    }
    const out = { wrong: 0, firstWrong: null, seeds, count: wanted(PerCar).length + wanted(Race).length };
    let shown = 0;
    out.compare = (k) => {
        const m = frames[k].mem;
        let bad = 0;
        const one = (name, st, bb) => {
            if (st === bb) return;
            bad++;
            if (shown++ < show) console.log(`${label}frame ${k} ${name}: ST ${st} (&${st.toString(16)}), BBC ${bb} (&${bb.toString(16)})`);
        };
        for (const v of wanted(PerCar)) {
            const [n, a, b, kind] = v;
            for (const c of cars) one(`car ${c} ${n}`, stValue(m, a + stride(v) * c, kind), bbc(b, kind, index(v, c)));
        }
        for (const v of wanted(Race)) one(v[0], stWord(m, v[1]), bbc(v[2], v[3], index(v, 0)));
        // TOS's generator: the BBC's seed against the trace's, run on by every number drawn to this frame
        if (!only || only.includes("seed")) one("seed", seeds[k], (peek(syms.RcSeed) | (peek(syms.RcSeed + 1) << 8)
            | (peek(syms.RcSeed + 2) << 16) | (peek(syms.RcSeed + 3) << 24)) >>> 0);
        // the gates' and barriers' boxes of mask B, every byte the trace has of it, against D13's store
        if (!only || only.includes("maskb"))
            for (const key of Object.keys(m)) {
                const a = Number(key) - MaskB;
                if (a >= 0 && a < 8000) one(`mask B (${a % 40}, ${Math.floor(a / 40)})`, m[key], mbByte(a % 40, Math.floor(a / 40)));
            }
        // the attribute map, every cell (the pickups, hazards and cones change it)
        if (!only || only.includes("map"))
            for (let i = 0; i < 1000; i++) {
                const st = m[AttrMap + i];
                if (st !== undefined) one(`map (${i % 40}, ${Math.floor(i / 40)})`, st, peek(syms.AttrMap + i));
            }
        if (bad) {
            out.wrong++;
            if (out.firstWrong === null) out.firstWrong = k;
        }
    };
    return out;
}
