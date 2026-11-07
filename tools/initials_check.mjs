// The initials (F_017A42, step 8): build/game.ssd, a game started and prepare to race's end reached with scores and a table poked in, every read of a player
// answered from a script, and the screen compared at each with tools/initials_model.mjs, the rules played out here by F_017A42's: left and right wrapping
// through the space, fire one press a letter, two cars at once, one entry pushing another down or off the end, "GAME OVER", a clear panel, and no time
// limit: it waits past the ST's 30 seconds (D29). The ST's reads are every 6 fields; a key pressed between them is seen in the field it's pressed, and a
// held key repeats after a wait (D30), so some cases give a timeline of keys held, field by field. The table's then compared, in both copies of Shared.
//
// Exit status: 1 if a screen or the table's wrong, else 0.
//
// Usage (from the repo root, after make game): node tools/initials_check.mjs [SHOTDIR]

import { writeFileSync } from "node:fs";
import { bootDisc, ram, runToAny, symbols } from "./jsbeeb.mjs";
import { screen } from "./initials_model.mjs";

const shots = process.argv[2];
const syms = symbols("build/tracks/t0.json");
const s = await bootDisc("build/game.ssd");
await runToAny(s, [[syms["game_resume.idle"]]], 80000000);
const bankbg = ram(s, 0, 1)[0], cpu = s._machine.processor;
const got = syms["game_read.got"], peek = (a) => s.readMemory(a, 1)[0], peeks = (a, n) => [...s.readMemory(a, n)];
let bad = 0;
const say = (t) => { if (bad++ < 30) console.log(t); };
const L = 4, R = 8, F = 0x80;
const digits = (n) => [...String(n).padStart(6, " ")].map((c) => c === " " ? 0x80 : Number(c));
const six = (n) => [...String(n).padStart(6, "0")].map(Number);
const Table = Array.from({ length: 31 }, (_, e) => e ? (31 - e) * 1000 : 0);    // entry 1 30,000 down to entry 30 1,000
const Names = (e) => [e % 26 + 12, (e * 3) % 26 + 12, (e * 7) % 26 + 12];
const taps = (...keys) => keys.flatMap((k) => [k, 0]);
// each case: who's a drone, their scores, and each entering car's reads, in order, then nothing
const Cases = [
    { name: "one entry", drone: [1, 0, 0], score: [28500, 100, 200], reads: [taps(L, L, R, R, R, F, R, F, L, F), [], []] },
    { name: "taps between the reads", drone: [1, 0, 0], score: [12500, 100, 200], keys: [[R, 7, 8], [R, 15, 16], [R, 23, 25], [F, 40, 41], [L, 50, 51], [F, 60, 62], [F, 70, 71]], want: [4, 27, 1] },
    { name: "a key held repeats, after a wait", drone: [1, 0, 0], score: [11500, 100, 200], keys: [[R, 10, 100], [F, 120, 150], [F, 160, 161], [F, 170, 171]] },
    // fire pressed at every phase of the 6 fields between reads, and held past the next: one letter each
    { name: "fire across a read, 1", drone: [1, 0, 0], score: [10500, 100, 200], keys: [[F, 30, 42], [F, 49, 61], [F, 68, 80]], want: [1, 1, 1] },
    { name: "fire across a read, 2", drone: [1, 0, 0], score: [9500, 100, 200], keys: [[F, 33, 45], [F, 52, 64], [F, 71, 83]], want: [1, 1, 1] },
    { name: "fire held",  drone: [1, 0, 0], score: [18500, 100, 200], reads: [[F, F, F, F, 0, F, F, F, 0, F, F], [], []] },
    { name: "two at once, the second above", drone: [1, 0, 1], score: [15500, 0, 25500], reads: [taps(R, F, F, F), [], taps(F, L, L, F, F)] },
    { name: "game over, and one with no score", drone: [1, 1, 0], score: [500, 0, 0], table: Array.from({ length: 31 }, (_, e) => e ? (31 - e) * 1000 : 0), reads: [[], [], []] },
    { name: "the last place pushed off", drone: [1, 1, 1], score: [1500, 1600, 1700], reads: [taps(F, F, F), taps(F, F, F), taps(F, F, F)] },
    { name: "no time limit", drone: [0, 1, 1], score: [0, 22500, 0], reads: [[], [...taps(R, F), ...Array(300).fill(0), ...taps(F, F)], []] },
];

for (let started = false; ;) {          // a game started, the select ended by fire
    const at = await runToAny(s, [[got, bankbg], [syms["game_resume.selected"], bankbg]], 2000000000);
    if (at !== got) break;
    if (cpu.x === 0) { cpu.a = 0x80; started = true; } else cpu.a = 0;
}
for (;;) {                              // prepare to race's file in: the screen's code's there
    const at = await runToAny(s, [[got, bankbg], [syms.prepare, bankbg]], 2000000000);
    if (at !== got) break;
    cpu.a = 0;
}

