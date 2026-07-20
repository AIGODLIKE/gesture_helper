"""Stable BLF line metrics measured from the live interface font.

``blf.dimensions()`` returns the ink bounding box of the glyphs actually in
the string — ``ace`` measures shorter than ``Ágj``, and CJK ideographs are
taller than Latin capitals. Any row height or vertical centering derived from
it jumps from label to label (and while a value text changes).

Instead, measure reference glyph sets once per (font, size):

- the ascent reference holds tall Latin glyphs, digits and common full-height
  CJK ideographs, so the tallest ink the current font stack renders on this
  machine (including Blender's CJK fallback font) defines the line top
- the descent reference adds descender glyphs for the line bottom

No font ships with the add-on; metrics always follow the user's UI font.
"""

from __future__ import annotations

import blf

# Latin references: tall glyphs sit exactly on the baseline, so the two
# measurements split ascent/descent precisely (accented caps are the tallest).
_LATIN_ASCENT_REF = "ÀÂbdfhklt0123456789"
_LATIN_DESCENT_REF = "gjpqy"
# Common full-height ideographs. CJK ink dips slightly below the baseline in
# most fonts, so it must stay OUT of the ascent split — it only widens the
# line box when the fallback font renders taller than the Latin envelope.
_CJK_REF = "国國體鬱髙"

_metrics: dict[tuple[int, float], tuple[float, float, float]] = {}


def clear_text_metrics() -> None:
    """Drop cached metrics (the UI font can change with user preferences)."""
    _metrics.clear()


def line_metrics(size: float, font_id: int = 0) -> tuple[float, float, float]:
    """Return ``(ascent, descent, line_height)`` for the UI font at *size*."""
    key = (font_id, round(float(size), 2))
    cached = _metrics.get(key)
    if cached is not None:
        return cached
    blf.size(font_id, size)
    ascent = blf.dimensions(font_id, _LATIN_ASCENT_REF)[1]
    full = blf.dimensions(font_id, _LATIN_ASCENT_REF + _LATIN_DESCENT_REF)[1]
    descent = max(0.0, full - ascent)
    line_h = ascent + descent
    cjk_h = blf.dimensions(font_id, _CJK_REF)[1]
    if cjk_h > line_h:
        # Rare: CJK fallback taller than the Latin envelope. The exact split is
        # unknowable from ink boxes; growing both sides keeps it centered.
        extra = (cjk_h - line_h) * 0.5
        ascent += extra
        descent += extra
        line_h = cjk_h
    result = (ascent, descent, line_h)
    _metrics[key] = result
    return result


def text_line_height(size: float, font_id: int = 0) -> float:
    """Constant line height for any label at *size*."""
    return line_metrics(size, font_id)[2]


def measure_text(text, size: float, font_id: int = 0) -> tuple[float, float]:
    """Width of *text* plus the constant line height (stable box size)."""
    blf.size(font_id, size)
    width = blf.dimensions(font_id, str(text))[0]
    return width, line_metrics(size, font_id)[2]


def baseline_offset(box_height: float, size: float, font_id: int = 0) -> float:
    """Distance from a box top DOWN to the baseline that centers the line box."""
    ascent, _descent, line_h = line_metrics(size, font_id)
    return (box_height - line_h) * 0.5 + ascent
