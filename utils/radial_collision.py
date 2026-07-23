"""Automatic radial collision avoidance.

Computes per-element ``overlay_offset`` values so that radial buttons
(directions 1–8) do not visually overlap.  The offsets are applied
during GPU drawing in :mod:`element.element_gpu_draw`.

Offsets are computed from scratch every frame to avoid drift; property
writes are minimised so that ``clear_derived_cache`` is triggered only
when a value actually changes.
"""
from __future__ import annotations

from mathutils import Vector

# Hard cap per axis to keep offsets bounded — identical to the soft-range
# defined on the FloatVectorProperty.
_MAX_OFFSET = 500.0


def compute_overlay_collision_offsets(direction_items: dict, radius: float, ops=None) -> None:
    """Analyse projected bounding boxes of radial items and push apart
    any that overlap.

    Only non-layout, direction 1–8 items are processed.  Bounding boxes
    include the *current* ``overlay_offset`` so that pushes converge
    across consecutive frames.

    Args:
        direction_items: ``{direction_str: ElementGpuProperty}`` dict
            from the active gesture.
        radius: Current radial radius in region pixels.
        ops: Optional operator instance; set on each item so that
            dimension properties use the cached draw-frame context.
    """
    from ..element.element_gpu_draw import get_position

    # ---- collect eligible items -------------------------------------------
    radial_items = []
    for item in direction_items.values():
        # Only process direction 1-8 radial buttons (non-layout, non-flight)
        if item.is_layout_container or str(item.direction) == '9':
            continue
        radial_items.append(item)

    if len(radial_items) < 2:
        return

    # Stamp *ops* so dimension reads use draw-frame cached scale / margins.
    if ops is not None:
        for item in radial_items:
            item.ops = ops

    # ---- compute bounding boxes (include current overlay_offset) ----------
    # Each box: (x_min, y_min, x_max, y_max)
    boxes: dict = {}
    for item in radial_items:
        pos = get_position(str(item.direction), radius)   # circle anchor
        doff = item.draw_direction_offset                  # outward offset
        w, h = item.draw_dimensions                        # button width, height
        mx, my = item.text_margin                          # extra margin

        cur_off = item.overlay_offset                      # current user/system offset

        cx = pos.x + doff.x + cur_off[0]
        cy = pos.y + doff.y + cur_off[1]

        boxes[item] = (
            cx - w * 0.5 - mx,
            cy - h * 0.5 - my,
            cx + w * 0.5 + mx,
            cy + h * 0.5 + my,
        )

    # ---- detect overlaps & accumulate push vectors ------------------------
    push: dict = {item: Vector((0.0, 0.0)) for item in radial_items}

    for i in range(len(radial_items)):
        for j in range(i + 1, len(radial_items)):
            a = radial_items[i]
            b = radial_items[j]
            ba = boxes[a]
            bb = boxes[b]

            ox = min(ba[2], bb[2]) - max(ba[0], bb[0])  # horizontal overlap
            oy = min(ba[3], bb[3]) - max(ba[1], bb[1])  # vertical overlap

            if ox <= 0 or oy <= 0:
                continue  # no overlap

            # --- compute separation direction (center → center) -------------
            ca = Vector(((ba[0] + ba[2]) * 0.5, (ba[1] + ba[3]) * 0.5))
            cb = Vector(((bb[0] + bb[2]) * 0.5, (bb[1] + bb[3]) * 0.5))
            direction = cb - ca

            if direction.length_squared < 1e-12:
                direction = Vector((1.0, 0.0))  # fallback for coincident centers

            direction.normalize()

            # Push each item away from the other by half the larger overlap.
            push_amount = max(ox, oy) * 0.5
            push[a] -= direction * push_amount
            push[b] += direction * push_amount

    # ---- apply offsets (only when changed, to minimise cache resets) ------
    for item in radial_items:
        new_offset = push[item]
        cur = item.overlay_offset
        cur_x, cur_y = cur[0], cur[1]

        new_x = min(_MAX_OFFSET, max(-_MAX_OFFSET, cur_x + new_offset.x))
        new_y = min(_MAX_OFFSET, max(-_MAX_OFFSET, cur_y + new_offset.y))

        if abs(new_x - cur_x) > 1e-4 or abs(new_y - cur_y) > 1e-4:
            item.overlay_offset = (new_x, new_y)
