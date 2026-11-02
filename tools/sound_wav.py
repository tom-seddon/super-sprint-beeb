"""The race's sound as WAVs, to listen to (Phase 4, step 10): the BBC's (its SN76489's fields, from tools/sn_check.mjs
--fields) and the ST's (its YM's fields at each VBL, from tools/st_trace_sound.py's capture, the hardware
envelope stepped as tools/sound_gen.py does). Both at 50 fields a second, so they line up but for the BBC's
start pause and dropped frames; neither has what the chips do between fields.

Usage: sound_wav.py BBC_FIELDS.json ST_CAPTURE.json OUTDIR
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ay2sn import Converter, render_sn, render_ay, write_wav
import sound_gen

conv = Converter(ay_clock=2_000_000, irqs_per_field=1)
fields, cap, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
os.makedirs(out, exist_ok=True)
states = [[f['n'][0], f['att'][0], f['n'][1], f['att'][1], f['n'][2], f['att'][2],
           -1 if f['noise'] is None else f['noise'], f['natt']] for f in fields]
write_wav(os.path.join(out, 'race_bbc.wav'), render_sn(states, conv))
F = cap['frames']
rows = []
for i, f in enumerate(F):
    g = list(f['regs'])
    for c in range(3):
        if g[8 + c] & 16:
            g[8 + c] = sound_gen.env_level(F, i) >> 1
    rows.append([g])
write_wav(os.path.join(out, 'race_st.wav'), render_ay(rows, conv, chips=[0]))
print(f'{len(fields)} BBC fields, {len(F)} ST fields: {out}/race_bbc.wav, {out}/race_st.wav')
