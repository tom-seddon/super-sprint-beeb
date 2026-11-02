#!/bin/sh
# Every oracle the game has, one after another (the builds share build/sprint.*, so not in parallel), each
# one's output in OUT/<name>.log and its exit status in OUT/verdicts.txt. Exit status 1 if any failed.
#
# Usage (from the repo root): tools/suite.sh OUT   (OUT outside the repository: the scratchpad or a temp dir)

OUT=${1:?usage: tools/suite.sh OUT}
mkdir -p "$OUT"
: > "$OUT/verdicts.txt"
fail=0
run() {
    name=$1; shift
    start=$(date +%s)
    "$@" > "$OUT/$name.log" 2>&1
    status=$?
    echo "$name $status $(( $(date +%s) - start ))s" >> "$OUT/verdicts.txt"
    [ $status -eq 0 ] || fail=1
}

run logic_build make logic
run logic_check node tools/logic_check.mjs
run maskb_check node tools/maskb_check.mjs
run logic_draws node tools/logic_draws.mjs
run sound_check node tools/sound_check.mjs
run render_race make check
run render_logic0 make check TRACE=logic0
run sn_check node tools/sn_check.mjs
run play_build make beeb TRACE=play
run keys_check node tools/keys_check.mjs
echo "done $fail" >> "$OUT/verdicts.txt"
exit $fail
