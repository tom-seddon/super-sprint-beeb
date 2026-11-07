// The initials' screen as it should be for a state (F_017A42): tools/screens.py's prepare to race, each drone's panel cleared, "GAME OVER" or the entry's
// words and the letters, placed by the ST's numbers and plotted a pixel at a time, nothing shared with src/initials.6502.
//
// state: { drone[3], panel[3] ("player", "blank", "over", "entry"), rank[3], letters[3] (each the letters shown, 1-26, 27 none) }

import { readFileSync } from "node:fs";
import { place, plotter } from "./upgrades_model.mjs";

const G = (f) => readFileSync(`build/gen/${f}`);
const all = G("prepare_all.bin"), none = G("prepare_none.bin"), big = G("initials_big.bin");
const Panels = [0, 27 * 8, 54 * 8, 80 * 8], Colour = [3, 1, 2], Lines = [3, 13, 23];

export function screen(st) {
    const out = Buffer.from(all), p = plotter(out);
    for (let c = 0; c < 3; c++)
        if (st.drone[c]) for (let r = 0; r < 6; r++) none.copy(out, r * 640 + Panels[c], r * 640 + Panels[c], r * 640 + Panels[c + 1]);
    const letter = (g, x, y, c) => {
        if (g === 27) return;
        for (let l = 0; l < 10; l++) {
            const v = big[(g - 1) * 20 + l * 2] << 8 | big[(g - 1) * 20 + l * 2 + 1];
            for (let j = 0; j < 16; j++) if (v >> (15 - j) & 1) p.pixel(x + j, y + 1 + l, c);
        }
    };
    for (let c = 0; c < 3; c++) {
        const kind = st.panel[c], left = 15 + 107 * c, ink = Colour[c];
        if (kind === "player") continue;
        for (const y of Lines) for (let l = 0; l < 6; l++) for (let b = 0; b < 26; b++) out[place((c * 27 + b) * 4, y + l)] = 0;
        if (kind === "over") {
            [..."game"].forEach((ch, i) => letter(ch.charCodeAt(0) & 31, left + 16 + i * 11, 2, ink));
            [..."over"].forEach((ch, i) => letter(ch.charCodeAt(0) & 31, left + 16 + i * 11, 19, ink));
        } else if (kind === "entry") {
            p.text("enter", left + 24, 3, ink);
            p.text("initials", left + 15, 11, ink);
            p.text("position", left + 6, 19, ink);
            if (st.rank[c] > 9) p.small(Math.floor(st.rank[c] / 10), left + 60, 19, ink);
            p.small(st.rank[c] % 10, left + 66, 19, ink);
            st.letters[c].forEach((g, i) => letter(g, 37 + 107 * c + 11 * i, 28, ink));
        }
    }
    return out;
}
