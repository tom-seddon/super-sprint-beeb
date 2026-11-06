// The upgrades' screen as it should be for a state (F_01A130): tools/screens.py's pictures, then the text the game draws over them,
// placed by the ST's numbers and plotted a pixel at a time, nothing shared with src/upgrades.6502.
//
// state: { car, drone[3], wrench[3], score[3] (6 bytes each), laps[3], level[3] (traction, top speed, turbo), dial, lit[4] }

import { readFileSync } from "node:fs";

const G = (f) => readFileSync(`build/gen/${f}`);
const all = G("upgrades_all.bin"), box = G("upgrades_box.bin"), font = G("upgrades_font.bin"), dial = G("upgrades_dial.bin"), Dial = 99;
const Small = 0, Big = 39 * 6, Comma = 10, Wrench = 11, White = 3, Bars = [[14, 105], [206, 105], [14, 168]];
const PanelX = [0, 108, 216], Colour = [3, 1, 2], Lit = [2, 1, 2], BoxOf = [3, 0, 2];
export const place = (x, y) => (y >> 3) * 640 + (x >> 2) * 8 + (y & 7);

export function screen(st) {
    const out = Buffer.from(all.subarray(st.car * 16000, (st.car + 1) * 16000));
    const pixel = (x, y, c) => {
        const at = place(x, y), n = x & 3, keep = 0x88 >> n;
        out[at] = (out[at] & ~keep) | (c & 2 ? 0x80 >> n : 0) | (c & 1 ? 8 >> n : 0);
    };
    const glyph = (off, lines, x, y, c) => {
        for (let l = 0; l < lines; l++)
            for (let j = 0; j < 8; j++) if (font[off + l] >> (7 - j) & 1) pixel(x + j, y + l, c);
    };
    const small = (g, x, y, c) => glyph(Small + g * 6, 6, x, y, c), big = (g, x, y, c) => glyph(Big + g * 11, 11, x, y, c);
    const code = (ch) => ch === " " ? 38 : (ch.charCodeAt(0) & 31) + 11;
    const text = (s, x, y, c) => { for (const ch of s) { small(code(ch), x, y, c); x += 6; } };
    for (let car = 0; car < 3; car++) {
        const x = PanelX[car], c = Colour[car];
        text(st.drone[car] ? "drone" : ["white car", "green car", "yellow car"][car], x + 2, 0, c);
        if (!st.drone[car]) {
            big(Wrench, x + 64, 0, c);
            big(Wrench + 1, x + 70, 0, c);
            small(Math.min(st.wrench[car], 9), x + 77, 0, c);
        }
        let dx = 2;
        st.score[car].forEach((d, i) => {
            if (!(d & 0x80)) big(d, x + dx, 7, c);
            if (i === 2 && !(d & 0x80)) big(Comma, x + dx + 10, 7, c);
            dx += i === 2 ? 14 : 10;
        });
        big(st.laps[car], x + 90, 7, c);
    }
    const lit = Lit[st.car];
    Bars.forEach(([x, y], u) => {
        for (let n = 1; n <= st.level[u]; n++) small(n, x + 24 + n * 12, y, lit);
        if (st.level[u] === 5) {
            for (let l = 0; l < 6; l++) for (let c = 0; c < 8; c++) out[place(x + 30 + c * 4, y - 38 + l)] = 0;
            text("taken", x + 30, y - 38, lit);
        }
    });
    st.lit.forEach((on, b) => {
        if (!on) return;
        for (let i = 0; i < 16000; i++) {
            const m = box[b * 16000 + i];
            if (m) out[i] = (out[i] & ~m) | (lit & 2 ? m & 0xf0 : 0) | (lit & 1 ? m & 0x0f : 0);
        }
    });
    for (let l = 0; l < 44; l++) {
        const lit = [];
        for (let c = 0; c < 16; c++) for (let p = 0; p < 16; p++) if (dial[p * 704 + l * 16 + c]) lit.push(c);
        if (lit.length) for (let c = Math.min(...lit); c <= Math.max(...lit); c++) out[place(128 + c * 4, Dial + l)] = dial[st.dial * 704 + l * 16 + c];
    }
    return out;
}

export const box_full = (st) => [st.level[1] === 5, false, st.level[2] === 5, st.level[0] === 5];
