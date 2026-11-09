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

// one of jsbeeb's own modules, by its file's name in src ("disc.js")
export const jsbeebModule = (file) => import(join(src, file));

// A DFS disc's files, by name ("$.TRACKC" or "TRACKC"): {load, exec, data, entry (the catalogue's offset)}. Side 0
// of an .ssd or .dsd, from its path or its bytes.
export function discFiles(path) {
    const d = typeof path === "string" ? readFileSync(path) : path, files = {};
    for (let i = 8; i <= d[0x105]; i += 8) {
        const name = String.fromCharCode(...d.subarray(i, i + 7)).trimEnd();
        const dir = String.fromCharCode(d[i + 7] & 0x7f), e = d.subarray(0x100 + i, 0x108 + i), hi = e[6];
        const length = e[4] | (e[5] << 8) | (((hi >> 4) & 3) << 16), sector = e[7] | ((hi & 3) << 8);
        const file = { load: e[0] | (e[1] << 8), exec: e[2] | (e[3] << 8), data: d.subarray(sector * 256, sector * 256 + length), entry: i };
        files[`${dir}.${name}`] = file;
        if (dir === "$") files[name] = file;
    }
    return files;
}

// A ZX02 stream unpacked (zx02depack.6502's format; the kit's zx02.py decompress, line for line): a Uint8Array.
export function unzx02(z) {
    const out = [];
    let pos = 0, mask = 0, byte = 0, back = null, offset = 1;
    const bit = () => {
        if (back !== null) { const b = back & 1; back = null; return b; }
        if (!mask) { byte = z[pos++]; mask = 128; }
        const b = byte & mask ? 1 : 0;
        mask >>= 1;
        return b;
    };
    const gamma = () => { let v = 1; while (bit()) v = ((v << 1) | bit()) & 0xff; return v; };
    const count = (v) => v || 256;
    const copy = (n) => { for (let i = 0; i < n; i++) out.push(out[out.length - offset]); };
    for (let state = "literals"; ;) {
        if (state === "literals") {
            const n = count(gamma());
            for (let i = 0; i < n; i++) out.push(z[pos++]);
            state = bit() ? "new" : "copy";
        } else if (state === "copy") {
            copy(count(gamma()));
            state = bit() ? "new" : "literals";
        } else {
            const msb = gamma();
            if (!msb) return Uint8Array.from(out);
            const lsb = z[pos++];
            offset = (msb - 1) * 128 + (lsb >> 1) + 1;
            back = lsb;
            copy(count((gamma() + 1) & 0xff));
            state = bit() ? "new" : "literals";
        }
    }
}

// A condition for a stop at a label in a file loaded over others at the same address (the screens' files, all at
// FrontPicOrg and BgOrg): the bytes there must be that file's, from the disc. As few as tell it from every other
// file's section there (at least 4), the others being those loaded to the same address. undefined for a label in
// no file's section, or in one no other such file's covers. Throws if no 16 bytes tell them apart.
export function fileGate(symbolsPath, discPath, label) {
    const sections = [];
    for (const asm of JSON.parse(readFileSync(symbolsPath)).assemblies) {
        const at = (i) => asm.sections[i];
        asm.sections.forEach((section, i) => {
            const file = section.parent == null ? undefined : at(section.parent);
            if (file?.attributes?.filename && section.attributes?.org !== undefined) sections.push({ section, file });
        });
    }
    const disc = discFiles(discPath), offsets = new Map(), next = new Map(), raw = new Map();
    for (const { section, file } of sections) {     // (a file is its sections, in order)
        const o = next.get(file) ?? 0;
        offsets.set(section, o);
        next.set(file, o + section.size);
    }
    const unpacked = (file) => {        // (a boot file the game's disc has packed says so by its load address: boot.6502)
        const f = disc[file.attributes.filename];
        if (!f || f.load === (file.attributes.load & 0xffff)) return f?.data;
        if (!raw.has(f)) raw.set(f, unzx02(f.data));
        return raw.get(f);
    };
    const bytesAt = ({ section, file }, addr, n) => {
        const data = unpacked(file);
        const o = offsets.get(section) + addr - section.attributes.org;
        return data && [...data.subarray(o, o + n)];
    };
    const value = (v) => (typeof v === "object" ? v.value : v);
    const home = sections.find(({ section }) => section.labels && label in section.labels);
    if (!home) return undefined;
    const addr = value(home.section.labels[label]);
    const covers = ({ section }) => section.attributes.org <= addr && addr < section.attributes.org + section.size;
    const others = sections.filter((x) => x.file !== home.file && x.file.attributes.load === home.file.attributes.load && covers(x));
    if (!others.length) return undefined;
    for (let n = 4; n <= 16; n++) {
        const mine = bytesAt(home, addr, n);
        if (!mine || mine.length < n) throw new Error(`${label}: ${home.file.attributes.filename} isn't on ${discPath}`);
        if (others.every((x) => { const b = bytesAt(x, addr, n); return !b || b.join() !== mine.join(); }))
            return mine.map((b, i) => (i ? `?(PC+${i}) = ${b}` : `?PC = ${b}`)).join(" && ");
    }
    throw new Error(`${label}: 16 bytes don't tell ${home.file.attributes.filename} from the files under it`);
}

