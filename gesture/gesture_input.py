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

_VISUAL_TRAIL_MIN_DISTANCE_PX = 2.0
_VISUAL_TRAIL_MAX_POINTS = 256



def _mouse_moved_enough(current: Vector, previous: Vector | None, *, min_dist: float = 1.0) -> bool:
    if previous is None:
        return True
    return (current - previous).length >= min_dist


def append_visual_trail_point(session: GestureSession, point: Vector) -> bool:
    """Append a sampled visual trail point without changing gesture semantics.

    The mouse trail is only rendered before the radial UI appears; retaining
    every high-frequency mouse sample makes stroke mesh construction grow
    without bound during a long hold. Keep the semantic trajectory untouched,
    sample the visual trail by distance, and periodically decimate its middle
    while preserving the anchor and newest point.
    """
    points = session.trajectory_mouse_move
    times = session.trajectory_mouse_move_time
    if points:
        try:
            if (point - points[-1]).length < _VISUAL_TRAIL_MIN_DISTANCE_PX:
                return False
        except (AttributeError, TypeError):
            if point == points[-1]:
                return False

    try:
        stored_point = point.copy()
    except AttributeError:
        stored_point = point
    points.append(stored_point)
    times.append(time.time())

    if len(points) > _VISUAL_TRAIL_MAX_POINTS:
        first_point, last_point = points[0], points[-1]
        first_time, last_time = times[0], times[-1]
        middle_points = points[1:-1:2]
        middle_times = times[1:-1:2]
        points[:] = [first_point, *middle_points, last_point]
        times[:] = [first_time, *middle_times, last_time]
    return True


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


