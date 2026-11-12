// Time attack's name (docs/brief-timeattack-2026-11-10.md, step 6g; tagame.6502's tg_type), typed for the checks:
// 3 fields with nothing held, then each character's key held 3 fields and let go 3, then Return held 3. The name's
// loop acts on a key as it goes down, and on nothing till every key held as it came up is let go (a key pressed in
// its first field counts as one held), so the caller lets go of the race's keys first.
//
// nameKeys(ch): the keys for a character (A-Z, 0-9, space, the point, minus, and ! as SHIFT and 1).
// typeName(s, name): name typed, then Return; at tg_type's loop (tg_type.field), nothing else held.
// toFront(s, syms, name): run to the front end's wait (game_resume.idle, in the background's bank), the name typed
//   if the race made an entry (tg_type's loop reached first), its save then done; true if it was typed.

import { runToAny } from "./jsbeeb.mjs";

const Field = 39936;

export const nameKeys = (ch) => ch === " " ? ["Space"] : ch === "." ? ["Period"] : ch === "-" ? ["Minus"]
    : ch === "!" ? ["ShiftLeft", "Digit1"] : ch >= "0" && ch <= "9" ? [`Digit${ch}`] : [`Key${ch}`];

export async function typeName(s, name) {
    await s.runFor(3 * Field);
    for (const ch of name) {
        const keys = nameKeys(ch);
        for (const k of keys) s.keyDown(k);
        await s.runFor(3 * Field);
        for (const k of [...keys].reverse()) s.keyUp(k);
        await s.runFor(3 * Field);
    }
    s.keyDown("Enter");
    await s.runFor(3 * Field);
    s.keyUp("Enter");
}

export async function toFront(s, syms, name) {
    const bg = s.readMemory(syms.bankbg, 1)[0];
    let typed = false;
    for (;;) {
        const at = await runToAny(s, [[syms["game_resume.idle"], bg], [syms["tg_type.field"], bg]], 400000000);
        if (at === syms["game_resume.idle"]) return typed;
        await typeName(s, name);
        typed = true;
    }
}
