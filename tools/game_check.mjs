// The game around the race against the ST's (Phase 5, step 6; D19): each of tools/st_trace_game.py's games played
// on build/game.ssd from the same seed, every read of a player's input given as the ST's read it, in order, so
// the BBC's screens must ask as often and for the same car, and the state compared at every point the ST's was
// dumped. A race isn't driven: the trace's result is put in at the frame the ST's was. At the race's return the
// whole logic is compared (tools/logic_compare.mjs); at the other points the game's own state: who's playing,
// wrenches, scores, upgrades, the race counter, the lap records, the generator. Prepare to race's screen is compared
// with tools/screens.py's as it's shown and as it ends, a join's panel and all, and so is the select's.
//
// Not yet: the initials (step 10), so their reads are skipped and the high scores aren't compared.
//
// Exit status: 1 if any game differs, or reads are left over or run out, else 0.
//
// Usage (from the repo root, after make game): node tools/game_check.mjs [GAMES]   (default three alone rejoin)

import { readFileSync } from "node:fs";
import { bootDisc, ram, runToAny, symbols } from "./jsbeeb.mjs";
import { comparer, PerCar, Race } from "./logic_compare.mjs";
import { bonus, First, screen as circle } from "./circle_model.mjs";
import { screen as upgrades } from "./upgrades_model.mjs";

const games = process.argv.length > 2 ? process.argv.slice(2) : ["three", "alone", "rejoin"];
const Region = 0x1c722;
const Keys = 0x1dfd4, Esc = Keys + 1, F5 = Keys + 0x3f, F10 = Keys + 0x44;
const CarOf = { 0: 0, 2: 1, 3: 2 };     // G_01DFCC's devices
const inRace = (pc) => pc >= 0xdc4c && pc < 0xe66a, inInitials = (pc) => pc >= 0x17a42 && pc < 0x18184;
const Flips = 16;                       // flips from the race's entry to its frame 0: the step's flip N is frame N - this
const Game = ["drone", "wrench", "score0", "score1", "score2", "score3", "score4", "score5", "seed"];

function firstSeed(values) {        // the generator's state before the first value, as st_trace_logic.py's seed()
    const Mul = 3141592621n, Inv = (() => { let x = 1n; for (let i = 0; i < 6; i++) x = (x * (2n - Mul * x)) & 0xffffffffn; return x; })();
    for (let low = 0n; low < 256n; low++) {
        const s = (BigInt(values[0]) << 8n) | low;
        let t = s, ok = true;
        for (const v of values.slice(1)) {
            t = (t * Mul + 1n) & 0xffffffffn;
            if (Number((t >> 8n) & 0xffffffn) !== v) { ok = false; break; }
        }
        if (ok) return Number(((s - 1n) * Inv) & 0xffffffffn);
    }
    throw new Error("the random numbers aren't one run of TOS's generator");
}

