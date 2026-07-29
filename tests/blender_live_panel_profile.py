"""Capture a short live Blender profile for Gesture panel playback hitches.

Open this file in Blender's Text Editor and choose Run Script. The recorder
waits briefly, then waits for actual playback before sampling the main thread
and writing artifacts under ``.tmp/panel-profile`` in the repository.
"""

from __future__ import annotations

import cProfile
from datetime import datetime
import functools
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import time

import bpy


SCRIPT_REVISION = "live-panel-profile-v4"
_AUTOMATION_MARKER = "GH_PROFILE_AUTOMATION"


def _is_text_editor_run(context) -> bool:
    space_data = getattr(context, "space_data", None)
    return (
        getattr(space_data, "type", None) == "TEXT_EDITOR"
        and getattr(space_data, "text", None) is not None
    )


def _resolve_profile_configuration(environ, context, *, background: bool) -> dict:
    text_editor_run = _is_text_editor_run(context)
    explicit_automation = environ.get(_AUTOMATION_MARKER) == "1"
    legacy_background_automation = (
        background and environ.get("GH_PROFILE_AUTO_QUIT") == "1"
    )
    automation = (
        not text_editor_run
        and (explicit_automation or legacy_background_automation)
    )
    if automation:
        return {
            "automation": True,
            "auto_quit": environ.get("GH_PROFILE_AUTO_QUIT") == "1",
            "warmup_seconds": float(
                environ.get("GH_PROFILE_WARMUP_SECONDS", "3.0")
            ),
            "profile_seconds": float(
                environ.get("GH_PROFILE_SECONDS", "10.0")
            ),
            "require_playback": (
                environ.get("GH_PROFILE_REQUIRE_PLAYBACK", "1") != "0"
            ),
            "require_gesture_panel": (
                environ.get("GH_PROFILE_REQUIRE_GESTURE_PANEL", "0") != "0"
            ),
            "configuration_source": (
                "explicit_automation"
                if explicit_automation
                else "legacy_background_automation"
            ),
            "text_editor_run": False,
        }

    # A Text Editor run is always a live measurement. Environment inherited
    # from an automated Blender process must never weaken its requirements.
    return {
        "automation": False,
        "auto_quit": False,
        "warmup_seconds": 3.0,
        "profile_seconds": 10.0,
        "require_playback": True,
        "require_gesture_panel": True,
        "configuration_source": (
            "interactive_text_editor_fixed"
            if text_editor_run
            else "interactive_fixed"
        ),
        "text_editor_run": text_editor_run,
    }


_CONFIGURATION = _resolve_profile_configuration(
    os.environ,
    bpy.context,
    background=bool(getattr(bpy.app, "background", False)),
)
# The explicit marker authorizes one script execution, not the Blender process.
os.environ.pop(_AUTOMATION_MARKER, None)

AUTOMATION = _CONFIGURATION["automation"]
AUTO_QUIT = _CONFIGURATION["auto_quit"]
WARMUP_SECONDS = _CONFIGURATION["warmup_seconds"]
PROFILE_SECONDS = _CONFIGURATION["profile_seconds"]
REQUIRE_PLAYBACK = _CONFIGURATION["require_playback"]
REQUIRE_GESTURE_PANEL = _CONFIGURATION["require_gesture_panel"]
CONFIGURATION_SOURCE = _CONFIGURATION["configuration_source"]
TEXT_EDITOR_RUN = _CONFIGURATION["text_editor_run"]
_DRIVER_KEY = "gesture_helper_live_panel_profile"


def _repository_root() -> Path:
    candidates = []
    text = getattr(getattr(bpy.context, "space_data", None), "text", None)
    text_path = getattr(text, "filepath", "")
    if text_path:
        candidates.append(Path(bpy.path.abspath(text_path)))

    source = globals().get("__file__")
    if source:
        candidates.append(Path(source))

    for module_name, module in tuple(sys.modules.items()):
        if not (
                module_name == "gesture_helper"
                or module_name.endswith(".gesture_helper")
        ):
            continue
        module_path = getattr(module, "__file__", "")
        if module_path:
            candidates.append(Path(module_path))

    configured = os.environ.get("GH_PROFILE_REPOSITORY")
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path.cwd())

    checked = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        search = (resolved, *resolved.parents)
        for directory in search:
            if directory in checked:
                continue
            checked.add(directory)
            if (
                    (directory / "blender_manifest.toml").is_file()
                    and (directory / "tests").is_dir()
            ):
                return directory
    raise RuntimeError(
        "Gesture Helper repository not found. Open this script from the "
        "repository tests folder before running it."
    )


