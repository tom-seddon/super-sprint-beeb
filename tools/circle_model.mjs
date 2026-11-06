// The winner's circle's screen as it should be for a state (F_01AC1C): tools/screens.py's pictures, each car's parts painted by its place, then the
// figure, the sparkles and the words, placed by the ST's numbers and plotted a pixel at a time, nothing shared with src/circle.6502. sums() works a
// race's bonuses out from its lap times the same way, by F_01AC1C's rules.
//
// state: { order[4], drone[4], avg[4], best[4] (each car's laps, in frames), shown[4][3] (its place, average and best bonuses so far), wrench[3],
//          score[3] (6 bytes each), laps[3], frame (the figure's, of the 16), spark[16] or null }

import { readFileSync } from "node:fs";
import { panels, place, plotter } from "./upgrades_model.mjs";

const G = (f) => readFileSync(`build/gen/${f}`);
const base = G("circle.bin"), cls = G("circle_class.bin"), figure = G("circle_figure.bin"), figureClass = G("circle_figure_class.bin");
const sparkle = G("circle_sparkle.bin"), junk = G("circle_junk.bin");
const Colours = [0xff, 0x0f, 0xf0, 0], PlaceX = [193, 109, 265, 91], PlaceY = [70, 122, 122, 171], Black = 0;
const SparkX = [0, 1, 4, 4, 6, 8, 10, 10, 28, 29, 31, 31, 32, 33, 35, 37], SparkY = [23, 45, 31, 45, 52, 38, 31, 52, 31, 38, 24, 45, 24, 38, 38, 52];
export const Hold = [[10, 10, 30], [10, 10, 10, 10], [10, 10, 10, 10, 10, 30, 10, 10, 10, 10], [100, 30, 30, 10, 10, 10, 10, 10, 10, 10, 10, 10]];
export const Steps = [[0, 1, 2, -1], [0, 1, 2, 1, -1], [0, 1, 0, 1, 0, 1, 2, 1, 2, 1, -1], [0, 1, 0, 1, 2, 3, 4, 5, 6, 0, 1, 0, -2]];
export const First = [0, 3, 6, 9];

const paint = (byte, m, body, sides) => {
    const b = m & 0x0f, s = m >> 4;
    return byte | ((b * 17) & body) | ((s * 17) & sides);
};
const look = (car, drone) => ({ sides: Colours[car], body: drone ? 0 : Colours[car] });
const row = (x, y) => place(x, y);

// A lap's bonus: what it's under the track's par, rounded down to 10.
export function bonus(frames, track) {
    const par = (15 + track) * 50, d = par > frames ? par - frames : 0;
    return d - d % 10;
}

// F_01AC1C: { avg, best (frames), points: [place, average, best] } for a car, as the race ended. ends: its 4 laps' end frames.
export function sums(ends, laps, raceFrames, track, placeNo) {
    const s16 = (v) => (v << 16) >> 16;
    const lens = ends.map((e, i) => i ? s16(e - ends[i - 1]) : e);
    let n = laps;
    if (!n) { lens[0] = raceFrames; n = 1; }
    const used = lens.slice(0, n), best = Math.min(10000, ...used), sum = s16(used.reduce((a, b) => a + b, 0)), avg = Math.trunc(sum / n);
    return { avg, best, points: [[1000, 500, 250, 0][placeNo], bonus(avg, track), bonus(best, track)] };
}

export function screen(st) {
    const out = Buffer.from(base);
    const places = st.order.map((car, p) => ({ car, ...look(car, st.drone[car]) }));
    // each car's masks are the map's, by where the place's palette entries are
    const owner = (at) => {
        const row8 = Math.floor(at / 640), y = row8 * 8 + (at & 7), x = ((at % 640) >> 3) * 4;
        if (y < 74) return 0;
        if (y < 140) return x < 150 ? 1 : 2;
        return 3;
    };
    for (let i = 0; i < 16000; i++) if (cls[i]) { const l = places[owner(i)]; out[i] = paint(out[i], cls[i], l.body, l.sides); }
    const f = st.frame * 384, l3 = places[3];
    for (let l = 0; l < 32; l++)
        for (let c = 0; c < 12; c++) out[row(160 + c * 4, 144 + l)] = paint(figure[f + l * 12 + c], figureClass[f + l * 12 + c], l3.body, l3.sides);
    const p = plotter(out), { small, bits } = p;
    panels(p, st);
    st.order.forEach((car, pl) => {
        const x = PlaceX[pl], y = PlaceY[pl];
        st.shown[car].forEach((v, line) => {
            const yy = y + line * 8, d = [Math.floor(v / 1000) % 10, Math.floor(v / 100) % 10, Math.floor(v / 10) % 10];
            let on = false;
            d.forEach((g, i) => { on ||= g > 0; if (on) ink(small, g, x + i * 6, yy, pl); });
            ink(small, 0, x + 18, yy, pl);
        });
        [st.avg[car], st.best[car]].forEach((frames, i) => {
            const yy = y + 8 + i * 8, tx = x - 36;
            let v = Math.trunc(frames / 5);
            if (v > 999) v = 999;
            if (v > 99) ink(small, Math.floor(v / 100), tx, yy, pl);
            const digit = (g, xx) => { if (g < 0) bits([...junk.subarray((-g - 1) * 6, -g * 6)].map((b) => b), xx, yy, Black); else ink(small, g, xx, yy, pl); };
            digit(Math.trunc(v / 10) % 10, tx + 6);
            ink(small, 10, tx + 12, yy, pl);
            digit(v % 10, tx + 18);
        });
    });
    if (st.spark) {
        const winner = places[0].body;
        st.spark.forEach((n, i) => {
            for (let l = 0; l < 8; l++)
                for (let h = 0; h < 2; h++) {
                    const at = row(SparkX[i] * 8 + h * 4, SparkY[i] + l), e = n * 48 + l * 6;
                    out[at] = (out[at] & sparkle[e + 2 + h]) | sparkle[e + h] | (sparkle[e + 4 + h] & winner);
                }
        });
    }
    return out;
}

const ink = (small, g, x, y) => small(g, x, y, Black);