async function play(name) {
    const { script, events } = JSON.parse(readFileSync(`build/trace/game_${name}.json`));
    const start = events.findIndex((e) => e.kind === "point" && e.name === "start");
    const end = events.findLastIndex((e) => e.kind === "point" && e.name === "over");
    const game = events.slice(start, end + 1);
    const values = game.filter((e) => e.kind === "random").map((e) => e.value);

    // the points' memory, as logic_compare wants it, each with the numbers drawn since the last
    const points = [], front = [], races = [];
    let drawn = [];
    for (const e of game) {
        if (e.kind === "random") drawn.push([e.n, e.value]);
        else if (e.kind === "point" && e.name !== "initials") {
            const bytes = Buffer.from(e.mem, "hex"), mem = {};
            for (let i = 0; i < bytes.length; i++) mem[Region + i] = bytes[i];
            points.push({ name: e.name, mem, random: drawn, bytes });
            drawn = [];
        } else if (e.kind === "input" && !inRace(e.from) && !inInitials(e.from)) front.push(e);
        else if (e.kind === "step") front.push(e);
    }
    let pi = 1;                         // (the game's start is only the seed's)
    for (let i = 0; i < points.length; i++) if (points[i].name === "race") races.push(points[i]);

    const syms = symbols("build/tracks/t0.json");
    const s = await bootDisc("build/game.ssd");
    const cpu = s._machine.processor;
    const peek = (a) => s.readMemory(a, 1)[0];
    const word = (a) => peek(a) | (peek(a + 1) << 8);
    const put = (a, v) => s.writeMemory(a, [v]);
    const idle = syms["game_resume.idle"];
    await runToAny(s, [[idle]], 80000000);
    const banktrace = ram(s, 2, 1)[0], bankbg = ram(s, 0, 1)[0];
    // MUTATE=LABEL+OFFSET=BYTE: a byte of the game's image changed: this check is seen to fail (it runs from a copy)
    if (process.env.MUTATE) {
        const [, label, off, v] = process.env.MUTATE.match(/^([\w.]+)\+(\d+)=(\d+)$/);
        s.writeMemory(syms.game_image + syms[label] + Number(off) - syms.GameOrg, [Number(v)], { bank: banktrace });
    }
    const seed = firstSeed(values);
    for (let i = 0; i < 4; i++) put(syms.GmSeed + i, (seed >>> (8 * i)) & 255);
    put(syms.GmSeeded, 1);

    // what's compared, through logic_compare's: a trace of the points
    const show = Number(process.env.SHOW ?? 12);
    const wholly = comparer(s, syms, { seed, frames: points }, { show, label: `${name}: ` });
    // (a track with no gates never reads its gates' variables, and the ST leaves the last track's in them)
    const all = [...PerCar, ...Race].map((v) => v[0]).concat("seed", "map");
    const noGates = comparer(s, syms, { seed, frames: points }, { only: all.filter((n) => !/^gate(lane|timer|pos|step)/.test(n)), show, label: `${name}: ` });
    const only = comparer(s, syms, { seed, frames: points }, { only: Game, show, label: `${name}: ` });
    let wrong = 0;
    const say = (t) => { console.log(`${name}: ${t}`); wrong++; };
    function extras(p, k) {
        const m = p.bytes, st = (a) => (m[a - Region] << 8) | m[a - Region + 1];
        const signed = (v) => (v >= 0x8000 ? v - 0x10000 : v);
        const race = peek(syms.GmRace), r = race >= 0x80 ? race - 256 : race;
        if (signed(st(0x1ebc2)) !== r) say(`${p.name}: race counter ST ${signed(st(0x1ebc2))}, BBC ${r}`);
        for (let c = 0; c < 3; c++)
            for (const [i, v, n] of [[0, syms.RcTraction, "traction"], [1, syms.RcTopUp, "top speed"], [2, syms.RcTurbo, "turbo"], [3, syms.GmScoreUp, "score"]]) {
                const a = st(0x1e2ac + 8 * c + 2 * i), b = peek(v + c);
                if (a !== b) say(`${p.name}: car ${c} ${n} ST ${a}, BBC ${b}`);
            }
        for (let t = 0; t < 8; t++) {
            const a = st(0x1d314 + 2 * t), b = (peek(syms.LapRecords + 2 * t) << 8) | peek(syms.LapRecords + 2 * t + 1);
            if (a !== b) say(`${p.name}: track ${t + 1}'s record ST ${a}, BBC ${b}`);
        }
    }

    // After a race nothing's to be heard yet (the tunes are step 9's): the ST silences its channels at a race's end
    // and on F10. The chip itself is read, each channel's volume.
    const chip = s._soundChip;
    async function silent(where) {
        if (where === "over") await s.runFor(4 * 39936);    // (F10's are the moment before; no reads to miss here)
        const loud = [0, 1, 2, 3].filter((c) => chip.volume[c] !== 0);
        if (loud.length) say(`${where}: channels ${loud.join(", ")} still sounding`);
    }

    // Prepare to race's screen, byte for byte: the picture, and each car's panel as it's playing or not (tools/screens.py)
    const prepareAll = readFileSync("build/gen/prepare_all.bin"), prepareNone = readFileSync("build/gen/prepare_none.bin");
    let screens = 0, joined = 0;
    function screen(where) {
        const got = ram(s, syms.PlayAddr, 16000), want = Buffer.from(prepareAll), Panels = [0, 27 * 8, 54 * 8, 80 * 8];
        const playing = [0, 1, 2].map((c) => peek(syms.RcDrone + c) === 0);
        for (let c = 0; c < 3; c++)
            if (!playing[c]) for (let r = 0; r < 6; r++) prepareNone.copy(want, r * 640 + Panels[c], r * 640 + Panels[c], r * 640 + Panels[c + 1]);
        let diff = 0;
        for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
        if (diff) say(`${where}: ${diff} bytes of the screen differ, ${playing.map(Number).join("")} playing`);
        if (where === "prepare shown") shownPlaying = playing.join();
        else if (playing.join() !== shownPlaying) joined++;
        screens++;
    }
    let shownPlaying = "";

    // The select screen's, the same: the picture, the panels, the dial, the rectangle, the difficulty, the seconds (tools/screens.py)
    const G = (f) => readFileSync(`build/gen/select${f}`);
    const sel = { base: G(".bin"), all: G("_all.bin"), none: G("_none.bin"), dial: G("_dial.bin"), text: G("_text.bin"), level: G("_level.bin") };
    const lineAt = (y) => (y >> 3) * 640 + (y & 7);
    const Rects = [[28, 34, 87], [53, 34, 87], [53, 88, 141], [53, 145, 199], [28, 145, 199], [3, 145, 199], [3, 88, 141], [3, 34, 87]];
    let dials = new Set();
    function selectScreen(where) {
        const want = Buffer.from(sel.base), Panels = [0, 27 * 8, 54 * 8, 80 * 8];
        const dial = peek(syms.SelShown), level = peek(syms.SelLevel), digit = peek(syms.SelDigit), track = peek(syms.SelTrack);
        dials.add(dial);
        if (dial >> 1 !== track || dial >> 2 !== level) say(`${where}: dial ${dial}, track ${track}, level ${level}`);
        for (let c = 0; c < 3; c++) {
            const from = peek(syms.RcDrone + c) ? sel.none : sel.all;
            for (let r = 0; r < 4; r++) from.copy(want, r * 640 + Panels[c], r * 640 + Panels[c], r * 640 + Panels[c + 1]);
        }
        const band = digit === 255 ? 0 : digit + 1;
        for (let l = 0; l < 6; l++)
            for (let c = 26; c < 56; c++) {     // (the rows of tracks either side share these lines)
                want[lineAt(89 + l) + c * 8] = sel.text[band * 480 + l * 80 + c];
                want[lineAt(139 + l) + c * 8] = sel.level[level * 480 + l * 80 + c];
            }
        for (let l = 0; l < 44; l++) for (let c = 0; c < 16; c++) want[lineAt(94 + l) + (32 + c) * 8] = sel.dial[dial * 704 + l * 16 + c];
        const [col, top, bottom] = Rects[track];
        for (let y = top; y <= bottom; y++) {
            const edge = y < top + 2 || y > bottom - 2, at = lineAt(y) + col * 8;
            want[at] ^= 0x30;
            if (edge) for (let c = 1; c <= 22; c++) want[at + c * 8] ^= 0xf0;
            else want[at + 22 * 8] ^= 0x30;
        }
        const got = ram(s, syms.PlayAddr, 16000);
        let diff = 0;
        for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
        if (diff) say(`${where}: ${diff} bytes of the screen differ (dial ${dial}, digit ${digit})`);
        if (diff && process.env.SHOWDIFF) {
            const rows = {};
            for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) { const y = Math.floor(i / 640) * 8 + (i & 7), c = (i % 640) >> 3; (rows[y] ??= []).push(`${c}:${got[i].toString(16)}/${want[i].toString(16)}`); }
            console.log(rows);
        }
        screens++;
    }

    // The upgrades', the same, from tools/upgrades_model.mjs: the panels, the levels as they were when the screen was drawn, the dial,
    // the box lit, the seconds and the figures paid for
    let upLevels, upScreens = 0, upReads = -1;
    function upgradeScreen(where) {
        const car = peek(syms.GsCar), n = [0, 1, 2];
        if (where === "upgrade shown") upLevels = [syms.RcTraction, syms.RcTopUp, syms.RcTurbo].map((a) => peek(a + car));
        const want = upgrades({
            car, drone: n.map((c) => peek(syms.RcDrone + c)), wrench: n.map((c) => peek(syms.RcWrench + c)),
            score: n.map((c) => [...s.readMemory(syms.RcScore + c * 6, 6)]), laps: n.map((c) => peek(syms.RcLaps + c)),
            level: upLevels, dial: peek(syms.UpShown), lit: [...s.readMemory(syms.UpLit, 4)],
        });
        const got = ram(s, syms.PlayAddr, 16000);
        let diff = 0;
        for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
        if (diff) say(`${where}: ${diff} bytes of the screen differ (car ${car})`);
        screens++;
        upScreens++;
    }

    // The circle's, from tools/circle_model.mjs, as shown and as it ends. The order, the laps and the kind are the race's, which the points check.
    let circleScreens = 0, circleCounted = false, circleFields = 0;
    function circleScreen(where, counted) {
        const n = [0, 1, 2], all = [0, 1, 2, 3], order = [...s.readMemory(syms.GsOrder, 4)];
        const s16 = (lo, hi, car) => (peek(hi + car) << 24 | peek(lo + car) << 16) >> 16;
        const avg = all.map((c) => s16(syms.GsAvgLapLo, syms.GsAvgLapHi, c)), best = all.map((c) => s16(syms.GsBestLapLo, syms.GsBestLapHi, c));
        const track = peek(syms.GmTrack), kind = peek(syms.GsKind);
        const want = circle({
            order, drone: [...s.readMemory(syms.RcDrone, 4)], avg, best, wrench: n.map((c) => peek(syms.RcWrench + c)),
            score: n.map((c) => [...s.readMemory(syms.RcScore + c * 6, 6)]), laps: n.map((c) => peek(syms.RcLaps + c)),
            shown: all.map((c) => counted ? [[1000, 500, 250, 0][order.indexOf(c)], bonus(avg[c], track), bonus(best[c], track)] : [0, 0, 0]),
            frame: First[kind] + peek(syms["circle_file.CiShown"]), spark: [...s.readMemory(syms.GsSpark, 16)],
        });
        const got = ram(s, syms.PlayAddr, 16000);
        let diff = 0;
        for (let i = 0; i < 16000; i++) if (got[i] !== want[i]) diff++;
        if (diff) say(`${where}: ${diff} bytes of the screen differ`);
        screens++;
        circleScreens++;
    }

    // the race's result, as the ST's pokes
    function result(entries) {
        for (const [a, ...b] of entries) {
            const w = (b[0] << 8) | b[1];
            if (a >= 0x1e354 && a < 0x1e35c) put(syms.RcLaps + (a - 0x1e354) / 2, w);
            else if (a >= 0x1e38c && a < 0x1e394) put(syms.RcCheck + (a - 0x1e38c) / 2, w);
            else if (a >= 0x1e394 && a < 0x1e39c) {
                put(syms.RcStripesLo + (a - 0x1e394) / 2, b[1]);
                put(syms.RcStripesHi + (a - 0x1e394) / 2, b[0]);
            } else if (a >= 0x1e32c && a < 0x1e34c) {
                const i = (a - 0x1e32c) / 2;
                put(syms.RcLapTimeLo + i, b[1]);
                put(syms.RcLapTimeHi + i, b[0]);
            } else if (a >= 0x1e324 && a < 0x1e32c) put(syms.RcWrench + (a - 0x1e324) / 2, w);
            else if (a >= 0x1dfa8 && a < 0x1dfc0) b.forEach((v, i) => put(syms.RcScore + a - 0x1dfa8 + i, v));
            else say(`a poke of &${a.toString(16)} not understood`);
        }
    }

    // the steps: the race's results in the order they come, Esc and F5 as they're reached among the reads
    const steps = script.steps;
    const raceSteps = steps.filter((st) => st.when[0] === "flip");
    const abandons = (st) => (st.poke ?? []).some(([a]) => a === F10);
    let ri = 0, read = 0, started = false, esc = false, f5 = false;
    const eat = () => {                 // past any steps before the next read
        while (read < front.length && front[read].kind === "step") {
            for (const [a] of steps[front[read].index].poke ?? []) {
                if (a === Esc) esc = true;
                if (a === F5) f5 = true;
            }
            read++;
        }
    };
    const stops = [
        ["game_read", syms["game_read.got"], bankbg], ["esc", syms["game_esc.got"], bankbg], ["f5", syms["game_f5.got"], bankbg],
        ["played", syms["logic_frame.played"], banktrace], ["abandon", syms["logic_frame.abandon"], banktrace],
        ["race", syms.game_resume, bankbg], ["select", syms["game_resume.selected"], bankbg], ["prepare", syms["game_resume.prepared"], bankbg],
        ["circle", syms["game_resume.after_circle"], bankbg], ["upgrades", syms["game_resume.after_upgrades"], bankbg],
        ["prepare again", syms["game_resume.after_prepare"], bankbg], ["restored", syms["game_resume.restored"], bankbg],
        ["over", syms["game_resume.attract"], bankbg],
        ["prepare shown", syms["prepare.shown"], bankbg], ["prepare over", syms["prepare.over"], bankbg],
        ["select shown", syms["select.shown"], bankbg], ["select over", syms["select.done"], bankbg],
        ["upgrade shown", syms["upgrade.shown"], bankbg], ["upgrade over", syms["upgrade.over"], bankbg],
        ["circle pass", syms["circle.count"], bankbg], ["circle fire", syms["game_fire.got"], bankbg], ["circle over", syms["circle.partied"], bankbg],
    ];
    const byAddr = new Map(stops.map(([n, a, b]) => [a, n]));
    const list = stops.map(([, a, b]) => [a, b]);
    for (;;) {
        const at = await runToAny(s, list, 2000000000);
        const stop = byAddr.get(at);
        if (stop === "game_read") {
            const car = cpu.x;
            if (!started) {
                if (car === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
                continue;
            }
            eat();
            const e = front[read];
            if (read >= front.length) { say(`the reads ran out (car ${car})`); break; }
            if (CarOf[e.device] !== car) { say(`read ${read}, from &${e.from.toString(16)}: ST car ${CarOf[e.device]}, BBC car ${car}`); break; }
            cpu.a = e.value;
            if (upReads >= 0 && ++upReads === 158) cpu.a |= 0x80;   // (the ST's time running out is fire here: the BBC has no limit, D27)
            read++;
        } else if (stop === "esc") {
            eat();
            cpu.a = esc ? 0x80 : 0;
        } else if (stop === "f5") {
            eat();
            cpu.a = f5 ? 0x80 : 0;
            f5 = false;
        } else if (stop === "played") {
            s.writeMemory(syms.RcInput, [0, 0, 0]);
            const st = raceSteps[ri];
            if (word(syms.LfFrame) === st.when[1] - Flips && !abandons(st)) result(st.poke);
        } else if (stop === "abandon") {
            const st = raceSteps[ri];
            cpu.a = word(syms.LfFrame) === st.when[1] - Flips && abandons(st) ? 0x80 : 0;
        } else {
            if (stop === "prepare shown" || stop === "prepare over") {
                screen(stop);
                continue;
            }
            if (stop === "select shown" || stop === "select over") {
                selectScreen(stop);
                continue;
            }
            if (stop === "circle fire") {               // (the ST's celebration's 200 fields, then fire: the BBC waits, D28)
                cpu.a = ++circleFields >= 200 ? 0x80 : 0;
                continue;
            }
            if (stop === "circle pass") {
                if (!circleCounted) circleScreen("circle shown", false);
                circleCounted = true;
                continue;
            }
            if (stop === "circle over") {
                circleScreen("circle over", true);
                circleCounted = false;
                circleFields = 0;
                continue;
            }
            if (stop === "upgrade shown" || stop === "upgrade over") {
                upgradeScreen(stop);
                upReads = stop === "upgrade shown" ? 0 : -1;
                continue;
            }
            if (stop === "race" && (peek(syms.GmStage) === 0 || peek(syms.GmBack))) continue;   // (GmBack: prepare's file loaded)
            const p = points[pi];
            if (p.name !== stop) { say(`at ${stop}, the ST's next point ${p.name}`); break; }
            eat();
            const gates = (p.bytes[0x1eb86 - Region] << 8) | p.bytes[0x1eb86 - Region + 1];
            (stop !== "race" || abandons(raceSteps[ri]) ? only : gates ? wholly : noGates).compare(pi);   // (F10 leaves mid-frame)
            extras(p, pi);
            console.log(`${name}: ${stop}: frames ${word(syms.LfFrame)}, ${read} reads`);
            if (stop === "circle" || stop === "over") await silent(stop);
            if (stop === "race") ri++;
            pi++;
            if (stop === "over") break;
        }
    }
    eat();
    if (read < front.length) say(`${front.length - read} reads left over`);
    const bad = wrong + wholly.wrong + noGates.wrong + only.wrong;
    console.log(`${name}: ${bad ? `WRONG, ${bad} points` : `exact at ${pi - 1} points, ${read} reads, ${screens} screens, ${upScreens} of them the upgrades', ${circleScreens} the circle's, ${joined} with a join`}`);
    s.destroy?.();
    return bad ? 1 : 0;
}

let bad = 0;
for (const g of games) bad += await play(g);
console.log(bad ? `${bad} of ${games.length} games wrong` : `all ${games.length} games exact`);
process.exit(bad ? 1 : 0);
