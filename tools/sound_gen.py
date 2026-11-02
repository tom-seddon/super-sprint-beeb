"""The race's sound effects for the BBC (Phase 4, step 10, D11): each cut from the ST's own sound, captured in Hatari
(tools/st_trace_sound.py), and converted field by field to the SN76489.

Usage: sound_gen.py OUTDIR [--wav]

Writes OUTDIR/sound.6502: each effect's fields, 3 bytes each: the tone period's low 8 bits; its high 2 bits |
the tone's attenuation << 2 | 1 << 6 if the noise sounds; the noise's rate | its attenuation << 4. And each
effect's length, its loop (the helicopter's), and its priority (the instrument's, while it plays: the ST's
starters test it). With --wav, OUTDIR/wav/<effect>_ym.wav and _sn.wav: the YM's fields and the SN's, to
listen to side by side.

The effects: start (the race's start, on each channel), bounce (a wall), bump (a car, a jump's landing),
slow (water, the yellow patch, a cone), skid (oil), wrench, bonus, tornado, wreck (the crash, then the
helicopter until it's gone: its fields' envelope a loop). Each is one instance from a captured race: the
first that started (its channel's priority under the starter's threshold), from its start to the field its
channel's priority falls back to 0 (the sequence's instrument 0), or for the start and the crash (priority
0 throughout) to where their sequence ends (by its waits, at the driver's 83.25 Hz). The fields are the
YM's state at each VBL; its 749 Hz pitch steps and 83 Hz volume steps fall between them, so each instance
differs a little from another (where the timer stood): one stands for all.

The conversion (ay2sn.py's rules, the kit's): the YM at 2 MHz and the SN at 4 MHz share a period (f =
125,000 / period); over the SN's 1023, an octave up at a time. A volume through ay2sn's table; in envelope
mode (bit 4), the hardware envelope stepped: its 32 levels of the YM2149 over 256 * period / 2 MHz, from the
last R13 write, at the field's time. The noise: the nearest of the SN's three white rates by frequency, its
attenuation the channel's. A channel with tone and noise on is the noise alone (as the kit's 1942 settled
by ear, tn_noise): the SN can't gate one by the other.
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ay2sn import sn_atten, Converter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
Captures = ['build/trace/sound_t0_r0.json', 'build/trace/sound_t6_r17.json', 'build/trace/sound_t0_r0_oil.json']
Threshold = {'bounce': 1, 'bump': 2, 'slow': 1, 'skid': 1, 'wrench': 4, 'bonus': 4, 'tornado': 3}
VblCycles = 160256                      # the ST's PAL frame, 8 MHz cycles
YmClock = 2_000_000
SnMax = 1023
Silent = 15
CONV = Converter(ay_clock=YmClock, irqs_per_field=1)
# the start's and the crash's sequences' lengths, in the driver's ticks (logic_snd.py: &F2 "ins25 wait80",
# &00 "ins20 wait35"): a wait N is N + 1 ticks
Ticks = {'start': 81, 'crash': 36}
TickHz = 749.3 / 9


def env_level(f, fi):
    """The envelope's level (0-31) at field fi, for shapes 8-15 (continuing) and 0-7."""
    r = f[fi]['regs']
    period = max(1, r[11] | r[12] << 8)
    shape = r[13] & 15
    env = f[fi]['env']
    if env is None:
        return 0
    k, cyc = env                        # written in the frame before field k's sample, at video cycle cyc
    t = ((fi - k) * VblCycles + (VblCycles - cyc)) / 8e6
    steps = t * YmClock / (8.0 * period)    # 32 steps a cycle of 256 * period
    n, step = int(steps // 32), int(steps % 32)
    up = bool(shape & 4)
    if shape < 8:                       # one ramp, then 0
        return (step if up else 31 - step) if n == 0 else 0
    hold, alt = shape & 1, shape & 2
    if hold:
        if n == 0:
            return step if up else 31 - step
        return (0 if up else 31) if alt else (31 if up else 0)
    if alt and n & 1:
        up = not up
    return step if up else 31 - step


def ym_field(f, fi, c):
    """Channel c at field fi as the YM plays it, its envelope stepped: (period, 4-bit volume, tone on,
    noise on, noise period)."""
    r = f[fi]['regs']
    v = r[8 + c]
    vol = env_level(f, fi) >> 1 if v & 16 else v & 15
    return (max(1, r[2 * c] | (r[2 * c + 1] & 15) << 8), vol, not (r[7] >> c) & 1, not (r[7] >> (3 + c)) & 1, r[6] & 31)


def channel_field(f, fi, c):
    """Channel c at field fi as the SN plays it: (period, attenuation, noise rate or None, noise attenuation)."""
    r = f[fi]['regs']
    v = r[8 + c]
    if v & 16:
        lvl = env_level(f, fi)
        att = 15 - ((min(lvl + 1, 31) >> 1) & 15)
    else:
        att = sn_atten(v & 15) if v & 15 else Silent
    tone_on = not (r[7] >> c) & 1
    noise_on = not (r[7] >> (3 + c)) & 1
    p = max(1, r[2 * c] | (r[2 * c + 1] & 15) << 8)
    n = CONV.sn_period(p)
    while n > SnMax:
        n >>= 1
    if noise_on and att < Silent:
        return (n, Silent, CONV.noise_rate(r[6]), att)
    return (n, att if tone_on else Silent, None, Silent)


def effects():
    """-> {name: (fields, loop start or None, priority, the YM's fields)}."""
    caps = [json.load(open(os.path.join(ROOT, p))) for p in Captures]
    out = {}
    for d in caps:
        F, S = d['frames'], d['starts']
        busy = {}                       # the fields each channel's effect holds, to keep instances clean
        for s in S:
            name, c, i = s['name'], s['channel'] % 3, s['index']
            if name in out or name == 'heli_gone':
                continue
            if name in Threshold and s['prio'][c] >= Threshold[name]:
                continue
            if name == 'wreck':
                # the crash, then the helicopter (priority 7) until it's gone: its steady fields, a loop
                n = int(math.ceil(Ticks['crash'] * 50 / TickHz))
                heli = next(j for j in range(i, len(F)) if F[j]['prio'][c] == 7)
                period = 256 * 700 / YmClock * 50   # the envelope's cycle in fields (period 700)
                cycles = 25                         # 25 cycles: 112.0 fields, within 0.01
                js = list(range(i, heli)) + list(range(heli, heli + round(cycles * period)))
                out['wreck'] = ([channel_field(F, j, c) for j in js], heli - i, 7, [ym_field(F, j, c) for j in js])
                continue
            if name not in Threshold:
                continue
            prio = next((F[j]['prio'][c] for j in range(i, min(i + 8, len(F))) if F[j]['prio'][c]), 0)
            end = next((j for j in range(i + 1, len(F)) if F[j]['prio'][c] == 0
                        and any(F[k]['prio'][c] for k in range(i, j))), None)
            others = [t for t in S if t is not s and t['channel'] % 3 == c and i <= t['index'] < (end or i)]
            if end is None or others:
                continue
            out[name] = ([channel_field(F, j, c) for j in range(i, end)], None, prio,
                         [ym_field(F, j, c) for j in range(i, end)])
    # the start: the race's first pause, on each channel, for its sequence's length from its first sound
    d = caps[0]
    F = d['frames']
    first = next(j for j in range(len(F)) if any(F[j]['regs'][8 + c] & 15 for c in range(3)))
    n = int(math.ceil(Ticks['start'] * 50 / TickHz))
    for c in range(3):
        js = range(first, first + n)
        out[f'start{c}'] = ([channel_field(F, j, c) for j in js], None, 0, [ym_field(F, j, c) for j in js])
    return out


def pack(fields):
    out = []
    for n, att, rate, natt in fields:
        out += [n & 255, (n >> 8) | att << 2 | (0x40 if rate is not None else 0), (rate or 0) | natt << 4]
    return out


Order = ['start0', 'start1', 'start2', 'bounce', 'bump', 'slow', 'skid', 'wrench', 'bonus', 'tornado', 'wreck']


def main(out, wav):
    fx = effects()
    missing = [n for n in Order if n not in fx]
    assert not missing, f'no clean instance of {missing}'
    os.makedirs(out, exist_ok=True)
    same = {n: next(m for m in Order if pack(fx[m][0]) == pack(fx[n][0])) for n in Order}   # (start0 and start1)
    lines = ['\\\\ sound.6502 - the race\'s effects, from the ST\'s sound (tools/sound_gen.py): 3 bytes a field', '']
    lines += [f'Fx{n.capitalize()} = {i}' for i, n in enumerate(Order)]
    lines += [f'FxCount = {len(Order)}', '']
    lines += ['.FxLen                                  ; each effect\'s fields',
              '    EQUB ' + ', '.join(str(len(fx[n][0])) for n in Order),
              '.FxLoop                                 ; the field its loop starts at (its length: none)',
              '    EQUB ' + ', '.join(str(fx[n][1] if fx[n][1] is not None else len(fx[n][0])) for n in Order),
              '.FxPrio                                 ; its priority while it plays',
              '    EQUB ' + ', '.join(str(fx[n][2]) for n in Order),
              '.FxLo                                   ; its fields\' address (an effect the same as an earlier one: its)',
              '    EQUB ' + ', '.join(f'LO(Fx_{same[n]})' for n in Order),
              '.FxHi',
              '    EQUB ' + ', '.join(f'HI(Fx_{same[n]})' for n in Order)]
    total = 0
    for n in Order:
        if same[n] != n:
            continue
        b = pack(fx[n][0])
        total += len(b)
        lines += [f'.Fx_{n}', '    EQUB ' + ', '.join(f'&{v:02X}' for v in b)]
    open(os.path.join(out, 'sound.6502'), 'w').write('\n'.join(lines) + '\n')
    print(f'{len(Order)} effects, {total} bytes: ' + ', '.join(f'{n} {len(fx[n][0])}' for n in Order))
    if wav:
        render(fx, os.path.join(out, 'wav'))


def render(fx, out):
    """Each effect as the SN plays its fields, and as the YM plays the same fields (its envelope stepped,
    both at 50 Hz: the ST's own steps between fields aren't in either), for the ear."""
    from ay2sn import render_sn, render_ay, write_wav
    os.makedirs(out, exist_ok=True)
    for n, (fields, loop, prio, ym) in fx.items():
        states = [[f[0], f[1], 0, Silent, 0, Silent, -1 if f[2] is None else 4 | f[2], f[3]] for f in fields]
        write_wav(os.path.join(out, f'{n}_sn.wav'), render_sn(states, CONV))
        rows = []
        for p, vol, tone, noise, nper in ym:     # channel A of one chip
            g = [0] * 16
            g[0], g[1], g[8], g[6] = p & 255, p >> 8, vol, nper
            g[7] = 0x3F & ~((0 if not tone else 1) | (0 if not noise else 8))
            rows.append([g])
        write_wav(os.path.join(out, f'{n}_ym.wav'), render_ay(rows, CONV, chips=[0]))


if __name__ == '__main__':
    main(sys.argv[1], '--wav' in sys.argv[2:])
