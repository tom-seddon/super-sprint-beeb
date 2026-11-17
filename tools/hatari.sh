#!/bin/sh
# Run the ST original headless in Hatari: TOS 1.04, the game from a write-protected copy of orig/st.
# Usage: tools/hatari.sh <seconds of wall time allowed> [extra Hatari options...]
# Debugger scripts: --parse file. Exit after N frames: --run-vbls N.
# Hatari: HATARI if set (a Mac's Hatari.app will do for the binary inside it), else the one make builds from the
# submodule extern/hatari (make hatari); on macOS, HATARI only (Tom, 2026-11-17: "Require the user to have it
# installed somewhere, or build it themselves, and require them to specify the path").
set -e
# A fault here is said on the terminal too: the tracers keep Hatari's stderr in their own files.
fail() {
    echo "tools/hatari.sh: $*" >&2
    [ -t 2 ] || { echo "tools/hatari.sh: $*" > /dev/tty; } 2> /dev/null || true
    exit 1
}
case $HATARI in "~/"*) HATARI=$HOME/${HATARI#"~/"} ;; esac   # (zsh leaves make HATARI=~/... as it is)
case $HATARI in ?*/*) [ "${HATARI#/}" != "$HATARI" ] || HATARI=$PWD/$HATARI ;; esac   # (relative to the caller)
case $HATARI in *.app|*.app/) HATARI=${HATARI%/}/Contents/MacOS/Hatari ;; esac
cd "$(dirname "$0")/.."
if [ "$(uname -s)" = Darwin ]; then
    [ -n "$HATARI" ] || fail "set HATARI to a Hatari of 2.5.0 or later (2.6.1 made the ST's files): make HATARI=/path/to/Hatari.app ..., or export it; on macOS make doesn't build one"
    other="set HATARI to one of 2.5.0 or later"
else
    [ -n "$HATARI" ] || { HATARI=build/hatari/src/hatari; built=1; }
    other="unset HATARI, and make builds 2.6.1 from extern/hatari"
fi

if ! command -v "$HATARI" > /dev/null 2>&1; then
    [ -n "$built" ] && fail "no Hatari at $HATARI: make hatari builds it there (or set HATARI to another)"
    fail "no Hatari at $HATARI (HATARI): $other"
fi
# 2.5.0 or later: 2.4.1's memory dumps break the tracers (docs/brief-ci-hatari-2026-11-10.md). --version prints,
# then exits 1.
version=$(SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$HATARI" --version < /dev/null 2> /dev/null |
    sed -n 's/^Hatari v\([0-9][0-9]*\.[0-9][0-9]*[^ ]*\).*/\1/p' | head -n 1)
major=${version%%.*}; minor=${version#*.}; minor=${minor%%[!0-9]*}
[ -n "$version" ] || fail "$HATARI doesn't say which Hatari it is (--version); the ST's files need 2.5.0 or later"
[ "$major" -gt 2 ] || { [ "$major" -eq 2 ] && [ "$minor" -ge 5 ]; } ||
    fail "$HATARI is Hatari $version; the ST's files need 2.5.0 or later ($other)"

# The game's files copied for this run alone (so several can run at once), and removed after.
mkdir -p build
disk=$(mktemp -d build/stdisk.XXXXXX)
trap 'rm -rf "$disk"' EXIT
cp -R orig/st/. "$disk/"   # orig/st/. not orig/st/: GNU cp copies the directory itself for the latter
limit=$1; shift
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy perl -e 'alarm shift; exec @ARGV or die "$ARGV[0]: $!\n"' "$limit" \
    "$HATARI" \
    --confirm-quit no --alert-level fatal --sound off --fast-forward on --statusbar off \
    --machine st --memsize 1024 --tos orig/tos104uk-english-06-04-1989.img \
    -d "$disk" --protect-hd on "$@" < /dev/null
