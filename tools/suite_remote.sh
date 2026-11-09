#!/bin/sh
# tools/suite.sh run whole on another machine, REMOTE (default agentbox: Tom's, for his laptop during development),
# so this one does no more than copy. Everything here runs here too: tools/suite.sh alone is the suite.
#
# Copied there with rsync into REMOTE_DIR (default super-sprint-beeb, in the home folder there), so after the first
# time only what has changed: this working tree as it is (committed or not, the submodules' too; not .git, build/
# or .venv), and the ST's files from build/ (docs/st-traces.md: Hatari makes them, and it needn't run there), their
# times kept so make judges them as it does here. There the suite makes its own .venv and Baron (the README's
# prerequisites: make, a C compiler, CMake, Ninja, Python 3.14, and Node for the checks), everything else in build/,
# and the races' models (MODELS at a time, default 12), with HATARI=/usr/bin/false: an ST file missing here fails
# the suite there, and wants making here first (make stfiles, or the script that makes it).
# Its OUT comes back here as OUT, with the discs it built (OUT/game.ssd, OUT/game.adl).
#
# One at a time: two runs would share REMOTE_DIR.
#
# Usage (from the repo root): tools/suite_remote.sh OUT [quick]   (OUT outside the repository, as tools/suite.sh)
# Exit status: the suite's, or 1 if the copying or the ssh fail.

OUT=${1:?usage: tools/suite_remote.sh OUT [quick]}
REMOTE=${REMOTE:-agentbox}
DIR=${REMOTE_DIR:-super-sprint-beeb}
ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE" "mkdir -p $DIR/build/trace $DIR/build/prof" ||
    { echo "can't reach $REMOTE: tools/suite.sh OUT runs the suite here"; exit 1; }
# the tree (--delete: a file gone here goes there; build/, .venv/ and out/ there are the suite's own)
rsync -a --delete --exclude=.git --exclude=/build/ --exclude=/.venv/ --exclude=/out/ --exclude=.DS_Store \
    ./ "$REMOTE:$DIR/" || exit 1
# the ST's files: the tracks' dumps, the screens, the traces (not Hatari's logs, the raw object traces or
# tools/all_tracks.sh's copies, made from the rest), and the disassembler's seeds if there are any
rsync -a build/gfx build/st_screens "$REMOTE:$DIR/build/" || exit 1
rsync -a --exclude='obj_*' --exclude='*_room.json' --include='*.json' --exclude='*' \
    build/trace/ "$REMOTE:$DIR/build/trace/" || exit 1
[ -f build/prof/seeds.txt ] && { rsync -a build/prof/seeds.txt "$REMOTE:$DIR/build/prof/" || exit 1; }
# the build's version, git's here: there's no .git there (the Makefile's VERSION)
version=$(make -s version) || exit 1
ssh -o ServerAliveInterval=30 "$REMOTE" "cd $DIR && rm -rf out/suite && VERSION='$version' HATARI=/usr/bin/false REMOTE= MACHINES=${MACHINES:-14} MODELS=${MODELS:-12} sh tools/suite.sh out/suite $2 > out/suite.log 2>&1; echo \$? > out/suite.status"
[ $? = 0 ] || exit 1
mkdir -p "$OUT"
rsync -a "$REMOTE:$DIR/out/suite/" "$OUT/" || exit 1
for f in out/suite.log build/game.ssd build/game.adl; do      # (one each: macOS's rsync 2.6.9 takes one remote source)
    rsync -a "$REMOTE:$DIR/$f" "$OUT/" || exit 1
done
status=$(ssh -o BatchMode=yes "$REMOTE" "cat $DIR/out/suite.status")
cat "$OUT/verdicts.txt"
exit ${status:-1}
