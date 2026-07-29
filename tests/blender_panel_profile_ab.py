"""Automated GUI A/B profile for Gesture sidebar and preview overhead.

Run this in a fresh, foreground Blender process.  The script enables the
checkout that contains this file, creates a small animated object, and records
two playback phases:

The default ``SIDEBAR`` mode records:

* ``gesture_panel_visible``: the VIEW_3D sidebar is open on the Gesture tab.
* ``sidebar_closed``: the same sidebar is hidden.

``GH_PANEL_AB_MODE=ELEMENT_PREVIEW`` keeps the sidebar visible and records:

* ``element_preview_active``: a large, expanded element tree is previewed.
* ``preview_closed``: the same scene and sidebar after closing the preview.

Preview mode requests both UI-region and overlay redraws at a fixed rate. It
does not start animation playback, because playback freezes the N-panel and
would hide the cost of rebuilding the editable element tree.

The run is deliberately gated by ``GH_PANEL_AB_AUTOMATION=1`` because a
successful or failed automated run quits Blender.  Results are written below
``.tmp/panel-profile-ab`` in the repository.

PowerShell example (do not add ``--background``)::

    $profileRoot = "D:/Development/Blender Addons/gesture_helper/.tmp/panel-ab-user"
    $env:BLENDER_USER_CONFIG = "$profileRoot/config"
    $env:BLENDER_USER_DATAFILES = "$profileRoot/datafiles"
    $env:BLENDER_USER_SCRIPTS = "$profileRoot/scripts"
    $env:GH_PANEL_AB_AUTOMATION = "1"
    & blender --factory-startup --python `
        "D:/Development/Blender Addons/gesture_helper/tests/blender_panel_profile_ab.py"
"""

from __future__ import annotations

from collections import Counter
import cProfile
from datetime import datetime
import functools
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import time
import traceback
from typing import Any

import bpy


AUTOMATION = os.environ.get("GH_PANEL_AB_AUTOMATION") == "1"
PROFILE_SECONDS = float(os.environ.get("GH_PANEL_AB_SECONDS", "3.0"))
STARTUP_DELAY_SECONDS = float(
    os.environ.get("GH_PANEL_AB_STARTUP_DELAY", "0.5")
)
SETTLE_SECONDS = float(os.environ.get("GH_PANEL_AB_SETTLE_SECONDS", "0.75"))
PLAYBACK_FPS = int(os.environ.get("GH_PANEL_AB_FPS", "60"))
PANEL_REDRAW_FPS = int(os.environ.get("GH_PANEL_AB_REDRAW_FPS", "60"))
ELEMENT_COUNT = int(os.environ.get("GH_PANEL_AB_ELEMENT_COUNT", "100"))
if ELEMENT_COUNT < 1:
    raise RuntimeError("GH_PANEL_AB_ELEMENT_COUNT must be at least 1")
PROFILE_MODE = os.environ.get("GH_PANEL_AB_MODE", "SIDEBAR").upper()
if PROFILE_MODE not in {"SIDEBAR", "ELEMENT_PREVIEW"}:
    raise RuntimeError(f"Unsupported GH_PANEL_AB_MODE: {PROFILE_MODE!r}")
PACKAGE_NAME = "gesture_helper"
DRIVER_KEY = "gesture_helper_panel_profile_ab"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


REPOSITORY = _repository_root()
OUTPUT_DIRECTORY = REPOSITORY / ".tmp" / (
    "preview-profile-ab"
    if PROFILE_MODE == "ELEMENT_PREVIEW"
    else "panel-profile-ab"
)


def _rna_pointer(value: Any) -> int:
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return 0


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