// the rules, played out
function start(c, table, names) {
    const t = { digits: table.slice(), names: names.map((n) => n.slice()) };
    const st = [0, 0, 0], rank = [0, 0, 0];
    for (let car = 0; car < 3; car++) {
        if (!c.drone[car]) { st[car] = 2; continue; }
        if (!c.score[car]) { st[car] = 3; continue; }
        for (let e = 30; e > 0; e--) if (c.score[car] > t.digits[e]) rank[car] = e;
        if (rank[car]) {
            st[car] = 1;
            const r = rank[car];
            for (let e = 29; e >= r; e--) { t.digits[e + 1] = t.digits[e]; t.names[e + 1] = t.names[e]; }
            t.digits[r] = c.score[car];
            for (let i = 0; i < car; i++)
                if (st[i] === 1 && r <= rank[i]) { if (rank[i] === 30) { rank[i] = 0; st[i] = 0; } else rank[i]++; }
        }
    }
    const panel = [0, 1, 2].map((car) => !c.drone[car] ? "player" : st[car] === 1 ? "entry" : st[car] === 0 ? "over" : "blank");
    return { t, st: st.map((v) => v === 3 ? 2 : v), rank, panel, pos: [0, 0, 0], letters: [[1, 1, 1], [1, 1, 1], [1, 1, 1]], drawn: [[1], [1], [1]], held: [0, 0, 0], car: 0, passes: 0, last: [0, 0, 0], wait: [0, 0, 0] };
}
function pass(m) {
    m.passes++;
    m.car = (m.car + 1) % 3;
}
function step(m, car, v) {
    const p = m.pos[car], l = m.letters[car];
    if (v & L) l[p] = l[p] - 1 || 27;
    else if (v & R) l[p] = l[p] + 1 === 28 ? 1 : l[p] + 1;
}
function take(m, car) {
    m.held[car] = 1;
    m.pos[car]++;
    if (m.pos[car] === 3) m.st[car] = 3;
}
// a read, the ST's, every 6 fields: the letter's drawn a field after it, and fire taken then
function read(m, car, v) {
    while (m.car !== car) pass(m);
    m.last[car] |= v;
    if (m.wait[car]) m.wait[car]--;
    else step(m, car, v);
    m.pending = { car, v };
}
function settled(m) {             // (the field after a read: done before the next compare)
    const { car, v } = m.pending ?? {};
    m.pending = null;
    if (car === undefined) return;
    if (m.st[car] === 1) {
        m.drawn[car][m.pos[car]] = m.letters[car][m.pos[car]];
        if (v & F) { if (!m.held[car]) take(m, car); } else if (!(m.last[car] & F)) m.held[car] = 0;
    }
    pass(m);
}
// a key seen between the reads: what's newly down acted on at once
function seen(m, car, v) {
    const pressed = v & ~m.last[car];
    m.last[car] = v;
    if (pressed & (L | R)) {
        step(m, car, pressed);
        m.wait[car] = 4;
        m.drawn[car][m.pos[car]] = m.letters[car][m.pos[car]];
    }
    if (pressed & F) {
        take(m, car);
        if (m.st[car] === 1) m.drawn[car][m.pos[car]] = m.letters[car][m.pos[car]];
    }
}
let screens = 0, shot = 0, reads = 0, entries = 0, longest = 0, keysSeen = 0;
const compare = (where, c, m) => {
    const want = screen({ drone: c.drone, panel: m.panel, rank: m.rank, letters: [0, 1, 2].map((car) => m.st[car] === 2 || m.panel[car] !== "entry" ? [] : m.drawn[car]) });
    const have = ram(s, syms.PlayAddr, 16000);
    let diff = 0, first = -1;
    for (let i = 0; i < 16000; i++) if (have[i] !== want[i]) { diff++; if (first < 0) first = i; }
    screens++;
    if (diff) say(`${where}: ${diff} bytes differ, the first at row ${Math.floor(first / 640)}, byte ${(first % 640) >> 3}, line ${first & 7}: ${have[first].toString(16)}, not ${want[first].toString(16)}`);
};
const raw = syms["game_raw.got"];
const stops = [[got, bankbg], [raw, bankbg], [syms["game_esc.got"], bankbg], [syms["prepare.over"], bankbg], [syms["initials.shown"], bankbg], [syms["initials.nobody"], bankbg], [syms["initials.over"], bankbg]];
const put = (a, bytes) => { s.writeMemory(a, bytes); ram(s, a, bytes.length, true).set(bytes); };     // (both copies of Shared)

