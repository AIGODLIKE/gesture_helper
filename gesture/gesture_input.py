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
    """Direction items memoized per input event.

    Poll expressions read live context, so results must not outlive one modal
    event; ``event_count`` bumps on every event, and the context id changes when
    the trajectory enters/leaves a child level. Within one event the condition
    tree is walked at most once.

    Values are mapped through the session proxy pool: the walk yields fresh
    PropertyGroup proxies every time, but GPU draw stamps hit boxes as Python
    attributes — identity must stay stable across events for input to see them.
    """
    if not is_draw_gpu:
        return raw_direction_items_dict(session, operator_gesture)
    from ..utils.public_cache import PublicCache
    key = (
        direction_items_context_id(session, operator_gesture),
        PublicCache.__derived_generation__,
        session.event_count,
    )
    memo = session._direction_items_memo
    if memo is not None and memo[0] == key:
        return memo[1]
    raw = raw_direction_items_dict(session, operator_gesture)
    raw = {k: session.canonical_element(v) for k, v in raw.items()}
    session._direction_items_memo = (key, raw)
    return raw


def clear_gesture_item_memos(session: GestureSession, ops=None) -> None:
    """Drop direction/extension item memos (call on gesture exit / reset)."""
    session._direction_items_memo = None
    session._gpu_extension_items_cache = None
    if ops is not None:
        ops._gpu_extension_items_cache = None


def invalidate_derived_caches(session: GestureSession, operator_gesture, *, force=False, ops=None):
    """Clear direction/extension memo only when tree level actually changed."""
    key = direction_items_context_id(session, operator_gesture)
    if not force and session._derived_cache_key == key:
        return
    session._derived_cache_key = key
    clear_gesture_item_memos(session, ops)


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


def cancel_bottom_child_dwell_timer(session: GestureSession):
    timer = getattr(session, "_bottom_child_dwell_timer", None)
    if timer is None:
        session._bottom_child_dwell_deadline = None
        return
    try:
        bpy.app.timers.unregister(timer)
    except ValueError:
        ...
    session._bottom_child_dwell_timer = None
    session._bottom_child_dwell_deadline = None


def _enter_child_level(session: GestureSession, ops, element, anchor) -> None:
    """Append *element* as a new gesture level anchored at *anchor*."""
    session.trajectory_tree.append(element, anchor)
    session._gesture_circle_center = anchor.copy()
    invalidate_derived_caches(
        session, getattr(ops, "operator_gesture", None), ops=ops,
    )
    session.extension_hover.clear()
    refresh_snapshot(session, ops)


def _arm_bottom_child_dwell(session: GestureSession, timeout_ms: float, ops) -> None:
    """Wait *timeout_ms* of no re-arm, then enter Down child if still hovering it.

    Only used when radial UI is up and a bottom extension exists — drag-through
    must not dive; stop and wait for the same gesture timeout to enter.
    """
    timeout = max(timeout_ms, 1) / 1000.0
    session._bottom_child_dwell_deadline = time.time() + timeout
    if session._bottom_child_dwell_timer is not None:
        return

    def _on_dwell(*_args):
        try:
            deadline = getattr(session, "_bottom_child_dwell_deadline", None)
            if deadline is None:
                session._bottom_child_dwell_timer = None
                return None
            remaining = deadline - time.time()
            if remaining > 0.01:
                return remaining
            session._bottom_child_dwell_timer = None
            session._bottom_child_dwell_deadline = None
            if getattr(session, "modal_report_done", False):
                return None
            snap = session.snapshot
            de = snap.direction_element
            draw_ctx = getattr(session, "draw_ctx", None)
            in_ext = bool(draw_ctx is not None and draw_ctx.in_extension_ui)
            if (
                    session.phase.shows_radial_ui
                    and snap.is_have_extension_item
                    and snap.is_access_child_gesture
                    and de is not None
                    and de.direction == "7"
                    and not in_ext
            ):
                _enter_child_level(session, ops, de, snap.mouse_window)
                tag_redraw_gesture_screen(session)
        except (AttributeError, ReferenceError):
            session._bottom_child_dwell_timer = None
            session._bottom_child_dwell_deadline = None
        return None

    session._bottom_child_dwell_timer = _on_dwell
    bpy.app.timers.register(_on_dwell, first_interval=timeout)


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
    """IDLE/TRACKING → UI_VISIBLE, seed trajectory, redraw.

    Do not refresh_snapshot here: timer callbacks have a bare context and would
    re-evaluate poll into an empty direction_items, wiping the invoke-time result.
    Modal mouse events recalculate; session memos are cleared on reset/exit.
    """
    if not session.advance_to_ui_visible():
        return False
    ensure_trajectory_seed(session)
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
    from ..element.extension_hit import (
        CHILD_ROW,
        PANEL,
        RIGHT_BAND,
        VERTICAL_TRAVEL,
        hit_test_extension,
    )

    extension_hover = session.extension_hover
    while len(extension_hover):
        last = extension_hover[-1]
        hover_len = len(extension_hover)
        flags = hit_test_extension(last)
        if not (flags & (CHILD_ROW | PANEL)):
            # Stay on stack while traveling vertically/right between nested panels.
            if (flags & (VERTICAL_TRAVEL | RIGHT_BAND)) and hover_len > 1:
                return
            extension_hover.pop()
        else:
            return


