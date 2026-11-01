# Super Sprint for the BBC Master: tools for studying the ST original (Phases 1-2).
# Generated files go in build/ (git-ignored); comparison pictures in docs/img/.

PYTHON3 ?= python3.14
PY = .venv/bin/python -P
VENV = .venv/installed

.PHONY: all venv disasm tracks convert sheets viewer clean

all: disasm convert sheets viewer

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

clean:
	rm -rf build/conv build/viewer build/super.s build/super.json
