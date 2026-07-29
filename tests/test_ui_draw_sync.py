from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "utils" / "ui_draw_sync.py"
PACKAGE = "gesture_helper_ui_draw_sync_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_ui_draw_sync_module():
    for package_name in (PACKAGE, f"{PACKAGE}.gesture", f"{PACKAGE}.utils"):
        package = _module(package_name)
        package.__path__ = []

    bpy = _module("bpy")
    bpy.context = types.SimpleNamespace(window=None, window_manager=None)
    bpy.app = types.SimpleNamespace(timers=types.SimpleNamespace())

    class GestureGpuDraw:
        __active_draw_instances__ = {}
        __finishing_draw_instances__ = {}

    _module(
        f"{PACKAGE}.gesture.gesture_draw_gpu",
        GestureGpuDraw=GestureGpuDraw,
    )

    name = f"{PACKAGE}.utils.ui_draw_sync"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, GestureGpuDraw


ui_draw_sync, GestureGpuDraw = _load_ui_draw_sync_module()


class FakeOperator:
    def __init__(self, identifier, session=None):
        self.bl_idname = identifier
        self.session = session


class FakeRow:
    def __init__(self):
        self.enabled = True
        self.labels = []

    def label(self, **kwargs):
        self.labels.append(kwargs)


class FakeLayout:
    def __init__(self):
        self.rows = []

    def row(self, *, align=False):
        row = FakeRow()
        self.rows.append((align, row))
        return row


