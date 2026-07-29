"""Runtime gesture session state (Input → Session → Execute/Render)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from mathutils import Vector

from .gesture_point_kd_tree import GesturePointKDTree
from .runtime_tooltip import HoverTooltipState, cancel_hover_tooltip


class GesturePhase(Enum):
    """Modal session lifecycle (exclusive — one phase at a time).

    IDLE        just invoked / no meaningful motion yet
    TRACKING    recording mouse trail; radial UI not shown
    UI_VISIBLE  radial menu shown (timeout); may include child levels
    """

    IDLE = auto()
    TRACKING = auto()
    UI_VISIBLE = auto()

    @property
    def shows_radial_ui(self) -> bool:
        return self is GesturePhase.UI_VISIBLE

    @property
    def records_mouse_trail(self) -> bool:
        """Trail polyline is only recorded before the radial UI appears."""
        return self is not GesturePhase.UI_VISIBLE


class ThresholdZone(Enum):
    """Distance from gesture center vs preference thresholds.

    INSIDE     distance <= start threshold
    BEYOND     start < distance <= start + confirm delta  (transition / preview)
    CONFIRM    distance > start + confirm delta           (armed / fire-ready)
    """

    INSIDE = auto()
    BEYOND = auto()
    CONFIRM = auto()

    @property
    def is_beyond(self) -> bool:
        """Past the start threshold (transition or confirm)."""
        return self is not ThresholdZone.INSIDE

    @property
    def is_transition(self) -> bool:
        """In the band between start and confirm — selected but not armed."""
        return self is ThresholdZone.BEYOND

    @property
    def is_confirm(self) -> bool:
        return self is ThresholdZone.CONFIRM


class UiHandoff(Enum):
    """How the gesture modal hands off to Blender UI on exit.

    NONE       normal finish
    DEFERRED   timer-deferred menu / operator (FINISHED+INTERFACE)
    """

    NONE = auto()
    DEFERRED = auto()

    @property
    def needs_interface(self) -> bool:
        return self is UiHandoff.DEFERRED


def threshold_zone_from_distance(distance: float, threshold: float, threshold_confirm: float) -> ThresholdZone:
    """Map distance to zone. *threshold_confirm* is the extra delta past *threshold*."""
    confirm_r = threshold + threshold_confirm
    if distance > confirm_r:
        return ThresholdZone.CONFIRM
    if distance > threshold:
        return ThresholdZone.BEYOND
    return ThresholdZone.INSIDE


@dataclass
class InputSnapshot:
    """Per-event computed input metrics; read-only for Execute/Render."""

    mouse_window: Vector = field(default_factory=lambda: Vector((0.0, 0.0)))
    angle: float | None = None
    angle_unsigned: float | None = None
    direction: int | None = None
    distance: float = 0.0
    threshold_zone: ThresholdZone = ThresholdZone.INSIDE
    is_beyond_extension_offset: bool = False
    extension_offset_distance: float = 0.0
    is_draw_gpu: bool = False
    is_access_child_gesture: bool = False
    is_have_extension_item: bool = False
    direction_element: Any = None
    direction_items: dict = field(default_factory=dict)
    extension_element: Any = None


class GestureSession:
    """Canonical runtime state for one gesture modal session."""

    def __init__(self):
        self._clear_runtime(event_count=0, move_count=0, stamp_time=False)
        self.area = None
        self.screen = None
        self.event = None
        self.invoke_event_type: str | None = None
        self.gesture_name: str = ""

    def _clear_runtime(self, *, event_count: int, move_count: int, stamp_time: bool):
        """Shared wipe for ``__init__`` and ``reset`` (keeps fields in sync)."""
        cancel_hover_tooltip(getattr(self, "tooltip_state", None))
        self.trajectory_tree = GesturePointKDTree()
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.extension_hover = []
        self.snapshot = InputSnapshot()
        self.phase = GesturePhase.IDLE
        self.handoff = UiHandoff.NONE
        self.modal_report_done = False

        self.event_count = event_count
        self.move_count = move_count
        self.last_mouse_mouse_time = time.time() if stamp_time else 0.0
        # Active LMB value drag on a property row: (element, start_mouse, start_value).
        self.property_drag: tuple | None = None
        # Set when a drag ended on the same event that exits the gesture.
        self._suppress_property_execute = False
        # True once the active drag moved far enough to count as a scrub.
        self._property_drag_moved = False
        # LMB-down state for the decrement/value/increment regions.  The draw
        # pass consumes this state; mouse geometry remains owned by the current
        # layout token on the element.
        self._numeric_pressed_element = None
        self._numeric_pressed_part = None
        # Generic press ownership for nonnumeric GPU surfaces. Drawing reads
        # this separately from hover and semantic selection/active state.
        self._ui_pressed_element = None
        # Per-event modal consumption marker. False only means that the event
        # may continue into the normal execute/exit checks.
        self._event_consumed = False
        # Invalid runtime item requested by an explicit LMB click. The modal
        # owner consumes it after cleanup and reveals the existing editor.
        self.repair_element = None
        self._gesture_circle_center: Vector | None = None
        self._last_trajectory_mouse: Vector | None = None
        self._derived_cache_key = None
        self._direction_items_memo = None
        # (cache_key, {element: items}) — replaced wholesale when the key changes.
        self._gpu_extension_items_cache = None
        self._gpu_panel_leaf_items_cache = None
        # Status values are keyed by derived generation/context, but a new
        # modal session must not retain dictionaries keyed by old RNA proxies.
        self._element_status_cache = None
        self._element_status_info_cache = None
        # Poll expressions are context-sensitive, but normally do not depend on
        # the mouse event itself. Keep one fingerprint per modal snapshot so
        # item/status caches can survive ordinary cursor motion.
        self._poll_context_fingerprint = None
        self._poll_context_serial = -1
        self._input_event_serial = 0
        # External RNA values can change during a property scrub without
        # touching the add-on's derived-cache generation. Bump this only when
        # the value really changes so condition-dependent items stay correct.
        self._poll_context_revision = 0
        # Per-draw automatic radial offsets. User-authored ``overlay_offset``
        # remains separate and is added only by the renderer.
        self.radial_auto_offsets: dict = {}
        self._radial_offset_cache = None
        # Visibility of the optional Modal Event panel captured at modal
        # entry.  While the gesture owns the UI, Panel.poll must not resolve
        # the active RNA element again: doing so can rebuild selection state
        # while the input handler is still dispatching events.
        self._modal_event_panel_element = None
        self._frozen_active_gesture = None
        self._frozen_active_element = None
        self._frozen_preview_active = False
        self._frozen_preview_scope = ''
        self._frozen_ui_selection_key: tuple[int, int] | None = None
        self._frozen_panel_status_info: dict[int, object] = {}
        # Canonical Element proxy pool — see ``canonical_element``.
        self._element_proxy_pool: dict = {}
        self._element_proxy_pool_generation = None
        self._gesture_timeout_timer = None
        self._gesture_timeout_deadline = None
        self._bottom_child_dwell_timer = None
        self._bottom_child_dwell_deadline = None
        self.tooltip_state = HoverTooltipState()
        self.draw_ctx = None  # DrawFrameContext | None
        # Static layout sizes survive GPU callbacks while their complete
        # content/context/style signature stays unchanged. Dynamic property
        # labels still use the per-frame cache only.
        self._layout_measure_cache = {}
        self._layout_measure_cache_key = None
        self._layout_measure_stability = {}
        self._layout_frame_measure_cache = None
        # Retained static GPU layout commands, keyed per root adapter/element.
        # Dynamic property layouts deliberately do not enter this cache.
        self._layout_render_cache = {}
        self.layout_token = object()

    def reset(self, event, area, screen, gesture_name: str = ""):
        """Initialize / reset for a new invoke."""
        self._clear_runtime(event_count=1, move_count=1, stamp_time=True)
        self.area = area
        self.screen = screen
        self.event = event
        self.invoke_event_type = event.type if event is not None else None
        self.gesture_name = gesture_name

    def canonical_element(self, element):
        """Session-stable Python proxy for an Element RNA struct.

        Blender creates a fresh PropertyGroup proxy on every RNA access and
        instance attributes (GPU hit boxes, layout tokens, ``ops``) do not
        transfer between proxies — ``hash``/``eq`` are pointer-based though.
        Item walks re-run every event for poll freshness; mapping the results
        through this pool keeps proxy IDENTITY stable so what the draw pass
        stamped is what input reads. Cleared when the structure cache rebuilds
        (RNA pointers may be gone) and on session reset.
        """
        from ..utils.public_cache import PublicCache
        generation = PublicCache.__structure_generation__
        if self._element_proxy_pool_generation != generation:
            self.release_element_proxies()
            self._element_proxy_pool.clear()
            self._element_proxy_pool_generation = generation
        return self._element_proxy_pool.setdefault(element, element)

    def release_element_proxies(self, owner=None) -> None:
        """Detach transient modal owners before Blender removes their RNA."""
        self._layout_render_cache.clear()
        for element in tuple(self._element_proxy_pool.values()):
            try:
                current = getattr(element, 'ops', None)
                if current is None:
                    continue
                if owner is not None and current is not owner:
                    continue
                if owner is None:
                    try:
                        if getattr(current, 'session', None) is not self:
                            continue
                    except ReferenceError:
                        pass
                element.ops = None
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                continue

    # ---- phase transitions (single write path) ----

    def advance_to_tracking(self) -> bool:
        """IDLE → TRACKING. Returns True if phase changed."""
        if self.phase is GesturePhase.IDLE:
            self.phase = GesturePhase.TRACKING
            return True
        return False

    def advance_to_ui_visible(self) -> bool:
        """IDLE/TRACKING → UI_VISIBLE. Returns True if phase changed."""
        if self.phase is GesturePhase.UI_VISIBLE:
            return False
        self.phase = GesturePhase.UI_VISIBLE
        return True

    def set_handoff(self, handoff: UiHandoff):
        self.handoff = handoff

    def clear_handoff(self):
        self.handoff = UiHandoff.NONE

    @property
    def child_depth(self) -> int:
        """Number of entered child levels (0 = root gesture)."""
        n = len(self.trajectory_tree)
        return max(0, n - 1)