class PanelCallCounter:
    """Temporarily count Python callbacks on the add-on's Panel classes."""

    CALLBACK_NAMES = ("poll", "draw", "draw_header", "draw_header_preset")

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.elapsed: Counter[str] = Counter()
        self._originals: list[tuple[type, str, Any]] = []

    def install(self, panel_classes: tuple[type, ...]) -> None:
        for panel_class in panel_classes:
            for method_name in self.CALLBACK_NAMES:
                descriptor = panel_class.__dict__.get(method_name)
                if descriptor is None:
                    continue
                key = f"{panel_class.bl_idname}.{method_name}"
                if isinstance(descriptor, classmethod):
                    wrapped = self._wrap(descriptor.__func__, key)
                    replacement = classmethod(wrapped)
                else:
                    replacement = self._wrap(descriptor, key)
                self._originals.append((panel_class, method_name, descriptor))
                setattr(panel_class, method_name, replacement)

    def _wrap(self, callback, key: str):
        @functools.wraps(callback)
        def counted(owner, context):
            self.counts[key] += 1
            started = time.perf_counter()
            try:
                return callback(owner, context)
            finally:
                self.elapsed[key] += time.perf_counter() - started

        return counted

    def snapshot(self) -> dict[str, int]:
        return dict(self.counts)

    def delta(self, baseline: dict[str, int]) -> dict[str, int]:
        keys = set(baseline) | set(self.counts)
        return {
            key: self.counts.get(key, 0) - baseline.get(key, 0)
            for key in sorted(keys)
            if self.counts.get(key, 0) - baseline.get(key, 0)
        }

    def elapsed_snapshot(self) -> dict[str, float]:
        return dict(self.elapsed)

    def elapsed_delta(self, baseline: dict[str, float]) -> dict[str, float]:
        keys = set(baseline) | set(self.elapsed)
        return {
            key: self.elapsed.get(key, 0.0) - baseline.get(key, 0.0)
            for key in sorted(keys)
            if self.elapsed.get(key, 0.0) - baseline.get(key, 0.0) > 0.0
        }

    def restore(self) -> None:
        for panel_class, method_name, descriptor in reversed(self._originals):
            setattr(panel_class, method_name, descriptor)
        self._originals.clear()


