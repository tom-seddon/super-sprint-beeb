# Super Sprint for the BBC Master: tools for studying the ST original (Phases 1-2), and the renderer test
# (Phase 3). Generated files go in build/ (git-ignored); comparison pictures in docs/img/.
#
#   make beeb      build/sprint.ssd: the renderer test (!BOOT, SPRINTA-D the banks, SPRINT), playing TRACE
#   make check     the renderer test in headless jsbeeb (a Master 128): every frame of the ST race against
#                  the model, and each frame's work timed (tools/render_check.mjs)

PYTHON3 ?= python3.14
PY = .venv/bin/python -P
VENV = .venv/installed

# The race the renderer test plays: by default a real race on track 5 (index 4) as the 18th race of a game
# (the counter 17), with gates, barriers, pickups, a wreck, and the tornado and cones (their coin flips
# forced); its wreck's helicopter comes from below. TRACE=heli1, heli2 or heli3 plays the same race with
# the helicopter forced to come from above or either side; TRACE=t0 to t7 the same race on track 1 to 8
# (index 0 to 7; t4 is the default's); TRACE=attract the attract mode's race on track 6; TRACE=logic0 the
# logic trace's race on track 1, drawn from the BBC's own race logic (Phase 4, step 8); TRACE=logic4 the default
# race (track 5, race 17, the hazards) drawn from the BBC's logic (step 11), and TRACE=h0 to h7 race 17 on
# track 1 to 8 so (h4 is logic4); TRACE=play the same race to play (make play: build/play.ssd): three players on the keys (Q W E, V B N, , . /), car 3 a drone.
TRACE ?= race
RACE = 17
FORCE = tornado,cones
RACEVBLS = 14000
ifeq ($(TRACE),attract)
TRACK = 5
TRACEFILE = build/trace/cars_t5.json
else ifneq ($(filter t0 t1 t2 t3 t4 t5 t6 t7,$(TRACE)),)
TRACK = $(subst t,,$(TRACE))
TRACEFILE = build/trace/race_t$(TRACK)_r$(RACE).json
else ifeq ($(TRACE),logic0)
TRACK = 0
TRACEFILE = build/trace/race_t0_r0_script.json
GENFLAGS = --logic
LOGICDEPS = build/lgen/tables.6502 build/lgen/sound.6502
else ifneq ($(filter logic4 h0 h1 h2 h3 h4 h5 h6 h7,$(TRACE)),)
TRACK = $(if $(filter logic4,$(TRACE)),4,$(subst h,,$(TRACE)))
TRACEFILE = build/trace/race_t$(TRACK)_r$(RACE).json
GENFLAGS = --logic
LOGICDEPS = build/lgen/tables.6502 build/lgen/sound.6502
LOGICTRACE = build/trace/logic_t$(TRACK)_r$(RACE).json
else ifeq ($(TRACE),play)
TRACK = 0
TRACEFILE = build/trace/race_t0_r0_script.json
GENFLAGS = --logic --play
LOGICDEPS = build/lgen/tables.6502 build/lgen/sound.6502
else ifneq ($(filter heli1 heli2 heli3,$(TRACE)),)
TRACK = 4
TRACEFILE = build/trace/race_t4_r$(RACE)_$(TRACE).json
else
TRACK = 4
TRACEFILE = build/trace/race_t4_r$(RACE).json
endif
GEN = build/gen

# A generator that fails part-way has written some of its files: its target goes, so the next make reruns it.
.DELETE_ON_ERROR:

.PHONY: all venv disasm tracks convert sheets viewer beeb play game check clean always logictrace hazardtrace hazardrace logic logiccheck

all: disasm convert sheets viewer beeb

# The Python virtual environment (git-ignored), made on first use and refreshed when requirements.txt changes.
venv: $(VENV)
$(VENV): requirements.txt
	$(PYTHON3) -m venv .venv
	.venv/bin/pip install -r requirements.txt
	touch $@

# The 68000 disassembly at run-time addresses, with Hatari profile addresses as extra seeds if present.
disasm: build/super.s
build/super.s: tools/st_disasm.py orig/st/AUTO/SUPER.PRG | $(VENV)
	mkdir -p build
	$(PY) tools/st_disasm.py orig/st/AUTO/SUPER.PRG build/super.s build/super.json \
		$(if $(wildcard build/prof/seeds.txt),--seeds build/prof/seeds.txt)

