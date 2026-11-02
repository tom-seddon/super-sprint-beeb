// Headless jsbeeb for the tools: jsbeeb itself, the build's symbols, a Master 128 booted from a disc, and
// reads of main and shadow RAM. After Teddy Boy's tools/jsbeeb.mjs.
//
// jsbeeb is the one the jsbeeb MCP runs: `.mcp.json` pins jsbeeb-mcp's version, and the jsbeeb loaded here
// is the one in the npx cache holding exactly that version (`npx -y jsbeeb-mcp@VERSION < /dev/null` once
// fetches it), as the beeb-port-kit's tools/jsbeeb_src.mjs does, so the tools and the kit's harnesses
// measure on one emulator. Its version goes to stderr. JSBEEB=path/to/jsbeeb overrides it.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

function jsbeebSrc() {
    if (process.env.JSBEEB) return join(process.env.JSBEEB, "src");
    const pin = /jsbeeb-mcp@([0-9.]+)/.exec(readFileSync(".mcp.json", "utf8"))?.[1];
    if (!pin) throw new Error(".mcp.json doesn't pin jsbeeb-mcp@VERSION");
    const npx = join(homedir(), ".npm", "_npx");
    for (const d of existsSync(npx) ? readdirSync(npx) : []) {
        const mods = join(npx, d, "node_modules");
        const pkg = join(mods, "jsbeeb-mcp", "package.json");
        if (existsSync(pkg) && JSON.parse(readFileSync(pkg)).version === pin
            && existsSync(join(mods, "jsbeeb", "src", "machine-session.js"))) {
            const v = JSON.parse(readFileSync(join(mods, "jsbeeb", "package.json"))).version;
            console.error(`[jsbeeb ${v}, jsbeeb-mcp ${pin}]`);
            return join(mods, "jsbeeb", "src");
        }
    }
    throw new Error(`no npx cache holds jsbeeb-mcp@${pin}: run \`npx -y jsbeeb-mcp@${pin} < /dev/null\` once, or set JSBEEB`);
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
export const cycles = (s) => s.elapsedCycles;

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
    s.keyDown("ShiftLeft");
    s.reset(true);
    await s.runFor(2000000);
    s.keyUp("ShiftLeft");
    return s;
}

// After a breakpoint stops a run, jsbeeb's next runFor also runs the cycles the stopped run had left: drop
// them, so a run is the cycles asked for from where the CPU is.
export function settle(s) {
    const cpu = s._machine.processor;
    cpu.targetCycles = cpu.currentCycles;
}

// run until the CPU reaches addr (an execute breakpoint, removed after), or throw after limit cycles
export async function runTo(s, addr, limit = 40000000) {
    const id = s.addBreakpoint("execute", addr);
    try {
        for (let ran = 0; ran < limit; ran += 200000) {
            s.resetBreakpointHits();
            settle(s);
            await s.runFor(200000);
            if (s.hitBreakpoint()) return;
        }
        throw new Error(`never reached &${addr.toString(16)}`);
    } finally {
        s.removeBreakpoint(id);
    }
}
