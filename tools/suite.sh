#!/bin/sh
# Every oracle the game has, one after another (the builds share build/sprint.*, so not in parallel), each
# one's output in OUT/<name>.log and its exit status in OUT/verdicts.txt. Exit status 1 if any failed.
#
# Everything runs on this machine, the races on the disc and the disc's other checks last (tools/disc_races.sh:
# their logs in OUT/disc_races), nine-tenths of the work: about 38 minutes on Tom's laptop. REMOTE=host sends just
# those to another machine as soon as the disc's made (tools/remote.sh), the rest running here meanwhile: about 4.
# tools/suite_remote.sh runs the whole suite on another machine.
#
# Usage (from the repo root): tools/suite.sh OUT [quick]   (OUT outside the repository: the scratchpad or a temp dir)
# quick: the races on the disc only one way round, 8 of 88. For changes to the front end's pictures alone, when the
# races are on this machine: about 10 minutes. Anything touching the race, the boot or the loads wants the whole suite.

OUT=${1:?usage: tools/suite.sh OUT [quick]}
[ "$2" = quick ] && export ROTATIONS=0
export REMOTE=${REMOTE-}
mkdir -p "$OUT"
: > "$OUT/verdicts.txt"
run() {
    name=$1; shift
    start=$(date +%s)
    "$@" > "$OUT/$name.log" 2>&1
    status=$?
    echo "$name $status $(( $(date +%s) - start ))s" >> "$OUT/verdicts.txt"
}

run prepare make venv baron build/zx02 build/trace/logic_t0_r0.json
run all_tracks tools/all_tracks.sh
run game_disc sh -c 'make build/zx02 && .venv/bin/python tools/make_game.py build/tracks build/zx02 build/game.ssd && .venv/bin/python -P tools/adfs_disc.py build/game.ssd build/game.adl'
[ -n "$REMOTE" ] && run disc_races tools/disc_races.sh "$OUT/disc_races" &
run st_frontend .venv/bin/python -P tools/st_frontend.py
run st_screens .venv/bin/python -P tools/st_screens_check.py
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
[ -n "$REMOTE" ] || run disc_races tools/disc_races.sh "$OUT/disc_races"
wait
for c in boot_check game_check attract_check flash_check options_check select_check upgrades_check circle_check initials_check tune_check tune_off save_check load_check game_adfs load_adfs boot_adfs; do            # (each on its own line, as the disc's jobs left it)
    status=$(cat "$OUT/disc_races/$c.status" 2>/dev/null)
    echo "$c ${status:-missing}" >> "$OUT/verdicts.txt"
done
fail=$(awk '$2 != 0 { bad = 1 } END { print bad + 0 }' "$OUT/verdicts.txt")
echo "done $fail" >> "$OUT/verdicts.txt"
exit $fail
