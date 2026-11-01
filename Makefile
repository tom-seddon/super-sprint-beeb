# Super Sprint for the BBC Master: tools for studying the ST original (Phases 1-2), and the renderer test
# (Phase 3). Generated files go in build/ (git-ignored); comparison pictures in docs/img/.
#
#   make beeb      build/sprint.ssd: the renderer test (!BOOT, SPRINTA-D the banks, SPRINT), playing TRACE
#   make check     the renderer test in headless jsbeeb (a Master 128): every frame of the ST race against
#                  the model, and each frame's work timed (tools/render_check.mjs)

PYTHON3 ?= python3.14
PY = .venv/bin/python -P
VENV = .venv/installed

# The race the renderer test plays: by default a real race on track 5 (index 4) as the 17th race of a game,
# with gates, barriers, pickups and a wreck; TRACE=attract plays the attract mode's race on track 6 instead.
TRACE ?= race
ifeq ($(TRACE),attract)
TRACK = 5
TRACEFILE = build/trace/cars_t5.json
else
TRACK = 4
RACE = 17
TRACEFILE = build/trace/race_t4_r$(RACE).json
endif
GEN = build/gen

.PHONY: all venv disasm tracks convert sheets viewer beeb check clean

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
build/trace/obj_t4_r$(RACE).json: tools/st_trace_objects.py tools/hatari.sh | $(VENV)
	$(PY) tools/st_trace_objects.py 4 $(RACE) $@
build/trace/race_t4_r$(RACE).json: tools/st_race.py build/trace/obj_t4_r$(RACE).json | $(VENV)
	$(PY) tools/st_race.py build/trace/obj_t4_r$(RACE).json $@

# The renderer test's data, and its disc. Baron 0.6 is on the PATH.
$(GEN)/cars.6502: tools/gendata.py tools/convert.py tools/st_sprites.py tools/objects.py build/conv/A_t0.bin \
		$(TRACEFILE) | $(VENV)
	$(PY) tools/gendata.py $(TRACK) $(TRACEFILE) $(GEN)

beeb: build/sprint.ssd
build/sprint.ssd: $(wildcard src/*.6502) $(GEN)/cars.6502
	baron -v --symbols build/sprint.json -o $@ --opt 2 src/boot.6502 src/sprint.6502 > build/sprint.lst

# The model each frame's play area is checked against, and the check.
build/check/model_$(TRACE).bin: tools/render_model.py tools/objects.py $(TRACEFILE) build/conv/A_t0.bin | $(VENV)
	mkdir -p build/check
	$(PY) tools/render_model.py $(TRACK) $(TRACEFILE) $@

check: build/sprint.ssd build/check/model_$(TRACE).bin
	node tools/render_check.mjs --model build/check/model_$(TRACE).bin

clean:
	rm -rf build/conv build/viewer build/super.s build/super.json build/gen build/check build/sprint.*