def _rna_pointer(value) -> int:
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return 0


def _sidebar_snapshot() -> list[dict[str, object]]:
    snapshots = []
    window_manager = getattr(bpy.context, "window_manager", None)
    for window_index, window in enumerate(getattr(window_manager, "windows", ())):
        screen = getattr(window, "screen", None)
        for area_index, area in enumerate(getattr(screen, "areas", ())):
            if getattr(area, "type", None) != "VIEW_3D":
                continue
            space = getattr(area, "spaces", None)
            active_space = getattr(space, "active", None)
            ui_region = next(
                (region for region in area.regions if region.type == "UI"),
                None,
            )
            snapshots.append({
                "window_index": window_index,
                "area_index": area_index,
                "area_pointer": _rna_pointer(area),
                "screen_pointer": _rna_pointer(screen),
                "animation_playing": bool(
                    getattr(screen, "is_animation_playing", False)
                ),
                "sidebar_visible": bool(
                    getattr(active_space, "show_region_ui", False)
                ),
                "sidebar_width": int(getattr(ui_region, "width", 0) or 0),
                "active_category": str(
                    getattr(ui_region, "active_panel_category", "") or ""
                ),
            })
    return snapshots


def _visible_sidebar_area_keys(
        snapshots: list[dict[str, object]],
) -> set[int]:
    return {
        int(item["area_pointer"])
        for item in snapshots
        if item["sidebar_visible"] and int(item["sidebar_width"]) > 1
    }


def _scene_snapshot() -> dict[str, object]:
    scene = getattr(bpy.context, "scene", None)
    render = getattr(scene, "render", None)
    fps = float(getattr(render, "fps", 0.0) or 0.0)
    fps_base = float(getattr(render, "fps_base", 1.0) or 1.0)
    return {
        "sync_mode": str(getattr(scene, "sync_mode", "") or ""),
        "render_fps": fps,
        "render_fps_base": fps_base,
        "target_fps": fps / fps_base if fps_base > 0.0 else 0.0,
        "frame_start": int(getattr(scene, "frame_start", 0) or 0),
        "frame_end": int(getattr(scene, "frame_end", 0) or 0),
        "frame_current": int(getattr(scene, "frame_current", 0) or 0),
    }


def _gesture_panel_class():
    for module in tuple(sys.modules.values()):
        panel_class = getattr(module, "GesturePanel", None)
        if getattr(panel_class, "bl_idname", None) == "GESTURE_PT_Layout":
            return panel_class
    return None


