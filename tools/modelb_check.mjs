// The game's and time attack's discs on a Model B, which they refuse (boot.6502: NMOS code to there): SHIFT-BREAK
// on jsbeeb's Model B with DFS 1.2 (PAGE &1900) and on its 1770 model (DFS and ADFS both, PAGE &1F00, the worst case;
// Tom, 2026-11-15: a Model B's test covers a B+'s, which jsbeeb hasn't), build/game.ssd and build/ta.ssd each:
// - "Super Sprint needs Master 128 or Compact" on MODE 7's screen within 10 s of the boot;
// - after BREAK, !BOOT's load address (its catalogue's) at or above the machine's PAGE, so its load leaves the
//   filing system's workspace, under PAGE, alone (the plan's "Possible later", 2026-11-15: it was &1200, below both);
// - the machine fine after it: *CAT lists the disc's files, BASIC works.
// The ADFS discs aren't tried: the 1770 model boots its DFS at SHIFT-BREAK. An ADFS-only Model B, Tom's worry, isn't
// one of jsbeeb's.
//
// Exit status: 1 if anything's wrong, else 0.
//
// Usage (from the repo root, after make game and make ta): node tools/modelb_check.mjs

import { discFiles, jsbeebModule } from "./jsbeeb.mjs";

const { MachineSession } = await jsbeebModule("machine-session.js");
const Refused = "Super Sprint needs Master 128 or Compact";
let bad = 0, checked = 0;
const want = (what, ok) => (ok ? checked++ : bad++ < 30 && console.log(`${what}: wrong`));

// (a pause before each line, as a person's)
const Gap = 200000;
const lines = async (s) => (await s.runUntilPrompt(20)).screenText.split("\n").map((l) => l.trimEnd());
async function type(s, text) {
    await s.runFor(Gap);
    await s.type(text);                                 // (jsbeeb's type() ends with RETURN)
    return lines(s);
}
// MODE 7's screen as text, the top row first (the OS's hardware scroll undone: &350, the top line's address), its
// 40-character rows run together
function screen(s) {
    const top = s.readMemory(0x350, 2), at = (top[0] | top[1] << 8) - 0x7c00, m = s.readMemory(0x7c00, 1000);
    return Array.from({ length: 1000 }, (_, i) => m[(at + i) % 1000] & 127)
        .map((b) => (b >= 32 ? String.fromCharCode(b) : " ")).join("");
}

for (const disc of ["build/game.ssd", "build/ta.ssd"]) {
    const boot = discFiles(disc)["!BOOT"];
    for (const model of ["B-DFS1.2", "B1770"]) {
        const what = `${disc} on a Model B (${model})`;
        const s = new MachineSession(model);
        await s.initialise();
        s.loadDisc(disc);
        s.keyDown("ShiftLeft");
        s.reset(true);
        await s.runFor(2000000);                        // (SHIFT held through the OS's start-up)
        s.keyUp("ShiftLeft");
        let seen = false;
        for (let t = 0; t < 100 && !seen; t++) {        // (up to 10 s, a tenth at a time)
            await s.runFor(200000);
            seen = screen(s).includes(Refused);
        }
        want(`${what}: refused, "${Refused}" (${JSON.stringify(screen(s).replace(/ +/g, " ").trim().slice(-80))})`, seen);
        s.reset(false);                                 // (BREAK)
        await lines(s);
        let o = await type(s, "PRINT ~PAGE");
        const page = parseInt(o.filter((l) => /^[0-9A-F]+$/.test(l.trim())).at(-1), 16);
        want(`${what}: !BOOT's load, &${boot.load.toString(16).toUpperCase()}, at or above PAGE, &${page.toString(16).toUpperCase()}`,
            page >= 0xe00 && boot.load >= page);
        o = await type(s, "*CAT");
        want(`${what}: the disc catalogued after it (${JSON.stringify(o.slice(-3))})`,
            o.some((l) => /!BOOT/.test(l)) && o.some((l) => /\bSPRINT\b/.test(l)) && o.at(-1) === ">");
        o = await type(s, "PRINT 6*7");
        want(`${what}: BASIC after it`, o.some((l) => l.trim() === "42") && o.at(-1) === ">");
    }
}
console.log(bad ? `${bad} wrong` : `Model Bs right: ${checked} checked (the game's and time attack's discs, on DFS 1.2 and the ` +
    `1770: refused, !BOOT loaded at or above PAGE, the disc and BASIC fine after)`);
process.exit(bad ? 1 : 0);
