#!/bin/sh
# The race count's hazards on every track, through the game's disc (Phase 5, step 4): each traced race's model
# made if it's out of date (tools/render_model.py: about a minute each, MODELS at a time, default 3), then
# tools/disc_races.mjs eleven times, each going round the eight tracks in the ST's order with the races in turn, so
# every track has every race and each kind of race follows others; their lines in OUT/races_J.log. The races: 1 no
# hazards, 2 the barriers, 4 the tornado (forced), 17 both and cones (forced), 50 the counter's end, all of them
# (`make hazardtrace` records them); and tools/human_traces.sh's, with two or three humans; and the demo. Then the
# race with cars put where one pixel of the wall probes decides (hprobe, state only), and the faults it's there
# for put back (--probes). Then the disc's other checks, which read only it and what it was made from:
# tools/break_check.mjs, tools/crash_check.mjs, tools/game_check.mjs, tools/attract_check.mjs, tools/flash_check.mjs, tools/options_check.mjs, tools/select_check.mjs, tools/upgrades_check.mjs, tools/circle_check.mjs, tools/initials_check.mjs, tools/tune_check.mjs (and again with --off: tune_off), tools/save_check.mjs, game_check and load_check again on build/game.adl (--adfs: game_adfs, load_adfs) and tools/load_check.mjs (last, as a race's job soon leaves a machine
# free). Exit status 1 if any is wrong, or if any job left no status. Each job's start and end (seconds since 1970)
# in OUT/<job>.time, for the suite's wall time.
#
# The jobs run on this machine, in a copy of what they read (OUT/tree, removed after), or with REMOTE=host on that
# one (tools/remote.sh copies what they read there, and their logs back): either way the builds can go on meanwhile.
# MACHINES run at once (default 4 here, 14 there). The models are made here.
#
# Usage (from the repo root, after make game): tools/disc_races.sh OUT   (OUT outside the repository; ROTATIONS="0"
# in the environment runs only those of the eleven). tools/disc_races.sh copy OUT first copies what the jobs read but
# the traces and models, so the builds can go on before this starts.

RACES="r1 r2 r4 r17 r50 h012 h12 h01 h02"     # (and demo0 demo17: state only, so no models)
ROTATIONS=${ROTATIONS:-0 1 2 3 4 5 6 7 8 9 10}
CHECKS="boot_check break_check crash_check game_check attract_check flash_check options_check select_check upgrades_check circle_check initials_check tune_check save_check load_check"

# What the jobs read (tools/disc_files.sh), in OUT/tree, where they run here: copy OUT copies the rest (build/gen's
# tables, the discs, the tools), as the builds after the disc's rewrite build/gen (tools/suite.sh runs it before them);
# copy OUT links hard-links the traces and models (or symlinks them, on another volume), once the models are made.
copy() {
    tools/disc_files.sh | while read -r f; do
        case $f in build/trace/*|build/check/*) [ "$2" = links ] || continue ;; *) [ "$2" = links ] && continue ;; esac
        case $f in */*) mkdir -p "$1/tree/${f%/*}" || exit 1 ;; *) mkdir -p "$1/tree" || exit 1 ;; esac
        if [ "$2" = links ]; then ln -f "$f" "$1/tree/$f" 2>/dev/null || ln -sf "$PWD/$f" "$1/tree/$f" || exit 1
        else cp -p "$f" "$1/tree/$f" || exit 1
        fi
    done
}
if [ "$1" = copy ]; then                # (tools/disc_races.sh copy OUT: the rest copied, before the builds go on)
    rm -rf "$2/tree"
    copy "$2" rest
    exit
fi

if [ "$1" = jobs ]; then                # (the jobs alone, where they run: tools/disc_races.sh jobs OUT)
    export OUT=$2                       # (not in the command: BSD xargs -I cuts an argument at 255 bytes)
    mkdir -p "$OUT"
    rm -f "$OUT"/*.log "$OUT"/*.status "$OUT"/*.time
    { for j in $ROTATIONS; do echo races_$j disc_races --rotate $j; done
      echo probe disc_races --races hprobe --tracks 0
      echo silence disc_races --races h012 --tracks 0 --noscreen --silence     # (a race the fault showed in)
      echo probes disc_races --probes
      for c in $CHECKS; do echo $c $c; done
      echo tune_off tune_check --off
      echo game_adfs game_check --adfs
      echo load_adfs load_check --adfs
      echo boot_adfs boot_check --adfs
    } | xargs -P ${MACHINES:-4} -L 1 sh -c 'n=$0; t=$1; shift; s=$(date +%s); node tools/$t.mjs "$@" > "$OUT/$n.log" 2>&1; echo $? > "$OUT/$n.status"; echo "$s $(date +%s)" > "$OUT/$n.time"'
    exit 0
fi

OUT=${1:?usage: tools/disc_races.sh OUT}
REMOTE=${REMOTE-}
mkdir -p "$OUT"
[ -n "$REMOTE" ] || [ -n "$DISC_COPIED" ] || { rm -rf "$OUT/tree"; copy "$OUT" rest; } || exit 1   # (tools/suite.sh
                                        # copies first, and says so: DISC_COPIED=1)
models=$(date +%s)
for r in $RACES; do for n in 0 1 2 3 4 5 6 7; do
    m=build/check/model_t${n}_$r.bin
    if [ ! -f $m ] || [ build/trace/race_t${n}_$r.json -nt $m ] || [ tools/render_model.py -nt $m ]; then echo "$n $r"; fi
done; done | xargs -P ${MODELS:-3} -L 1 sh -c '.venv/bin/python -P tools/render_model.py $0 build/trace/race_t$0_$1.json build/check/model_t$0_$1.bin --cue build/trace/logic_t$0_$1.json > /dev/null' || exit 1
models="$models $(date +%s)"            # (written after the jobs, which clear OUT's *.time)
if [ -n "$REMOTE" ]; then
    export REMOTE ROTATIONS
    tools/remote.sh "$OUT" || exit 1
else
    # here, in OUT/tree: the traces and models (15GB, which nothing rewrites) linked in now, beside the rest
    copy "$OUT" links || exit 1
    out=$(cd "$OUT" && pwd)
    (cd "$OUT/tree" && sh tools/disc_races.sh jobs "$out")
    rm -rf "$OUT/tree"
fi
echo "$models" > "$OUT/models.time"
fail=0
status() { [ "$(cat "$OUT/$1.status" 2>/dev/null)" = 0 ] || { echo "$1: failed (status $(cat "$OUT/$1.status" 2>/dev/null))"; fail=1; }; }
for j in $ROTATIONS; do
    grep -a '^track .*loaded\|^all \| races wrong' "$OUT/races_$j.log"
    status races_$j
done
grep -a '^track .*loaded' "$OUT/probe.log"; status probe
grep -a 'after the end' "$OUT/silence.log"; status silence
grep -a '^control\|^car \|^all \| entries not' "$OUT/probes.log"; status probes
for c in $CHECKS tune_off game_adfs load_adfs boot_adfs; do
    echo "$c: $(grep -av '^\[jsbeeb\|^Loading' "$OUT/$c.log" | tail -1)"
    status $c
done
exit $fail