class AutomatedPanelABProfile:
    def __init__(self) -> None:
        self.counter = PanelCallCounter()
        self.panel_module = None
        self.addon_was_enabled = PACKAGE_NAME in bpy.context.preferences.addons
        self.addon_enabled_by_script = False
        self.window = None
        self.area = None
        self.window_region = None
        self.ui_region = None
        self.space = None
        self.category = "Gesture"
        self.addon_source: str | None = None
        self.animation_object = None
        self.preview_instance = None
        self.fixture_leaf_count = 0
        self.fixture_node_count = 0
        self.phase_name: str | None = None
        self.phase_profile: cProfile.Profile | None = None
        self.phase_started_at = 0.0
        self.phase_frames: list[tuple[float, int]] = []
        self.phase_counter_baseline: dict[str, int] = {}
        self.phase_elapsed_baseline: dict[str, float] = {}
        self.phase_redraw_requests: list[float] = []
        self.phases: list[dict[str, Any]] = []
        self.visible_setup_baseline: dict[str, int] = {}
        self.started_at = datetime.now().astimezone()
        self.run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.finished = False
        self.error: dict[str, str] | None = None

        self.frame_handler = self._on_frame_change
        self.bootstrap_timer = self._bootstrap
        self.verify_visible_timer = self._verify_visible
        self.start_visible_timer = self._start_visible_phase
        self.finish_phase_timer = self._finish_phase
        self.start_hidden_timer = self._start_hidden_phase
        self.redraw_timer = self._redraw_tick
        self.quit_timer = self._quit

    def install(self) -> None:
        if bpy.app.background:
            raise RuntimeError(
                "This profile needs a foreground Blender window; do not use "
                "--background."
            )
        previous = bpy.app.driver_namespace.get(DRIVER_KEY)
        if previous is not None:
            previous.cancel()
        bpy.app.driver_namespace[DRIVER_KEY] = self
        bpy.app.handlers.frame_change_post.append(self.frame_handler)
        bpy.app.timers.register(
            self.bootstrap_timer,
            first_interval=STARTUP_DELAY_SECONDS,
        )
        print(
            "[Gesture panel A/B] armed; "
            f"each condition records for {PROFILE_SECONDS:.2f}s"
        )

    def _bootstrap(self):
        try:
            if self.addon_was_enabled:
                raise RuntimeError(
                    "gesture_helper was already enabled; launch a separate "
                    "Blender process with --factory-startup"
                )
            self._load_addon_and_install_counters()
            self._find_view3d_context()
            self._create_animation()
            if PROFILE_MODE == "ELEMENT_PREVIEW":
                self._create_preview_fixture()
            self._configure_visible_sidebar()
            self.visible_setup_baseline = self.counter.snapshot()
            self._tag_redraw()
            bpy.app.timers.register(
                self.verify_visible_timer,
                first_interval=SETTLE_SECONDS,
            )
        except BaseException as exc:  # Blender timers otherwise swallow context.
            self._fail(exc)
        return None

    def _load_addon_and_install_counters(self) -> None:
        repository_parent = str(REPOSITORY.parent)
        if repository_parent not in sys.path:
            sys.path.insert(0, repository_parent)

        import gesture_helper.ui.panel as panel_module

        package_module = sys.modules[PACKAGE_NAME]
        package_path = Path(package_module.__file__).resolve()
        if package_path.parent != REPOSITORY:
            raise RuntimeError(
                "Imported a different gesture_helper checkout: "
                f"{package_path.parent}"
            )
        self.addon_source = str(package_path)
        self.panel_module = panel_module
        self.counter.install(tuple(panel_module.panel_list))
        if not self.addon_was_enabled:
            result = bpy.ops.preferences.addon_enable(module=PACKAGE_NAME)
            if result != {"FINISHED"}:
                raise RuntimeError(f"Could not enable {PACKAGE_NAME}: {result}")
            self.addon_enabled_by_script = True
        if PACKAGE_NAME not in bpy.context.preferences.addons:
            raise RuntimeError(f"{PACKAGE_NAME} is not enabled")
        self.category = str(panel_module.GesturePanel.bl_category or "Gesture")

    def _find_view3d_context(self) -> None:
        candidates = []
        window_manager = bpy.context.window_manager
        for window in window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type != "VIEW_3D":
                    continue
                window_region = next(
                    (region for region in area.regions if region.type == "WINDOW"),
                    None,
                )
                ui_region = next(
                    (region for region in area.regions if region.type == "UI"),
                    None,
                )
                if window_region is None or ui_region is None:
                    continue
                candidates.append((area.width * area.height, window, area,
                                   window_region, ui_region))
        if not candidates:
            raise RuntimeError("No usable VIEW_3D area with WINDOW and UI regions")
        _, self.window, self.area, self.window_region, self.ui_region = max(
            candidates, key=lambda item: item[0]
        )
        self.space = self.area.spaces.active

    def _create_animation(self) -> None:
        scene = self.window.scene
        mesh = bpy.data.meshes.new("GH_AB_Profile_Mesh")
        obj = bpy.data.objects.new("GH_AB_Profile_Object", mesh)
        scene.collection.objects.link(obj)
        obj.location.x = -2.0
        obj.keyframe_insert(data_path="location", index=0, frame=1)
        obj.location.x = 2.0
        obj.keyframe_insert(data_path="location", index=0, frame=1000)
        scene.frame_start = 1
        scene.frame_end = 1000
        scene.render.fps = PLAYBACK_FPS
        scene.render.fps_base = 1.0
        if hasattr(scene, "sync_mode"):
            scene.sync_mode = "NONE"
        scene.frame_set(1)
        self.animation_object = obj

    def _create_preview_fixture(self) -> None:
        from gesture_helper.utils.gesture_persistence import suppress_gesture_disk_save
        from gesture_helper.utils.gesture_store import get_gesture_store
        from gesture_helper.utils.public_cache import PublicCacheFunc
        from gesture_helper.utils.selection import select_element

        store = get_gesture_store()
        if store is None:
            raise RuntimeError("Gesture store is unavailable")
        with suppress_gesture_disk_save():
            store.gesture.clear()
            gesture = store.gesture.add()
            gesture.name = "Element Preview Profile"
            gesture.gesture_type = "RADIAL"
            root = gesture.element.add()
            root.element_type = "COLUMN"
            root.__init_element__()
            root.name = "Profile Elements"
            root.show_child = True
            self.fixture_node_count = 1
            created = 0
            # A realistic expanded tree: COLUMN > BOX > ROW > OPERATOR.
            # Twelve leaves per box keeps the viewport dense while ensuring
            # 100/300-item runs exercise recursive N-panel construction.
            while created < ELEMENT_COUNT:
                box = root.element.add()
                box.element_type = "BOX"
                box.__init_element__()
                box.name = f"Profile Group {self.fixture_node_count:03d}"
                box.show_child = True
                self.fixture_node_count += 1
                for _row_index in range(4):
                    if created >= ELEMENT_COUNT:
                        break
                    row = box.element.add()
                    row.element_type = "ROW"
                    row.__init_element__()
                    row.name = f"Profile Row {self.fixture_node_count:03d}"
                    row.show_child = True
                    self.fixture_node_count += 1
                    for _column_index in range(3):
                        if created >= ELEMENT_COUNT:
                            break
                        item = row.element.add()
                        item.element_type = "OPERATOR"
                        item.__init_element__()
                        created += 1
                        self.fixture_node_count += 1
                        item.name = f"Profile Operator {created:03d}"
                        item.operator_bl_idname = "mesh.primitive_cube_add"
                        item.operator_context = "EXEC_DEFAULT"
            self.fixture_leaf_count = created
            store.index_gesture = 0
            PublicCacheFunc.cache_clear()
            select_element(root)

    def _start_element_preview(self) -> None:
        from gesture_helper.utils.session_state import SessionState

        with bpy.context.temp_override(
            window=self.window,
            screen=self.window.screen,
            area=self.area,
            region=self.window_region,
        ):
            result = bpy.ops.wm.gesture_preview(
                "INVOKE_DEFAULT",
                scope="ELEMENT",
            )
        if "RUNNING_MODAL" not in result:
            raise RuntimeError(f"Could not start element preview: {result}")
        self.preview_instance = SessionState.gesture_preview_instance
        if self.preview_instance is None:
            raise RuntimeError("Element preview did not publish its owner")

    def _request_preview_close(self) -> None:
        from gesture_helper.utils.session_state import SessionState

        if not SessionState.gesture_preview_active:
            self.preview_instance = None
            return
        with bpy.context.temp_override(
            window=self.window,
            screen=self.window.screen,
            area=self.area,
            region=self.window_region,
        ):
            result = bpy.ops.wm.gesture_preview_close("EXEC_DEFAULT")
        if result != {"FINISHED"}:
            raise RuntimeError(f"Could not request preview close: {result}")

    def _configure_visible_sidebar(self) -> None:
        self.space.show_region_ui = True
        # Blender 5.2 exposes Region.active_panel_category as read-only. Keep
        # the isolated profile deterministic by registering the add-on panels
        # under the category that is already active in the factory-startup UI.
        # This changes only the disposable test preferences.
        active_category = str(
            getattr(self.ui_region, "active_panel_category", "") or ""
        )
        if not active_category or active_category == "UNSUPPORTED":
            active_category = "Item"
        if active_category != self.category:
            from gesture_helper.utils.pref import get_pref

            get_pref().draw_property.panel_name = active_category
            self.category = active_category

    def _configure_hidden_sidebar(self) -> None:
        self.space.show_region_ui = False

    def _target_sidebar_snapshot(self) -> dict[str, Any]:
        return {
            "window_pointer": _rna_pointer(self.window),
            "screen_pointer": _rna_pointer(self.window.screen),
            "area_pointer": _rna_pointer(self.area),
            "area_size": [int(self.area.width), int(self.area.height)],
            "sidebar_visible": bool(self.space.show_region_ui),
            "sidebar_width": int(self.ui_region.width),
            "active_category": str(
                getattr(self.ui_region, "active_panel_category", "") or ""
            ),
            "animation_playing": bool(self.window.screen.is_animation_playing),
        }

    def _tag_redraw(self) -> None:
        self.area.tag_redraw()

    def _verify_visible(self):
        try:
            snapshot = self._target_sidebar_snapshot()
            setup_calls = self.counter.delta(self.visible_setup_baseline)
            root_draw_key = "GESTURE_PT_Layout.draw"
            if not snapshot["sidebar_visible"]:
                raise RuntimeError("VIEW_3D sidebar did not open")
            if snapshot["active_category"] != self.category:
                raise RuntimeError(
                    "Gesture category did not become active: "
                    f"{snapshot['active_category']!r} != {self.category!r}"
                )
            if setup_calls.get(root_draw_key, 0) < 1:
                raise RuntimeError(
                    "Gesture root panel did not draw; it may be collapsed or "
                    "outside the visible sidebar"
                )
            if PROFILE_MODE == "ELEMENT_PREVIEW":
                self._start_element_preview()
            else:
                self._start_animation_playback()
            bpy.app.timers.register(
                self.start_visible_timer,
                first_interval=SETTLE_SECONDS,
            )
        except BaseException as exc:
            self._fail(exc)
        return None

    def _start_visible_phase(self):
        try:
            snapshot = self._target_sidebar_snapshot()
            if not snapshot["sidebar_visible"]:
                raise RuntimeError("VIEW_3D sidebar closed before the A phase")
            if snapshot["active_category"] != self.category:
                raise RuntimeError("Gesture category changed before the A phase")
            if PROFILE_MODE != "ELEMENT_PREVIEW" and not snapshot["animation_playing"]:
                raise RuntimeError("Animation stopped before the A phase")
            phase = (
                "element_preview_active"
                if PROFILE_MODE == "ELEMENT_PREVIEW"
                else "gesture_panel_visible"
            )
            self._start_phase(phase)
        except BaseException as exc:
            self._fail(exc)
        return None

    def _start_animation_playback(self) -> None:
        if self.window.screen.is_animation_playing:
            return
        with bpy.context.temp_override(
            window=self.window,
            screen=self.window.screen,
            area=self.area,
            region=self.window_region,
        ):
            result = bpy.ops.screen.animation_play()
        if result != {"FINISHED"} or not self.window.screen.is_animation_playing:
            raise RuntimeError(f"Could not start animation playback: {result}")

    def _stop_animation_playback(self) -> None:
        if not self.window or not self.area or not self.window.screen.is_animation_playing:
            return
        try:
            with bpy.context.temp_override(
                window=self.window,
                screen=self.window.screen,
                area=self.area,
                region=self.window_region,
            ):
                bpy.ops.screen.animation_play()
        except (ReferenceError, RuntimeError, TypeError):
            pass

    def _start_phase(self, name: str) -> None:
        self.phase_name = name
        self.phase_frames = []
        self.phase_redraw_requests = []
        self.phase_counter_baseline = self.counter.snapshot()
        self.phase_elapsed_baseline = self.counter.elapsed_snapshot()
        self.phase_started_at = time.perf_counter()
        self.phase_profile = cProfile.Profile()
        self.phase_profile.enable()
        if PROFILE_MODE == "ELEMENT_PREVIEW":
            bpy.app.timers.register(self.redraw_timer, first_interval=0.0)
        bpy.app.timers.register(
            self.finish_phase_timer,
            first_interval=PROFILE_SECONDS,
        )
        print(f"[Gesture panel A/B] recording {name}")

    def _redraw_tick(self):
        if self.phase_name is None:
            return None
        self.phase_redraw_requests.append(time.perf_counter())
        try:
            self.ui_region.tag_redraw()
            self.window_region.tag_redraw()
        except (AttributeError, ReferenceError, RuntimeError):
            return None
        return 1.0 / max(1, PANEL_REDRAW_FPS)

    def _on_frame_change(self, scene, *_args) -> None:
        if self.phase_name is None:
            return
        self.phase_frames.append((
            time.perf_counter(),
            int(getattr(scene, "frame_current", 0)),
        ))

    def _finish_phase(self):
        try:
            phase_name = self.phase_name
            profile = self.phase_profile
            if phase_name is None or profile is None:
                raise RuntimeError("Phase finish callback ran without an active phase")
            profile.disable()
            if bpy.app.timers.is_registered(self.redraw_timer):
                bpy.app.timers.unregister(self.redraw_timer)
            elapsed = max(0.0, time.perf_counter() - self.phase_started_at)
            self.phase_name = None
            self.phase_profile = None
            self.phases.append(self._phase_payload(phase_name, profile, elapsed))
            first_phase = (
                "element_preview_active"
                if PROFILE_MODE == "ELEMENT_PREVIEW"
                else "gesture_panel_visible"
            )
            if phase_name == first_phase:
                if PROFILE_MODE == "ELEMENT_PREVIEW":
                    self._request_preview_close()
                else:
                    self._configure_hidden_sidebar()
                self._tag_redraw()
                bpy.app.timers.register(
                    self.start_hidden_timer,
                    first_interval=SETTLE_SECONDS,
                )
            else:
                self._complete()
        except BaseException as exc:
            self._fail(exc)
        return None

    def _start_hidden_phase(self):
        try:
            snapshot = self._target_sidebar_snapshot()
            if PROFILE_MODE == "ELEMENT_PREVIEW":
                from gesture_helper.utils.session_state import SessionState

                if SessionState.gesture_preview_active:
                    return 0.1
                if not snapshot["sidebar_visible"]:
                    raise RuntimeError("VIEW_3D sidebar closed before preview B phase")
            elif snapshot["sidebar_visible"]:
                raise RuntimeError("VIEW_3D sidebar did not close for B phase")
            if PROFILE_MODE != "ELEMENT_PREVIEW" and not snapshot["animation_playing"]:
                raise RuntimeError("Animation stopped during the A/B transition")
            phase = (
                "preview_closed"
                if PROFILE_MODE == "ELEMENT_PREVIEW"
                else "sidebar_closed"
            )
            self._start_phase(phase)
        except BaseException as exc:
            self._fail(exc)
        return None

    def _phase_payload(
        self,
        name: str,
        profile: cProfile.Profile,
        elapsed: float,
    ) -> dict[str, Any]:
        frame_times = [sample[0] for sample in self.phase_frames]
        frame_values = [sample[1] for sample in self.phase_frames]
        intervals_ms = [
            (current - previous) * 1000.0
            for previous, current in zip(frame_times, frame_times[1:])
            if current >= previous
        ]
        interval_sum = sum(intervals_ms)
        profile_path = OUTPUT_DIRECTORY / f"{self.run_stamp}-{name}.pstats"
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        profile.dump_stats(str(profile_path))
        callback_counts = self.counter.delta(self.phase_counter_baseline)
        callback_seconds = self.counter.elapsed_delta(self.phase_elapsed_baseline)
        return {
            "name": name,
            "requested_seconds": PROFILE_SECONDS,
            "elapsed_seconds": elapsed,
            "sidebar": self._target_sidebar_snapshot(),
            "frame_change_count": len(frame_times),
            "frame_values": frame_values,
            "frame_intervals_ms": intervals_ms,
            "observed_frame_rate": (
                (len(intervals_ms) * 1000.0 / interval_sum)
                if interval_sum > 0.0 else 0.0
            ),
            "interval_mean_ms": (
                statistics.fmean(intervals_ms) if intervals_ms else None
            ),
            "interval_median_ms": (
                statistics.median(intervals_ms) if intervals_ms else None
            ),
            "interval_p95_ms": _percentile(intervals_ms, 0.95),
            "interval_max_ms": max(intervals_ms) if intervals_ms else None,
            "redraw_request_count": len(self.phase_redraw_requests),
            "redraw_request_rate": (
                len(self.phase_redraw_requests) / elapsed if elapsed > 0.0 else 0.0
            ),
            "panel_callback_counts": callback_counts,
            "panel_callback_seconds": callback_seconds,
            "panel_callback_mean_ms": {
                key: callback_seconds[key] * 1000.0 / callback_counts[key]
                for key in callback_seconds.keys() & callback_counts.keys()
                if callback_counts[key]
            },
            "cprofile": {
                "pstats_file": str(profile_path),
                "top_functions": self._profile_rows(profile, addon_only=False),
                "top_addon_functions": self._profile_rows(
                    profile, addon_only=True
                ),
            },
        }

    @staticmethod
    def _profile_rows(
        profile: cProfile.Profile,
        *,
        addon_only: bool,
    ) -> list[dict[str, Any]]:
        stats = pstats.Stats(profile)
        rows = []
        repository_marker = str(REPOSITORY).replace("\\", "/").lower()
        for (filename, line, function), values in stats.stats.items():
            primitive_calls, total_calls, total_time, cumulative_time, _ = values
            normalized = filename.replace("\\", "/")
            if addon_only:
                normalized_lower = normalized.lower()
                if repository_marker not in normalized_lower:
                    continue
                if "/tests/" in normalized_lower:
                    continue
            rows.append({
                "file": normalized,
                "line": line,
                "function": function,
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_seconds": total_time,
                "cumulative_seconds": cumulative_time,
            })
        rows.sort(key=lambda row: row["cumulative_seconds"], reverse=True)
        return rows[:120]

    def _complete(self) -> None:
        if PROFILE_MODE == "ELEMENT_PREVIEW":
            self._request_preview_close()
        self._stop_animation_playback()
        self.finished = True
        self._remove_callbacks()
        report_path = self._write_report(success=True)
        self.counter.restore()
        bpy.app.driver_namespace.pop(DRIVER_KEY, None)
        print(f"[Gesture panel A/B] complete: {report_path}")
        self._schedule_quit()

    def _fail(self, exc: BaseException) -> None:
        if self.finished:
            return
        if self.phase_profile is not None:
            self.phase_profile.disable()
        self.phase_name = None
        self.phase_profile = None
        self.error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
        }
        self._stop_animation_playback()
        self.finished = True
        self._remove_callbacks()
        report_path = self._write_report(success=False)
        self.counter.restore()
        bpy.app.driver_namespace.pop(DRIVER_KEY, None)
        print(f"[Gesture panel A/B] FAILED: {self.error['message']}")
        print(f"[Gesture panel A/B] report: {report_path}")
        self._schedule_quit()

    def _write_report(self, *, success: bool) -> Path:
        OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        report_path = (
            OUTPUT_DIRECTORY / f"panel-profile-ab-{self.run_stamp}.json"
        )
        payload = {
            "success": success,
            "recorded_at": datetime.now().astimezone().isoformat(),
            "started_at": self.started_at.isoformat(),
            "repository": str(REPOSITORY),
            "blender_version": bpy.app.version_string,
            "python_version": sys.version,
            "blender_user_paths": {
                resource: bpy.utils.user_resource(resource)
                for resource in ("CONFIG", "DATAFILES", "SCRIPTS", "EXTENSIONS")
                if resource != "EXTENSIONS" or bpy.app.version >= (4, 2, 0)
            },
            "configuration": {
                "profile_mode": PROFILE_MODE,
                "profile_seconds": PROFILE_SECONDS,
                "settle_seconds": SETTLE_SECONDS,
                "playback_fps": PLAYBACK_FPS,
                "panel_redraw_fps": PANEL_REDRAW_FPS,
                "element_leaf_count": (
                    self.fixture_leaf_count
                    if PROFILE_MODE == "ELEMENT_PREVIEW" else None
                ),
                "element_total_node_count": (
                    self.fixture_node_count
                    if PROFILE_MODE == "ELEMENT_PREVIEW" else None
                ),
                "order": (
                    ["element_preview_active", "preview_closed"]
                    if PROFILE_MODE == "ELEMENT_PREVIEW"
                    else ["gesture_panel_visible", "sidebar_closed"]
                ),
                "cprofile_and_frame_timing_recorded_together": True,
            },
            "addon": {
                "module": PACKAGE_NAME,
                "was_enabled": self.addon_was_enabled,
                "enabled_by_script": self.addon_enabled_by_script,
                "source": self.addon_source,
                "panel_category": self.category,
            },
            "animation": {
                "object": getattr(self.animation_object, "name", None),
                "frame_start": 1,
                "frame_end": 1000,
            },
            "phases": self.phases,
            "error": self.error,
        }
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        latest_path = OUTPUT_DIRECTORY / "latest.json"
        latest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path

    def _remove_callbacks(self) -> None:
        if PROFILE_MODE == "ELEMENT_PREVIEW":
            try:
                self._request_preview_close()
            except (AttributeError, ReferenceError, RuntimeError):
                pass
        try:
            bpy.app.handlers.frame_change_post.remove(self.frame_handler)
        except ValueError:
            pass
        callbacks = (
            self.bootstrap_timer,
            self.verify_visible_timer,
            self.start_visible_timer,
            self.finish_phase_timer,
            self.start_hidden_timer,
            self.redraw_timer,
        )
        for callback in callbacks:
            try:
                if bpy.app.timers.is_registered(callback):
                    bpy.app.timers.unregister(callback)
            except (AttributeError, RuntimeError, ValueError):
                pass

    def _schedule_quit(self) -> None:
        if AUTOMATION and not bpy.app.timers.is_registered(self.quit_timer):
            bpy.app.timers.register(self.quit_timer, first_interval=0.25)

    def _quit(self):
        if AUTOMATION:
            bpy.ops.wm.quit_blender()
        return None

    def cancel(self) -> None:
        if self.finished:
            return
        if self.phase_profile is not None:
            self.phase_profile.disable()
        self.phase_name = None
        self.phase_profile = None
        self._stop_animation_playback()
        self.finished = True
        self._remove_callbacks()
        self.counter.restore()


if AUTOMATION:
    AutomatedPanelABProfile().install()
else:
    print(
        "[Gesture panel A/B] not started: set "
        "GH_PANEL_AB_AUTOMATION=1 in an isolated Blender process"
    )