# Each track's background and masks, dumped from the original running in Hatari (about 5 s a track).
tracks: build/gfx/bg_t7.npy
build/gfx/bg_t7.npy: tools/st_dump_tracks.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_dump_tracks.py

# MODE 1 conversions for every palette option.
convert: build/conv/A_t0.bin
build/conv/A_t0.bin: tools/convert.py tools/st_sprites.py build/gfx/bg_t7.npy | $(VENV)
	$(PY) tools/convert.py build/conv

sheets: convert | $(VENV)
	$(PY) tools/compare_sheets.py

# Bootable viewer discs, one per option: build/viewer/disc<option>.ssd.
viewer: convert | $(VENV)
	$(PY) tools/make_viewer.py

# The ST's attract race on track 6: the four cars' places and frames, every frame (Hatari, about 15 s).
build/trace/cars_t5.json: tools/st_trace_cars.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_cars.py 5 $@

# A real race (Hatari, about 20 s): every object drawing routine's calls logged, then turned into frames.
build/trace/obj_t%_r$(RACE).json: tools/st_trace_objects.py tools/hatari.sh | $(VENV)
	VBLS=$(RACEVBLS) $(PY) tools/st_trace_objects.py $* $(RACE) $@ $(if $(FORCE),$(FORCE),-)
build/trace/race_t%_r$(RACE).json: tools/st_race.py build/trace/obj_t%_r$(RACE).json | $(VENV)
	$(PY) tools/st_race.py build/trace/obj_t$*_r$(RACE).json $@
build/trace/obj_t4_r$(RACE)_heli%.json: tools/st_trace_objects.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_objects.py 4 $(RACE) $@ $(FORCE),heli$*
build/trace/race_t4_r$(RACE)_heli%.json: tools/st_race.py build/trace/obj_t4_r$(RACE)_heli%.json | $(VENV)
	$(PY) tools/st_race.py build/trace/obj_t4_r$(RACE)_heli$*.json $@

# A race's logic (Phase 4, D9; Hatari, about 30 s): the blue car driven by tools/logic_scripts/tN.json (track
# index N), every per-car variable, input and random number, every frame, race 0. `make logictrace`: track 1.
build/trace/logic_t%_r0.json: tools/st_trace_logic.py tools/hatari.sh tools/logic_scripts/t%.json | $(VENV)
	$(PY) tools/st_trace_logic.py $* 0 tools/logic_scripts/t$*.json $@
# race 17's logic on track N (step 11, then every track): accelerate held, the tornado and cones forced, the
# renderer's own race (race_tN_r17.json) from the logic's side; 14,000 VBLs (about 5 minutes), as the longest races
# outrun the tracer's default 6,000
build/trace/logic_t%_r$(RACE).json: tools/st_trace_logic.py tools/hatari.sh | $(VENV)
	VBLS=$(RACEVBLS) $(PY) tools/st_trace_logic.py $* $(RACE) - $@ $(FORCE)
logictrace: build/trace/logic_t0_r0.json $(foreach t,0 1 2 3 4 5 6 7,build/trace/logic_t$(t)_r$(RACE).json)
# Phase 5, step 4: the race count's hazards on every track, for tools/disc_races.sh: race 1 none, 2 the barriers, 4
# the tornado (forced), 50 the counter's end, all forced, each race's logic and draw calls. (Race 17 is the rule
# above's.) 14,000 VBLs: the slow drones of the early races outrun 9,000. About 3 hours one at a time.
hazardtrace:
	$(MAKE) hazardrace RACE=1 FORCE=
	$(MAKE) hazardrace RACE=2 FORCE=
	$(MAKE) hazardrace RACE=4 FORCE=tornado
	$(MAKE) hazardrace RACE=50 FORCE=tornado,cones
hazardrace: $(foreach t,0 1 2 3 4 5 6 7,build/trace/logic_t$(t)_r$(RACE).json build/trace/race_t$(t)_r$(RACE).json)

