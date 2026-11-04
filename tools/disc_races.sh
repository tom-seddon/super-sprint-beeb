#!/bin/sh
# The race count's hazards on every track, through the game's disc (Phase 5, step 4): each traced race's model
# made if it's out of date (tools/render_model.py: about a minute each, MODELS at a time, default 3), then
# tools/disc_races.mjs five times, on as many machines at once, each going round the eight tracks in the ST's
# order with the races in turn, so every track has every race and each kind of race follows others; their lines
# in OUT/races_J.log. The races: 1 no hazards, 2 the barriers, 4 the tornado (forced), 17 both and cones
# (forced), 50 the counter's end, all of them (`make hazardtrace` records them). Exit status 1 if any is wrong.
#
# Usage (from the repo root, after make game): tools/disc_races.sh OUT   (OUT outside the repository)

OUT=${1:?usage: tools/disc_races.sh OUT}
RACES="1 2 4 17 50"
mkdir -p "$OUT"
for r in $RACES; do for n in 0 1 2 3 4 5 6 7; do
    m=build/check/model_t${n}_r$r.bin
    if [ ! -f $m ] || [ build/trace/race_t${n}_r$r.json -nt $m ] || [ tools/render_model.py -nt $m ]; then echo "$n $r"; fi
done; done | xargs -P ${MODELS:-3} -L 1 sh -c '.venv/bin/python -P tools/render_model.py $0 build/trace/race_t$0_r$1.json build/check/model_t$0_r$1.bin --cue build/trace/logic_t$0_r$1.json > /dev/null' || exit 1
fail=0
for j in 0 1 2 3 4; do
    ( node tools/disc_races.mjs --rotate $j > "$OUT/races_$j.log" 2>&1; echo $? > "$OUT/races_$j.status" ) &
done
wait
for j in 0 1 2 3 4; do
    grep -a '^track .*loaded\|^all \| races wrong' "$OUT/races_$j.log"
    [ "$(cat "$OUT/races_$j.status")" = 0 ] || fail=1
done
exit $fail
