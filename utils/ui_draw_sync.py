"""Debounce RNA writes that must not run inside Panel/UIList draw()."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Callable, Optional

import bpy

_SYNC_DEBOUNCE_SEC = 0.15
_pending: dict[str, Callable[[], None]] = {}

_MSG_GESTURE = "Paused: gesture"
_MSG_ANIMATION = "Paused: playback"
_MSG_OPERATOR = "Paused: operator"

# One-shot poller: after a modal skip, refresh UI once the modal ends.
_modal_ui_refresh_fn: Optional[Callable[[], Optional[float]]] = None
# Coalesce modal checks across a normal UI redraw burst.
_PANEL_IDLE_CACHE_SEC = 0.12
# Playback and modal state is stable for the duration of a UI redraw burst.
# Re-reading ``Screen.is_animation_playing`` for every panel header/body is
# cheap compared with a full layout, but it still adds up when Blender sends
# several notifier passes per frame.  Keep the active state for a short window
# and let the next expiry observe playback stopping promptly.
_PANEL_ACTIVE_CACHE_SEC = 0.12
# (area pointer, screen pointer) -> (source, message, expiry).
# ``expiry`` is ``None`` for active playback; the playback handlers invalidate
# that entry exactly at start/stop, so the hot path does not call the clock.
# Paused states are stable until their lifecycle says otherwise; the short
# idle entry only coalesces the several poll/header/body calls in one UI pass.
_panel_pause_cache: dict[
    tuple[int, int],
    tuple[str, Optional[str], Optional[float]],
] = {}
# Area pointer -> gesture session.  A visible Element UIList asks for the same
# frozen selection/status session once per row; cache the area lookup for the
# current pause lifecycle instead of walking the draw-instance registries.
_gesture_panel_session_cache: dict[int, object] = {}
_frozen_ui_selection: dict[tuple[int, int], tuple[object, object]] = {}


@dataclass(slots=True)
class _PanelContentSnapshot:
    active_gesture: object = None
    active_element: object = None
    preview_active: bool = False
    preview_scope: str = ''
    status_infos: dict[int, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _OwnedPanelFreeze:
    owner: object
    message: str
    area_key: int
    snapshot: _PanelContentSnapshot


# Area pointer -> semantic snapshot. Playback rebuilds the full disabled layout
# once at entry; this pins its inputs if Blender later requests another UI
# refresh without re-running selection/status discovery.
_playback_panel_snapshots: dict[int, _PanelContentSnapshot] = {}
# Area pointer -> snapshot retained while a regular window modal is running.
_modal_panel_snapshots: dict[int, _PanelContentSnapshot] = {}
# Add-on-owned modal drags explicitly freeze the existing panel layout.  They
# are tracked here because Blender does not expose a cheap modal-start signal
# to Panel.draw, and scanning every window's modal stack on every row is costly.
_panel_layout_freezes: dict[int, _OwnedPanelFreeze] = {}


def _rna_pointer(value) -> int:
    if value is None:
        return 0
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


def _panel_context_key(context) -> tuple[int, int]:
    return (
        _rna_pointer(getattr(context, 'area', None)),
        _rna_pointer(getattr(context, 'screen', None)),
    )


def _capture_panel_content() -> _PanelContentSnapshot:
    snapshot = _PanelContentSnapshot()
    try:
        from .pref import get_pref
        pref = get_pref()
        snapshot.active_gesture = pref.active_gesture
        snapshot.active_element = pref.active_element
    except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError, TypeError):
        pass
    try:
        from .session_state import SessionState
        snapshot.preview_active = bool(SessionState.gesture_preview_active)
        snapshot.preview_scope = str(SessionState.gesture_preview_scope or '')
    except (AttributeError, ImportError, ReferenceError, RuntimeError, TypeError):
        pass
    return snapshot


def _playback_panel_snapshot(context, *, capture: bool = False):
    area = getattr(context, 'area', None)
    area_key = _rna_pointer(area)
    snapshot = _playback_panel_snapshots.get(area_key)
    if snapshot is not None or not capture:
        return snapshot
    snapshot = _capture_panel_content()
    _playback_panel_snapshots[area_key] = snapshot
    return snapshot


def _modal_panel_snapshot(context, *, capture: bool = False):
    area_key = _rna_pointer(getattr(context, 'area', None))
    snapshot = _modal_panel_snapshots.get(area_key)
    if snapshot is not None or not capture:
        return snapshot
    snapshot = _capture_panel_content()
    _modal_panel_snapshots[area_key] = snapshot
    return snapshot


def invalidate_modal_panel_state() -> None:
    _modal_panel_snapshots.clear()
    invalidate_panel_pause_cache()


def invalidate_panel_pause_cache() -> None:
    """Invalidate pause decisions without discarding playback semantics.

    Gesture, explicit-drag, and generic-modal transitions can overlap active
    playback. They may change which pause source wins, but they must not make
    another area recapture selection or preview content mid-playback.
    """
    global _panel_pause_cache
    if isinstance(_panel_pause_cache, dict):
        _panel_pause_cache.clear()
    else:  # Defensive for live module reloads from older builds.
        _panel_pause_cache = {}
    _gesture_panel_session_cache.clear()


def invalidate_playback_panel_state() -> None:
    """Discard playback snapshots only at a playback lifecycle boundary."""
    _playback_panel_snapshots.clear()
    invalidate_panel_pause_cache()


def release_gesture_panel_state(session) -> None:
    """Release one gesture's frozen UI state after its modal lifecycle ends."""
    if session is None:
        return
    selection_key = getattr(session, "_frozen_ui_selection_key", None)
    if selection_key is not None:
        clear_frozen_ui_selection(None, selection_key=selection_key)
        session._frozen_ui_selection_key = None
    else:
        # Compatibility with sessions created before a live module reload.
        gesture = getattr(session, "_frozen_active_gesture", None)
        area = getattr(session, "area", None)
        clear_frozen_ui_selection(gesture, area=area)
    invalidate_panel_pause_cache()


