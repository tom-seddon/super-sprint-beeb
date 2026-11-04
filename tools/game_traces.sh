#!/bin/sh
# Phase 5 step 5's traces: the whole games (tools/game_scripts.py, tools/st_trace_game.py) as build/trace/game_NAME.json,
# and the demo race on every track at the race counters 0 (as a fresh boot) and 17 (the hazards: the counter a
# game leaves behind) as build/trace/logic_tN_demoR.json, JOBS at a time (default 3); a trace already made is kept.
# Exit status 1 if any failed.
#
# Usage (from the repo root): tools/game_traces.sh

if [ "$1" = game ]; then
    out=build/trace/game_$2.json dir=build/trace/g_$2
    [ -f $out ] && exit 0
    mkdir -p $dir
    TRACEDIR=$PWD/$dir .venv/bin/python -P tools/st_trace_game.py tools/game_scripts/$2.json $out > $dir/out 2>&1 || { cat $dir/out; exit 1; }
    echo "game $2: $(tail -1 $dir/out)"
    rm -rf $dir
    exit 0
elif [ "$1" = demo ]; then
    out=build/trace/logic_t$2_demo$3.json dir=build/trace/d_$2_$3
    [ -f $out ] && exit 0
    mkdir -p $dir
    DEMO=1 VBLS=9000 TRACEDIR=$PWD/$dir .venv/bin/python -P tools/st_trace_logic.py $2 $3 - $out > $dir/out 2>&1 || { cat $dir/out; exit 1; }
    echo "demo track $(($2 + 1)) race $3: $(tail -1 $dir/out | cut -d';' -f1)"
    rm -rf $dir
    exit 0
fi
.venv/bin/python -P tools/game_scripts.py || exit 1
{
    for g in three alone rejoin; do echo game $g; done
    for n in 0 1 2 3 4 5 6 7; do echo demo $n 0; echo demo $n 17; done
} | xargs -P ${JOBS:-3} -L 1 tools/game_traces.sh