for (const c of Cases) {
    const table = c.table ?? Table, names = Array.from({ length: 31 }, (_, e) => Names(e));
    table.forEach((v, e) => { if (e) { put(syms.HiScores + e * 6, six(v)); put(syms.HiNames + e * 3, names[e]); } });
    for (let car = 0; car < 3; car++) {
        s.writeMemory(syms.RcDrone + car, [c.drone[car]]);
        s.writeMemory(syms.RcScore + car * 6, digits(c.score[car]));
    }
    const m = start(c, table, names), left = (c.reads ?? [[], [], []]).map((r) => r.slice());
    let shown = false, caseReads = 0;
    let entering = false, field = 0, lastField = 0;
    const held = (car) => {             // (the keys down now, for the case's only entering car)
        field += (peek(syms.vsyncs) - lastField) & 255;
        lastField = peek(syms.vsyncs);
        if (!c.keys || !m.rank[car]) return 0;
        return c.keys.reduce((v, [k, from, to]) => field >= from && field < to ? v | k : v, 0);
    };
    cpu.pc = syms.prepare;              // (each case prepare to race again, as it's the screen under the panels)
    for (; ;) {
        const at = await runToAny(s, stops, 2000000000);
        if (at === syms["game_esc.got"]) cpu.a = 0x80;      // (no need to sit through it)
        else if (at === syms["prepare.over"]) entering = true;
        else if (at === raw) {
            if (!shown) { cpu.a = 0; continue; }
            cpu.a = held(cpu.x);
            if (cpu.a !== m.last[cpu.x]) { seen(m, cpu.x, cpu.a); keysSeen++; }
            else m.last[cpu.x] = cpu.a;
        } else if (at === got) {
            if (!entering) { cpu.a = 0; continue; }
            const car = cpu.x;
            reads++;
            if (++caseReads > 1000) {   // (there's no limit to end an entry a fault has left waiting)
                say(`${c.name}: still entering after ${caseReads} reads`);
                console.log(`${bad} wrong`);
                process.exit(1);
            }
            settled(m);
            while (m.car !== car) pass(m);
            compare(`${c.name}, read ${reads}`, c, m);
            const v = c.keys ? held(car) : left[car].shift() ?? 0;
            cpu.a = v;
            read(m, car, v);
        } else if (at === syms["initials.shown"]) {
            shown = true;
            lastField = peek(syms.vsyncs);
            compare(`${c.name}, shown`, c, m);
            if (shots) writeFileSync(`${shots}/in${shot++}.png`, await s.screenshotActive({ scale: 2 }));
        } else if (at === syms["initials.nobody"]) {
            compare(`${c.name}, nobody entering`, c, m);
            if (shots) writeFileSync(`${shots}/in${shot++}.png`, await s.screenshotActive({ scale: 2 }));
            break;
        } else if (at === syms["initials.over"]) {
            settled(m);
            if (m.st.includes(1)) say(`${c.name}: over with an entry not finished here: positions ${m.pos}`);
            compare(`${c.name}, over`, c, m);
            longest = Math.max(longest, m.passes);
            if (c.want && c.want.join() !== m.letters[0].join()) say(`${c.name}: letters ${m.letters[0]}, not ${c.want}`);
            if (shots) writeFileSync(`${shots}/in${shot++}.png`, await s.screenshotActive({ scale: 2 }));
            for (let car = 0; car < 3; car++)
                if (m.rank[car] && (m.st[car] === 1 || m.st[car] === 3)) { m.t.names[m.rank[car]] = m.letters[car].map((l) => l + 11); entries++; }
            break;
        }
    }
    for (const shadow of [false, true]) {
        const where = shadow ? "the shadow copy's" : "the main copy's";
        for (let e = 1; e < 31; e++) {
            const d = [...ram(s, syms.HiScores + e * 6, 6, shadow)], n = [...ram(s, syms.HiNames + e * 3, 3, shadow)];
            if (d.join() !== six(m.t.digits[e]).join()) say(`${c.name}: ${where} entry ${e}'s score ${d.join("")}, not ${m.t.digits[e]}`);
            if (n.join() !== m.t.names[e].join()) say(`${c.name}: ${where} entry ${e}'s initials ${n}, not ${m.t.names[e]}`);
        }
    }
}
if (longest <= 750) say(`it never waited past the ST's 750 passes: ${longest}`);
if (!keysSeen) say("no key seen between the reads");
console.log(bad ? `${bad} wrong` : `${screens} screens of the initials right, ${reads} reads, ${keysSeen} changes of keys between them, ${entries} entries, up to ${longest} passes waited`);
process.exit(bad ? 1 : 0);