def _cached_panel_pause_entry(
        context,
        *,
        refresh_animation: bool = True,
        cache_key: tuple[int, int] | None = None,
):
    """Return a still-valid pause entry without repeating state discovery."""
    if not isinstance(_panel_pause_cache, dict):
        return None
    if cache_key is None:
        cache_key = _panel_context_key(context)
    cached = _panel_pause_cache.get(cache_key)
    if cached is None:
        return None

    source, message, expiry = cached
    if source in {'GESTURE', 'EXPLICIT'}:
        return cached
    if source == 'ANIMATION':
        if expiry is None:
            return cached
        now = time.monotonic()
        if now < expiry:
            return cached
        if not refresh_animation:
            # The caller only needs the cached source (for example, to
            # distinguish a gesture freeze from playback).  Let the next full
            # pause lookup validate the finite scrubbing entry instead of
            # briefly exposing an enabled layout mid-scrub.
            return cached
        if refresh_animation and _is_animation_busy(context):
            refreshed = (
                source,
                message,
                None if _is_animation_playing(context) else now + _PANEL_ACTIVE_CACHE_SEC,
            )
            _panel_pause_cache[cache_key] = refreshed
            return refreshed
        _panel_pause_cache.pop(cache_key, None)
        _playback_panel_snapshots.pop(cache_key[0], None)
        return None
    if source == 'MODAL':
        if _is_blocking_modal() or _modal_ui_refresh_fn is not None:
            return cached
        _panel_pause_cache.pop(cache_key, None)
        _modal_panel_snapshots.pop(cache_key[0], None)
        return None
    if source == 'IDLE' and time.monotonic() < expiry:
        return cached
    _panel_pause_cache.pop(cache_key, None)
    return None


def begin_panel_layout_freeze(owner, message: str = _MSG_OPERATOR) -> None:
    """Freeze an add-on-owned modal panel without coupling it to input state."""
    owner_key = id(owner)
    area = getattr(owner, '_modal_area', None) or getattr(bpy.context, 'area', None)
    area_key = _rna_pointer(area)
    snapshot = _capture_panel_content()
    # A numeric modal can be handed off from a gesture or started during
    # playback. Preserve the preview row already visible under that freeze;
    # the live preview owner may have been closed before this modal begins.
    previous = _playback_panel_snapshots.get(area_key)
    if previous is not None:
        snapshot.preview_active = previous.preview_active
        snapshot.preview_scope = previous.preview_scope
    else:
        session = get_gesture_modal_session(bpy.context)
        if session is not None:
            snapshot.preview_active = bool(
                getattr(session, '_frozen_preview_active', False)
            )
            snapshot.preview_scope = str(
                getattr(session, '_frozen_preview_scope', '') or ''
            )
    _panel_layout_freezes[owner_key] = _OwnedPanelFreeze(
        owner=owner,
        message=message,
        area_key=area_key,
        snapshot=snapshot,
    )
    invalidate_panel_pause_cache()


