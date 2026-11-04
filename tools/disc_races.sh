#!/bin/sh
# The race count's hazards on every track, through the game's disc (Phase 5, step 4): each traced race's model
# made if it's out of date (tools/render_model.py: about a minute each, MODELS at a time, default 3), then
# tools/disc_races.mjs nine times, MACHINES at once (default 4), each going round the eight tracks in the ST's
# order with the races in turn, so every track has every race and each kind of race follows others; their lines
# in OUT/races_J.log. The races: 1 no hazards, 2 the barriers, 4 the tornado (forced), 17 both and cones
# (forced), 50 the counter's end, all of them (`make hazardtrace` records them); and tools/human_traces.sh's, with
# two or three humans. Then the race with cars put where one pixel of the wall probes decides (hprobe, state only), and
# the faults it's there for put back (--probes). Exit status 1 if any is wrong.
#
# Usage (from the repo root, after make game): tools/disc_races.sh OUT   (OUT outside the repository)

OUT=${1:?usage: tools/disc_races.sh OUT}
RACES="r1 r2 r4 r17 r50 h012 h12 h01 h02"
mkdir -p "$OUT"
for r in $RACES; do for n in 0 1 2 3 4 5 6 7; do
    m=build/check/model_t${n}_$r.bin
    if [ ! -f $m ] || [ build/trace/race_t${n}_$r.json -nt $m ] || [ tools/render_model.py -nt $m ]; then echo "$n $r"; fi
done; done | xargs -P ${MODELS:-3} -L 1 sh -c '.venv/bin/python -P tools/render_model.py $0 build/trace/race_t$0_$1.json build/check/model_t$0_$1.bin --cue build/trace/logic_t$0_$1.json > /dev/null' || exit 1
fail=0
export OUT                              # (not in the command: BSD xargs -I cuts an argument at 255 bytes)
for j in 0 1 2 3 4 5 6 7 8; do echo $j; done | xargs -P ${MACHINES:-4} -L 1 sh -c 'node tools/disc_races.mjs --rotate $0 > "$OUT/races_$0.log" 2>&1; echo $? > "$OUT/races_$0.status"'
for j in 0 1 2 3 4 5 6 7 8; do
    grep -a '^track .*loaded\|^all \| races wrong' "$OUT/races_$j.log"
    [ "$(cat "$OUT/races_$j.status")" = 0 ] || fail=1
done
node tools/disc_races.mjs --races hprobe --tracks 0 > "$OUT/probe.log" 2>&1 || fail=1
grep -a '^track .*loaded' "$OUT/probe.log"
node tools/disc_races.mjs --probes > "$OUT/probes.log" 2>&1 || fail=1
grep -a '^control\|^car \|^all \| entries not' "$OUT/probes.log"
exit $fail
