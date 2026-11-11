// An autopilot for car 0, for time attack's checks (tools/ta_ghost_check.mjs): along the drones' path (the ST's, read
// from SUPER.DAT as tools/gen_logic.py does) as a drone takes its segments (drone.6502's next_segment, an even car's
// lane), steering for the segment's end, lifting off to turn (a turn accelerating costs speed) and not turning below
// speed 6. Crude: it laps 6 of the 8 tracks; on tracks 5 and 8 it wedges against a wall. Lost (put back after a
// wreck), it takes the nearest segment.
//
// Usage: const pilot = makePilot(s, syms) at logic_frame.played (the logic's bank and ANDY in), then pilot() there
// each frame: RcInput's byte for car 0.
import { readFileSync } from "node:fs";

// The path from the ST's data, as tools/gen_logic.py's path() reads it (time attack's build has none, D51): SUPER.DAT's
// entries at G_01E2A6, each x8, y8, length and direction word, big-endian; G_01D158's start and G_01D168's count a track.
const Super = readFileSync(new URL("../orig/st/SUPER.DAT", import.meta.url));
const PathOff = 0x2ce3a, PathStart = [0, 0x2a2, 0x554, 0x826, 0xc78, 0xfaa, 0x13fc, 0x17ce];
const PathCount = [0x54, 0x56, 0x5a, 0x8a, 0x66, 0x8a, 0x7a, 0x7c];
function path(track) {
    const base = PathOff + PathStart[track] + 2;
    const word = (k) => Super.readInt16BE(base + 2 * k);
    return [...Array(PathCount[track])].map((_, i) => {
        const d = word(4 * i + 3) & 0xffff;
        return { x: word(4 * i), y: word(4 * i + 1), len: word(4 * i + 2) & 255, dlo: d & 255, dhi: d >> 8 };
    });
}

export function makePilot(s, syms) {
    const cpu = s._machine.processor;
    const m = (a) => cpu.readmem(a);
    const s8 = (v) => (v & 0x80 ? v - 256 : v);
    const w16 = (lo, hi) => { const v = m(lo) | (m(hi) << 8); return v & 0x8000 ? v - 65536 : v; };
    const P = path(m(syms.TrackNum)), n = P.length;
    const DX = [...Array(16)].map((_, f) => s8(m(syms.DirX + f))), DY = [...Array(16)].map((_, f) => s8(m(syms.DirY + f)));
    for (const p of P) { const t = p.dlo & 15; p.ex = p.x + p.len * DX[t]; p.ey = p.y + p.len * DY[t]; }
    let idx = 0;
    const next = (i) => {
        let y = i + 2; if (y >= n) y -= n;
        const p = P[y];
        if (p.dhi === 1 && p.dlo === 0) return (y + 3) % n;            // a fork: an even car 3 on
        if (p.dhi & 2) return (y + m(syms.RcGateLane + (p.dlo & 3))) % n;
        if (p.dhi & 4) return (y + p.dlo) % n;
        return y;
    };
    const segDist = (p, x, y) => {
        const vx = p.ex - p.x, vy = p.ey - p.y, L = vx * vx + vy * vy || 1;
        let t = ((x - p.x) * vx + (y - p.y) * vy) / L; const tc = Math.max(0, Math.min(1, t));
        return [Math.hypot(x - p.x - tc * vx, y - p.y - tc * vy), t];
    };
    let held = 0;
    const input = function () {
        const x = w16(syms.RcX8Lo, syms.RcX8Hi), y = w16(syms.RcY8Lo, syms.RcY8Hi), dir = m(syms.RcDir);
        let [d, t] = segDist(P[idx], x, y);
        if (d > 8 * 40) {                                              // lost (put back): the nearest segment
            let best = 1e9; for (let i = 0; i < n; i++) { const [di] = segDist(P[i], x, y); if (di < best) { best = di; idx = i; } }
            [d, t] = segDist(P[idx], x, y);
        }
        for (let k = 0; k < 4 && (t > 0.999 || Math.hypot(P[idx].ex - x, P[idx].ey - y) < 8 * 20); k++) { idx = next(idx); [d, t] = segDist(P[idx], x, y); }
        const p = P[idx];
        const tx = p.ex - x, ty = p.ey - y;
        let want = 0, bestDot = -1e9;
        for (let f = 0; f < 16; f++) { const dot = (DX[f] * tx + DY[f] * ty) / Math.hypot(DX[f], DY[f]); if (dot > bestDot) { bestDot = dot; want = f; } }
        const diff = (want - dir + 16) & 15;
        const speed = m(syms.RcSpeedLo) | (m(syms.RcSpeedHi) << 8);
        if (diff === 0 || (speed & 0x8000) || speed < 6) return 0x80;   // (a turn costs speed: none from a standstill)
        return diff <= 8 ? 8 : 4;                                       // (a turn accelerating costs speed: lift off)
    };
    input.idx = () => idx;
    input.P = P;
    return input;
}