def end_panel_layout_freeze(owner) -> None:
    """Release an add-on-owned panel freeze."""
    _panel_layout_freezes.pop(id(owner), None)
    invalidate_panel_pause_cache()


def clear_panel_layout_freezes() -> None:
    """Drop every frozen panel snapshot during add-on teardown."""
    _panel_layout_freezes.clear()
    _frozen_ui_selection.clear()
    _modal_panel_snapshots.clear()
    invalidate_playback_panel_state()


def _explicit_panel_freeze(context=None) -> Optional[_OwnedPanelFreeze]:
    target_area = getattr(context, 'area', None)
    target_key = _rna_pointer(target_area)
    target_type = getattr(target_area, 'type', None)
    for state in tuple(_panel_layout_freezes.values()):
        if (
                context is None
                or target_type == 'PREFERENCES'
                or state.area_key == 0
                or state.area_key == target_key
        ):
            return state
    return None


def _explicit_panel_freeze_message(context=None) -> Optional[str]:
    state = _explicit_panel_freeze(context)
    return state.message if state is not None else None


def _is_real_gesture_instance(instance) -> bool:
    """Return whether *instance* is the executable gesture modal.

    Preview and real gesture draw instances can coexist, and the per-area draw
    registry may replace one with the other.  Identify each registered instance
    directly instead of subtracting a process-wide preview flag from a count.
    Blender exposes operator identifiers in dotted or RNA-style form depending
    on the API surface, so accept both spellings.
    """
    try:
        identifier = str(getattr(instance, "bl_idname", "")).casefold()
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return False
    return identifier in {"wm.gesture_operator", "wm_ot_gesture_operator"}


def is_gesture_modal_active(context=None) -> bool:
    """True while a real gesture modal is running.

    The gesture preview also registers a draw instance, but it must NOT pause
    panel drawing — editing elements while previewing is the whole point.
    """
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        active = GestureGpuDraw.__active_draw_instances__
        finishing = GestureGpuDraw.__finishing_draw_instances__
        if not active and not finishing:
            return False
        target_area = getattr(context, 'area', None)
        target_type = getattr(target_area, 'type', None)
        for instance in (*active.values(), *finishing.values()):
            if not _is_real_gesture_instance(instance):
                continue
            if target_area is None or target_type == 'PREFERENCES':
                return True
            session = getattr(instance, 'session', None)
            owner_area = getattr(session, 'area', None)
            if owner_area is target_area:
                return True
            try:
                if (
                        owner_area is not None
                        and owner_area.as_pointer() == target_area.as_pointer()
                ):
                    return True
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                ...
        return False
    except Exception:
        return False


def is_gesture_panel_frozen(context=None) -> bool:
    """Whether heavy editor panels should keep their last layout disabled.

    This deliberately follows the real gesture lifecycle rather than generic
    modal operators: preview remains editable, while a gesture owns the panel
    freeze until its final dispatch has completed.
    """
    if context is not None:
        cached = _cached_panel_pause_entry(context, refresh_animation=False)
        if cached is not None:
            return cached[0] == 'GESTURE'
    elif isinstance(_panel_pause_cache, dict):
        if any(entry[0] == 'GESTURE' for entry in _panel_pause_cache.values()):
            return True
    return is_gesture_modal_active(context)


def is_panel_layout_frozen(context=None) -> bool:
    """Whether the existing panel layout must remain visible and disabled."""
    if context is not None:
        cached = _cached_panel_pause_entry(context)
        if cached is not None:
            return cached[0] in {'GESTURE', 'EXPLICIT', 'ANIMATION', 'MODAL'}
    elif isinstance(_panel_pause_cache, dict):
        # Finite ANIMATION entries represent timeline scrubbing, which has no
        # playback pre/post handler. Validate an expired entry against the live
        # global context so it cannot freeze schedules forever or retain a
        # stale per-area selection snapshot.
        for cache_key, entry in tuple(_panel_pause_cache.items()):
            if entry[0] not in {'GESTURE', 'EXPLICIT', 'ANIMATION', 'MODAL'}:
                continue
            if entry[0] != 'ANIMATION':
                return True
            cached = _cached_panel_pause_entry(
                bpy.context,
                cache_key=cache_key,
            )
            if cached is not None:
                return True
    if _explicit_panel_freeze(context) is not None:
        return True
    # Playback handlers invalidate the old cache before requesting a UI redraw.
    # A pending draw-sync timer can run in that short gap, so do not require a
    # Panel.draw call to have populated the ANIMATION entry first.
    animation_context = context if context is not None else bpy.context
    if _is_animation_busy(animation_context):
        return True
    return is_gesture_panel_frozen(context)