// the CPU's cycles since power-on
export const cycles = (s) => s.elapsedCycles;

// main RAM (shadow false) or shadow RAM (true) at &3000-&7FFF, as jsbeeb keeps them: shadow is &8000 on
export function ram(s, addr, length, shadow = false) {
    const mem = s._machine.processor.ramRomOs;
    const at = addr + (shadow ? 0x8000 : 0);
    return mem.subarray(at, at + length);
}

// A Master 128 with its DFS, the disc booted with SHIFT-BREAK, SHIFT held for hold cycles (ADFS wants longer: its drive spins up first)
export async function bootDisc(disc = "build/sprint.ssd", model = "Master", hold = 2000000) {
    const s = new MachineSession(model);
    await s.initialise();
    s.loadDisc(disc);
    s.keyDown("ShiftLeft");
    s.reset(true);
    await s.runFor(hold);
    s.keyUp("ShiftLeft");
    return s;
}

// The game's disc for a check: build/game.ssd, or with --adfs on the command line build/game.adl (D32) on a Master
// with ADFS, booted by SHIFT-BREAK too, held longer as its drive spins up first. The two discs hold the same files.
// gameArgs: the command line's arguments but --adfs.
export const adfs = process.argv.includes("--adfs");
export const gameDisc = adfs ? "build/game.adl" : "build/game.ssd";
export const gameArgs = process.argv.slice(2).filter((a) => a !== "--adfs");
export const bootGame = () => (adfs ? bootDisc(gameDisc, "MasterADFS", 8000000) : bootDisc(gameDisc));

// After a breakpoint stops a run, jsbeeb's next runFor also runs the cycles the stopped run had left: drop
// them, so a run is the cycles asked for from where the CPU is.
export function settle(s) {
    const cpu = s._machine.processor;
    cpu.targetCycles = cpu.currentCycles;
}

// ANDY's bytes: a Master's 4K over &8000-&8FFF while ROMSEL's bit 7 is set (D15: mask B and the logic's
// state), whatever the CPU has paged now; readMemory's { bank } reads the bank's own &8000-&8FFF instead
export function andy(s, addr, length = 1) {
    if (addr < 0x8000 || addr + length > 0x9000) throw new Error(`&${addr.toString(16)}: not in ANDY`);
    const cpu = s._machine.processor, romsel = cpu.romsel;
    try {
        cpu.romSelect(romsel | 0x80);
        return s.readMemory(addr, length);
    } finally {
        cpu.romSelect(romsel);
    }
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

// run until the CPU reaches any of addrs, each [address, bank, condition] (bank: the sideways bank that must be
// paged in, for an address in &8000-&BFFF, where another bank's code can sit; condition: jsbeeb's, as fileGate's;
// either undefined if not wanted), or throw after limit cycles. -> the address reached. The breakpoints are
// removed after.
export async function runToAny(s, addrs, limit = 40000000) {
    const ids = addrs.map(([a, bank, condition]) => s.addBreakpoint("execute", a, { bank, condition }));
    try {
        for (let ran = 0; ran < limit; ran += 200000) {
            s.resetBreakpointHits();
            settle(s);
            await s.runFor(200000);
            const hit = s.hitBreakpoint();
            if (hit) return hit.address;
        }
        throw new Error(`never reached ${addrs.map(([a]) => `&${a.toString(16)}`).join(", ")}`);
    } finally {
        for (const id of ids) s.removeBreakpoint(id);
    }
}
