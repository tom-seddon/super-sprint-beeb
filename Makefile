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
# logic trace's race on track 1, drawn from the BBC's own race logic (Phase 4, step 8).
TRACE ?= race
RACE = 17
FORCE = tornado,cones
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
LOGICDEPS = build/lgen/tables.6502
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

.PHONY: all venv disasm tracks convert sheets viewer beeb check clean always logictrace logic logiccheck

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
	$(PY) tools/st_trace_objects.py $* $(RACE) $@ $(FORCE)
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
logictrace: build/trace/logic_t0_r0.json

# The race logic's test (Phase 4): the logic trace's race replayed through the BBC's logic, no display
# (build/logic.ssd), and its check against the ST's state every frame (tools/logic_check.mjs).
LOGICTRACE = build/trace/logic_t0_r0.json
build/lgen/tables.6502: tools/gen_logic.py tools/logic_maps.py build/super.s $(LOGICTRACE) | $(VENV)
	$(PY) tools/gen_logic.py $(LOGICTRACE) build/lgen
logic: build/logic.ssd
build/logic.ssd: $(wildcard src/*.6502) build/lgen/tables.6502
	baron -v --symbols build/logic.json -o $@ --opt 2 src/logictest.6502 > build/logic.lst
logiccheck: build/logic.ssd build/trace/race_t0_r0_script.json
	node tools/logic_check.mjs $(LOGICARGS)
	node tools/maskb_check.mjs
	node tools/logic_draws.mjs

# The same race's draw calls from the ST (Hatari, about 40 s): the renderer's model for it, and the draw
# calls the BBC's logic must make (tools/logic_draws.mjs).
build/trace/race_t0_r0_script.json: tools/st_trace_objects.py tools/st_race.py tools/hatari.sh tools/logic_scripts/t0.json | $(VENV)
	$(PY) tools/st_trace_objects.py 0 0 build/trace/obj_t0_r0_script.json - tools/logic_scripts/t0.json
	$(PY) tools/st_race.py build/trace/obj_t0_r0_script.json $@

# The renderer test's data, and its disc. Baron 0.6 is on the PATH. $(GEN)/tracefile names the trace the
# data was made from, so playing another (TRACEFILE=...) remakes it, and so does coming back.
$(GEN)/tracefile: always
	@mkdir -p $(GEN)
	@echo '$(TRACEFILE) $(GENFLAGS)' | cmp -s - $@ || echo '$(TRACEFILE) $(GENFLAGS)' > $@
always:

$(GEN)/cars.6502: tools/gendata.py tools/convert.py tools/st_sprites.py tools/objects.py build/conv/A_t0.bin \
		$(TRACEFILE) $(GEN)/tracefile | $(VENV)
	$(PY) tools/gendata.py $(TRACK) $(TRACEFILE) $(GEN) $(GENFLAGS)

beeb: build/sprint.ssd
build/sprint.ssd: $(wildcard src/*.6502) $(GEN)/cars.6502 $(LOGICDEPS)
	baron -v --symbols build/sprint.json -o $@ --opt 2 src/boot.6502 src/sprint.6502 > build/sprint.lst

# The model each frame's play area is checked against, and the check.
build/check/model_$(TRACE).bin: tools/render_model.py tools/objects.py tools/gendata.py $(TRACEFILE) build/conv/A_t0.bin | $(VENV)
	mkdir -p build/check
	$(PY) tools/render_model.py $(TRACK) $(TRACEFILE) $@

check: build/sprint.ssd build/check/model_$(TRACE).bin
	node tools/render_check.mjs --model build/check/model_$(TRACE).bin

clean:
	rm -rf build/conv build/viewer build/super.s build/super.json build/gen build/check build/sprint.*