def get_gesture_modal_session(context=None):
    """Return the real-gesture session for *context*, if one is registered.

    A window manager can contain more than one 3D View. Prefer the session
    owning the queried area so a frozen Modal Event panel cannot borrow state
    from another window; callers without an area still get the first session.
    """
    try:
        from ..gesture.gesture_draw_gpu import GestureGpuDraw
        active_instances = GestureGpuDraw.__active_draw_instances__
        finishing_instances = GestureGpuDraw.__finishing_draw_instances__
        if not active_instances and not finishing_instances:
            return None
        target_area = getattr(context, "area", None)
        target_key = _rna_pointer(target_area)
        cached = _gesture_panel_session_cache.get(target_key)
        if cached is not None:
            return cached
        fallback = None
        for instance in (*active_instances.values(), *finishing_instances.values()):
            if _is_real_gesture_instance(instance):
                session = getattr(instance, "session", None)
                if session is None:
                    continue
                if fallback is None:
                    fallback = session
                if target_area is None:
                    _gesture_panel_session_cache[target_key] = session
                    return session
                owner_area = getattr(session, "area", None)
                if owner_area is target_area:
                    _gesture_panel_session_cache[target_key] = session
                    return session
                try:
                    if (
                            owner_area is not None
                            and target_area is not None
                            and owner_area.as_pointer() == target_area.as_pointer()
                    ):
                        _gesture_panel_session_cache[target_key] = session
                        return session
                except (AttributeError, ReferenceError, RuntimeError, TypeError):
                    pass
        if (
                fallback is not None
                and (
                    target_area is None
                    or getattr(target_area, 'type', None) == 'PREFERENCES'
                )
        ):
            _gesture_panel_session_cache[target_key] = fallback
            return fallback
    except Exception:
        return None
    return None


def get_frozen_active_element(context=None):
    """Return the activity snapshot captured at real-gesture modal entry."""
    state = _explicit_panel_freeze(context)
    if state is not None:
        return state.snapshot.active_element
    playback = _playback_panel_snapshot(context)
    if playback is not None:
        return playback.active_element
    modal = _modal_panel_snapshot(context)
    if modal is not None:
        return modal.active_element
    session = get_gesture_modal_session(context)
    return getattr(session, "_frozen_active_element", None)


def set_frozen_ui_selection(gesture, active_element, *, area=None):
    """Pin the active Element used by a gesture UIList for one lifecycle."""
    if gesture is None:
        return None
    key = (_rna_pointer(gesture), _rna_pointer(area))
    _frozen_ui_selection[key] = (gesture, active_element)
    return key


def clear_frozen_ui_selection(
        gesture,
        *,
        area=None,
        area_key=None,
        selection_key=None,
) -> None:
    """Release a gesture UIList selection snapshot."""
    if selection_key is not None:
        _frozen_ui_selection.pop(tuple(selection_key), None)
        return
    if gesture is None:
        return
    gesture_key = _rna_pointer(gesture)
    if area is not None:
        area_key = _rna_pointer(area)
    if area_key is not None:
        _frozen_ui_selection.pop((gesture_key, area_key), None)
        return
    for key in tuple(_frozen_ui_selection):
        if key[0] == gesture_key:
            _frozen_ui_selection.pop(key, None)


def clear_frozen_ui_selections() -> None:
    """Drop all gesture UIList snapshots during teardown."""
    _frozen_ui_selection.clear()


