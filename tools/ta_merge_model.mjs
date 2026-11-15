// The merge MERGE makes (docs/brief-merge-2026-11-15.md §3, D57), modelled from the brief, not from src/merge.6502:
// - a track's table: both discs' entries (an empty one, its time 0, not one), each of the source's that's one of the
//   destination's (time, upgrades and name, the name to its end: its first 0 or 10 characters) out, one for one; then
//   in order of time, a stable sort of the destination's then the source's, so the destination's first on a tie and
//   each table's own order kept; the first 10, the rest of the 10 empty (all 0);
// - a track's ghost: the source's if it has one and the destination hasn't, or it's faster; a tie kept;
// - each track's line: "Track n  no change", or "+k entries" (or "entry") and/or "ghost added" or "ghost replaced";
//   and "Nothing to change." after them if no track has a change.
//
// TIMES as tatable.6502 lays it out: 80 entries, a column a field (time low, time high, upgrades, then 10-byte names),
// track * 10 + place.

export const Entries = 80, NameLen = 10, TableLen = Entries * (3 + NameLen);

// entry e of table t: [time, upgrades, name bytes]
export function entry(t, e) {
    return [t[e] | t[Entries + e] << 8, t[2 * Entries + e], Array.from(t.subarray(3 * Entries + e * NameLen, 3 * Entries + (e + 1) * NameLen))];
}
export function setEntry(t, e, [time, ups, name]) {
    t[e] = time & 255;
    t[Entries + e] = time >> 8;
    t[2 * Entries + e] = ups;
    for (let i = 0; i < NameLen; i++) t[3 * Entries + e * NameLen + i] = name[i] ?? 0;
}
// a name's bytes to its end
const ended = (name) => { const i = name.indexOf(0); return i < 0 ? name : name.slice(0, i); };
const same = (a, b) => a[0] === b[0] && a[1] === b[1] && ended(a[2]).join() === ended(b[2]).join();

// dst, src: the tables (1,040 bytes, or null: none); dGhosts, sGhosts: each track's ghost's time, or null
export function merge(dst, src, dGhosts, sGhosts) {
    const table = new Uint8Array(TableLen), added = [], ghost = [], lines = [];
    for (let track = 0; track < 8; track++) {
        const of = (t) => (t ? Array.from({ length: 10 }, (_, i) => entry(t, track * 10 + i)).filter((x) => x[0]) : []);
        const d = of(dst), matched = d.map(() => false);
        const s = of(src).filter((x) => {
            const i = d.findIndex((y, j) => !matched[j] && same(x, y));
            if (i < 0) return true;
            matched[i] = true;
            return false;
        });
        const all = [...d.map((x) => [x, false]), ...s.map((x) => [x, true])].sort((a, b) => a[0][0] - b[0][0]).slice(0, 10);
        all.forEach(([x], i) => setEntry(table, track * 10 + i, x));
        added.push(all.filter(([, fromSource]) => fromSource).length);
        const sg = sGhosts[track], dg = dGhosts[track];
        ghost.push(sg == null ? 0 : dg == null ? 1 : sg < dg ? 2 : 0);
        const parts = [];
        if (added[track]) parts.push(`+${added[track]} ${added[track] === 1 ? "entry" : "entries"}`);
        if (ghost[track]) parts.push(ghost[track] === 1 ? "ghost added" : "ghost replaced");
        lines.push(`Track ${track + 1}  ${parts.length ? parts.join(", ") : "no change"}`);
    }
    return { table, added, ghost, lines, nothing: added.every((n) => !n) && ghost.every((g) => !g) };
}
