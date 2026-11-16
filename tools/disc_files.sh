#!/bin/sh
# What tools/disc_races.sh's jobs read, a path a line, from the repo root: for tools/remote.sh to copy to another
# machine, and for tools/disc_races.sh to copy here before the jobs run (the builds after the disc's, time attack's
# above all, rewrite build/gen, which they read).
#
# Usage (from the repo root): tools/disc_files.sh
echo .mcp.json
for f in disc_races.sh disc_races.mjs boot_check.mjs break_check.mjs crash_check.mjs game_check.mjs attract_check.mjs flash_check.mjs options_check.mjs select_check.mjs upgrades_check.mjs upgrades_model.mjs circle_check.mjs circle_model.mjs initials_check.mjs initials_model.mjs tune_check.mjs save_check.mjs load_check.mjs jsbeeb.mjs logic_compare.mjs; do
    echo tools/$f
done
echo build/game.ssd; echo build/game.adl; echo build/game_slots.json; echo build/gen/version.6502; for f in title credits scores records prepare_all prepare_none options options_on options_off options_clash options_version select select_all select_none select_dial select_text select_level upgrades_all upgrades_box upgrades_font upgrades_dial circle circle_class circle_figure circle_figure_class circle_sparkle circle_junk initials_big; do echo build/gen/$f.bin; done; echo build/gen/tunes_expect.json; echo orig/st/SSPRINT.HSC
ls build/tracks/t?.json build/trace/logic_t?_r1.json build/trace/logic_t?_r2.json build/trace/logic_t?_r4.json \
   build/trace/logic_t?_r17.json build/trace/logic_t?_r50.json build/trace/logic_t?_h*.json build/trace/logic_t?_demo*.json \
   build/trace/game_*.json \
   build/check/model_t?_r1.bin build/check/model_t?_r2.bin build/check/model_t?_r4.bin build/check/model_t?_r17.bin \
   build/check/model_t?_r50.bin build/check/model_t?_h*.bin