def update_extension_hover(session: GestureSession, ops):
    """Sync extension_hover from hit areas before execute / between events."""
    if not session.phase.shows_radial_ui:
        session.extension_hover.clear()
        from .draw_frame_context import refresh_draw_ctx_extension_flag
        refresh_draw_ctx_extension_flag(session, ops)
        return

    for el in session.extension_hover:
        el.ops = ops
    ext = session.snapshot.extension_element
    if ext is not None:
        ext.ops = ops

    extension_rollback(session)

    if ext is not None and ext not in session.extension_hover:
        session.extension_hover.insert(0, ext)

    # Inline layout panels are always painted in their direction slot.  Add a
    # layout to the hover stack only when the pointer is actually over its
    # panel/leaf, so the panel blocks radial confirmation without behaving like
    # a child-gesture entry.
    from ..element.extension_hit import CHILD_ROW, PANEL, hit_test_extension
    if not any(getattr(item, 'is_layout_container', False) for item in session.extension_hover):
        for candidate in session.snapshot.direction_items.values():
            if not candidate.is_layout_container:
                continue
            candidate.ops = ops
            if hit_test_extension(candidate, ops) & (PANEL | CHILD_ROW):
                session.extension_hover.append(candidate)
                break

    if not session.extension_hover:
        from .draw_frame_context import refresh_draw_ctx_extension_flag
        refresh_draw_ctx_extension_flag(session, ops)
        return

    guard = 0
    while session.extension_hover and guard < 16:
        guard += 1
        last = session.extension_hover[-1]
        last.ops = ops
        if last.is_layout_container:
            items = last.panel_leaf_items
        else:
            items = getattr(last, 'extension_items', [])
        found = None
        for item in items:
            item.ops = ops
            if item.is_child_gesture and item.extension_by_child_is_hover:
                found = item
                break
            if item.is_layout_container:
                flags = hit_test_extension(item, ops)
                if flags & (PANEL | CHILD_ROW):
                    found = item
                    break
        if found is not None and found not in session.extension_hover:
            session.extension_hover.append(found)
            continue
        break

    from .draw_frame_context import refresh_draw_ctx_extension_flag
    refresh_draw_ctx_extension_flag(session, ops)


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
    from .draw_frame_context import refresh_draw_frame_context
    draw_ctx = refresh_draw_frame_context(session, ops)

    angle = compute_angle(last_point, mouse) if is_draw_gpu else None
    angle_unsigned = compute_angle_unsigned(angle) if is_draw_gpu else None
    distance = (last_point - mouse).magnitude if is_draw_gpu and last_point is not None else 0.0

    maybe_promote_phase_on_timeout(session, gp.timeout, ops)
    ui_visible = session.phase.shows_radial_ui

    zone = threshold_zone_from_distance(
        distance,
        draw_ctx.threshold,
        draw_ctx.threshold_confirm,
    )

    operator_gesture = ops.operator_gesture
    direction_items = get_direction_items(session, operator_gesture, is_draw_gpu=is_draw_gpu)
    raw_items = direction_items
    extension_element = direction_items.get("9")

    extension_offset_distance = 0.0
    if extension_element and is_draw_gpu:
        # Only trust the offset anchor when this session's GPU draw stamped it;
        # a value left by a previous gesture would skew direction correction.
        from ..element.extension_hit import layout_is_current
        offset_position = (
            getattr(extension_element, "extension_offset_start_position", None)
            if layout_is_current(extension_element, ops) else None
        )
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

    @staticmethod
    def _hovered_property_row(session: GestureSession, ops):
        """Property leaf currently hovered (panel row or radial direction), or None."""
        if not session.phase.shows_radial_ui:
            return None
        if session.extension_hover:
            last = session.extension_hover[-1]
            if last.is_layout_container:
                items = last.panel_leaf_items
            else:
                items = getattr(last, 'extension_items', []) or []
            for item in items:
                item.ops = ops
                if item.is_property_display and item.extension_by_child_is_hover:
                    return item
            # Browsing a panel: do not fall through to the radial direction.
            from ..element.extension_hit import stack_blocks_radial
            if stack_blocks_radial(session.extension_hover, ops):
                return None

        snap = session.snapshot
        de = snap.direction_element
        if de is not None and de.is_property_display:
            de.ops = ops
            if getattr(de, 'mouse_is_in_area', False) or snap.threshold_zone.is_confirm:
                return de
        return None

    @staticmethod
    def _is_radial_numeric_confirm(session: GestureSession, item) -> bool:
        """True when *item* is the radial INT/FLOAT direction in the confirm zone."""
        if session.extension_hover:
            return False
        snap = session.snapshot
        return (
            snap.direction_element == item
            and snap.threshold_zone.is_confirm
            and item.display_property_type in {'INT', 'FLOAT'}
            and item.display_property_is_editable
        )

    def _handle_property_drag(self, session: GestureSession, ops, event) -> bool | None:
        """LMB / radial confirm drag on INT/FLOAT; click toggle for bool/enum.

        Returns None when the event is not handled here.
        """
        drag = session.property_drag
        if drag is not None:
            element, start_mouse, start_value = drag
            if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                mouse = Vector((event.mouse_x, event.mouse_y))
                delta = element.property_drag_delta(start_mouse, mouse)
                element.apply_property_drag(start_value, delta, precise=event.shift)
                # Remember that the value was actually scrubbed so release can
                # skip launching the post-gesture modal mouse operator.
                if abs(delta) >= 2.0:
                    session._property_drag_moved = True
                return True
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                session.property_drag = None
                if getattr(session, '_property_drag_moved', False):
                    session._suppress_property_execute = True
                session._property_drag_moved = False
                return True
            if event.value == 'PRESS' and event.type in {'RIGHTMOUSE', 'ESC'}:
                element.set_display_property_value(start_value)
                session.property_drag = None
                session._property_drag_moved = False
                return True
            if event.value == 'RELEASE' and event.type == session.invoke_event_type:
                # Gesture key released mid-drag: keep the dragged value and let
                # the normal exit flow run (swallowing it would leave a zombie
                # modal with no exit trigger left). The executor must not fire
                # the row again on this release.
                session.property_drag = None
                if getattr(session, '_property_drag_moved', False):
                    session._suppress_property_execute = True
                session._property_drag_moved = False
                return None
            # Swallow everything else while dragging (keys must not leak).
            return True

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            item = self._hovered_property_row(session, ops)
            if item is None:
                return None
            if not item.display_property_is_editable:
                return True
            prop_type = item.display_property_type
            if prop_type in {'INT', 'FLOAT'}:
                start_value = item.display_property_value
                if start_value is None:
                    return None
                session.property_drag = (
                    item,
                    Vector((event.mouse_x, event.mouse_y)),
                    start_value,
                )
                session._property_drag_moved = False
                return True
            if prop_type in {'BOOLEAN', 'ENUM'}:
                item.toggle_display_property()
                return True

        return None

    def _arm_radial_property_drag(self, session: GestureSession, ops, event) -> None:
        """Start numeric scrubbing after the current event snapshot is ready."""
        if session.property_drag is not None:
            return
        if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            return
        item = self._hovered_property_row(session, ops)
        if item is None or not self._is_radial_numeric_confirm(session, item):
            return
        start_value = item.display_property_value
        if start_value is None:
            return
        session.property_drag = (
            item,
            Vector((event.mouse_x, event.mouse_y)),
            start_value,
        )
        session._property_drag_moved = False

    def _handle_child_navigation(
            self, session: GestureSession, ops, snap, mouse, in_extension_ui: bool,
    ) -> None:
        """Normal gesture child navigation; preview overrides this policy."""
        element = snap.direction_element
        if (
                snap.is_access_child_gesture
                and element is not None
                and not in_extension_ui
        ):
            need_dwell = (
                session.phase.shows_radial_ui
                and snap.is_have_extension_item
                and element.direction == "7"
            )
            if need_dwell:
                _arm_bottom_child_dwell(
                    session, ops.pref.gesture_property.timeout, ops,
                )
            else:
                cancel_bottom_child_dwell_timer(session)
                _enter_child_level(session, ops, element, mouse)
        else:
            cancel_bottom_child_dwell_timer(session)

    def on_event(self, session: GestureSession, ops, event) -> bool:
        """Update session from *event*. Returns whether a redraw is needed."""
        session.event = event
        drag_result = self._handle_property_drag(session, ops, event)
        if drag_result is not None:
            return drag_result
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

        # Arm radial numeric scrubbing only after this event's snapshot is
        # current.  The old implementation inspected the previous snapshot
        # before refresh, so changing direction could lock the next move to a
        # property that was no longer under the cursor.
        self._arm_radial_property_drag(session, ops, event)

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
            draw_ctx = getattr(session, "draw_ctx", None)
            if draw_ctx is not None:
                in_extension_ui = draw_ctx.in_extension_ui
            else:
                in_extension_ui = bool(getattr(ops, "mouse_is_in_extension_any_area", False))
            self._handle_child_navigation(
                session, ops, snap, emp, in_extension_ui,
            )

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