def get_frozen_ui_selection(gesture, context=None):
    """Return ``(gesture, active_element)`` for a frozen Element UIList."""
    if gesture is None:
        return None
    gesture_key = _rna_pointer(gesture)
    area_key = _rna_pointer(getattr(context, 'area', None))
    # An explicit value drag can be invoked while the originating gesture is
    # still in its finishing handoff. Keep its snapshot self-contained so the
    # gesture cleanup cannot delete the drag's selection out from under it.
    state = _explicit_panel_freeze(context)
    if (
            state is not None
            and _rna_pointer(state.snapshot.active_gesture) == gesture_key
    ):
        return state.snapshot.active_gesture, state.snapshot.active_element
    # Frozen source precedence is explicit drag > playback > gesture session.
    playback = _playback_panel_snapshot(context)
    if (
            playback is not None
            and _rna_pointer(playback.active_gesture) == gesture_key
    ):
        return playback.active_gesture, playback.active_element
    modal = _modal_panel_snapshot(context)
    if (
            modal is not None
            and _rna_pointer(modal.active_gesture) == gesture_key
    ):
        return modal.active_gesture, modal.active_element
    snapshot = _frozen_ui_selection.get((gesture_key, area_key))
    if snapshot is not None:
        return snapshot
    snapshot = _frozen_ui_selection.get((gesture_key, 0))
    if snapshot is not None:
        return snapshot
    # Preferences is a separate window/area, but it must display the same
    # frozen selection as the gesture's owning VIEW_3D.  Match by stable RNA
    # pointer rather than borrowing an unrelated gesture's snapshot.
    if getattr(getattr(context, 'area', None), 'type', None) == 'PREFERENCES':
        session = get_gesture_modal_session(context)
        frozen_gesture = getattr(session, '_frozen_active_gesture', None)
        if _rna_pointer(frozen_gesture) == gesture_key:
            return (frozen_gesture, getattr(session, '_frozen_active_element', None))
        for key, value in _frozen_ui_selection.items():
            if key[0] == gesture_key:
                return value
    if area_key == 0:
        for key, value in _frozen_ui_selection.items():
            if key[0] == gesture_key:
                return value
    return None


def get_frozen_active_gesture(context=None):
    """Return the gesture selected when the disabled layout was entered."""
    state = _explicit_panel_freeze(context)
    if state is not None:
        return state.snapshot.active_gesture
    playback = _playback_panel_snapshot(context)
    if playback is not None:
        return playback.active_gesture
    modal = _modal_panel_snapshot(context)
    if modal is not None:
        return modal.active_gesture
    session = get_gesture_modal_session(context)
    return getattr(session, "_frozen_active_gesture", None)


def get_frozen_preview_state(context=None) -> tuple[bool, str]:
    """Return the preview row state captured with the disabled layout."""
    state = _explicit_panel_freeze(context)
    if state is not None:
        snapshot = state.snapshot
        return snapshot.preview_active, snapshot.preview_scope
    playback = _playback_panel_snapshot(context)
    if playback is not None:
        return playback.preview_active, playback.preview_scope
    modal = _modal_panel_snapshot(context)
    if modal is not None:
        return modal.preview_active, modal.preview_scope
    session = get_gesture_modal_session(context)
    return (
        bool(getattr(session, "_frozen_preview_active", False)),
        str(getattr(session, "_frozen_preview_scope", '') or ''),
    )


def get_frozen_element_status_info(element, context=None):
    """Pin a list-row status for the current disabled panel lifecycle."""
    cache = None
    state = _explicit_panel_freeze(context)
    if state is not None:
        cache = state.snapshot.status_infos
    if cache is None:
        playback = _playback_panel_snapshot(context)
        if playback is not None:
            cache = playback.status_infos
    if cache is None:
        modal = _modal_panel_snapshot(context)
        if modal is not None:
            cache = modal.status_infos
    if cache is None:
        session = get_gesture_modal_session(context)
        if session is not None:
            cache = getattr(session, "_frozen_panel_status_info", None)
            if cache is None:
                cache = {}
                session._frozen_panel_status_info = cache
    if cache is None:
        return element.list_status_info

    element_key = _rna_pointer(element)
    status = cache.get(element_key)
    if status is None:
        try:
            from ..element.element_status import get_cached_ui_status_info
            status = get_cached_ui_status_info(element)
        except (AttributeError, ImportError, ReferenceError, RuntimeError, TypeError):
            status = None
        if status is None:
            status = element.list_status_info
        cache[element_key] = status
    return status


def _animation_screens(context):
    """Yield the context screen followed by other live Blender window screens."""
    screen = getattr(context, "screen", None)
    if screen is not None:
        yield screen
    wm = getattr(context, "window_manager", None)
    if wm is None:
        wm = getattr(bpy.context, "window_manager", None)
    try:
        windows = getattr(wm, "windows", ()) or ()
        for window in windows:
            other = getattr(window, "screen", None)
            if other is not None and other is not screen:
                yield other
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return


