#!/bin/sh
# Every track's play build assembled (docs/brief-room-2026-11-02.md §1's method), each region's free bytes printed:
# race 17's objects (the tornado, cones, barriers and every gate frame: each track's at their most) and the
# logic's data from a copy of track 1's logic trace with its track number changed (the play build carries no
# traced inputs, so the copy only picks the track's mask B, map, path, probes and hazards). Track 1's play
# build is made again at the end, as the suite leaves it. Each track's disc and listing are kept in build/tracks/
# for tools/track_slots.py (Phase 5's fixed layout), which it runs. Exit status 1 if any track doesn't assemble,
# or if any byte outside the slots differs between tracks.
#
# Usage (from the repo root): tools/all_tracks.sh [ta]   (ta: the time attack variant's builds, TRACE=ta, kept in
# build/tracks_ta, its logs build/all_tracks_ta_tN.log; track 1's TRACE=ta build made again at the end, its
# build/gen kept as build/tracks_ta/gen)

case "$1" in
    '') variant=play; dir=build/tracks; log=build/all_tracks_t ;;
    ta) variant=ta; dir=build/tracks_ta; log=build/all_tracks_ta_t ;;
    *) echo "usage: tools/all_tracks.sh [ta]"; exit 1 ;;
esac

fail=0
for n in 0 1 2 3 4 5 6 7; do
    trace=build/trace/logic_t${n}_room.json
    # (the copy, 50MB and 6 seconds, kept until the trace it's from is made again)
    [ "$trace" -nt build/trace/logic_t0_r0.json ] || .venv/bin/python -c "
import json, os
t = json.load(open('build/trace/logic_t0_r0.json'))
t['track'], t['race'] = $n, 17
json.dump(t, open('$trace.tmp', 'w'))
os.replace('$trace.tmp', '$trace')"
    if make beeb TRACE=$variant TRACK=$n TRACEFILE=build/trace/race_t${n}_r17.json LOGICTRACE=$trace > $log$n.log 2>&1
    then
        mkdir -p $dir
        cp build/sprint.ssd $dir/t$n.ssd; cp build/sprint.lst $dir/t$n.lst; cp build/sprint.json $dir/t$n.json
        echo "track $((n + 1)) (index $n): $(grep -h 'bytes free' build/sprint.lst | grep -v PADTO | sed 's/ bytes free.*//; s/^the //' | tr '\n' ';' | sed 's/;$//; s/;/; /g')"
    else
        echo "track $((n + 1)) (index $n): FAILS ($(grep -a -m1 'error' $log$n.log))"
        fail=1
    fi
done
.venv/bin/python tools/track_slots.py $dir > $dir/slots.txt || fail=1    # (outside the slots,
tail -1 $dir/slots.txt                                                      # every track the same)
make beeb TRACE=$variant > /dev/null 2>&1 || fail=1
# time attack's checks read its front end's tables and pictures (tools/ta_checks.sh): kept with its builds, as
# build/gen is the next build's
[ $variant = ta ] && { rm -rf $dir/gen; cp -R build/gen $dir/gen || fail=1; }
exit $fail
