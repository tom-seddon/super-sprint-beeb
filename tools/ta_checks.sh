#!/bin/sh
# Time attack's checks (docs/brief-timeattack-2026-11-10.md), MACHINES at a time (default 4), each one's output in
# OUT/<name>.log and its exit status in OUT/<name>.status, then a line each. Exit status 1 if any failed or left no
# status. They read only time attack's discs, build/ta.ssd and build/ta.adl, its tracks' builds in build/tracks_ta
# (tools/all_tracks.sh ta: their symbols, and its front end's tables in build/tracks_ta/gen) and orig/st (the
# autopilot's path), so they can run beside anything else but a build of time attack.
#
# On the DFS disc: the ghost every frame (ta_ghost_check), its files (ta_save_check), the table (ta_table_check), the
# menu (ta_menu_check), its 32 rows (ta_rows_check), SCORES (ta_scores_check), the pictures (ta_picture_check), the
# options (ta_options_check), the boot (boot_check --ta) and MERGE (ta_merge_check). On the ADFS disc too: the boot
# (boot_adfs), MERGE (merge_adfs), the ghost (ghost_adfs: every track loaded, raced twice, the second race with the
# ghost the first saved), and the ADFS cases ta_save_check and ta_scores_check have.
#
# GHOSTS (default 1) splits each ghost check into that many pieces, each its own machine racing a share of the eight
# tracks (TRACKS=0,2,4,6 and 1,3,5,7 for 2), their logs and statuses OUT/ghost.0 and so on, ghost's and ghost_adfs's
# made from them (wrong if any piece is wrong or left none). Only where there are more cores than checks: on a laptop
# with 2 cores, GHOSTS=2 was slower (JOURNAL.md, 2026-11-13); tools/suite_remote.sh sets it for agentbox.
#
# tools/suite.sh runs it after time attack's build, so tools/suite_remote.sh runs it on another machine.
#
# Usage (from the repo root, after make ta): tools/ta_checks.sh OUT   (OUT outside the repository)

OUT=${1:?usage: tools/ta_checks.sh OUT}
mkdir -p "$OUT"
rm -f "$OUT"/*.log "$OUT"/*.status "$OUT"/*.time
CHECKS="ghost menu rows table save scores picture options boot boot_adfs ghost_adfs merge merge_adfs"
export OUT
GHOSTS=${GHOSTS:-1}
case $GHOSTS in [1-8]) ;; *) echo "GHOSTS is 1 to 8"; exit 1 ;; esac
# piece k of GHOSTS: tracks k, k+GHOSTS, ... (- for all, as one)
tracks() { [ "$GHOSTS" = 1 ] && { echo -; return; }; i=$1; l=; while [ $i -lt 8 ]; do l=$l${l:+,}$i; i=$((i + GHOSTS)); done; echo $l; }
pieces() { [ "$GHOSTS" = 1 ] && { echo $1; return; }; k=0; while [ $k -lt $GHOSTS ]; do echo $1.$k; k=$((k + 1)); done; }
# (the longest first: the ghost's two, or their pieces, the two discs' side by side)
{ k=0
  while [ $k -lt $GHOSTS ]; do
      p=$(pieces ghost | sed -n "$((k + 1))p"); q=$(pieces ghost_adfs | sed -n "$((k + 1))p")
      echo "$p $(tracks $k) ta_ghost_check"
      echo "$q $(tracks $k) ta_ghost_check build/ta.adl"
      k=$((k + 1))
  done
  echo save - ta_save_check
  echo table - ta_table_check
  echo scores - ta_scores_check
  echo options - ta_options_check
  echo picture - ta_picture_check
  echo menu - ta_menu_check
  echo rows - ta_rows_check
  echo boot - boot_check --ta
  echo boot_adfs - boot_check --ta --adfs
  echo merge - ta_merge_check
  echo merge_adfs - ta_merge_check --adfs
} | xargs -P ${MACHINES:-4} -L 1 sh -c 'n=$0; tr=$1; t=$2; shift 2; [ "$tr" = - ] || export TRACKS=$tr; s=$(date +%s); node tools/$t.mjs "$@" > "$OUT/$n.log" 2>&1; echo $? > "$OUT/$n.status"; echo "$n $(( $(date +%s) - s ))s" > "$OUT/$n.time"'
# the pieces made one: each ghost's status wrong if any piece's is, its log theirs in turn, its time the longest
if [ "$GHOSTS" != 1 ]; then
    for g in ghost ghost_adfs; do
        st=0; most=0; : > "$OUT/$g.log"
        for p in $(pieces $g); do
            ps=$(cat "$OUT/$p.status" 2>/dev/null); [ "$ps" = 0 ] || st=1
            pt=$(cut -d' ' -f2 "$OUT/$p.time" 2>/dev/null | tr -d s); [ "${pt:-0}" -gt $most ] && most=$pt
            { echo "== $p (TRACKS=$(tracks ${p##*.})): ${ps:-missing}"; cat "$OUT/$p.log"; } >> "$OUT/$g.log" 2>/dev/null
        done
        echo $st > "$OUT/$g.status"; echo "$g ${most}s" > "$OUT/$g.time"
        echo "$GHOSTS pieces, the longest ${most}s: $([ $st = 0 ] && echo all right || echo "one or more wrong")" >> "$OUT/$g.log"
    done
fi
fail=0
for c in $CHECKS; do
    status=$(cat "$OUT/$c.status" 2>/dev/null)
    echo "$c: ${status:-missing} ($(cat "$OUT/$c.time" 2>/dev/null | cut -d' ' -f2)) $(grep -av '^\[jsbeeb\|^Loading' "$OUT/$c.log" 2>/dev/null | tail -1)"
    [ "$status" = 0 ] || fail=1
done
exit $fail
