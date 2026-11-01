// A screenshot of the renderer test in headless jsbeeb (a Master 128), at a frame of the race: the display
// as it was shown, two frames after that frame was drawn.
//
// Usage (from the repo root, after make beeb): node tools/screenshot.mjs FRAME OUT.png
// (Each stop is a breakpoint: after one, jsbeeb's runFor also runs the cycles the stopped run had left.)

import { writeFileSync } from "node:fs";
import { bootDisc, runTo, symbols } from "./jsbeeb.mjs";

const [frame, out] = [Number(process.argv[2]), process.argv[3]];
const syms = symbols();
const s = await bootDisc();
for (let n = 0; n < frame + 3; n++) await runTo(s, syms["frame_loop.frame_top"]);
writeFileSync(out, await s.screenshotActive({ scale: 2 }));
process.exit(0);
