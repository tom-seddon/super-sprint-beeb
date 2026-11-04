#!/bin/sh
# Races with more than one human on the ST (brief-phase5 step 4's follow-on): for each track, four races driven
# by tools/steer_script.py, each with its own mix of hazards: all three cars, race 17 (the tornado and cones forced);
# cars 1 and 2, race 2 (the barriers; car 0 a drone); cars 0 and 1, race 4 (the tornado, forced); cars 0 and 2,
# race 1. Each race's logic and draw calls, as build/trace/logic_tN_hCARS.json and race_tN_hCARS.json, JOBS at a
# time (default 3); a race already traced is kept. About 2 hours at 3. Then logic_t0_hprobe.json: track 1, race 1,
# tools/logic_scripts/probe_t0.json's cars put where one pixel of the wall probes decides (the spots: every place
# on the track where a car's human and drone-driven shapes at facing 6 hit differently). Exit status 1 if any failed.
#
# Usage (from the repo root): tools/human_traces.sh [TRACKS]

TRACKS=${1:-0 1 2 3 4 5 6 7}
if [ "$1" = one ]; then
    n=$2; cars=$3; race=$4; force=$5
    logic=build/trace/logic_t${n}_h$cars.json obj=build/trace/obj_t${n}_h$cars.json out=build/trace/race_t${n}_h$cars.json
    [ -f $logic ] && [ -f $out ] && exit 0
    dir=build/trace/h_${n}_$cars
    mkdir -p $dir
    .venv/bin/python -P tools/steer_script.py $cars $n $dir/script.json > /dev/null || exit 1
    VBLS=14000 TRACEDIR=$PWD/$dir .venv/bin/python -P tools/st_trace_logic.py $n $race $dir/script.json $logic $force > $dir/logic.out 2>&1 || { cat $dir/logic.out; exit 1; }
    VBLS=14000 TRACEDIR=$PWD/$dir .venv/bin/python -P tools/st_trace_objects.py $n $race $obj ${force:--} $dir/script.json > $dir/obj.out 2>&1 || { cat $dir/obj.out; exit 1; }
    .venv/bin/python -P tools/st_race.py $obj $out > $dir/race.out || exit 1
    echo "track $((n + 1)) cars $cars: $(tail -1 $dir/logic.out | cut -d';' -f1), $(cat $dir/race.out)"
    rm -rf $dir
    exit 0
fi
for n in $TRACKS; do
    echo "$n 012 17 tornado,cones"; echo "$n 12 2"; echo "$n 01 4 tornado"; echo "$n 02 1"
done | xargs -P ${JOBS:-3} -L 1 tools/human_traces.sh one || exit 1
out=build/trace/logic_t0_hprobe.json
[ -f $out ] && exit 0
mkdir -p build/trace/h_probe
VBLS=7000 TRACEDIR=$PWD/build/trace/h_probe .venv/bin/python -P tools/st_trace_logic.py 0 1 tools/logic_scripts/probe_t0.json $out > /dev/null || exit 1
rm -rf build/trace/h_probe
