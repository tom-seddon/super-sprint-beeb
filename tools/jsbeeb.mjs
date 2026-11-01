// Headless jsbeeb for the tools: jsbeeb itself, the build's symbols, a Master 128 booted from a disc, and
// reads of main and shadow RAM. After Teddy Boy's tools/jsbeeb.mjs.
//
// jsbeeb comes from jsbeeb-mcp's npm package (npx jsbeeb-mcp fetches it), or JSBEEB=path/to/jsbeeb.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

function jsbeebSrc() {
    if (process.env.JSBEEB) return join(process.env.JSBEEB, "src");
    const npx = join(homedir(), ".npm", "_npx");
    for (const d of existsSync(npx) ? readdirSync(npx) : []) {
        const src = join(npx, d, "node_modules", "jsbeeb", "src");
        if (existsSync(join(src, "machine-session.js"))) return src;
    }
    throw new Error("jsbeeb not found: run `npx jsbeeb-mcp` once, or set JSBEEB");
}

const src = jsbeebSrc();
const { MachineSession } = await import(join(src, "machine-session.js"));

// every label, ZA_AUTO and assignment in the build's symbols, by name (scoped names as Baron writes them)
export function symbols(path = "build/sprint.json") {
    const syms = {};
    for (const asm of JSON.parse(readFileSync(path)).assemblies)
        for (const section of asm.sections)
            for (const kind of ["labels", "za_autos", "assignments"])
                for (const [k, v] of Object.entries(section[kind] || {})) syms[k] = typeof v === "object" ? v.value : v;
    return syms;
}

// the CPU's cycles since power-on
export const cycles = (s) => {
    const cpu = s._machine.processor;
    return cpu.cycleSeconds * 2000000 + cpu.currentCycles;
};

// main RAM (shadow false) or shadow RAM (true) at &3000-&7FFF, as jsbeeb keeps them: shadow is &8000 on
export function ram(s, addr, length, shadow = false) {
    const mem = s._machine.processor.ramRomOs;
    const at = addr + (shadow ? 0x8000 : 0);
    return mem.subarray(at, at + length);
}

// A Master 128 with its DFS, the disc booted with SHIFT-BREAK
export async function bootDisc(disc = "build/sprint.ssd", model = "Master") {
    const s = new MachineSession(model);
    await s.initialise();
    s.loadDisc(disc);
    s.keyDown(16);                      // SHIFT
    s.reset(true);
    await s.runFor(2000000);
    s.keyUp(16);
    return s;
}

// run until the CPU reaches addr (an execute breakpoint, removed after), or throw after limit cycles
export async function runTo(s, addr, limit = 40000000) {
    const id = s.addBreakpoint("execute", addr);
    try {
        for (let ran = 0; ran < limit; ran += 200000) {
            s.resetBreakpointHits();
            await s.runFor(200000);
            if (s.hitBreakpoint()) return;
        }
        throw new Error(`never reached &${addr.toString(16)}`);
    } finally {
        s.removeBreakpoint(id);
    }
}
