#!/bin/sh
# Every oracle the game has, one after another (the builds share build/sprint.*, so not in parallel), each
# one's output in OUT/<name>.log and its exit status in OUT/verdicts.txt. Exit status 1 if any failed.
#
# The races on the disc and the disc's other checks (tools/disc_races.sh: their logs in OUT/disc_races), nine-tenths
# of the work, start as soon as the disc's made, in the background, in their own copy of what they read (or with
# REMOTE=host on that machine: tools/remote.sh); the builds and checks after the disc's run here meanwhile, then time
# attack's build, its discs (build/ta.ssd, build/ta.adl) and its checks (tools/ta_checks.sh: their logs in OUT/ta),
# beside the disc's still running. Each step's start and end in OUT/times.txt. tools/suite_remote.sh runs the whole
# suite on another machine.
#
# Usage (from the repo root): tools/suite.sh OUT [quick]   (OUT outside the repository: the scratchpad or a temp dir)
# quick: the races on the disc only one way round, 8 of 88. For changes to the front end's pictures alone, when the
# races are on this machine: about 10 minutes. Anything touching the race, the boot or the loads wants the whole suite.

OUT=${1:?usage: tools/suite.sh OUT [quick]}
[ "$2" = quick ] && export ROTATIONS=0
export REMOTE=${REMOTE-}
mkdir -p "$OUT"
: > "$OUT/verdicts.txt"
began=$(date +%s)
echo "began $began" > "$OUT/times.txt"          # (each step's start and end, seconds since 1970, for the wall time)
run() {
    name=$1; shift
    start=$(date +%s)
    "$@" > "$OUT/$name.log" 2>&1
    status=$?
    echo "$name $status $(( $(date +%s) - start ))s" >> "$OUT/verdicts.txt"
    echo "$name $start $(date +%s)" >> "$OUT/times.txt"
}

run prepare make venv baron build/zx02 build/trace/logic_t0_r0.json
run all_tracks tools/all_tracks.sh
run readmes .venv/bin/python -P tools/disc_readme.py --check
run game_disc sh -c 'make build/zx02 && .venv/bin/python tools/make_game.py build/tracks build/zx02 build/game.ssd game && .venv/bin/python -P tools/adfs_disc.py build/game.ssd build/game.adl'
# the disc's jobs in the background, in their own copy of what they read (taken now, before the builds below
# rewrite build/gen), or with REMOTE=host on that machine
[ -n "$REMOTE" ] || run disc_copy tools/disc_races.sh copy "$OUT/disc_races"
run disc_races env DISC_COPIED=1 tools/disc_races.sh "$OUT/disc_races" &
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
# time attack (docs/brief-timeattack-2026-11-10.md): its tracks' builds and discs (make ta), then its checks
# (tools/ta_checks.sh, MACHINES at a time), here, beside the disc's: the builds share build/sprint.* and build/gen,
# which the disc's jobs don't read where they run
run ta_tracks tools/all_tracks.sh ta
run ta_disc sh -c '.venv/bin/python tools/make_game.py build/tracks_ta build/zx02 build/ta.ssd ta && .venv/bin/python -P tools/adfs_disc.py build/ta.ssd build/ta.adl'
run modelb_check node tools/modelb_check.mjs   # (both discs refused on a Model B, !BOOT above its PAGE)
run ta_checks tools/ta_checks.sh "$OUT/ta"
wait
for c in boot_check break_check crash_check game_check attract_check flash_check options_check select_check upgrades_check circle_check initials_check tune_check tune_off save_check load_check game_adfs load_adfs boot_adfs; do            # (each on its own line, as the disc's jobs left it)
    status=$(cat "$OUT/disc_races/$c.status" 2>/dev/null)
    echo "$c ${status:-missing}" >> "$OUT/verdicts.txt"
done
for c in ghost menu rows table save scores picture options boot boot_adfs ghost_adfs merge merge_adfs; do
    status=$(cat "$OUT/ta/$c.status" 2>/dev/null)
    echo "ta_$c ${status:-missing}" >> "$OUT/verdicts.txt"
done
fail=$(awk '$2 != 0 { bad = 1 } END { print bad + 0 }' "$OUT/verdicts.txt")
echo "done $fail" >> "$OUT/verdicts.txt"
echo "done $(date +%s) $(( $(date +%s) - began ))s" >> "$OUT/times.txt"
exit $fail
