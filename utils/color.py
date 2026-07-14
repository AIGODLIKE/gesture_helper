"""Scene-linear ColorProperty → display / GPU uniforms.

Blender ``subtype='COLOR'`` stores scene-linear values. The preference picker
hex uses IEC 61966-2-1 sRGB (e.g. ``#27b3aa``).

Viewport overlays use builtin ``UNIFORM_COLOR`` which runs
``blender_srgb_to_framebuffer_space`` (IEC sRGB→linear), then the sRGB
framebuffer encodes linear→bytes. A plain IEC round-trip is correct when that
encode is also IEC. On common GPU paths the encode approximates **gamma 2.2**,
which shifts the picker hex (``#27b3aa`` → ``#2bb2a9``). ``color_to_gpu``
pre-emphasizes so the encode lands on the picker color.

BLF expects plain IEC display sRGB — use ``color_to_srgb``, not ``color_to_gpu``.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=512)
def linear_to_srgb_tuple(r: float, g: float, b: float, a: float = 1.0) -> tuple[float, float, float, float]:
    """Cached IEC 61966-2-1 linear → sRGB (hot path, no numpy)."""

    def ch(c: float) -> float:
        c = 0.0 if c < 0.0 else (1.0 if c > 1.0 else float(c))
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    return ch(r), ch(g), ch(b), float(a)


def color_to_srgb(color) -> tuple[float, float, float, float]:
    """Scene-linear → IEC display sRGB (BLF / picker-matched, no GPU pre-emphasis)."""
    c = tuple(color)
    if len(c) == 3:
        return linear_to_srgb_tuple(c[0], c[1], c[2], 1.0)
    return linear_to_srgb_tuple(c[0], c[1], c[2], c[3])


@lru_cache(maxsize=512)
def _gpu_uniform_from_srgb(r: float, g: float, b: float, a: float) -> tuple[float, float, float, float]:
    """IEC sRGB display → overlay shader uniform (gamma-2.2 FB encode compensate)."""
    # Want g22(IEC_decode(u)) == display.  =>  IEC_decode(u) == display**2.2
    # =>  u == IEC_encode(display**2.2)
    return linear_to_srgb_tuple(r ** 2.2, g ** 2.2, b ** 2.2, a)


def color_to_gpu(color) -> tuple[float, float, float, float]:
    """Scene-linear → GPU overlay uniform (IEC picker hex after framebuffer encode)."""
    srgb = color_to_srgb(color)
    return _gpu_uniform_from_srgb(srgb[0], srgb[1], srgb[2], srgb[3])


def clear_color_cache() -> None:
    linear_to_srgb_tuple.cache_clear()
    _gpu_uniform_from_srgb.cache_clear()