def _is_animation_playing(context) -> bool:
    return any(
        bool(getattr(screen, "is_animation_playing", False))
        for screen in _animation_screens(context)
    )


def _is_animation_busy(context) -> bool:
    # Playback is screen-scoped, while Gesture panels may also be visible in a
    # second Blender window. Pause every copy when any window is playing so a
    # Preferences/secondary panel cannot keep rebuilding on frame notifiers.
    return any(
        bool(
            getattr(screen, "is_animation_playing", False)
            or getattr(screen, "is_scrubbing", False)
        )
        for screen in _animation_screens(context)
    )


def _is_force_show_panels() -> bool:
    try:
        from .pref import get_pref
        return bool(get_pref().draw_property.force_show_panels_during_modal)
    except Exception:
        return False


def _is_blocking_modal(_context=None) -> bool:
    try:
        return bool(bpy.context.window.modal_operators[:])
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return False


def _has_cached_modal_pause() -> bool:
    if not isinstance(_panel_pause_cache, dict):
        return False
    return any(
        entry[0] == 'MODAL'
        for entry in _panel_pause_cache.values()
    )


def is_panel_pause_source_active(context=None) -> bool:
    context = context if context is not None else bpy.context
    window_modal = _is_blocking_modal() or _has_cached_modal_pause()
    if window_modal:
        _schedule_modal_ui_refresh()
    return bool(
        window_modal
        or _explicit_panel_freeze(context) is not None
        or _is_animation_busy(context)
        or is_gesture_modal_active(context)
    )


def tag_gesture_ui_regions() -> None:
    """Redraw VIEW_3D UI (and Preferences) once — not WINDOW, to avoid FPS hit."""
    current = getattr(bpy.context, "window", None)
    wm = getattr(bpy.context, "window_manager", None)
    try:
        windows = list(getattr(wm, "windows", ()) or ())
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        windows = []
    if current is not None and current not in windows:
        windows.insert(0, current)
    for window in windows:
        try:
            screen = window.screen
            for area in screen.areas:
                if area.type not in {'VIEW_3D', 'PREFERENCES'}:
                    continue
                for region in area.regions:
                    if region.type == 'UI' or (
                            area.type == 'PREFERENCES' and region.type == 'WINDOW'
                    ):
                        region.tag_redraw()
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            continue


def _schedule_modal_ui_refresh() -> None:
    """After skipping for a modal, poll until it ends and redraw once."""
    global _modal_ui_refresh_fn
    if _modal_ui_refresh_fn is not None:
        return

    def _poll():
        global _modal_ui_refresh_fn
        try:
            # Animation and add-on-owned freezes have their own lifecycle and
            # never start this poller. If either begins while the timer is
            # alive, defer to its explicit lifecycle.
            if (
                    _is_animation_busy(bpy.context)
                    or _explicit_panel_freeze(bpy.context) is not None
                    or is_gesture_modal_active(bpy.context)
            ):
                return 0.12
            if _is_blocking_modal():
                return 0.12
        except Exception:
            ...
        _modal_ui_refresh_fn = None
        invalidate_modal_panel_state()
        try:
            tag_gesture_ui_regions()
        except Exception:
            ...
        return None

    _modal_ui_refresh_fn = _poll
    try:
        bpy.app.timers.register(_poll, first_interval=0.12)
    except Exception:
        _modal_ui_refresh_fn = None


def draw_heavy_panel_paused(layout, _message: str) -> None:
    """Keep a paused panel body cheap; the pause message lives in the root title.

    Foreign modal operators use this cheap row. Gestures, value drags, and
    playback take the layout-frozen path so existing controls remain visible
    and disabled.
    """
    row = layout.row(align=True)
    row.enabled = False
    # Keep one inert row so an expanded child panel does not collapse abruptly,
    # while avoiding a duplicate pause label in every child panel.
    row.label(text="", icon='BLANK1')


