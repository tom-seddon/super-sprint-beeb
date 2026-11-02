#!/bin/sh
# Every track's race 17 (brief-phase4 step 13: accelerate held, the tornado and cones forced) through the BBC's
# logic and drawn from it, each check's verdict on a line: the logic against the ST's every frame
# (logic_check), mask B's bytes (maskb_check), the wall columns (walls_check), the draw calls against the ST's
# (logic_draws), and the game drawn from the logic against the model (make check TRACE=hN). Each check's
# output in OUT/<check>_tN.log. Exit status 1 if any failed.
#
# Usage (from the repo root): tools/tracks_check.sh OUT [TRACKS]   (TRACKS: indexes, default "0 1 2 3 4 5 6 7";
# OUT outside the repository)

OUT=${1:?usage: tools/tracks_check.sh OUT [TRACKS]}
TRACKS=${2:-0 1 2 3 4 5 6 7}
mkdir -p "$OUT"
fail=0
run() {
    name=$1; shift
    if "$@" > "$OUT/$name.log" 2>&1; then v=ok; else v=FAIL; fail=1; fi
    echo "$name $v: $(grep -v '^\[jsbeeb\|^Loading' "$OUT/$name.log" | tail -1)"
}
for n in $TRACKS; do
    trace=build/trace/logic_t${n}_r17.json
    run logic_build_t$n make logic LOGICTRACE=$trace
    run logic_check_t$n node tools/logic_check.mjs --trace $trace
    run maskb_check_t$n node tools/maskb_check.mjs $n
    run walls_check_t$n node tools/walls_check.mjs $n
    run logic_draws_t$n node tools/logic_draws.mjs --race build/trace/race_t${n}_r17.json
    run render_t$n make check TRACE=h$n
done
make logic > /dev/null 2>&1 || fail=1                   # (track 1's race 0 again, as the suite has it)
exit $fail
