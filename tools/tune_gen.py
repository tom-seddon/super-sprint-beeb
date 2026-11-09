"""The front end's tunes for the BBC (Phase 5, step 9, D11): each captured whole on the ST (tools/st_trace_tunes.py),
converted field by field to the SN76489 as the race's effects are (tools/sound_gen.py's channel_field), and written as
each channel's stream of steps, packed.

Usage: tune_gen.py TUNES.json OUTDIR [--wav WAVDIR]

A tune's fields run from its start to one field after its last sound (a silent one, so the chip's left quiet). Each
channel is a stream of one step a field:
- one byte, level << 4 | d, d 0-7 or 9-15: the YM's 4-bit level (0 silent), and the tone's period moved by d, signed
  (-7 to +7: the ST's vibrato), or for a channel on the noise, d 0, the same noise;
- three bytes, level << 4 | 8, then the period's low byte and its high 2 bits, or the noise's rate and &40: a new note.
The level is the YM's, not the SN's attenuation, so the player can fade it as the ST does (the volume times the
master, G_01F264, / 16) before SnAtten turns it into one. A tone's level is 0 where the ST had it off, and a channel
on the noise plays the noise alone (sound_gen's rule); the captures never have two channels on the noise at once, nor
the YM's envelope (both are checked here).

Writes OUTDIR/tunes_expect.json (each tune's fields, for tools/tune_check.mjs), OUTDIR/tunes_fixed.bin (the select's,
prepare's, the join's and the ding's, at the fourth bank's end; its length in OUTDIR/tunes_fixed.6502) and
OUTDIR/tunes_circle.bin (the circle's five, in TRACKC): each a block of descriptors, 10 bytes a tune, then the tunes,
each packed whole with ZX02 (its three streams one after the other, which packs better than a field at a time). A
descriptor, little-endian words: the packed tune's offset in the block, its channel 1's and 2's streams' offsets in
the unpacked tune, the unpacked tune's size, its fields. Each block is unpacked again here (the kit's zx02.py) and
played by the same steps as the BBC's player, and must give the converter's fields exactly.

With --wav, WAVDIR/<tune>_ym.wav and _sn.wav: the YM's fields (its three channels) and the SN's, to listen to side
by side.
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reference', 'beeb-port-kit', 'template', 'tools'))
import sound_gen as G
from ay2sn import sn_atten

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
Fixed = ['select', 'prepare', 'join', 'ding']   # (src/front.6502's Tune... numbers, in this order)
Slot = {'select': 0x900, 'prepare': 0x900, 'join': 0x550, 'ding': 0x550, **{f'circle{k}': 0x900 for k in range(5)}}
# each tune's room unpacked in ANDY (front.6502): slot 0 at &8000, slot 1 the jingle's at &8900 up to the logic's state
Circle = [f'circle{k}' for k in range(5)]
Desc = 10


def level_of(att):
    """The YM level the converter's attenuation came from (SnAtten's inverse: the lowest that gives it)."""
    return next(v for v in range(16) if (sn_atten(v) if v else G.Silent) == att)


def fields_of(F):
    """-> the tune's fields, each channel (period or noise rate, level, on the noise) as the converter has it."""
    loud = [i for i, fd in enumerate(F) if any(fd['regs'][8 + c] & 31 for c in range(3))]
    n = loud[-1] + 2
    out = []
    for i in range(n):
        r = F[i]['regs']
        assert not any(r[8 + c] & 16 for c in range(3)), f'field {i}: the envelope'
        row = []
        for c in range(3):
            p, att, rate, natt = G.channel_field(F, i, c)
            row.append((rate, level_of(natt), True) if rate is not None else (p, level_of(att), False))
        assert sum(ch[2] for ch in row) <= 1, f'field {i}: two channels on the noise'
        out.append(row)
    return out


def stream(fields, c):
    out, prev = [], None
    for row in fields:
        v, lvl, noisy = row[c]
        if prev and prev[2] == noisy and (v == prev[0] if noisy else -7 <= v - prev[0] <= 7):
            out.append(lvl << 4 | (0 if noisy else (v - prev[0]) & 15))
        else:
            out += [lvl << 4 | 8, v & 255, 0x40 if noisy else v >> 8]
        prev = (v, lvl, noisy)
    return out


