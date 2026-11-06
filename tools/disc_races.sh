#!/bin/sh
# The race count's hazards on every track, through the game's disc (Phase 5, step 4): each traced race's model
# made if it's out of date (tools/render_model.py: about a minute each, MODELS at a time, default 3), then
# tools/disc_races.mjs eleven times, each going round the eight tracks in the ST's order with the races in turn, so
# every track has every race and each kind of race follows others; their lines in OUT/races_J.log. The races: 1 no
# hazards, 2 the barriers, 4 the tornado (forced), 17 both and cones (forced), 50 the counter's end, all of them
# (`make hazardtrace` records them); and tools/human_traces.sh's, with two or three humans; and the demo. Then the
# race with cars put where one pixel of the wall probes decides (hprobe, state only), and the faults it's there
# for put back (--probes). Then the disc's other checks, which read only it and what it was made from:
# tools/game_check.mjs, tools/attract_check.mjs, tools/flash_check.mjs, tools/options_check.mjs, tools/select_check.mjs, tools/upgrades_check.mjs, tools/circle_check.mjs and tools/load_check.mjs (last, as a race's job soon leaves a machine
# free). Exit status 1 if any is wrong, or if any job left no status.
#
# The jobs run on REMOTE, by default agentbox (tools/remote.sh copies what they read there, and their logs back);
# `REMOTE= tools/disc_races.sh OUT` runs them on this machine. Either way MACHINES run at once (default 14 there,
# 4 here). The models are made here.
#
# Usage (from the repo root, after make game): tools/disc_races.sh OUT   (OUT outside the repository; ROTATIONS="0"
# in the environment runs only those of the eleven)

RACES="r1 r2 r4 r17 r50 h012 h12 h01 h02"     # (and demo0 demo17: state only, so no models)
ROTATIONS=${ROTATIONS:-0 1 2 3 4 5 6 7 8 9 10}
CHECKS="game_check attract_check flash_check options_check select_check upgrades_check circle_check load_check"

if [ "$1" = jobs ]; then                # (the jobs alone, where they run: tools/disc_races.sh jobs OUT)
    export OUT=$2                       # (not in the command: BSD xargs -I cuts an argument at 255 bytes)
    mkdir -p "$OUT"
    rm -f "$OUT"/*.log "$OUT"/*.status
    { for j in $ROTATIONS; do echo races_$j disc_races --rotate $j; done
      echo probe disc_races --races hprobe --tracks 0
      echo silence disc_races --races h012 --tracks 0 --noscreen --silence     # (a race the fault showed in)
      echo probes disc_races --probes
      for c in $CHECKS; do echo $c $c; done
    } | xargs -P ${MACHINES:-4} -L 1 sh -c 'n=$0; t=$1; shift; node tools/$t.mjs "$@" > "$OUT/$n.log" 2>&1; echo $? > "$OUT/$n.status"'
    exit 0
fi

OUT=${1:?usage: tools/disc_races.sh OUT}
REMOTE=${REMOTE-agentbox}
mkdir -p "$OUT"
for r in $RACES; do for n in 0 1 2 3 4 5 6 7; do
    m=build/check/model_t${n}_$r.bin
    if [ ! -f $m ] || [ build/trace/race_t${n}_$r.json -nt $m ] || [ tools/render_model.py -nt $m ]; then echo "$n $r"; fi
done; done | xargs -P ${MODELS:-3} -L 1 sh -c '.venv/bin/python -P tools/render_model.py $0 build/trace/race_t$0_$1.json build/check/model_t$0_$1.bin --cue build/trace/logic_t$0_$1.json > /dev/null' || exit 1
if [ -n "$REMOTE" ]; then
    export REMOTE ROTATIONS
    tools/remote.sh "$OUT" || exit 1
else
    tools/disc_races.sh jobs "$OUT"
fi
fail=0
status() { [ "$(cat "$OUT/$1.status" 2>/dev/null)" = 0 ] || { echo "$1: failed (status $(cat "$OUT/$1.status" 2>/dev/null))"; fail=1; }; }
for j in $ROTATIONS; do
    grep -a '^track .*loaded\|^all \| races wrong' "$OUT/races_$j.log"
    status races_$j
done
grep -a '^track .*loaded' "$OUT/probe.log"; status probe
grep -a 'after the end' "$OUT/silence.log"; status silence
grep -a '^control\|^car \|^all \| entries not' "$OUT/probes.log"; status probes
for c in $CHECKS; do
    echo "$c: $(grep -av '^\[jsbeeb\|^Loading' "$OUT/$c.log" | tail -1)"
    status $c
done
exit $fail