def heavy_panel_skip_message(context) -> Optional[str]:
    """Message when Element/Modal panels should skip heavy draw; else None.

    Skips during gesture modal, animation play/scrub, and any modal operator in
    ``bpy.context.window.modal_operators``. The temporary force-show preference
    overrides every pause source.
    """
    global _panel_pause_cache
    try:
        if not isinstance(_panel_pause_cache, dict):
            _panel_pause_cache = {}
        # This is an explicit override for every pause source.  Check it
        # before consulting the cache so the preference has unambiguous
        # semantics even when a redraw arrives before its update callback.
        if _is_force_show_panels():
            _panel_pause_cache.clear()
            return None
        cache_key = _panel_context_key(context)
        cached = _cached_panel_pause_entry(context, cache_key=cache_key)
        if cached is not None:
            return cached[1]

        explicit_message = _explicit_panel_freeze_message(context)
        if explicit_message:
            _panel_pause_cache[cache_key] = ('EXPLICIT', explicit_message, 0.0)
            return explicit_message

        if _is_animation_busy(context):
            # Playback itself redraws the region at start/stop. Do not add a
            # Python timer or allow a persisted override onto this hot path.
            message = _MSG_ANIMATION
            now = time.monotonic()
            _playback_panel_snapshot(context, capture=True)
            _panel_pause_cache[cache_key] = (
                'ANIMATION',
                message,
                None if _is_animation_playing(context) else now + _PANEL_ACTIVE_CACHE_SEC,
            )
            return message

        if is_gesture_modal_active(context):
            message = _MSG_GESTURE
            _panel_pause_cache[cache_key] = ('GESTURE', message, 0.0)
            return message

        if _is_blocking_modal() or _has_cached_modal_pause():
            message = _MSG_OPERATOR
            _modal_panel_snapshot(context, capture=True)
            _panel_pause_cache[cache_key] = ('MODAL', message, 0.0)
            _schedule_modal_ui_refresh()
            return message

        now = time.monotonic()
        _panel_pause_cache[cache_key] = (
            'IDLE', None, now + _PANEL_IDLE_CACHE_SEC,
        )
        return None
    except Exception:
        return None


def panel_pause_state(context) -> tuple[Optional[str], bool]:
    """Return ``(message, keep_existing_layout)`` with one pause lookup."""
    message = heavy_panel_skip_message(context)
    if message is None:
        return None, False
    cached = _cached_panel_pause_entry(context, refresh_animation=False)
    if cached is not None:
        return message, cached[0] in {'GESTURE', 'EXPLICIT', 'ANIMATION', 'MODAL'}
    return message, is_panel_layout_frozen(context)


def schedule(key: str, callback: Callable[[], None], *, delay: float = _SYNC_DEBOUNCE_SEC) -> None:
    """Run *callback* once after *delay*; coalesces repeats while pending."""
    if key in _pending:
        return
    # Gesture redraws the whole screen (incl. N-panel); syncing keymaps mid-modal
    # can restart bindings and make the direction arc hitch.
    if is_panel_layout_frozen():
        return

    def _flush():
        _pending.pop(key, None)
        if is_panel_layout_frozen():
            return None
        try:
            callback()
        except Exception:
            from .debug_util import debug_traceback
            debug_traceback(key='operator')
        return None

    _pending[key] = _flush
    try:
        bpy.app.timers.register(_flush, first_interval=delay)
    except Exception:
        _pending.pop(key, None)
        if is_panel_layout_frozen():
            return
        try:
            callback()
        except Exception:
            from .debug_util import debug_traceback
            debug_traceback(key='operator')


def cancel_all() -> None:
    """Cancel pending draw-sync timers (call on unregister / gesture start)."""
    global _modal_ui_refresh_fn
    for fn in list(_pending.values()):
        try:
            if bpy.app.timers.is_registered(fn):
                bpy.app.timers.unregister(fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
    _pending.clear()
    if _modal_ui_refresh_fn is not None:
        try:
            if bpy.app.timers.is_registered(_modal_ui_refresh_fn):
                bpy.app.timers.unregister(_modal_ui_refresh_fn)
        except (ValueError, RuntimeError, AttributeError):
            ...
        _modal_ui_refresh_fn = None
    invalidate_panel_pause_cache()


def cancel_modal_ui_refresh() -> None:
    """Cancel the post-modal UI refresh timer after an explicit redraw.

    Gesture completion tags the UI regions synchronously after final operator
    dispatch. Leaving the polling timer alive would tag the same regions again
    on its next tick, needlessly rebuilding every panel a second time.
    """
    global _modal_ui_refresh_fn
    fn = _modal_ui_refresh_fn
    _modal_ui_refresh_fn = None
    invalidate_panel_pause_cache()
    if fn is None:
        return
    try:
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
    except (ValueError, RuntimeError, AttributeError):
        ...