# The race logic's test (Phase 4): the logic trace's race replayed through the BBC's logic, no display
# (build/logic.ssd), and its check against the ST's state every frame (tools/logic_check.mjs). LOGICTRACE picks
# the race: build/trace/logic_t4_r17.json for the hazards'. build/lgen/tracefile names the one the data was made
# from, so another remakes it (a second's wait before it's rewritten: make 3.81's file times are whole
# seconds here, and a stamp written in the second a fast build ended would look no newer than its outputs).
LOGICTRACE ?= build/trace/logic_t0_r0.json
build/lgen/tracefile: always
	@mkdir -p build/lgen
	@echo '$(LOGICTRACE)' | cmp -s - $@ || { sleep 1; echo '$(LOGICTRACE)' > $@; }
build/lgen/tables.6502: tools/gen_logic.py tools/logic_maps.py tools/maskb.py build/super.s $(LOGICTRACE) build/lgen/tracefile | $(VENV)
	$(PY) tools/gen_logic.py $(LOGICTRACE) build/lgen
logic: build/logic.ssd
build/logic.ssd: $(wildcard src/*.6502) build/lgen/tables.6502 build/lgen/sound.6502
	baron -v --symbols build/logic.json -o $@ --opt 2 src/logictest.6502 > build/logic.lst
# The race's sound (step 10, D11): the ST's sound captured in Hatari (about 40 s each: the logic race, it with
# oil poked across the start, the hazard race), and the effects cut from them and converted for the SN76489.
build/trace/sound_t0_r0.json: tools/st_trace_sound.py tools/hatari.sh tools/logic_scripts/t0.json | $(VENV)
	$(PY) tools/st_trace_sound.py 0 0 $@ - tools/logic_scripts/t0.json
build/trace/sound_t0_r0_oil.json: tools/st_trace_sound.py tools/hatari.sh tools/logic_scripts/t0.json | $(VENV)
	$(PY) tools/st_trace_sound.py 0 0 $@ oil tools/logic_scripts/t0.json
build/trace/sound_t6_r$(RACE).json: tools/st_trace_sound.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_sound.py 6 $(RACE) $@ $(FORCE)
build/trace/sound_t4_r$(RACE)_hz.json: tools/st_trace_sound.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_sound.py 4 $(RACE) $@ $(FORCE)
SOUNDCAPS = build/trace/sound_t0_r0.json build/trace/sound_t6_r$(RACE).json build/trace/sound_t0_r0_oil.json
build/lgen/sound.6502: tools/sound_gen.py tools/ay2sn.py $(SOUNDCAPS) | $(VENV)
	@mkdir -p build/lgen
	$(PY) tools/sound_gen.py build/lgen

LOGICTRACK = $(word 1,$(subst _, ,$(subst build/trace/logic_t,,$(LOGICTRACE))))
LOGICDRAWS = $(if $(filter 0,$(LOGICTRACK)),build/trace/race_t0_r0_script.json,build/trace/race_t$(LOGICTRACK)_r$(RACE).json)
logiccheck: build/logic.ssd $(LOGICDRAWS)
	node tools/logic_check.mjs --trace $(LOGICTRACE) $(LOGICARGS)
	node tools/maskb_check.mjs $(LOGICTRACK)
	node tools/logic_draws.mjs --race $(LOGICDRAWS)

# The same race's draw calls from the ST (Hatari, about 40 s): the renderer's model for it, and the draw
# calls the BBC's logic must make (tools/logic_draws.mjs).
build/trace/race_t0_r0_script.json: tools/st_trace_objects.py tools/st_race.py tools/hatari.sh tools/logic_scripts/t0.json | $(VENV)
	$(PY) tools/st_trace_objects.py 0 0 build/trace/obj_t0_r0_script.json - tools/logic_scripts/t0.json
	$(PY) tools/st_race.py build/trace/obj_t0_r0_script.json $@

# The renderer test's data, and its disc. Baron 0.6 is on the PATH. $(GEN)/tracefile names the trace the
# data was made from, so playing another (TRACEFILE=...) remakes it, and so does coming back.
$(GEN)/tracefile: always
	@mkdir -p $(GEN)
	@echo '$(TRACEFILE) $(GENFLAGS)' | cmp -s - $@ || { sleep 1; echo '$(TRACEFILE) $(GENFLAGS)' > $@; }
always:

$(GEN)/cars.6502: tools/gendata.py tools/convert.py tools/st_sprites.py tools/objects.py build/conv/A_t0.bin \
		$(TRACEFILE) $(GEN)/tracefile | $(VENV)
	$(PY) tools/gendata.py $(TRACK) $(TRACEFILE) $(GEN) $(GENFLAGS)

beeb: build/sprint.ssd

# The disc to play, kept as build/play.ssd: the game's (make game: the play build loads the next track's file
# after each race, so its disc is the one with them). build/sprint.ssd is whichever build was made last.
play: game
	cp build/game.ssd build/play.ssd
# The front end's pictures and tables, for the file TRACKF: a screen's look is in tools/screens.py. They're drawn
# against the ST's screens, captured in Hatari (about 30 s, tools/game_traces.sh's): made if missing, and like that
# script's, a capture already made is kept (a new tracer or script doesn't remake it: delete the file).
STSCREENS = build/st_screens/screens.json build/st_screens/options.json
$(STSCREENS): build/st_screens/%.json: | $(VENV)
	tools/game_traces.sh screens $*
$(GEN)/front.6502: tools/screens.py tools/screen_options.py tools/st_frontend.py | build/zx02 $(VENV) $(STSCREENS)
	mkdir -p $(GEN)
	$(PY) tools/screens.py $(GEN) build/zx02

# The front end's tunes (Phase 5, step 9, D11): captured whole on the ST (about 35 s, in Hatari), converted and packed.
build/trace/tunes.json: tools/st_trace_tunes.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_tunes.py $@
$(GEN)/tunes_fixed.bin: tools/tune_gen.py tools/sound_gen.py tools/ay2sn.py build/trace/tunes.json | build/zx02 $(VENV)
	mkdir -p $(GEN)
	$(PY) tools/tune_gen.py build/trace/tunes.json $(GEN)
$(GEN)/tunes_circle.bin: $(GEN)/tunes_fixed.bin

build/sprint.ssd: $(wildcard src/*.6502) $(GEN)/cars.6502 $(GEN)/front.6502 $(GEN)/tunes_fixed.bin $(LOGICDEPS)
	baron -v --symbols build/sprint.json -o $@ --opt 2 src/boot.6502 src/sprint.6502 > build/sprint.lst

# The game's disc (Phase 5, 3b): every track's play build (tools/all_tracks.sh, which checks their layout),
# then track 1's as it boots and a packed file for each track's slots (tools/make_game.py). The compressor is
# the beeb-port-kit's ZX02, built from its source (one compressor, so the disc doesn't depend on the machine).
ZX02SRC = reference/beeb-port-kit/template/tools/zx02src/src
build/zx02: $(ZX02SRC)/compress.c $(ZX02SRC)/memory.c $(ZX02SRC)/optimize.c $(ZX02SRC)/zx02.c
	mkdir -p build
	cc -O2 -o $@ $^
# tools/all_tracks.sh copies track 1's logic trace for each track's room before it calls make, so it's made here
# if missing (an order-only prerequisite: a newer tracer doesn't trace it again).
game: build/zx02 | $(VENV) build/trace/logic_t0_r0.json
	tools/all_tracks.sh
	$(PY) tools/make_game.py build/tracks build/zx02 build/game.ssd
	$(PY) tools/adfs_disc.py build/game.ssd build/game.adl

# The model each frame's play area is checked against, and the check.
CUETRACE = $(if $(filter --logic,$(GENFLAGS)),$(LOGICTRACE))
build/check/model_$(TRACE).bin: tools/render_model.py tools/objects.py tools/gendata.py $(TRACEFILE) $(CUETRACE) build/conv/A_t0.bin | $(VENV)
	mkdir -p build/check
	$(PY) tools/render_model.py $(TRACK) $(TRACEFILE) $@ $(if $(CUETRACE),--cue $(CUETRACE))

check: build/sprint.ssd build/check/model_$(TRACE).bin
	node tools/render_check.mjs --model build/check/model_$(TRACE).bin

clean:
	rm -rf build/conv build/viewer build/super.s build/super.json build/gen build/check build/sprint.*
