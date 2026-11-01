# Super Sprint for the BBC Master: tools for studying the ST original (Phases 1-2).
# Generated files go in build/ (git-ignored); comparison pictures in docs/img/.

PY = .venv/bin/python -P

.PHONY: all disasm tracks convert sheets viewer clean

all: disasm convert sheets viewer

# The 68000 disassembly at run-time addresses, with Hatari profile addresses as extra seeds if present.
disasm: build/super.s
build/super.s: tools/st_disasm.py orig/st/AUTO/SUPER.PRG
	mkdir -p build
	$(PY) tools/st_disasm.py orig/st/AUTO/SUPER.PRG build/super.s build/super.json \
		$(if $(wildcard build/prof/seeds.txt),--seeds build/prof/seeds.txt)

# Each track's background and masks, dumped from the original running in Hatari (about 5 s a track).
tracks: build/gfx/bg_t7.npy
build/gfx/bg_t7.npy: tools/st_dump_tracks.py tools/hatari.sh
	$(PY) tools/st_dump_tracks.py

# MODE 1 conversions for every palette option.
convert: build/conv/A_t0.bin
build/conv/A_t0.bin: tools/convert.py tools/st_sprites.py build/gfx/bg_t7.npy
	$(PY) tools/convert.py build/conv

sheets: convert
	$(PY) tools/compare_sheets.py

# Bootable viewer discs, one per option: build/viewer/disc<option>.ssd.
viewer: convert
	$(PY) tools/make_viewer.py

clean:
	rm -rf build/conv build/viewer build/super.s build/super.json
