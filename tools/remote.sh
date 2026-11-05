#!/bin/sh
# tools/disc_races.sh's jobs on the machine REMOTE: what they read copied there (rsync, so after the first time only
# what has changed: a new game.ssd and the tools, about 1MB; the traces and models are 10GB), the jobs run in
# REMOTE_DIR, and their logs and statuses back in OUT. Needs only Node and jsbeeb there: `npx -y jsbeeb-mcp@VERSION
# < /dev/null` once, and Node on the PATH of `ssh REMOTE CMD`. Exit status 1 if the copying or the ssh fail; whether
# a job passed is in its status file, which tools/disc_races.sh reads.
#
# Usage (from the repo root): REMOTE=host tools/remote.sh OUT   (ROTATIONS and MACHINES as tools/disc_races.sh)

OUT=${1:?usage: REMOTE=host tools/remote.sh OUT}
REMOTE=${REMOTE:?no REMOTE}
DIR=${REMOTE_DIR:-super-sprint-beeb}    # (relative to the home folder there)
list=$(mktemp) || exit 1
trap 'rm -f "$list"' EXIT
{
    echo .mcp.json
    for f in disc_races.sh disc_races.mjs game_check.mjs attract_check.mjs load_check.mjs jsbeeb.mjs logic_compare.mjs; do
        echo tools/$f
    done
    echo build/game.ssd; echo build/game_slots.json; for f in title credits scores; do echo build/gen/$f.bin; done
    ls build/tracks/t?.json build/trace/logic_t?_r1.json build/trace/logic_t?_r2.json build/trace/logic_t?_r4.json \
       build/trace/logic_t?_r17.json build/trace/logic_t?_r50.json build/trace/logic_t?_h*.json build/trace/logic_t?_demo*.json \
       build/trace/game_*.json \
       build/check/model_t?_r1.bin build/check/model_t?_r2.bin build/check/model_t?_r4.bin build/check/model_t?_r17.bin \
       build/check/model_t?_r50.bin build/check/model_t?_h*.bin
} > "$list"
ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE" "mkdir -p $DIR" || { echo "can't reach $REMOTE: REMOTE= runs the jobs here"; exit 1; }
rsync -az --files-from="$list" . "$REMOTE:$DIR/" || exit 1
# (the jobs' own exit is always 0; a dropped connection shows as an ssh failure, or a job with no status)
ssh -o ServerAliveInterval=30 "$REMOTE" "cd $DIR && ROTATIONS='$ROTATIONS' MACHINES=${MACHINES:-14} sh tools/disc_races.sh jobs out" || exit 1
rsync -a "$REMOTE:$DIR/out/" "$OUT/" || exit 1