class LivePanelProfile:
    def __init__(self) -> None:
        self.profile = cProfile.Profile()
        self.active = False
        self.finished = False
        self.waiting_for_playback = False
        self.waiting_message: str | None = None
        self.live_status_state: str | None = None
        self.started_at = 0.0
        self.frame_times: list[float] = []
        self.frame_values: list[int] = []
        self.output_dir = _repository_root() / ".tmp" / "panel-profile"
        self.start_sidebar = _sidebar_snapshot()
        self.scene_at_arm = _scene_snapshot()
        self.scene_at_start: dict[str, object] = {}
        self.sidebar_at_start: list[dict[str, object]] = []
        self.panel_draw_counts: dict[int, int] = {}
        self.panel_probe_baselines: dict[int, int] = {}
        self.panel_ready_areas: set[int] = set()
        self.panel_ready_at_start: set[int] = set()
        self.panel_probe_class = None
        self.panel_probe_original = None
        self.start_timer = self._start
        self.finish_timer = self._finish
        self.frame_handler = self._on_frame_change

    def install(self) -> None:
        previous = bpy.app.driver_namespace.get(_DRIVER_KEY)
        if previous is not None:
            previous.cancel()
        if REQUIRE_GESTURE_PANEL:
            self._install_panel_probe()
        bpy.app.driver_namespace[_DRIVER_KEY] = self
        bpy.app.handlers.frame_change_post.append(self.frame_handler)
        bpy.app.timers.register(
            self.start_timer,
            first_interval=WARMUP_SECONDS,
        )
        message = (
            f"Gesture panel profile starts in {WARMUP_SECONDS:.0f}s; "
            "switch to the 3D View and start playback"
        )
        self._set_status(message)
        self._publish_live_status("armed", message, self.start_sidebar)
        print(
            "[Gesture profile] armed; start playback now. "
            f"Sampling begins in {WARMUP_SECONDS:.0f}s."
        )

    def _install_panel_probe(self) -> None:
        panel_class = _gesture_panel_class()
        if panel_class is None:
            raise RuntimeError(
                "Gesture panel is not registered. Enable/reload Gesture Helper "
                "before running this profiler."
            )
        original = panel_class.__dict__.get("draw_header")
        if original is None or not callable(original):
            raise RuntimeError("Gesture panel draw_header callback was not found")

        recorder = self

        @functools.wraps(original)
        def counted(panel, context):
            area_key = _rna_pointer(getattr(context, "area", None))
            recorder.panel_draw_counts[area_key] = (
                recorder.panel_draw_counts.get(area_key, 0) + 1
            )
            return original(panel, context)

        self.panel_probe_class = panel_class
        self.panel_probe_original = original
        setattr(panel_class, "draw_header", counted)

    def _restore_panel_probe(self) -> None:
        panel_class = self.panel_probe_class
        original = self.panel_probe_original
        self.panel_probe_class = None
        self.panel_probe_original = None
        if panel_class is not None and original is not None:
            setattr(panel_class, "draw_header", original)

    def _request_panel_probe(self, area_keys: set[int]) -> None:
        self.panel_probe_baselines = {
            area_key: self.panel_draw_counts.get(area_key, 0)
            for area_key in area_keys
        }
        window_manager = getattr(bpy.context, "window_manager", None)
        for window in getattr(window_manager, "windows", ()):
            screen = getattr(window, "screen", None)
            for area in getattr(screen, "areas", ()):
                if _rna_pointer(area) not in area_keys:
                    continue
                for region in getattr(area, "regions", ()):
                    if getattr(region, "type", None) == "UI":
                        region.tag_redraw()

    def _wait(
            self,
            state: str,
            message: str,
            sidebar: list[dict[str, object]],
    ) -> float:
        self._set_status(message)
        self._publish_live_status(state, message, sidebar)
        if message != self.waiting_message:
            self.waiting_message = message
            print(f"[Gesture profile] waiting: {message}")
        return 0.25

    def _set_status(self, text: str | None) -> None:
        workspace = getattr(bpy.context, "workspace", None)
        try:
            workspace.status_text_set(text)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            pass

    def _publish_live_status(
            self,
            state: str,
            message: str,
            sidebar: list[dict[str, object]],
        **details,
    ) -> None:
        if state == self.live_status_state:
            return
        payload = {
            "state": state,
            "message": message,
            "pid": os.getpid(),
            "updated_at": datetime.now().astimezone().isoformat(),
            "script_revision": SCRIPT_REVISION,
            "configuration_source": CONFIGURATION_SOURCE,
            "automation": AUTOMATION,
            "auto_quit": AUTO_QUIT,
            "text_editor_run": TEXT_EDITOR_RUN,
            "warmup_seconds": WARMUP_SECONDS,
            "requested_profile_seconds": PROFILE_SECONDS,
            "required_playback": REQUIRE_PLAYBACK,
            "required_gesture_panel": REQUIRE_GESTURE_PANEL,
            "sidebar": sidebar,
            "scene": _scene_snapshot(),
            **details,
        }
        status_path = self.output_dir / "latest-status.json"
        temporary_path = self.output_dir / f".latest-status-{os.getpid()}.tmp"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(status_path)
            self.live_status_state = state
        except OSError as exc:
            print(f"[Gesture profile] could not update live status: {exc}")
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _start(self):
        if self.finished:
            return None
        sidebar = _sidebar_snapshot()
        visible_area_keys = _visible_sidebar_area_keys(sidebar)
        if REQUIRE_GESTURE_PANEL:
            if not visible_area_keys:
                return self._wait(
                    "waiting_for_sidebar",
                    "Open the 3D View sidebar and select the Gesture tab",
                    sidebar,
                )
            newly_ready = {
                area_key
                for area_key, baseline in self.panel_probe_baselines.items()
                if self.panel_draw_counts.get(area_key, 0) > baseline
            }
            self.panel_ready_areas.update(newly_ready)
            ready_visible = self.panel_ready_areas & visible_area_keys
            if not ready_visible:
                self._request_panel_probe(visible_area_keys)
                return self._wait(
                    "waiting_for_gesture_panel",
                    "Select the Gesture sidebar tab; waiting for its title to draw",
                    sidebar,
                )
        if REQUIRE_PLAYBACK and not any(
                item["animation_playing"] for item in sidebar
        ):
            self.waiting_for_playback = True
            return self._wait(
                "waiting_for_playback",
                "Start animation playback in the 3D View",
                sidebar,
            )
        self.waiting_for_playback = False
        self.waiting_message = None
        self.sidebar_at_start = sidebar
        self.scene_at_start = _scene_snapshot()
        self.panel_ready_at_start = self.panel_ready_areas & visible_area_keys
        self.active = True
        self.started_at = time.perf_counter()
        recording_message = (
            f"Recording Gesture panel performance for {PROFILE_SECONDS:.0f}s"
        )
        self._set_status(recording_message)
        self._publish_live_status("recording", recording_message, sidebar)
        self.profile.enable()
        bpy.app.timers.register(
            self.finish_timer,
            first_interval=PROFILE_SECONDS,
        )
        print(
            "[Gesture profile] recording for "
            f"{PROFILE_SECONDS:.0f}s..."
        )
        return None

    def _on_frame_change(self, scene, *_args) -> None:
        if not self.active:
            return
        self.frame_times.append(time.perf_counter())
        self.frame_values.append(int(getattr(scene, "frame_current", 0)))

    def _remove_callbacks(self) -> None:
        try:
            bpy.app.handlers.frame_change_post.remove(self.frame_handler)
        except ValueError:
            pass
        for callback in (self.start_timer, self.finish_timer):
            try:
                if bpy.app.timers.is_registered(callback):
                    bpy.app.timers.unregister(callback)
            except (AttributeError, RuntimeError, ValueError):
                pass

    def _frame_summary(self, elapsed: float) -> dict[str, object]:
        intervals = [
            current - previous
            for previous, current in zip(self.frame_times, self.frame_times[1:])
            if current >= previous
        ]
        frame_start = int(self.scene_at_start.get("frame_start", 0) or 0)
        frame_end = int(self.scene_at_start.get("frame_end", 0) or 0)
        frame_count = max(0, frame_end - frame_start + 1)
        raw_steps = [
            current - previous
            for previous, current in zip(self.frame_values, self.frame_values[1:])
        ]
        normalized_steps = []
        for raw_step in raw_steps:
            step = raw_step
            if frame_count > 1:
                if raw_step < -(frame_count / 2.0):
                    step = raw_step + frame_count
                elif raw_step > frame_count / 2.0:
                    step = raw_step - frame_count
            normalized_steps.append(step)
        direction_score = sum(normalized_steps)
        direction = 1 if direction_score > 0 else -1 if direction_score < 0 else 0
        advances = []
        wrap_count = 0
        for previous, current in zip(self.frame_values, self.frame_values[1:]):
            if current == previous:
                advances.append(0)
                continue
            if direction >= 0:
                if current > previous or frame_count <= 1:
                    advance = current - previous
                else:
                    advance = (
                        (frame_end - previous)
                        + (current - frame_start)
                        + 1
                    )
                    wrap_count += 1
            elif current < previous or frame_count <= 1:
                advance = previous - current
            else:
                advance = (
                    (previous - frame_start)
                    + (frame_end - current)
                    + 1
                )
                wrap_count += 1
            advances.append(max(0, advance))

        advanced_frames = sum(advances)
        callback_steps = sum(advance > 0 for advance in advances)
        skipped_frames = sum(max(0, advance - 1) for advance in advances)
        summary: dict[str, object] = {
            "frame_change_count": len(self.frame_times),
            "observed_frame_rate": (
                len(intervals) / sum(intervals)
                if intervals and sum(intervals) > 0.0
                else 0.0
            ),
            "profile_elapsed_seconds": elapsed,
            "first_frame": self.frame_values[0] if self.frame_values else None,
            "last_frame": self.frame_values[-1] if self.frame_values else None,
            "timeline_direction": (
                "FORWARD" if direction > 0
                else "REVERSE" if direction < 0
                else "STATIC"
            ),
            "advanced_frames": advanced_frames,
            "effective_timeline_fps": (
                advanced_frames / elapsed if elapsed > 0.0 else 0.0
            ),
            "jump_event_count": sum(advance > 1 for advance in advances),
            "skipped_frames": skipped_frames,
            "duplicate_frame_events": sum(advance == 0 for advance in advances),
            "wrap_count": wrap_count,
            "presented_ratio": (
                callback_steps / advanced_frames
                if advanced_frames > 0
                else 0.0
            ),
        }
        if intervals:
            ordered = sorted(intervals)
            p95_index = min(len(ordered) - 1, int(len(ordered) * 0.95))
            summary.update({
                "interval_mean_ms": statistics.fmean(intervals) * 1000.0,
                "interval_median_ms": statistics.median(intervals) * 1000.0,
                "interval_p95_ms": ordered[p95_index] * 1000.0,
                "interval_max_ms": max(intervals) * 1000.0,
            })
        return summary

    @staticmethod
    def _top_functions(stats: pstats.Stats) -> list[dict[str, object]]:
        rows = []
        for (filename, line, name), values in stats.stats.items():
            primitive_calls, total_calls, total_time, cumulative_time, _callers = values
            normalized = filename.replace("\\", "/")
            if not any(
                    marker in normalized
                    for marker in (
                        "/gesture_helper/",
                        "ui/panel.py",
                        "utils/ui_draw_sync.py",
                        "ui/ui_list.py",
                    )
            ):
                continue
            rows.append({
                "file": normalized,
                "line": line,
                "function": name,
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_seconds": total_time,
                "cumulative_seconds": cumulative_time,
            })
        rows.sort(key=lambda row: row["cumulative_seconds"], reverse=True)
        return rows[:100]

    def _validation_reasons(
            self,
            frame_summary: dict[str, object],
            sidebar_at_finish: list[dict[str, object]],
    ) -> list[str]:
        reasons = []
        if REQUIRE_PLAYBACK:
            if int(frame_summary["frame_change_count"]) < 2:
                reasons.append("fewer than two animation frame changes were captured")
            if not any(item["animation_playing"] for item in sidebar_at_finish):
                reasons.append("animation was no longer playing when sampling finished")
        if REQUIRE_GESTURE_PANEL:
            visible_at_start = _visible_sidebar_area_keys(self.sidebar_at_start)
            visible_at_finish = _visible_sidebar_area_keys(sidebar_at_finish)
            if not self.panel_ready_at_start:
                reasons.append("Gesture panel title was not observed before sampling")
            if not visible_at_start:
                reasons.append("3D View sidebar was not visible when sampling started")
            if not (self.panel_ready_at_start & visible_at_finish):
                reasons.append("measured Gesture sidebar was not visible at finish")
        return reasons

    def _write_results(
            self,
            elapsed: float,
            frame_summary: dict[str, object],
            sidebar_at_finish: list[dict[str, object]],
            scene_at_finish: dict[str, object],
    ) -> tuple[tuple[Path, Path, Path], bool]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = self.output_dir / f"panel-profile-{stamp}"
        pstats_path = stem.with_suffix(".pstats")
        text_path = stem.with_suffix(".txt")
        json_path = stem.with_suffix(".json")

        self.profile.dump_stats(str(pstats_path))
        top_addon_functions = self._top_functions(pstats.Stats(self.profile))
        readable = io.StringIO()
        stats = pstats.Stats(self.profile, stream=readable)
        stats.strip_dirs().sort_stats("cumulative").print_stats(120)
        text_path.write_text(readable.getvalue(), encoding="utf-8")

        invalid_reasons = self._validation_reasons(
            frame_summary,
            sidebar_at_finish,
        )
        payload = {
            "script_revision": SCRIPT_REVISION,
            "configuration_source": CONFIGURATION_SOURCE,
            "automation": AUTOMATION,
            "auto_quit": AUTO_QUIT,
            "text_editor_run": TEXT_EDITOR_RUN,
            "valid": not invalid_reasons,
            "invalid_reasons": invalid_reasons,
            "recorded_at": datetime.now().astimezone().isoformat(),
            "blender_version": ".".join(str(item) for item in bpy.app.version),
            "warmup_seconds": WARMUP_SECONDS,
            "requested_profile_seconds": PROFILE_SECONDS,
            "required_playback": REQUIRE_PLAYBACK,
            "required_gesture_panel": REQUIRE_GESTURE_PANEL,
            "frame_summary": frame_summary,
            "scene_at_arm": self.scene_at_arm,
            "scene_at_start": self.scene_at_start,
            "scene_at_finish": scene_at_finish,
            "sidebar_at_arm": self.start_sidebar,
            "sidebar_at_start": self.sidebar_at_start,
            "sidebar_at_finish": sidebar_at_finish,
            "gesture_panel_probe": {
                "draw_counts_by_area": self.panel_draw_counts,
                "ready_areas": sorted(self.panel_ready_at_start),
            },
            "top_addon_functions": top_addon_functions,
        }
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return (pstats_path, text_path, json_path), not invalid_reasons

    def _finish(self):
        if self.finished:
            return None
        self.profile.disable()
        elapsed = max(0.0, time.perf_counter() - self.started_at)
        self.active = False
        self.finished = True
        self._remove_callbacks()
        frame_summary = self._frame_summary(elapsed)
        sidebar_at_finish = _sidebar_snapshot()
        scene_at_finish = _scene_snapshot()
        try:
            paths, valid = self._write_results(
                elapsed,
                frame_summary,
                sidebar_at_finish,
                scene_at_finish,
            )
            final_state = "finished" if valid else "invalid"
            final_message = (
                "Gesture panel profile completed"
                if valid
                else "Gesture panel profile completed with invalid data"
            )
            self._publish_live_status(
                final_state,
                final_message,
                sidebar_at_finish,
                valid=valid,
                artifacts=[str(path) for path in paths],
            )
        except Exception as exc:
            self._publish_live_status(
                "failed",
                f"Gesture panel profile failed: {exc}",
                sidebar_at_finish,
                valid=False,
            )
            raise
        finally:
            self._restore_panel_probe()
            if bpy.app.driver_namespace.get(_DRIVER_KEY) is self:
                bpy.app.driver_namespace.pop(_DRIVER_KEY, None)
            self._set_status(None)
        print(f"[Gesture profile] {'complete' if valid else 'INVALID'}:")
        for path in paths:
            print(f"  {path}")
        return None

    def cancel(self) -> None:
        if self.finished:
            return
        if self.active:
            self.profile.disable()
        self.active = False
        self.finished = True
        self._remove_callbacks()
        self._restore_panel_probe()
        self._publish_live_status(
            "cancelled",
            "Gesture panel profile was cancelled",
            _sidebar_snapshot(),
            valid=False,
        )
        if bpy.app.driver_namespace.get(_DRIVER_KEY) is self:
            bpy.app.driver_namespace.pop(_DRIVER_KEY, None)
        self._set_status(None)


def main() -> None:
    LivePanelProfile().install()

    if AUTO_QUIT:
        def _quit_after_profile():
            bpy.ops.wm.quit_blender()
            return None

        bpy.app.timers.register(
            _quit_after_profile,
            first_interval=WARMUP_SECONDS + PROFILE_SECONDS + 1.0,
        )


if __name__ == "__main__":
    main()
