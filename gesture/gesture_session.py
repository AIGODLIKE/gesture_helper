"""Runtime gesture session state (Input → Session → Execute/Render)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from mathutils import Vector

from .gesture_point_kd_tree import GesturePointKDTree


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
    """Distance from gesture center vs preference thresholds."""

    INSIDE = auto()    # within start threshold
    BEYOND = auto()    # past start threshold
    CONFIRM = auto()   # past confirm threshold

    @property
    def is_beyond(self) -> bool:
        return self is not ThresholdZone.INSIDE

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

    @property
    def ignore_window_deactivate(self) -> bool:
        return self is UiHandoff.DEFERRED


def threshold_zone_from_distance(distance: float, threshold: float, threshold_confirm: float) -> ThresholdZone:
    if distance > (threshold_confirm + threshold):
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
        self.trajectory_tree = GesturePointKDTree()
        self.trajectory_mouse_move: list = []
        self.trajectory_mouse_move_time: list = []
        self.extension_hover: list = []
        self.snapshot = InputSnapshot()
        self.phase = GesturePhase.IDLE
        self.handoff = UiHandoff.NONE
        self.modal_report_done = False

        self.area = None
        self.screen = None
        self.event = None
        self.invoke_event_type: str | None = None
        self.gesture_name: str = ""

        self.event_count = 0
        self.move_count = 0
        self.last_mouse_mouse_time = 0.0
        self._gesture_circle_center: Vector | None = None
        self._last_trajectory_mouse: Vector | None = None
        self._derived_cache_key = None
        self._direction_items_memo = None
        self._gpu_extension_items_cache = None
        self._gesture_timeout_timer = None
        self._gesture_timeout_deadline = None
        self.draw_ctx = None  # DrawFrameContext | None

    def reset(self, event, area, screen, gesture_name: str = ""):
        """Initialize / reset for a new invoke."""
        self.trajectory_tree = GesturePointKDTree()
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.extension_hover = []
        self.snapshot = InputSnapshot()
        self.phase = GesturePhase.IDLE
        self.handoff = UiHandoff.NONE
        self.modal_report_done = False

        self.area = area
        self.screen = screen
        self.event = event
        self.invoke_event_type = event.type if event is not None else None
        self.gesture_name = gesture_name

        self.event_count = 1
        self.move_count = 1
        self.last_mouse_mouse_time = time.time()
        self._gesture_circle_center = None
        self._last_trajectory_mouse = None
        self._derived_cache_key = None
        self._direction_items_memo = None
        self._gpu_extension_items_cache = None
        self._gesture_timeout_timer = None
        self._gesture_timeout_deadline = None
        self.draw_ctx = None

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
