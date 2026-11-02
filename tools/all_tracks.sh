#!/bin/sh
# Every track's play build assembled (docs/brief-room-2026-11-02.md §1's method), each region's free bytes printed:
# race 17's objects (the tornado, cones, barriers and every gate frame: each track's at their most) and the
# logic's data from a copy of track 1's logic trace with its track number changed (the play build carries no
# traced inputs, so the copy only picks the track's mask B, map, path, probes and hazards). Track 1's play
# build is made again at the end, as the suite leaves it. Exit status 1 if any track doesn't assemble.
#
# Usage (from the repo root): tools/all_tracks.sh

fail=0
for n in 0 1 2 3 4 5 6 7; do
    trace=build/trace/logic_t${n}_room.json
    .venv/bin/python -c "
import json
t = json.load(open('build/trace/logic_t0_r0.json'))
t['track'], t['race'] = $n, 17
json.dump(t, open('$trace', 'w'))"
    if make beeb TRACE=play TRACK=$n TRACEFILE=build/trace/race_t${n}_r17.json LOGICTRACE=$trace > build/all_tracks_t$n.log 2>&1
    then
        echo "track $((n + 1)) (index $n): $(grep -h 'bytes free' build/sprint.lst | grep -v PADTO | sed 's/ bytes free.*//; s/^the //' | tr '\n' ';' | sed 's/;$//; s/;/; /g')"
    else
        echo "track $((n + 1)) (index $n): FAILS ($(grep -a -m1 'error' build/all_tracks_t$n.log))"
        fail=1
    fi
done
make beeb TRACE=play > /dev/null 2>&1 || fail=1
exit $fail
