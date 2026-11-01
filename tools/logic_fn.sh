#!/bin/sh
# Print one function from build/super.s: tools/logic_fn.sh <hex addr>
cd "$(dirname "$0")/.."
a=$(echo "$1" | tr a-f A-F)
awk -v a="$a" '
  $0 ~ "^F_"a":" || $0 ~ "^[a-z]+_"a":" {on=1}
  on && /^[A-Za-z]+_[0-9A-F]+:/ && $0 !~ a && /^(F|gemdos|xbios|bios|L)_/ { if ($0 !~ /^L_/) exit }
  on {print}' build/super.s
