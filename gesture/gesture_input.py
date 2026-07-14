"""Gesture input processor — sole writer of session selection / trajectory state."""

from __future__ import annotations

import math
import time

import bpy
from mathutils import Vector

from .gesture_session import (
    GestureSession,
    InputSnapshot,
    threshold_zone_from_distance,
)



def _mouse_moved_enough(current: Vector, previous: Vector | None, *, min_dist: float = 1.0) -> bool:
    if previous is None:
        return True
    return (current - previous).length >= min_dist


def compute_angle(last_window: Vector | None, mouse: Vector) -> float | None:
    if last_window is None:
        return None
    vector = last_window - mouse
    if vector.length_squared == 0.0:
        return None
    return (180 * vector.angle_signed(Vector((-1, 0)), Vector((0, 0)))) / math.pi


def compute_angle_unsigned(angle: float | None) -> float | None:
    if angle is None:
        return None
    return angle if angle >= 0 else 360 + angle


def compute_direction_from_angle(
        angle_unsigned: float | None,
        *,
        is_have_extension_item: bool,
        is_beyond_extension_offset: bool,
        raw_items: dict,
        extension_hover: list,
) -> int | None:
    """Direction 1-9 with extension-zone correction."""
    if angle_unsigned is None:
        return None
    if angle_unsigned > 337.5:
        d = 1
    else:
        d = int((angle_unsigned + 22.5) // 45 + 1)
    if is_have_extension_item and is_beyond_extension_offset and d in (6, 8):
        bottom = raw_items.get("9")
        in_vertical = bool(bottom is not None and bottom.mouse_is_in_extension_vertical_area)
        if in_vertical or len(extension_hover) > 1:
            return 7
    return d


def direction_items_context_id(session: GestureSession, operator_gesture) -> int | None:
    tree = session.trajectory_tree
    last_element = tree.last_element if len(tree) else None
    if last_element is not None:
        return id(last_element)
    return id(operator_gesture) if operator_gesture is not None else None


def raw_direction_items_dict(session: GestureSession, operator_gesture) -> dict:
    tree = session.trajectory_tree
    last_element = tree.last_element if len(tree) else None
    if last_element:
        return last_element.gesture_direction_items
    if operator_gesture:
        return operator_gesture.gesture_direction_items
    return {}


def get_direction_items(session: GestureSession, operator_gesture, *, is_draw_gpu: bool) -> dict:
    raw = raw_direction_items_dict(session, operator_gesture)
    if not is_draw_gpu:
        return raw
    from ..utils.public_cache import PublicCache
    key = (direction_items_context_id(session, operator_gesture), PublicCache.__derived_generation__)
    memo = session._direction_items_memo
    if memo is not None and memo[0] == key:
        return memo[1]
    session._direction_items_memo = (key, raw)
    return raw


def invalidate_derived_caches(session: GestureSession, operator_gesture, *, force=False, ops=None):
    """Clear direction/extension memo only when tree level actually changed."""
    key = direction_items_context_id(session, operator_gesture)
    if not force and session._derived_cache_key == key:
        return
    session._derived_cache_key = key
    session._direction_items_memo = None
    session._gpu_extension_items_cache = None
    if ops is not None:
        ops._gpu_extension_items_cache = None


def tag_redraw_gesture_screen(session: GestureSession):
    """Redraw only the VIEW_3D WINDOW region.

    Tagging the whole area also redraws the Gesture N-panel (UI region) every
    mouse move — that is a major lag source when the sidebar is open, and can
    disturb modal mouse_region association used by extension hover.
    """
    area = session.area
    if area is not None:
        try:
            from ..utils.region_mouse import find_window_region
            region = find_window_region(area)
            if region is not None:
                region.tag_redraw()
                return
            area.tag_redraw()
            return
        except ReferenceError:
            ...
    screen = session.screen
    if screen is not None:
        try:
            for a in screen.areas:
                a.tag_redraw()
            return
        except ReferenceError:
            ...
    from ..utils.public import tag_redraw
    tag_redraw()


def ensure_trajectory_seed(session: GestureSession):
    tree = session.trajectory_tree
    if tree is None or len(tree):
        return
    try:
        if session.event is None:
            return
        press = Vector((session.event.mouse_x, session.event.mouse_y))
        session._gesture_circle_center = press
        session._last_trajectory_mouse = press.copy()
        tree.append(None, press)
        # Seed mouse trail at the same press point so the drawn line starts
        # on the origin marker (not at the first MOUSEMOVE sample).
        if not session.trajectory_mouse_move:
            session.trajectory_mouse_move.append(press.copy())
            session.trajectory_mouse_move_time.append(time.time())
    except (AttributeError, ReferenceError, TypeError):
        ...


def cancel_timeout_timer(session: GestureSession):
    timer = session._gesture_timeout_timer
    if timer is None:
        session._gesture_timeout_deadline = None
        return
    try:
        bpy.app.timers.unregister(timer)
    except ValueError:
        ...
    session._gesture_timeout_timer = None
    session._gesture_timeout_deadline = None


def schedule_timeout_timer(session: GestureSession, timeout_ms: float, ops=None):
    """Schedule UI timeout. ``timeout_ms <= 0`` means show radial UI immediately.

    Avoid unregister/register on every MOUSEMOVE: bump a deadline and let the
    existing timer callback reschedule itself.
    """
    if session.phase.shows_radial_ui:
        cancel_timeout_timer(session)
        return
    timeout = timeout_ms / 1000
    if timeout <= 0:
        cancel_timeout_timer(session)
        _promote_ui_visible(session, ops)
        return

    session._gesture_timeout_deadline = time.time() + timeout
    if session._gesture_timeout_timer is not None:
        return

    def _on_timeout(*_args):
        try:
            if session.phase.shows_radial_ui:
                session._gesture_timeout_timer = None
                session._gesture_timeout_deadline = None
                return None
            deadline = getattr(session, '_gesture_timeout_deadline', None)
            if deadline is None:
                session._gesture_timeout_timer = None
                return None
            remaining = deadline - time.time()
            if remaining > 0.01:
                return remaining
            session._gesture_timeout_timer = None
            session._gesture_timeout_deadline = None
            _promote_ui_visible(session, ops)
        except (AttributeError, ReferenceError):
            session._gesture_timeout_timer = None
            session._gesture_timeout_deadline = None
        return None

    session._gesture_timeout_timer = _on_timeout
    bpy.app.timers.register(_on_timeout, first_interval=timeout)


def _promote_ui_visible(session: GestureSession, ops=None) -> bool:
    """IDLE/TRACKING → UI_VISIBLE, seed trajectory, optional snapshot refresh, redraw."""
    if not session.advance_to_ui_visible():
        return False
    ensure_trajectory_seed(session)
    if ops is not None:
        try:
            refresh_snapshot(session, ops)
            update_extension_hover(session, ops)
        except (AttributeError, ReferenceError, TypeError, RuntimeError):
            ...
    tag_redraw_gesture_screen(session)
    return True


def maybe_promote_phase_on_timeout(session: GestureSession, timeout_ms: float, ops=None) -> bool:
    """Promote to UI_VISIBLE when idle timeout elapsed (or timeout disabled)."""
    if session.phase.shows_radial_ui:
        return False
    timeout_s = timeout_ms / 1000
    if timeout_s <= 0:
        return _promote_ui_visible(session, ops)
    if (time.time() - session.last_mouse_mouse_time) > timeout_s:
        return _promote_ui_visible(session, ops)
    return False


def extension_rollback(session: GestureSession):
    """Pop extension hover stack when mouse leaves panels."""
    extension_hover = session.extension_hover
    while len(extension_hover):
        last = extension_hover[-1]
        hover_len = len(extension_hover)
        if not last.extension_by_child_is_hover and not last.mouse_is_in_extension_area:
            is_vertical_outside = last.mouse_is_in_extension_vertical_outside_area
            is_right_outside = last.mouse_is_in_extension_right_outside_area
            if (is_vertical_outside or is_right_outside) and hover_len > 1:
                return
            extension_hover.pop()
        else:
            return


def update_extension_hover(session: GestureSession, ops):
    """Sync extension_hover from hit areas before execute / between events."""
    if not session.phase.shows_radial_ui:
        session.extension_hover.clear()
        return

    for el in session.extension_hover:
        el.ops = ops
    ext = session.snapshot.extension_element
    if ext is not None:
        ext.ops = ops

    extension_rollback(session)

    if ext is None:
        return

    if ext not in session.extension_hover:
        session.extension_hover.insert(0, ext)

    guard = 0
    while session.extension_hover and guard < 16:
        guard += 1
        last = session.extension_hover[-1]
        last.ops = ops
        found = None
        for item in getattr(last, 'extension_items', []):
            item.ops = ops
            if item.is_child_gesture and item.extension_by_child_is_hover:
                found = item
                break
        if found is not None and found not in session.extension_hover:
            session.extension_hover.append(found)
            continue
        break


def check_return_previous(session: GestureSession, return_distance: float, operator_gesture, ops=None):
    mouse = session.snapshot.mouse_window
    point, index, distance = session.trajectory_tree.find_nearest(mouse)
    if point is None or index < 0:
        return False
    points_kd_tree = session.trajectory_tree
    # Never pop the only remaining root anchor.
    if len(points_kd_tree) <= 1:
        return False
    if (distance < return_distance) and (index + 1 != len(points_kd_tree.child_element)):
        points_kd_tree.remove(index)
        last = points_kd_tree.last_point
        if last is not None:
            session._gesture_circle_center = last.copy()
        invalidate_derived_caches(session, operator_gesture, force=True, ops=ops)
        return True
    return False


def refresh_snapshot(session: GestureSession, ops) -> InputSnapshot:
    """Compute InputSnapshot once per event (or after trajectory change)."""
    event = session.event
    mouse = Vector((event.mouse_x, event.mouse_y)) if event is not None else Vector((0.0, 0.0))
    tree = session.trajectory_tree
    last_point = tree.last_point
    screen_ok = False
    try:
        screen_ok = bpy.context.screen == session.screen
    except (AttributeError, ReferenceError):
        ...
    is_draw_gpu = last_point is not None and screen_ok

    pref = ops.pref
    gp = pref.gesture_property
    scale = bpy.context.preferences.view.ui_scale

    angle = compute_angle(last_point, mouse) if is_draw_gpu else None
    angle_unsigned = compute_angle_unsigned(angle) if is_draw_gpu else None
    distance = (last_point - mouse).magnitude if is_draw_gpu and last_point is not None else 0.0

    maybe_promote_phase_on_timeout(session, gp.timeout, ops)
    ui_visible = session.phase.shows_radial_ui

    zone = threshold_zone_from_distance(
        distance,
        gp.threshold * scale,
        gp.threshold_confirm * scale,
    )

    operator_gesture = ops.operator_gesture
    raw_items = raw_direction_items_dict(session, operator_gesture)
    direction_items = get_direction_items(session, operator_gesture, is_draw_gpu=is_draw_gpu)
    extension_element = direction_items.get("9")

    extension_offset_distance = 0.0
    if extension_element and is_draw_gpu:
        offset_position = getattr(extension_element, "extension_offset_start_position", None)
        from ..utils.region_mouse import find_window_region
        region = find_window_region(session.area) or getattr(bpy.context, 'region', None)
        if offset_position is not None and last_point is not None and region is not None:
            last_region = Vector((last_point.x - region.x, last_point.y - region.y))
            extension_offset_distance = (last_region - offset_position).magnitude

    is_beyond_extension_offset = distance > extension_offset_distance
    is_have_extension_item = ui_visible and "9" in raw_items

    direction = (
        compute_direction_from_angle(
            angle_unsigned,
            is_have_extension_item=is_have_extension_item,
            is_beyond_extension_offset=is_beyond_extension_offset,
            raw_items=raw_items,
            extension_hover=session.extension_hover,
        ) if is_draw_gpu else None
    )

    direction_element = (
        direction_items.get(str(direction)) if direction is not None else None
    )
    is_access_child = (
        zone.is_confirm
        and direction_element is not None
        and direction_element.is_child_gesture
    )

    snap = InputSnapshot(
        mouse_window=mouse,
        angle=angle,
        angle_unsigned=angle_unsigned,
        direction=direction,
        distance=distance,
        threshold_zone=zone,
        is_beyond_extension_offset=is_beyond_extension_offset,
        extension_offset_distance=extension_offset_distance,
        is_draw_gpu=is_draw_gpu,
        is_access_child_gesture=is_access_child,
        is_have_extension_item=is_have_extension_item,
        direction_element=direction_element,
        direction_items=direction_items,
        extension_element=extension_element,
    )
    session.snapshot = snap
    return snap


class GestureInputProcessor:
    """Process modal events into GestureSession updates. Returns visual_dirty."""

    def on_event(self, session: GestureSession, ops, event) -> bool:
        """Update session from *event*. Returns whether a redraw is needed."""
        session.event = event
        visual_dirty = False
        moved = False
        if event.type == "MOUSEMOVE":
            session.move_count += 1
            session.last_mouse_mouse_time = time.time()
            schedule_timeout_timer(session, ops.pref.gesture_property.timeout, ops)
            emp = Vector((event.mouse_x, event.mouse_y))
            if _mouse_moved_enough(emp, session._last_trajectory_mouse):
                moved = True
                session._last_trajectory_mouse = emp.copy()
                session.advance_to_tracking()
            else:
                # Sub-pixel jitter: bump timeout only, skip snapshot/redraw work.
                return False

        session.event_count += 1

        prev = session.snapshot
        prev_direction = prev.direction
        prev_distance = prev.distance
        prev_zone = prev.threshold_zone
        prev_phase = session.phase
        refresh_snapshot(session, ops)
        snap = session.snapshot

        snap_changed = (
            snap.direction != prev_direction
            or snap.threshold_zone is not prev_zone
            or abs(snap.distance - prev_distance) >= 1.0
            or session.phase is not prev_phase
        )

        if not moved:
            if snap_changed:
                visual_dirty = True
            if session.phase.shows_radial_ui:
                before = list(session.extension_hover)
                update_extension_hover(session, ops)
                if session.extension_hover != before:
                    visual_dirty = True
                    refresh_snapshot(session, ops)
            return visual_dirty

        # Significant mouse move: trail / child enter / hover updates.
        visual_dirty = True
        emp = session.snapshot.mouse_window
        operator_gesture = ops.operator_gesture

        if session.event_count > 2:
            snap = session.snapshot
            if session.phase.records_mouse_trail:
                if not len(session.trajectory_mouse_move) or session.trajectory_mouse_move[-1] != emp:
                    session.trajectory_mouse_move.append(emp)
                    session.trajectory_mouse_move_time.append(time.time())

            if not len(session.trajectory_tree):
                session.trajectory_tree.append(None, emp)
                if session._gesture_circle_center is None:
                    session._gesture_circle_center = emp.copy()
                refresh_snapshot(session, ops)
                snap = session.snapshot

            # While browsing extension flyouts, do not enter a radial child
            # gesture — that would clear extension_hover and collapse nesting.
            in_extension_ui = bool(getattr(ops, "mouse_is_in_extension_any_area", False))
            if (
                    snap.is_access_child_gesture
                    and snap.direction_element is not None
                    and not in_extension_ui
            ):
                de = snap.direction_element
                if snap.is_have_extension_item and de.direction == "7":
                    # Legacy gate: enter bottom child only after timeout while
                    # still inside extension offset (rarely true on the same
                    # MOUSEMOVE that just refreshed last_mouse_mouse_time).
                    last_timeout = (time.time() - session.last_mouse_mouse_time) > (
                        ops.pref.gesture_property.timeout / 1000
                    )
                    if last_timeout and not snap.is_beyond_extension_offset:
                        session.trajectory_tree.append(de, emp)
                        session._gesture_circle_center = emp.copy()
                        invalidate_derived_caches(session, operator_gesture, ops=ops)
                        session.extension_hover.clear()
                        refresh_snapshot(session, ops)
                        snap = session.snapshot
                else:
                    session.trajectory_tree.append(de, emp)
                    session._gesture_circle_center = emp.copy()
                    invalidate_derived_caches(session, operator_gesture, ops=ops)
                    session.extension_hover.clear()
                    refresh_snapshot(session, ops)
                    snap = session.snapshot

            if session.phase.shows_radial_ui:
                scale = bpy.context.preferences.view.ui_scale
                return_distance = ops.gesture_property.return_distance * scale
                if check_return_previous(session, return_distance, operator_gesture, ops=ops):
                    session.extension_hover.clear()
                    refresh_snapshot(session, ops)

            before_hover = list(session.extension_hover)
            update_extension_hover(session, ops)
            if session.extension_hover != before_hover:
                refresh_snapshot(session, ops)

        return visual_dirty