class GestureModalStateTests(unittest.TestCase):
    def setUp(self):
        GestureGpuDraw.__active_draw_instances__.clear()
        GestureGpuDraw.__finishing_draw_instances__.clear()
        ui_draw_sync._modal_ui_refresh_fn = None
        ui_draw_sync._panel_pause_cache = {}
        ui_draw_sync._panel_layout_freezes.clear()
        ui_draw_sync._gesture_panel_session_cache.clear()
        ui_draw_sync._frozen_ui_selection.clear()
        ui_draw_sync._playback_panel_snapshots.clear()
        ui_draw_sync._modal_panel_snapshots.clear()

    def test_preview_only_does_not_pause_panels(self):
        GestureGpuDraw.__active_draw_instances__[1] = FakeOperator(
            "wm.gesture_preview",
        )

        self.assertFalse(ui_draw_sync.is_gesture_modal_active())

    def test_overlay_lifecycle_modals_do_not_block_panels(self):
        old_window = ui_draw_sync.bpy.context.window
        try:
            ui_draw_sync.bpy.context.window = types.SimpleNamespace(
                modal_operators=[FakeOperator("wm.gesture_preview")],
            )
            self.assertFalse(ui_draw_sync._is_blocking_modal())
            ui_draw_sync.bpy.context.window.modal_operators[:] = [
                FakeOperator("WM_OT_gesture_preview"),
            ]
            self.assertFalse(ui_draw_sync._is_blocking_modal())
            for identifier in ("wm.gesture_menu", "WM_OT_gesture_menu"):
                ui_draw_sync.bpy.context.window.modal_operators[:] = [
                    FakeOperator(identifier),
                ]
                self.assertFalse(ui_draw_sync._is_blocking_modal())
        finally:
            ui_draw_sync.bpy.context.window = old_window

    def test_non_preview_modal_still_blocks_alongside_preview(self):
        old_window = ui_draw_sync.bpy.context.window
        try:
            ui_draw_sync.bpy.context.window = types.SimpleNamespace(
                modal_operators=[FakeOperator("wm.gesture_preview"), object()],
            )
            self.assertTrue(ui_draw_sync._is_blocking_modal())
        finally:
            ui_draw_sync.bpy.context.window = old_window

    def test_real_gesture_is_detected_after_same_area_preview_is_replaced(self):
        area_key = 1
        GestureGpuDraw.__active_draw_instances__[area_key] = FakeOperator(
            "wm.gesture_preview",
        )
        GestureGpuDraw.__active_draw_instances__[area_key] = FakeOperator(
            "wm.gesture_operator",
        )

        self.assertTrue(ui_draw_sync.is_gesture_modal_active())

    def test_preview_and_real_gesture_can_coexist_in_different_areas(self):
        GestureGpuDraw.__active_draw_instances__.update({
            1: FakeOperator("WM_OT_gesture_preview"),
            2: FakeOperator("WM_OT_gesture_operator"),
        })

        self.assertTrue(ui_draw_sync.is_gesture_modal_active())

    def test_real_gesture_session_is_exposed_for_frozen_panels(self):
        session = object()
        GestureGpuDraw.__active_draw_instances__[1] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )

        self.assertIs(ui_draw_sync.get_gesture_modal_session(), session)

    def test_frozen_panel_uses_the_session_for_its_own_area(self):
        class FakeArea:
            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        first_area = FakeArea(1)
        second_area = FakeArea(2)
        first = types.SimpleNamespace(area=first_area)
        second = types.SimpleNamespace(area=second_area)
        GestureGpuDraw.__active_draw_instances__.update({
            1: FakeOperator("wm.gesture_operator", session=first),
            2: FakeOperator("wm.gesture_operator", session=second),
        })

        context = types.SimpleNamespace(area=second_area)
        self.assertIs(ui_draw_sync.get_gesture_modal_session(context), second)

    def test_frozen_panel_never_borrows_another_areas_session(self):
        class FakeArea:
            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        owner_area = FakeArea(1)
        other_area = FakeArea(2)
        session = types.SimpleNamespace(area=owner_area)
        GestureGpuDraw.__active_draw_instances__[1] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )

        self.assertIsNone(
            ui_draw_sync.get_gesture_modal_session(
                types.SimpleNamespace(area=other_area),
            ),
        )

    def test_real_gesture_only_freezes_its_view3d_and_preferences(self):
        class FakeArea:
            def __init__(self, pointer, area_type="VIEW_3D"):
                self.pointer = pointer
                self.type = area_type

            def as_pointer(self):
                return self.pointer

        owner_area = FakeArea(1)
        other_area = FakeArea(2)
        preferences_area = FakeArea(3, "PREFERENCES")
        session = types.SimpleNamespace(area=owner_area)
        GestureGpuDraw.__active_draw_instances__[1] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )

        self.assertTrue(ui_draw_sync.is_gesture_panel_frozen(
            types.SimpleNamespace(area=owner_area),
        ))
        self.assertFalse(ui_draw_sync.is_gesture_panel_frozen(
            types.SimpleNamespace(area=other_area),
        ))
        self.assertTrue(ui_draw_sync.is_gesture_panel_frozen(
            types.SimpleNamespace(area=preferences_area),
        ))
        self.assertIs(
            ui_draw_sync.get_gesture_modal_session(
                types.SimpleNamespace(area=preferences_area),
            ),
            session,
        )

    def test_finishing_marker_bridges_unregister_and_final_dispatch(self):
        preview = FakeOperator("wm.gesture_preview")
        gesture = FakeOperator("wm.gesture_operator")
        GestureGpuDraw.__active_draw_instances__[1] = gesture

        self.assertTrue(ui_draw_sync.is_gesture_modal_active())

        GestureGpuDraw.__finishing_draw_instances__[id(gesture)] = gesture
        GestureGpuDraw.__active_draw_instances__.clear()
        GestureGpuDraw.__active_draw_instances__[1] = preview

        self.assertTrue(ui_draw_sync.is_gesture_modal_active())

        GestureGpuDraw.__finishing_draw_instances__.clear()

        self.assertFalse(ui_draw_sync.is_gesture_modal_active())

    def test_paused_panel_draws_only_a_disabled_status_row(self):
        layout = FakeLayout()

        ui_draw_sync.draw_heavy_panel_paused(layout, "Paused")

        self.assertEqual(len(layout.rows), 1)
        align, row = layout.rows[0]
        self.assertTrue(align)
        self.assertFalse(row.enabled)
        self.assertEqual(row.labels, [{"text": "", "icon": "BLANK1"}])

    def test_force_show_setting_overrides_real_gesture(self):
        with (
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=True),
                patch.object(ui_draw_sync, "_is_force_show_panels", return_value=True),
                patch.object(ui_draw_sync, "_schedule_modal_ui_refresh") as schedule,
        ):
            message = ui_draw_sync.heavy_panel_skip_message(object())

        self.assertIsNone(message)
        schedule.assert_not_called()

    def test_animation_pause_is_stable_across_redraws_without_a_timer(self):
        screen = types.SimpleNamespace(
            is_animation_playing=True,
            is_scrubbing=False,
        )
        context = types.SimpleNamespace(area=None, screen=screen)

        with (
                patch.object(
                    ui_draw_sync,
                    "is_gesture_modal_active",
                    return_value=False,
                ) as gesture_active,
                patch.object(ui_draw_sync, "_is_blocking_modal") as blocking_modal,
                patch.object(ui_draw_sync, "_schedule_modal_ui_refresh") as schedule,
        ):
            messages = [
                ui_draw_sync.heavy_panel_skip_message(context)
                for _index in range(20)
            ]

        self.assertEqual(messages, [ui_draw_sync._MSG_ANIMATION] * 20)
        gesture_active.assert_not_called()
        blocking_modal.assert_not_called()
        schedule.assert_not_called()

        screen.is_animation_playing = False
        # Blender's animation_playback_post handler invalidates this snapshot
        # before the stop redraw. Simulate that lifecycle transition here.
        ui_draw_sync.invalidate_playback_panel_state()
        with (
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
                patch.object(ui_draw_sync, "_is_force_show_panels", return_value=False),
                patch.object(ui_draw_sync, "_is_blocking_modal", return_value=False),
        ):
            self.assertIsNone(ui_draw_sync.heavy_panel_skip_message(context))

    def test_force_show_setting_overrides_animation(self):
        context = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(
                is_animation_playing=True,
                is_scrubbing=False,
            ),
        )
        with (
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
                patch.object(ui_draw_sync, "_is_force_show_panels", return_value=True),
        ):
            message = ui_draw_sync.heavy_panel_skip_message(context)

        self.assertIsNone(message)

    def test_playback_in_another_window_pauses_this_panel(self):
        local_screen = types.SimpleNamespace(
            is_animation_playing=False,
            is_scrubbing=False,
        )
        playing_screen = types.SimpleNamespace(
            is_animation_playing=True,
            is_scrubbing=False,
        )
        context = types.SimpleNamespace(
            area=None,
            screen=local_screen,
            window_manager=types.SimpleNamespace(
                windows=(types.SimpleNamespace(screen=local_screen),
                         types.SimpleNamespace(screen=playing_screen)),
            ),
        )

        self.assertEqual(
            ui_draw_sync.heavy_panel_skip_message(context),
            ui_draw_sync._MSG_ANIMATION,
        )

    def test_animation_freezes_full_layout_without_repeated_gesture_scans(self):
        context = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(
                is_animation_playing=True,
                is_scrubbing=False,
            ),
        )
        with patch.object(
                ui_draw_sync,
                "is_gesture_modal_active",
                return_value=False,
        ) as gesture_active:
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_ANIMATION,
            )
            for _index in range(20):
                self.assertTrue(ui_draw_sync.is_panel_layout_frozen(context))

        gesture_active.assert_not_called()

    def test_playback_freezes_schedules_before_the_first_panel_redraw(self):
        context = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(
                is_animation_playing=True,
                is_scrubbing=False,
            ),
        )
        old_context = ui_draw_sync.bpy.context
        ui_draw_sync.bpy.context = context
        try:
            self.assertEqual(ui_draw_sync._panel_pause_cache, {})
            self.assertTrue(ui_draw_sync.is_panel_layout_frozen())
        finally:
            ui_draw_sync.bpy.context = old_context

    def test_animation_snapshot_pins_selection_until_invalidation(self):
        class FakeArea:
            def as_pointer(self):
                return 71

        gesture = object()
        element = object()
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=gesture,
            active_element=element,
        )
        context = types.SimpleNamespace(
            area=FakeArea(),
            screen=types.SimpleNamespace(
                is_animation_playing=True,
                is_scrubbing=False,
            ),
        )

        with (
                patch.dict(sys.modules, {pref_module.__name__: pref_module}),
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
        ):
            self.assertEqual(
                ui_draw_sync.panel_pause_state(context),
                (ui_draw_sync._MSG_ANIMATION, True),
            )

        self.assertIs(ui_draw_sync.get_frozen_active_gesture(context), gesture)
        self.assertIs(ui_draw_sync.get_frozen_active_element(context), element)
        self.assertEqual(
            ui_draw_sync.get_frozen_ui_selection(gesture, context),
            (gesture, element),
        )
        ui_draw_sync.invalidate_playback_panel_state()
        self.assertEqual(ui_draw_sync._playback_panel_snapshots, {})

    def test_window_modal_preserves_and_disables_the_full_layout(self):
        class FakeArea:
            def as_pointer(self):
                return 72

        gesture = object()
        element = object()
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=gesture,
            active_element=element,
            draw_property=types.SimpleNamespace(
                force_show_panels_during_modal=False,
            ),
        )
        context = types.SimpleNamespace(
            area=FakeArea(),
            screen=types.SimpleNamespace(
                is_animation_playing=False,
                is_scrubbing=False,
            ),
        )
        old_window = ui_draw_sync.bpy.context.window
        ui_draw_sync.bpy.context.window = types.SimpleNamespace(
            modal_operators=[object()],
        )
        try:
            with (
                    patch.dict(sys.modules, {pref_module.__name__: pref_module}),
                    patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
                    patch.object(ui_draw_sync, "_schedule_modal_ui_refresh"),
            ):
                self.assertEqual(
                    ui_draw_sync.panel_pause_state(context),
                    (ui_draw_sync._MSG_OPERATOR, True),
                )
            self.assertIs(ui_draw_sync.get_frozen_active_gesture(context), gesture)
            self.assertIs(ui_draw_sync.get_frozen_active_element(context), element)
        finally:
            ui_draw_sync.bpy.context.window = old_window

        ui_draw_sync.invalidate_modal_panel_state()
        self.assertEqual(ui_draw_sync._modal_panel_snapshots, {})

    def test_non_playback_lifecycles_preserve_every_area_snapshot(self):
        class FakeArea:
            type = "VIEW_3D"

            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        first = ui_draw_sync._PanelContentSnapshot(
            active_gesture=object(),
            active_element=object(),
        )
        second = ui_draw_sync._PanelContentSnapshot(
            active_gesture=object(),
            active_element=object(),
        )
        ui_draw_sync._playback_panel_snapshots.update({81: first, 82: second})

        session = types.SimpleNamespace(
            area=FakeArea(81),
            _frozen_active_gesture=None,
            _frozen_ui_selection_key=None,
        )
        ui_draw_sync.release_gesture_panel_state(session)
        self.assertIs(ui_draw_sync._playback_panel_snapshots[81], first)
        self.assertIs(ui_draw_sync._playback_panel_snapshots[82], second)

        owner = types.SimpleNamespace(_modal_area=FakeArea(81))
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=object(),
            active_element=object(),
        )
        with patch.dict(sys.modules, {pref_module.__name__: pref_module}):
            ui_draw_sync.begin_panel_layout_freeze(owner)
            ui_draw_sync.end_panel_layout_freeze(owner)
        ui_draw_sync.cancel_modal_ui_refresh()

        self.assertIs(ui_draw_sync._playback_panel_snapshots[81], first)
        self.assertIs(ui_draw_sync._playback_panel_snapshots[82], second)

        ui_draw_sync.invalidate_playback_panel_state()
        self.assertEqual(ui_draw_sync._playback_panel_snapshots, {})

    def test_teardown_clears_every_frozen_panel_snapshot(self):
        ui_draw_sync._panel_layout_freezes[1] = object()
        ui_draw_sync._frozen_ui_selection[(1, 2)] = (object(), object())
        ui_draw_sync._playback_panel_snapshots[1] = (
            ui_draw_sync._PanelContentSnapshot(
                active_gesture=object(),
                active_element=object(),
            )
        )
        ui_draw_sync._modal_panel_snapshots[1] = (
            ui_draw_sync._PanelContentSnapshot(
                active_gesture=object(),
                active_element=object(),
            )
        )
        ui_draw_sync._panel_pause_cache[(1, 2)] = ('ANIMATION', 'paused', None)

        ui_draw_sync.clear_panel_layout_freezes()

        self.assertEqual(ui_draw_sync._panel_layout_freezes, {})
        self.assertEqual(ui_draw_sync._frozen_ui_selection, {})
        self.assertEqual(ui_draw_sync._playback_panel_snapshots, {})
        self.assertEqual(ui_draw_sync._modal_panel_snapshots, {})
        self.assertEqual(ui_draw_sync._panel_pause_cache, {})

    def test_playback_snapshot_pins_preview_state_across_other_invalidations(self):
        class FakeArea:
            def as_pointer(self):
                return 83

        gesture = object()
        element = object()
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=gesture,
            active_element=element,
        )
        state = types.SimpleNamespace(
            gesture_preview_active=True,
            gesture_preview_scope="ELEMENT",
        )
        session_module = types.ModuleType(f"{PACKAGE}.utils.session_state")
        session_module.SessionState = state
        context = types.SimpleNamespace(
            area=FakeArea(),
            screen=types.SimpleNamespace(
                is_animation_playing=True,
                is_scrubbing=False,
            ),
        )

        with patch.dict(sys.modules, {
                pref_module.__name__: pref_module,
                session_module.__name__: session_module,
        }):
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_ANIMATION,
            )

        state.gesture_preview_active = False
        state.gesture_preview_scope = ""
        ui_draw_sync.invalidate_panel_pause_cache()

        self.assertEqual(
            ui_draw_sync.get_frozen_preview_state(context),
            (True, "ELEMENT"),
        )

    def test_active_scrub_stays_frozen_after_finite_cache_expiry(self):
        class FakeArea:
            def as_pointer(self):
                return 72

        context = types.SimpleNamespace(
            area=FakeArea(),
            screen=types.SimpleNamespace(
                is_animation_playing=False,
                is_scrubbing=True,
            ),
        )
        cache_key = ui_draw_sync._panel_context_key(context)
        ui_draw_sync._panel_pause_cache[cache_key] = (
            'ANIMATION',
            ui_draw_sync._MSG_ANIMATION,
            -1.0,
        )

        self.assertTrue(ui_draw_sync.is_panel_layout_frozen(context))
        self.assertIn(cache_key, ui_draw_sync._panel_pause_cache)

    def test_expired_scrub_discards_area_snapshot_before_next_scrub(self):
        class FakeArea:
            def as_pointer(self):
                return 73

        first_gesture = object()
        first_element = object()
        second_gesture = object()
        second_element = object()
        selection = [first_gesture, first_element]
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=selection[0],
            active_element=selection[1],
        )
        context = types.SimpleNamespace(
            area=FakeArea(),
            screen=types.SimpleNamespace(
                is_animation_playing=False,
                is_scrubbing=True,
            ),
        )

        with (
                patch.dict(sys.modules, {pref_module.__name__: pref_module}),
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
        ):
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_ANIMATION,
            )
            cache_key = ui_draw_sync._panel_context_key(context)
            ui_draw_sync._panel_pause_cache[cache_key] = (
                'ANIMATION',
                ui_draw_sync._MSG_ANIMATION,
                -1.0,
            )
            context.screen.is_scrubbing = False
            self.assertIsNone(ui_draw_sync.heavy_panel_skip_message(context))
            self.assertNotIn(73, ui_draw_sync._playback_panel_snapshots)

            selection[:] = [second_gesture, second_element]
            context.screen.is_scrubbing = True
            # The previous idle result is also finite; advance directly to the
            # next UI pass rather than waiting in the unit test.
            ui_draw_sync._panel_pause_cache.clear()
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_ANIMATION,
            )

        self.assertIs(
            ui_draw_sync.get_frozen_active_gesture(context),
            second_gesture,
        )
        self.assertIs(
            ui_draw_sync.get_frozen_active_element(context),
            second_element,
        )

    def test_frozen_ui_selection_is_area_scoped(self):
        class FakeArea:
            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        gesture = object()
        active = object()
        owner_area = FakeArea(1)
        other_area = FakeArea(2)
        ui_draw_sync.set_frozen_ui_selection(
            gesture,
            active,
            area=owner_area,
        )

        self.assertEqual(
            ui_draw_sync.get_frozen_ui_selection(
                gesture,
                types.SimpleNamespace(area=owner_area),
            ),
            (gesture, active),
        )
        self.assertIsNone(ui_draw_sync.get_frozen_ui_selection(
            gesture,
            types.SimpleNamespace(area=other_area),
        ))
        ui_draw_sync.clear_frozen_ui_selection(gesture, area=owner_area)

    def test_area_key_zero_cleanup_does_not_clear_other_areas(self):
        gesture = object()
        zero_active = object()
        other_active = object()
        ui_draw_sync.set_frozen_ui_selection(gesture, zero_active)
        ui_draw_sync.set_frozen_ui_selection(
            gesture,
            other_active,
            area=types.SimpleNamespace(as_pointer=lambda: 22),
        )

        ui_draw_sync.clear_frozen_ui_selection(gesture, area_key=0)

        gesture_key = ui_draw_sync._rna_pointer(gesture)
        self.assertNotIn((gesture_key, 0), ui_draw_sync._frozen_ui_selection)
        self.assertIn((gesture_key, 22), ui_draw_sync._frozen_ui_selection)
        self.assertEqual(
            ui_draw_sync.get_frozen_ui_selection(
                gesture,
                types.SimpleNamespace(
                    area=types.SimpleNamespace(as_pointer=lambda: 22),
                ),
            ),
            (gesture, other_active),
        )

    def test_release_uses_captured_key_after_rna_pointers_become_invalid(self):
        class InvalidatablePointer:
            def __init__(self, pointer):
                self.pointer = pointer
                self.invalid = False

            def as_pointer(self):
                if self.invalid:
                    raise ReferenceError("RNA struct was removed")
                return self.pointer

        gesture = InvalidatablePointer(91)
        area = InvalidatablePointer(92)
        key = ui_draw_sync.set_frozen_ui_selection(
            gesture,
            object(),
            area=area,
        )
        session = types.SimpleNamespace(
            area=area,
            _frozen_active_gesture=gesture,
            _frozen_ui_selection_key=key,
        )
        gesture.invalid = True
        area.invalid = True

        ui_draw_sync.release_gesture_panel_state(session)

        self.assertEqual(ui_draw_sync._frozen_ui_selection, {})
        self.assertIsNone(session._frozen_ui_selection_key)

    def test_explicit_handoff_survives_gesture_snapshot_cleanup(self):
        class FakeArea:
            type = "VIEW_3D"

            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        gesture = object()
        gesture_element = object()
        explicit_element = object()
        other_element = object()
        owner_area = FakeArea(11)
        other_area = FakeArea(22)
        owner = types.SimpleNamespace(_modal_area=owner_area)
        owner_context = types.SimpleNamespace(area=owner_area)
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=gesture,
            active_element=explicit_element,
        )
        ui_draw_sync.set_frozen_ui_selection(
            gesture,
            gesture_element,
            area=owner_area,
        )
        ui_draw_sync.set_frozen_ui_selection(
            gesture,
            other_element,
            area=other_area,
        )

        with patch.dict(sys.modules, {pref_module.__name__: pref_module}):
            ui_draw_sync.begin_panel_layout_freeze(owner)
            self.assertEqual(
                ui_draw_sync.get_frozen_ui_selection(gesture, owner_context),
                (gesture, explicit_element),
            )

            # Simulate release_gesture_panel_state() running after the numeric
            # modal has already been invoked from the gesture finishing path.
            ui_draw_sync.clear_frozen_ui_selection(gesture, area=owner_area)
            self.assertEqual(
                ui_draw_sync.get_frozen_ui_selection(gesture, owner_context),
                (gesture, explicit_element),
            )
            ui_draw_sync.end_panel_layout_freeze(owner)

        self.assertIsNone(
            ui_draw_sync.get_frozen_ui_selection(
                gesture,
                types.SimpleNamespace(area=owner_area),
            ),
        )
        self.assertIsNotNone(
            ui_draw_sync.get_frozen_ui_selection(
                gesture,
                types.SimpleNamespace(area=other_area),
            ),
        )

    def test_explicit_handoff_inherits_the_visible_gesture_preview_row(self):
        class FakeArea:
            type = "VIEW_3D"

            def as_pointer(self):
                return 84

        area = FakeArea()
        context = types.SimpleNamespace(area=area)
        session = types.SimpleNamespace(
            area=area,
            _frozen_preview_active=True,
            _frozen_preview_scope="ELEMENT",
        )
        GestureGpuDraw.__finishing_draw_instances__[84] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )
        owner = types.SimpleNamespace(_modal_area=area)
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=object(),
            active_element=object(),
        )
        old_context = ui_draw_sync.bpy.context
        ui_draw_sync.bpy.context = context
        try:
            with patch.dict(sys.modules, {pref_module.__name__: pref_module}):
                ui_draw_sync.begin_panel_layout_freeze(owner)
            self.assertEqual(
                ui_draw_sync.get_frozen_preview_state(context),
                (True, "ELEMENT"),
            )
        finally:
            ui_draw_sync.end_panel_layout_freeze(owner)
            ui_draw_sync.bpy.context = old_context

    def test_explicit_none_snapshot_shadows_playback_and_gesture(self):
        class FakeArea:
            type = "VIEW_3D"

            def as_pointer(self):
                return 23

        area = FakeArea()
        context = types.SimpleNamespace(area=area)
        owner = types.SimpleNamespace(_modal_area=area)
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=None,
            active_element=None,
        )
        session = types.SimpleNamespace(
            area=area,
            _frozen_active_gesture=object(),
            _frozen_active_element=object(),
        )
        GestureGpuDraw.__active_draw_instances__[23] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )

        with patch.dict(sys.modules, {pref_module.__name__: pref_module}):
            ui_draw_sync.begin_panel_layout_freeze(owner)
        ui_draw_sync._playback_panel_snapshots[23] = (
            ui_draw_sync._PanelContentSnapshot(
                active_gesture=object(),
                active_element=object(),
            )
        )
        try:
            self.assertIsNone(ui_draw_sync.get_frozen_active_gesture(context))
            self.assertIsNone(ui_draw_sync.get_frozen_active_element(context))
        finally:
            ui_draw_sync.end_panel_layout_freeze(owner)

    def test_pause_source_precedence_matches_snapshot_precedence(self):
        class FakeArea:
            type = "VIEW_3D"

            def as_pointer(self):
                return 24

        area = FakeArea()
        screen = types.SimpleNamespace(
            is_animation_playing=True,
            is_scrubbing=False,
        )
        context = types.SimpleNamespace(area=area, screen=screen)
        owner = types.SimpleNamespace(_modal_area=area)
        pref_module = types.ModuleType(f"{PACKAGE}.utils.pref")
        pref_module.get_pref = lambda: types.SimpleNamespace(
            active_gesture=object(),
            active_element=object(),
        )
        GestureGpuDraw.__active_draw_instances__[24] = FakeOperator(
            "wm.gesture_operator",
            session=types.SimpleNamespace(area=area),
        )

        with patch.dict(sys.modules, {pref_module.__name__: pref_module}):
            ui_draw_sync.begin_panel_layout_freeze(owner)
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_OPERATOR,
            )
            ui_draw_sync.end_panel_layout_freeze(owner)
            self.assertEqual(
                ui_draw_sync.heavy_panel_skip_message(context),
                ui_draw_sync._MSG_ANIMATION,
            )

        screen.is_animation_playing = False
        ui_draw_sync.invalidate_playback_panel_state()
        self.assertEqual(
            ui_draw_sync.heavy_panel_skip_message(context),
            ui_draw_sync._MSG_GESTURE,
        )

    def test_preferences_context_uses_gesture_frozen_selection(self):
        class FakeArea:
            type = "VIEW_3D"

            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        owner_area = FakeArea(31)
        preferences_area = types.SimpleNamespace(type="PREFERENCES")
        gesture = object()
        active = object()
        session = types.SimpleNamespace(
            area=owner_area,
            _frozen_active_gesture=gesture,
            _frozen_active_element=active,
        )
        GestureGpuDraw.__active_draw_instances__[31] = FakeOperator(
            "wm.gesture_operator",
            session=session,
        )

        self.assertEqual(
            ui_draw_sync.get_frozen_ui_selection(
                gesture,
                types.SimpleNamespace(area=preferences_area),
            ),
            (gesture, active),
        )

    def test_released_gesture_does_not_leave_a_cached_session(self):
        session = types.SimpleNamespace(
            area=types.SimpleNamespace(as_pointer=lambda: 41),
            _frozen_active_gesture=object(),
        )
        operator = FakeOperator("wm.gesture_operator", session=session)
        GestureGpuDraw.__active_draw_instances__[41] = operator
        context = types.SimpleNamespace(area=session.area)

        self.assertIs(ui_draw_sync.get_gesture_modal_session(context), session)
        GestureGpuDraw.__active_draw_instances__.clear()
        ui_draw_sync.release_gesture_panel_state(session)

        self.assertIsNone(ui_draw_sync.get_gesture_modal_session(context))

    def test_ui_refresh_tags_owner_regions_in_all_windows(self):
        class FakeRegion:
            def __init__(self, region_type):
                self.type = region_type
                self.redraws = 0

            def tag_redraw(self):
                self.redraws += 1

        view_ui = FakeRegion("UI")
        view_window = FakeRegion("WINDOW")
        pref_window = FakeRegion("WINDOW")
        view_area = types.SimpleNamespace(
            type="VIEW_3D",
            regions=(view_ui, view_window),
        )
        preferences_area = types.SimpleNamespace(
            type="PREFERENCES",
            regions=(pref_window,),
        )
        windows = (
            types.SimpleNamespace(
                screen=types.SimpleNamespace(areas=(view_area,)),
            ),
            types.SimpleNamespace(
                screen=types.SimpleNamespace(areas=(preferences_area,)),
            ),
        )
        old_manager = ui_draw_sync.bpy.context.window_manager
        ui_draw_sync.bpy.context.window_manager = types.SimpleNamespace(
            windows=windows,
        )
        try:
            ui_draw_sync.tag_gesture_ui_regions()
        finally:
            ui_draw_sync.bpy.context.window_manager = old_manager

        self.assertEqual(view_ui.redraws, 1)
        self.assertEqual(view_window.redraws, 0)
        self.assertEqual(pref_window.redraws, 1)

    def test_idle_cache_coalesces_modal_stack_scans_in_one_ui_pass(self):
        context = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(
                is_animation_playing=False,
                is_scrubbing=False,
            ),
        )
        with (
                patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
                patch.object(ui_draw_sync, "_is_force_show_panels", return_value=False),
                patch.object(ui_draw_sync, "_is_blocking_modal", return_value=False) as blocking_modal,
        ):
            for _index in range(10):
                self.assertIsNone(ui_draw_sync.heavy_panel_skip_message(context))

        blocking_modal.assert_called_once_with()

    def test_explicit_drag_freeze_preserves_layout_without_modal_polling(self):
        owner = object()
        context = types.SimpleNamespace(
            area=None,
            screen=types.SimpleNamespace(
                is_animation_playing=False,
                is_scrubbing=False,
            ),
        )

        ui_draw_sync.begin_panel_layout_freeze(owner)
        try:
            with (
                    patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False),
                    patch.object(ui_draw_sync, "_is_blocking_modal") as blocking_modal,
                    patch.object(ui_draw_sync, "_schedule_modal_ui_refresh") as schedule,
            ):
                self.assertTrue(ui_draw_sync.is_panel_layout_frozen())
                self.assertEqual(
                    ui_draw_sync.heavy_panel_skip_message(context),
                    ui_draw_sync._MSG_OPERATOR,
                )
            blocking_modal.assert_not_called()
            schedule.assert_not_called()
        finally:
            ui_draw_sync.end_panel_layout_freeze(owner)

        with patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=False):
            self.assertFalse(ui_draw_sync.is_panel_layout_frozen())

    def test_explicit_drag_freeze_is_scoped_to_its_view3d(self):
        class FakeArea:
            type = "VIEW_3D"

            def __init__(self, pointer):
                self.pointer = pointer

            def as_pointer(self):
                return self.pointer

        owner_area = FakeArea(1)
        other_area = FakeArea(2)
        owner = types.SimpleNamespace(_modal_area=owner_area)

        ui_draw_sync.begin_panel_layout_freeze(owner)
        try:
            self.assertTrue(ui_draw_sync.is_panel_layout_frozen(
                types.SimpleNamespace(area=owner_area),
            ))
            self.assertFalse(ui_draw_sync.is_panel_layout_frozen(
                types.SimpleNamespace(area=other_area),
            ))
        finally:
            ui_draw_sync.end_panel_layout_freeze(owner)

    def test_explicit_finish_cancels_pending_ui_refresh(self):
        timer = types.SimpleNamespace()
        ui_draw_sync._modal_ui_refresh_fn = timer
        with (
                patch.object(
                    ui_draw_sync.bpy.app.timers,
                    "is_registered",
                    return_value=True,
                    create=True,
                ),
                patch.object(
                    ui_draw_sync.bpy.app.timers,
                    "unregister",
                    create=True,
                ) as unregister,
        ):
            ui_draw_sync.cancel_modal_ui_refresh()

        self.assertIsNone(ui_draw_sync._modal_ui_refresh_fn)
        unregister.assert_called_once_with(timer)

    def test_modal_refresh_is_coalesced_while_gesture_is_active(self):
        registered = []
        with patch.object(
                ui_draw_sync.bpy.app.timers,
                "register",
                side_effect=lambda fn, **_kwargs: registered.append(fn),
                create=True,
        ):
            with patch.object(ui_draw_sync, "is_gesture_modal_active", return_value=True):
                ui_draw_sync._schedule_modal_ui_refresh()
                first = ui_draw_sync._modal_ui_refresh_fn
                ui_draw_sync._schedule_modal_ui_refresh()

        self.assertIsNotNone(first)
        self.assertIs(ui_draw_sync._modal_ui_refresh_fn, first)
        self.assertEqual(registered, [first])

    def test_modal_refresh_tags_regions_once_after_gesture_ends(self):
        registered = []
        with patch.object(
                ui_draw_sync.bpy.app.timers,
                "register",
                side_effect=lambda fn, **_kwargs: registered.append(fn),
                create=True,
        ), patch.object(
                ui_draw_sync,
                "is_gesture_modal_active",
                side_effect=(True, False),
        ), patch.object(
                ui_draw_sync,
                "_is_force_show_panels",
                return_value=False,
        ), patch.object(
                ui_draw_sync,
                "_is_blocking_modal",
                return_value=False,
        ), patch.object(
                ui_draw_sync,
                "_is_animation_busy",
                return_value=False,
        ), patch.object(ui_draw_sync, "tag_gesture_ui_regions") as tag_regions:
            ui_draw_sync._schedule_modal_ui_refresh()
            poll = registered[0]

            self.assertEqual(poll(), 0.12)
            self.assertIs(ui_draw_sync._modal_ui_refresh_fn, poll)
            self.assertIsNone(poll())

        self.assertIsNone(ui_draw_sync._modal_ui_refresh_fn)
        tag_regions.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
