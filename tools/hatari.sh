#!/bin/sh
# Run the ST original headless in Hatari: TOS 1.04, the game from a write-protected copy of orig/st.
# Usage: tools/hatari.sh <seconds of wall time allowed> [extra Hatari options...]
# Debugger scripts: --parse file. Exit after N frames: --run-vbls N.
set -e
cd "$(dirname "$0")/.."
HATARI=${HATARI:-/Users/tom/Applications/Hatari.app/Contents/MacOS/Hatari}   # (elsewhere: HATARI=...)
mkdir -p build/stdisk
cp -R orig/st/. build/stdisk/   # orig/st/. not orig/st/: GNU cp copies the directory itself for the latter
limit=$1; shift
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy exec perl -e 'alarm shift; exec @ARGV' "$limit" "$HATARI" \
    --confirm-quit no --alert-level fatal --sound off --fast-forward on --statusbar off \
    --machine st --memsize 1024 --tos orig/tos104uk-english-06-04-1989.img \
    -d build/stdisk --protect-hd on "$@" < /dev/null