def play(raw, offs, n):
    """The BBC player's steps (src/sound.6502): -> the fields, as fields_of gives them."""
    pos, state, out = list(offs), [None] * 3, []
    for _ in range(n):
        row = []
        for c in range(3):
            b = raw[pos[c]]
            lvl, d = b >> 4, b & 15
            if d == 8:
                lo, hi = raw[pos[c] + 1], raw[pos[c] + 2]
                state[c] = (lo, True) if hi & 0x40 else (lo | hi << 8, False)
                pos[c] += 3
            else:
                v, noisy = state[c]
                state[c] = (v if noisy else v + (d - 16 if d > 8 else d), noisy)
                pos[c] += 1
            row.append((state[c][0], lvl, state[c][1]))
        out.append(row)
    assert pos[0] == offs[1] and pos[1] == offs[2] and pos[2] == len(raw), 'the streams not used up'
    return out


def zx02(data):
    exe = os.path.join(ROOT, 'build', 'zx02')
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'in'), 'wb').write(bytes(data))
        subprocess.run([exe, '-f', '-q', os.path.join(d, 'in'), os.path.join(d, 'out')], check=True, capture_output=True)
        return open(os.path.join(d, 'out'), 'rb').read()


def block(T, names, path):
    import zx02 as Z                    # (the kit's, in Python: each packed tune unpacked again)
    descs, blobs, at = [], [], Desc * len(names)
    report = []
    for name in names:
        fields = fields_of(T[name])
        streams = [stream(fields, c) for c in range(3)]
        raw = streams[0] + streams[1] + streams[2]
        assert len(raw) <= Slot[name], f'{name}: {len(raw)} bytes unpacked, its slot {Slot[name]}'
        offs = [0, len(streams[0]), len(streams[0]) + len(streams[1])]
        assert play(raw, offs, len(fields)) == fields, f'{name}: the player and the converter differ'
        packed = zx02(raw)
        assert list(Z.decompress(packed)) == raw, f'{name}: ZX02 round trip'
        descs += [at, offs[1], offs[2], len(raw), len(fields)]
        blobs.append(packed)
        at += len(packed)
        report.append(f'{name} {len(fields)} fields, {len(raw)} bytes, {len(packed)} packed')
    data = b''.join(w.to_bytes(2, 'little') for w in descs) + b''.join(blobs)
    open(path, 'wb').write(data)
    print(f'{os.path.basename(path)}: {len(data)} bytes: ' + '; '.join(report))
    return len(data)


def wavs(T, out):
    from ay2sn import render_sn, render_ay, write_wav
    os.makedirs(out, exist_ok=True)
    for name in Fixed + Circle:
        F = T[name]
        fields = fields_of(F)
        states = []
        for row in fields:
            st = []
            noise, natt = -1, G.Silent
            for v, lvl, noisy in row:
                att = sn_atten(lvl) if lvl else G.Silent
                if noisy:
                    st += [0, G.Silent]
                    noise, natt = 4 | v, att
                else:
                    st += [v, att]
            states.append(st + [noise, natt])
        write_wav(os.path.join(out, f'{name}_sn.wav'), render_sn(states, G.CONV))
        write_wav(os.path.join(out, f'{name}_ym.wav'), render_ay([[F[i]['regs']] for i in range(len(fields))], G.CONV, chips=[0]))
    print(f'{2 * len(Fixed + Circle)} wavs in {out}')


def main(tunes, out, wav=None):
    T = json.load(open(tunes))
    os.makedirs(out, exist_ok=True)
    n = block(T, Fixed, os.path.join(out, 'tunes_fixed.bin'))
    open(os.path.join(out, 'tunes_fixed.6502'), 'w').write(
        f'\\\\ tunes_fixed.6502 - tunes_fixed.bin\'s length, to end it at the fourth bank\'s end (tools/tune_gen.py)\n'
        f'TunesFixedLen = {n}\n')
    block(T, Circle, os.path.join(out, 'tunes_circle.bin'))
    # what tools/tune_check.mjs looks for at the chip: each field's channels as the converter has them
    json.dump({n: fields_of(T[n]) for n in Fixed + Circle}, open(os.path.join(out, 'tunes_expect.json'), 'w'))
    if wav:
        wavs(T, wav)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) not in (2, 4) or (len(a) == 4 and a[2] != '--wav'):
        print(__doc__)
        sys.exit(2)
    main(a[0], a[1], a[3] if len(a) == 4 else None)
