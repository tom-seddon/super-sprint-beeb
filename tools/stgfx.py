"""Atari ST low-res graphics helpers: planar decoding, palettes, PNG output."""
import numpy as np
from PIL import Image


def st_rgb(word):
    """ST palette word (0RGB, 3 bits a channel; the STE's 4th bit ignored) to 8-bit RGB."""
    r, g, b = (word >> 8) & 7, (word >> 4) & 7, word & 7
    return tuple(round(c * 255 / 7) for c in (r, g, b))


def palette_from_words(words):
    return [st_rgb(w) for w in words]


def planar_to_indices(buf, width_px, height):
    """Interleaved 4-plane ST bitmap (16-pixel groups of 4 words) to a (height, width_px) index array."""
    words_per_line = width_px // 16 * 4
    a = np.frombuffer(bytes(buf[:words_per_line * 2 * height]), dtype='>u2').reshape(height, width_px // 16, 4)
    bits = np.arange(15, -1, -1)
    planes = (a[:, :, :, None] >> bits) & 1                 # h, groups, plane, 16
    idx = (planes[:, :, 0] | planes[:, :, 1] << 1 | planes[:, :, 2] << 2 | planes[:, :, 3] << 3)
    return idx.reshape(height, width_px).astype(np.uint8)


def indices_to_png(idx, palette, path, scale=1, transparent=None):
    pal = np.array(palette, dtype=np.uint8)
    rgb = pal[idx]
    img = Image.fromarray(rgb)
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)
    img.save(path)
    return img
