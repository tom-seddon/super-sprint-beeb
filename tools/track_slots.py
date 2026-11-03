"""The fixed layout's check (Phase 5, 3a): the eight tracks' play builds may differ only inside the slots, the
per-track parts each region keeps at a fixed address, so one build's code and tables serve every track and a
track's file carries its slots alone.

Usage: track_slots.py DIR   (DIR holds t0.ssd .. t7.ssd and t0.lst .. t7.lst: tools/all_tracks.sh keeps them)

A slot is the bytes from a label `XSlot` to `XSlotEnd` in the same section. Its start must be at the same
address on every track; its end may differ only at a file's end (nothing after it to move). Every byte
outside a slot that differs between tracks is printed with the label it falls under, and the exit status is 1
if there is any (2 if the builds can't be compared).
"""
import bisect, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import dfs                                      # the kit's .ssd reader (used in place)

Files = {'SPRINTA': 'BgBank', 'SPRINTB': 'CarsBank', 'SPRINTC': 'TraceBank', 'SPRINTD': 'ObjBank'}


def listing(path):
    """(section -> sorted [(address, label)], {label: (section, address)}) from a listing's label lines."""
    by, at, stack = {}, {}, []
    for l in open(path, errors='replace'):
        m = re.match(r'^SECTION (\w+)', l)
        if m:
            stack.append(m.group(1))
            continue
        if l.startswith('ENDSECTION') and stack:
            stack.pop()
            continue
        m = re.match(r'^  ([0-9A-F]{4})\s+\.([A-Za-z_]\w*)\s*$', l)
        if m and stack:
            a = int(m.group(1), 16)
            by.setdefault(stack[-1], []).append((a, m.group(2)))
            at.setdefault(m.group(2), (stack[-1], a))
    return {k: sorted(set(v)) for k, v in by.items()}, at


def place(fname, off, at):
    """A disc file's offset -> (section, address)."""
    if fname in Files:
        return Files[fname], 0x8000 + off
    a = 0x3000 + off
    img, end = at['maincode_image'][1], at['maincode_end'][1]
    if a < img:
        return 'Shared', a
    if a < end:
        return 'MainCode', 0x0E00 + a - img
    if 'andy_image' in at and at['andy_image'][1] <= a < at['andy_end'][1]:
        return 'Andy', 0x8000 + a - at['andy_image'][1]
    return 'Sprint', a


def main(d):
    imgs = [dfs.read_image(f'{d}/t{n}.ssd').files for n in range(8)]
    lists = [listing(f'{d}/t{n}.lst') for n in range(8)]
    by0, at0 = lists[0]
    # the slots, by section: [start, end), the end the largest over the tracks
    slots, bad = {}, 0
    for name, (sec, a) in at0.items():
        if not name.endswith('Slot') or name + 'End' not in at0:
            continue
        starts = {l[1][name][1] for l in lists}
        if len(starts) > 1:
            print(f'{name}: starts at {sorted(hex(s) for s in starts)}, not one address')
            bad += 1
        slots.setdefault(sec, []).append((a, max(l[1][name + 'End'][1] for l in lists), name))
    for f in ['SPRINTA', 'SPRINTB', 'SPRINTC', 'SPRINTD', 'SPRINT']:
        ds = [im[f].data for im in imgs]
        n = max(len(x) for x in ds)
        runs, i = [], 0
        while i < n:
            vals = {x[i] if i < len(x) else None for x in ds}
            sec, a = place(f, i, at0)
            inside = any(s <= a < e for s, e, _ in slots.get(sec, []))
            if len(vals) > 1 and not inside:
                j = i
                while j < n and len({x[j] if j < len(x) else None for x in ds}) > 1 \
                        and not any(s <= place(f, j, at0)[1] < e for s, e, _ in slots.get(place(f, j, at0)[0], [])):
                    j += 1
                runs.append((sec, a, j - i))
                i = j
            else:
                i += 1
        merged = []                             # runs closer than 16 bytes as one
        for r in runs:
            if merged and merged[-1][0] == r[0] and r[1] - (merged[-1][1] + merged[-1][2]) < 16:
                merged[-1] = (r[0], merged[-1][1], r[1] + r[2] - merged[-1][1])
            else:
                merged.append(r)
        for sec, a, k in merged[:20]:
            v = by0.get(sec, [])
            p = bisect.bisect_right(v, (a, '~')) - 1
            label = f'{v[p][1]}+{a - v[p][0]}' if p >= 0 else '?'
            print(f'{f} {sec} &{a:04X} {k} byte(s) differ outside a slot ({label})')
        if len(merged) > 20:
            print(f'{f}: and {len(merged) - 20} runs more')
        bad += len(merged)
    for sec, v in sorted(slots.items()):
        print(f'{sec}: ' + ', '.join(f'{n} &{s:04X}-&{e - 1:04X} ({e - s})' for s, e, n in sorted(v)))
    print('outside the slots: ' + ('the same on every track' if not bad else f'{bad} differences'))
    return 1 if bad else 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
