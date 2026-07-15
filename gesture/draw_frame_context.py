"""Per-frame draw / hit-test snapshot (scale, prefs, mouse) — fill once, reuse."""

from __future__ import annotations

from dataclasses import dataclass

import bpy


@dataclass(slots=True)
class DrawFrameContext:
    """Cached values for one GPU draw / input snapshot cycle."""

    ui_scale: float = 1.0
    text_gpu_draw_size: float = 0.0
    text_gpu_draw_radius: float = 0.0
    margin_x: float = 0.0
    margin_y: float = 0.0
    gesture_radius: float = 0.0
    threshold: float = 0.0
    threshold_confirm: float = 0.0
    # WINDOW-region mouse for hit tests (same space as GPU POST_PIXEL boxes).
    mouse_region: tuple[float, float] | None = None


def refresh_draw_frame_context(session, ops) -> DrawFrameContext:
    """Build DrawFrameContext from prefs + mouse; store on *session*."""
    try:
        scale = float(bpy.context.preferences.view.ui_scale)
    except (AttributeError, TypeError):
        scale = 1.0

    pref = ops.pref
    draw = pref.draw_property
    gp = pref.gesture_property
    mx, my = draw.margin

    from ..utils.region_mouse import ops_window_mouse
    mouse = ops_window_mouse(ops)

    ctx = DrawFrameContext(
        ui_scale=scale,
        text_gpu_draw_size=float(draw.text_gpu_draw_size) * scale,
        text_gpu_draw_radius=float(draw.text_gpu_draw_radius) * scale,
        margin_x=float(mx) * scale,
        margin_y=float(my) * scale,
        gesture_radius=float(gp.radius) * scale,
        threshold=float(gp.threshold) * scale,
        threshold_confirm=float(gp.threshold_confirm) * scale,
        mouse_region=mouse,
    )
    session.draw_ctx = ctx
    return ctx


def draw_ctx_from_ops(ops) -> DrawFrameContext | None:
    session = getattr(ops, "session", None)
    if session is None:
        return None
    return getattr(session, "draw_ctx", None)
