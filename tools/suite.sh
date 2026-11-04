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
run walls_check node tools/walls_check.mjs
run arith_check node tools/arith_check.mjs
run sound_check node tools/sound_check.mjs
run logic4_build make logic LOGICTRACE=build/trace/logic_t4_r17.json
run logic4_check node tools/logic_check.mjs --trace build/trace/logic_t4_r17.json
run logic4_maskb node tools/maskb_check.mjs 4
run logic4_walls node tools/walls_check.mjs 4
run logic4_draws node tools/logic_draws.mjs --race build/trace/race_t4_r17.json
run render_logic4 make check TRACE=logic4
run render_race make check
run render_logic0 make check TRACE=logic0
run sn_check node tools/sn_check.mjs
run play_build make beeb TRACE=play
run keys_check node tools/keys_check.mjs
run all_tracks tools/all_tracks.sh
run game_disc sh -c 'make build/zx02 && .venv/bin/python tools/make_game.py build/tracks build/zx02 build/game.ssd'
run load_check node tools/load_check.mjs
run game_check node tools/game_check.mjs
run disc_races tools/disc_races.sh "$OUT/disc_races"
echo "done $fail" >> "$OUT/verdicts.txt"
exit $fail