def _stable_rna_identity(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


def direction_items_context_id(session: GestureSession, operator_gesture) -> int | None:
    tree = session.trajectory_tree
    last_element = tree.last_element if len(tree) else None
    if last_element is not None:
        return _stable_rna_identity(last_element)
    return _stable_rna_identity(operator_gesture)


def refresh_poll_context_fingerprint(session: GestureSession):
    """Capture the context inputs used by poll expressions for this snapshot.

    Direction/extension walks and element status checks used to key their
    memo by ``event_count``. Cursor motion then invalidated the same poll
    result dozens of times per second even though the Blender context had not
    changed. The fingerprint is refreshed once per input event/snapshot and
    shared by all render-time consumers.
    """
    current = getattr(session, '_poll_context_fingerprint', None)
    serial = getattr(session, '_input_event_serial', 0)
    event_type = getattr(getattr(session, 'event', None), 'type', None)
    if current is not None:
        # A blocking gesture cannot change Blender selection/mode/tool through
        # ordinary cursor motion. Reuse the invoke/non-mouse snapshot so the
        # active-tool lookup does not run on every MOUSEMOVE.
        if event_type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            return current
        if getattr(session, '_poll_context_serial', -1) == serial:
            return current

    from ..utils.gesture_items import poll_context_fingerprint

    try:
        value = poll_context_fingerprint()
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        value = ()
    session._poll_context_fingerprint = value
    session._poll_context_serial = serial
    return value


def _poll_context_key(session: GestureSession):
    value = getattr(session, "_poll_context_fingerprint", None)
    if value is None:
        value = refresh_poll_context_fingerprint(session)
    return value, getattr(session, "_poll_context_revision", 0)


def raw_direction_items_dict(session: GestureSession, operator_gesture) -> dict:
    tree = session.trajectory_tree
    last_element = tree.last_element if len(tree) else None
    if last_element:
        return last_element.gesture_direction_items
    if operator_gesture:
        return operator_gesture.gesture_direction_items
    return {}


def get_direction_items(session: GestureSession, operator_gesture, *, is_draw_gpu: bool) -> dict:
    """Direction items memoized per content/context state.

    Poll expressions read live context, so results must not outlive one modal
    context; the trajectory context id changes when entering/leaving a child
    level and the poll fingerprint changes when Blender context changes.
    Within one content/context state the condition tree is walked at most once.

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
        _poll_context_key(session),
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
    session._gpu_panel_leaf_items_cache = None
    session._element_status_info_cache = None
    session._layout_measure_cache.clear()
    session._layout_measure_cache_key = None
    session._layout_measure_stability.clear()
    session._layout_frame_measure_cache = None
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
    from ..utils.region_mouse import find_window_region

    area = session.area
    if area is not None:
        try:
            region = find_window_region(area)
            if region is not None:
                region.tag_redraw()
            # Never fall back to ``area.tag_redraw()`` here.  That marks the
            # sidebar UI region too, rebuilding the frozen Gesture panels on
            # every mouse move when Blender cannot expose a WINDOW region.
            return
        except ReferenceError:
            ...
    screen = session.screen
    if screen is not None:
        try:
            for a in screen.areas:
                region = find_window_region(a)
                if region is not None:
                    region.tag_redraw()
            return
        except ReferenceError:
            ...
    # A missing WINDOW region is unusual during normal modal dispatch.  It is
    # safer to skip this redraw than to invalidate every area and wake the
    # disabled panel layout while the gesture is still consuming events.


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
                sync_runtime_tooltip(session, ops)
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
    if ops is not None:
        sync_runtime_tooltip(session, ops)
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
        from ..element.extension_hit import panel_hit_items
        items = panel_hit_items(last, ops)
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


def get_runtime_hovered_element(session: GestureSession, ops):
    """Return the visible runtime item targeted for annotation or clicking."""
    for container in reversed(tuple(session.extension_hover)):
        container.ops = ops
        from ..element.extension_hit import panel_hit_items
        items = panel_hit_items(container, ops)
        for item in items:
            item.ops = ops
            if item.extension_by_child_is_hover:
                return item

    if session.extension_hover:
        from ..element.extension_hit import stack_blocks_radial
        if stack_blocks_radial(session.extension_hover, ops):
            return None

    snap = session.snapshot
    element = snap.direction_element
    if element is not None and snap.threshold_zone.is_beyond:
        element.ops = ops
        return element
    return None


def get_runtime_action_element(session: GestureSession, ops):
    """Resolve a selected layout container to the leaf it actually executes."""
    element = get_runtime_hovered_element(session, ops)
    if element is not None and element.is_layout_container:
        element = element.main_element
    if element is not None:
        element.ops = ops
    return element


def sync_runtime_tooltip(session: GestureSession, ops) -> bool:
    """Update delayed tooltip ownership after input has resolved the hover."""
    from .runtime_tooltip import sync_hover_tooltip

    target = (
        get_runtime_action_element(session, ops)
        if (
            session.phase.shows_radial_ui
            and getattr(session, 'property_drag', None) is None
        )
        else None
    )
    state = session.tooltip_state
    changed = sync_hover_tooltip(
        state,
        target,
        delay_ms=getattr(
            ops.pref.gesture_property,
            'hover_tooltip_delay',
            300,
        ),
        redraw=lambda: tag_redraw_gesture_screen(session),
    )
    if not changed:
        return False
    if target is not None:
        from ..element.element_tooltip import build_runtime_tooltip

        state.tooltip = build_runtime_tooltip(
            target,
            preview_read_only=bool(getattr(ops, 'preview_read_only', False)),
        )
        if state.tooltip is None:
            sync_hover_tooltip(
                state,
                None,
                delay_ms=0,
                redraw=lambda: tag_redraw_gesture_screen(session),
            )
    return True


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
    refresh_poll_context_fingerprint(session)
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
    if ui_visible and is_draw_gpu:
        # Once the overlay has been drawn, its current hit rectangles are the
        # source of truth. Manual/automatic offsets can move a visible button
        # into a different angular sector; falling back to the angle keeps the
        # original drag gesture behavior between buttons and before first draw.
        from ..element.extension_hit import (
            find_radial_root_hit,
            resolve_radial_root_selection,
        )
        root_hit = find_radial_root_hit(
            direction_items,
            ops,
            mouse=draw_ctx.mouse_region,
            preferred_direction=direction,
        )
        direction, direction_element = resolve_radial_root_selection(
            direction, direction_element, root_hit,
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
    def _begin_property_drag_interaction(session: GestureSession, event) -> None:
        """Hide the pointer and lock hover to the pressed numeric surface."""
        draw_ctx = getattr(session, 'draw_ctx', None)
        hover_mouse = getattr(draw_ctx, 'mouse_region', None)
        if hover_mouse is None:
            try:
                hover_mouse = (event.mouse_region_x, event.mouse_region_y)
            except AttributeError:
                hover_mouse = None
        session._property_drag_hover_mouse = hover_mouse

        window = getattr(bpy.context, 'window', None)
        session._property_drag_cursor_window = None
        session._property_drag_cursor_hidden = False
        if window is None:
            return
        try:
            window.cursor_modal_set('NONE')
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return
        session._property_drag_cursor_window = window
        session._property_drag_cursor_hidden = True

    @staticmethod
    def _end_property_drag_interaction(session: GestureSession) -> None:
        """Restore the pre-drag cursor and release the locked hover exactly once."""
        window = getattr(session, '_property_drag_cursor_window', None)
        cursor_hidden = bool(
            getattr(session, '_property_drag_cursor_hidden', False)
        )
        session._property_drag_cursor_window = None
        session._property_drag_cursor_hidden = False
        session._property_drag_hover_mouse = None
        if not cursor_hidden or window is None:
            return
        try:
            window.cursor_modal_restore()
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            pass

    @staticmethod
    def _update_ui_press(session: GestureSession, ops, event) -> bool:
        """Track left-button feedback without changing gesture execution."""
        current = getattr(session, '_ui_pressed_element', None)
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if current is None:
                return False
            session._ui_pressed_element = None
            return True
        if event.value == 'PRESS' and event.type in {'ESC', 'RIGHTMOUSE'}:
            if current is None:
                return False
            session._ui_pressed_element = None
            return True
        if event.type != 'LEFTMOUSE' or event.value != 'PRESS':
            return False
        element = get_runtime_action_element(session, ops)
        if element is current:
            return False
        session._ui_pressed_element = element
        return current is not element

    @staticmethod
    def _hovered_property_row(session: GestureSession, ops):
        """Property leaf currently hovered (panel row or radial direction), or None."""
        if not session.phase.shows_radial_ui:
            return None
        if session.extension_hover:
            last = session.extension_hover[-1]
            from ..element.extension_hit import panel_hit_items
            items = panel_hit_items(last, ops)
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
    def _handle_repair_click(session: GestureSession, ops, event) -> bool:
        """Turn an explicit click on a broken item into an editor handoff."""
        if (
                session.property_drag is not None
                or event.type != 'LEFTMOUSE'
                or event.value != 'PRESS'
        ):
            return False
        element = get_runtime_action_element(session, ops)
        if element is None:
            return False
        from ..element.extension_hit import _mouse_for, point_in_rect
        mouse = _mouse_for(element, ops)
        if not (
                point_in_rect(mouse, getattr(element, 'item_draw_area', None))
                or point_in_rect(
                    mouse,
                    getattr(element, 'extension_by_child_draw_area', None),
                )
        ):
            return False
        from ..element.element_status import get_element_status_info
        info = get_element_status_info(element, ops=ops)
        if not info.status.is_error:
            return False
        session.repair_element = element
        session._event_consumed = True
        return True

    def _handle_property_wheel(self, session: GestureSession, ops, event) -> bool | None:
        """Adjust a hovered scalar property by one mouse-wheel notch."""
        if event.value != 'PRESS' or event.type not in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return None
        item = self._hovered_property_row(session, ops)
        if item is None or item.display_property_type not in {'INT', 'FLOAT'}:
            return None
        if not item.display_property_is_editable:
            return None

        session._event_consumed = True
        # The release of the gesture key must not launch a second numeric drag
        # after this wheel interaction has already changed the value.
        session._suppress_property_execute = True
        direction = 1 if event.type == 'WHEELUPMOUSE' else -1
        changed = item.apply_property_wheel(
            direction,
            precise=getattr(event, 'shift', False),
        )
        if changed:
            session._poll_context_revision = (
                getattr(session, '_poll_context_revision', 0) + 1
            )
            # Conditions may depend on the value being adjusted.
            refresh_snapshot(session, ops)
        return changed

    def _handle_property_reset(
            self, session: GestureSession, ops, event,
    ) -> bool | None:
        """Reset a hovered scalar number or boolean when Backspace is pressed."""
        if event.value != 'PRESS' or event.type != 'BACK_SPACE':
            return None
        drag = session.property_drag
        item = (
            drag[0]
            if drag is not None
            else self._hovered_property_row(session, ops)
        )
        if (
                item is None
                or item.display_property_type not in {'BOOLEAN', 'INT', 'FLOAT'}
        ):
            return None
        if not item.display_property_is_editable:
            return None

        session._event_consumed = True
        # The invoking gesture key may still be held. Its later release must
        # not toggle the boolean or launch another numeric edit after reset.
        session._suppress_property_execute = True
        if drag is not None:
            self._end_property_drag_interaction(session)
            session.property_drag = None
            session._numeric_pressed_element = None
            session._numeric_pressed_part = None
            session._property_drag_moved = False

        changed = item.reset_display_property_to_default()
        if changed:
            session._poll_context_revision = (
                getattr(session, '_poll_context_revision', 0) + 1
            )
            refresh_snapshot(session, ops)
        return changed

    def cancel_property_drag(
            self,
            session: GestureSession,
            ops=None,
            *,
            refresh: bool = False,
    ) -> bool:
        """Restore and clear an active property scrub exactly once."""
        drag = session.property_drag
        if drag is None:
            self._end_property_drag_interaction(session)
            return False
        element, _start_mouse, start_value = drag
        self._end_property_drag_interaction(session)
        session.property_drag = None
        session._numeric_pressed_element = None
        session._numeric_pressed_part = None
        session._property_drag_moved = False
        changed = element.set_display_property_value(start_value)
        if changed:
            session._poll_context_revision = (
                getattr(session, '_poll_context_revision', 0) + 1
            )
            if refresh and ops is not None:
                refresh_snapshot(session, ops)
        return changed

    def _handle_property_drag(self, session: GestureSession, ops, event) -> bool | None:
        """LMB drag on INT/FLOAT; click toggle for bool/enum.

        Returns None when the event is not handled here.
        """
        reset_result = self._handle_property_reset(session, ops, event)
        if reset_result is not None:
            return reset_result

        if (
                session.property_drag is None
                and getattr(session, '_numeric_pressed_element', None) is not None
        ):
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                session._numeric_pressed_element = None
                session._numeric_pressed_part = None
                session._event_consumed = True
                return False
            if event.value == 'PRESS' and event.type in {'RIGHTMOUSE', 'ESC'}:
                session._numeric_pressed_element = None
                session._numeric_pressed_part = None

        drag = session.property_drag
        if drag is not None:
            element, start_mouse, start_value = drag
            if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                session._event_consumed = True
                mouse = Vector((event.mouse_x, event.mouse_y))
                delta = element.property_drag_delta(start_mouse, mouse)
                changed, applied_delta = element.apply_property_drag(
                    start_value,
                    delta,
                    precise=event.shift,
                    return_applied_delta=True,
                )
                if applied_delta != delta:
                    element.rebase_property_drag_start(
                        start_mouse, mouse, applied_delta,
                    )
                if changed:
                    session._poll_context_revision = (
                        getattr(session, '_poll_context_revision', 0) + 1
                    )
                    # Do not refresh spatial selection during an active scrub.
                    # The live property renderer sees the new RNA value, while
                    # conditions and hover are resolved again after release.
                # Remember that the value was actually scrubbed so release can
                # skip launching the post-gesture modal mouse operator.
                if abs(delta) >= 2.0:
                    session._property_drag_moved = True
                # The event remains consumed even when integer rounding leaves
                # the value unchanged; only a real value change redraws.
                return changed
            if event.value == 'RELEASE' and event.type == session.invoke_event_type:
                # The invoke key may itself be LMB.  Handle its release before
                # the generic LMB drag release so the modal exit path still
                # receives the event instead of leaving a zombie gesture.
                # Keep the dragged value and suppress a second property execute.
                self._end_property_drag_interaction(session)
                session.property_drag = None
                session._numeric_pressed_element = None
                session._numeric_pressed_part = None
                if getattr(session, '_property_drag_moved', False):
                    session._suppress_property_execute = True
                session._property_drag_moved = False
                return None
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                session._event_consumed = True
                self._end_property_drag_interaction(session)
                session.property_drag = None
                session._numeric_pressed_element = None
                session._numeric_pressed_part = None
                if getattr(session, '_property_drag_moved', False):
                    session._suppress_property_execute = True
                session._property_drag_moved = False
                return False
            if event.value == 'PRESS' and event.type in {'RIGHTMOUSE', 'ESC'}:
                session._event_consumed = True
                return self.cancel_property_drag(
                    session,
                    ops,
                    refresh=True,
                )
            # Swallow everything else while dragging (keys must not leak).
            session._event_consumed = True
            return False

        wheel_result = self._handle_property_wheel(session, ops, event)
        if wheel_result is not None:
            return wheel_result

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            item = self._hovered_property_row(session, ops)
            if item is None:
                return None
            if not item.display_property_is_editable:
                session._event_consumed = True
                return False
            prop_type = item.display_property_type
            if prop_type in {'INT', 'FLOAT'}:
                from ..element.extension_hit import numeric_property_arrow_direction

                arrow_direction = numeric_property_arrow_direction(item, ops)
                if arrow_direction:
                    from ..utils.number_arrows import (
                        NUMBER_PART_DECREMENT,
                        NUMBER_PART_INCREMENT,
                    )

                    session._event_consumed = True
                    session._suppress_property_execute = True
                    session._numeric_pressed_element = item
                    session._numeric_pressed_part = (
                        NUMBER_PART_INCREMENT
                        if arrow_direction > 0
                        else NUMBER_PART_DECREMENT
                    )
                    changed = item.apply_property_wheel(
                        arrow_direction,
                        precise=getattr(event, 'shift', False),
                    )
                    if changed:
                        session._poll_context_revision = (
                            getattr(session, '_poll_context_revision', 0) + 1
                        )
                        refresh_snapshot(session, ops)
                    # Pressed feedback is a visual change even when the RNA
                    # value is already clamped at its hard bound.
                    return True
                start_value = item.display_property_value
                if start_value is None:
                    return None
                session._event_consumed = True
                session.property_drag = (
                    item,
                    Vector((event.mouse_x, event.mouse_y)),
                    start_value,
                )
                from ..utils.number_arrows import NUMBER_PART_VALUE

                session._numeric_pressed_element = item
                session._numeric_pressed_part = NUMBER_PART_VALUE
                session._property_drag_moved = False
                self._begin_property_drag_interaction(session, event)
                return True
            if prop_type in {'BOOLEAN', 'ENUM'}:
                session._event_consumed = True
                changed = item.toggle_display_property()
                if changed:
                    session._poll_context_revision = (
                        getattr(session, '_poll_context_revision', 0) + 1
                    )
                    refresh_snapshot(session, ops)
                return changed

        return None

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
        def finish(result: bool) -> bool:
            return bool(sync_runtime_tooltip(session, ops) or result)

        session.event = event
        session._input_event_serial = getattr(session, '_input_event_serial', 0) + 1
        session._event_consumed = False
        press_dirty = self._update_ui_press(session, ops, event)
        # Poll context can change without a meaningful mouse move (for
        # example, an object/mode switch while a gesture is held). Capture it
        # before the sub-pixel fast path so the next draw invalidates only the
        # affected content caches.
        refresh_poll_context_fingerprint(session)
        if self._handle_repair_click(session, ops, event):
            return finish(True)
        drag_result = self._handle_property_drag(session, ops, event)
        if drag_result is not None:
            return finish(bool(drag_result or press_dirty))
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
                return finish(False)

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
            return finish(bool(visual_dirty or press_dirty))

        # Significant mouse move: trail / child enter / hover updates.
        visual_dirty = True
        emp = session.snapshot.mouse_window
        operator_gesture = ops.operator_gesture

        if session.event_count > 2:
            snap = session.snapshot
            if session.phase.records_mouse_trail:
                append_visual_trail_point(session, emp)

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

        return finish(bool(visual_dirty or press_dirty))
