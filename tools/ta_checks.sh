#!/bin/sh
# Time attack's checks (docs/brief-timeattack-2026-11-10.md), MACHINES at a time (default 4), each one's output in
# OUT/<name>.log and its exit status in OUT/<name>.status, then a line each. Exit status 1 if any failed or left no
# status. They read only time attack's discs, build/ta.ssd and build/ta.adl, its tracks' builds in build/tracks_ta
# (tools/all_tracks.sh ta: their symbols, and its front end's tables in build/tracks_ta/gen) and orig/st (the
# autopilot's path), so they can run beside anything else but a build of time attack.
#
# On the DFS disc: the ghost every frame (ta_ghost_check), its files (ta_save_check), the table (ta_table_check), the
# menu (ta_menu_check), its 32 rows (ta_rows_check), SCORES (ta_scores_check), the pictures (ta_picture_check), the
# options (ta_options_check) and the boot (boot_check --ta). On the ADFS disc too: the boot (boot_adfs), the ghost
# (ghost_adfs: every track loaded, raced twice, the second race with the ghost the first saved), and the ADFS cases
# ta_save_check and ta_scores_check have.
#
# tools/suite.sh runs it after time attack's build, so tools/suite_remote.sh runs it on another machine.
#
# Usage (from the repo root, after make ta): tools/ta_checks.sh OUT   (OUT outside the repository)

OUT=${1:?usage: tools/ta_checks.sh OUT}
mkdir -p "$OUT"
rm -f "$OUT"/*.log "$OUT"/*.status
CHECKS="ghost menu rows table save scores picture options boot boot_adfs ghost_adfs"
export OUT
# (the longest first: the ghost's two)
{ echo ghost ta_ghost_check
  echo ghost_adfs ta_ghost_check build/ta.adl
  echo save ta_save_check
  echo table ta_table_check
  echo scores ta_scores_check
  echo options ta_options_check
  echo picture ta_picture_check
  echo menu ta_menu_check
  echo rows ta_rows_check
  echo boot boot_check --ta
  echo boot_adfs boot_check --ta --adfs
} | xargs -P ${MACHINES:-4} -L 1 sh -c 'n=$0; t=$1; shift; s=$(date +%s); node tools/$t.mjs "$@" > "$OUT/$n.log" 2>&1; echo $? > "$OUT/$n.status"; echo "$n $(( $(date +%s) - s ))s" > "$OUT/$n.time"'
fail=0
for c in $CHECKS; do
    status=$(cat "$OUT/$c.status" 2>/dev/null)
    echo "$c: ${status:-missing} ($(cat "$OUT/$c.time" 2>/dev/null | cut -d' ' -f2)) $(grep -av '^\[jsbeeb\|^Loading' "$OUT/$c.log" 2>/dev/null | tail -1)"
    [ "$status" = 0 ] || fail=1
done
exit $fail
