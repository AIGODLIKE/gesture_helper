"""Blender background smoke test for the unified preview lifecycle."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))


assert bpy.ops.preferences.addon_enable(module='gesture_helper') == {'FINISHED'}

from gesture_helper.gesture.gesture_draw_gpu import GestureGpuDraw  # noqa: E402
from gesture_helper.gesture.menu import GestureMenuRuntime  # noqa: E402
from gesture_helper.ops.quick_add.gesture_preview import GesturePreview  # noqa: E402
from gesture_helper.utils.gesture_persistence import suppress_gesture_disk_save  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.selection import select_element  # noqa: E402
from gesture_helper.utils.session_state import SessionState  # noqa: E402


# Background Blender has no current wmEvent, so INVOKE_DEFAULT never calls a
# modal operator's Python invoke callback. Add a test-only execute callback
# while keeping Blender responsible for constructing the real RNA instance.
original_invoke = GesturePreview.invoke


def preview_event(region, event_type='NONE'):
    return SimpleNamespace(
        type=event_type,
        type_prev='NONE',
        value='PRESS',
        mouse_x=int(region.x + region.width * 0.5),
        mouse_y=int(region.y + region.height * 0.5),
        mouse_region_x=int(region.width * 0.5),
        mouse_region_y=int(region.height * 0.5),
        alt=False,
        ctrl=False,
        shift=False,
    )


def preview_test_execute(self, context):
    event = preview_event(context.region)
    return original_invoke(self, context, event)


bpy.utils.unregister_class(GesturePreview)
GesturePreview.execute = preview_test_execute
bpy.utils.register_class(GesturePreview)

preview_rna = bpy.ops.wm.gesture_preview.get_rna_type().properties
assert preview_rna.get('gesture') is not None
assert preview_rna.get('scope') is not None
assert bpy.types.Operator.bl_rna_get_subclass_py('WM_OT_gesture_preview') is not None
assert bpy.types.Operator.bl_rna_get_subclass_py('WM_OT_gesture_preview_close') is not None

window = bpy.context.window
area = next(candidate for candidate in window.screen.areas if candidate.type == 'VIEW_3D')
region = next(candidate for candidate in area.regions if candidate.type == 'WINDOW')
override = {'window': window, 'area': area, 'region': region}


def assert_preview_globals_clean() -> None:
    assert not SessionState.gesture_preview_active
    assert SessionState.gesture_preview_instance is None
    assert SessionState.gesture_preview_scope == ''
    assert not GesturePreview._active_by_window
    assert not GesturePreview._active_by_area
    assert not GesturePreview._draw_handles
    assert not GestureGpuDraw.__active_draw_instances__


def assert_preview_clean(instance) -> None:
    assert_preview_globals_clean()
    assert instance._preview_event_timer is None


def start_preview(scope, renderer):
    with bpy.context.temp_override(**override):
        result = bpy.ops.wm.gesture_preview('EXEC_DEFAULT', scope=scope)
    assert result == {'RUNNING_MODAL'}, (scope, renderer, result)
    instance = SessionState.gesture_preview_instance
    assert instance is not None
    assert SessionState.gesture_preview_scope == scope
    assert instance._preview_renderer == renderer
    return instance


def close_preview(instance) -> None:
    with bpy.context.temp_override(**override):
        assert bpy.ops.wm.gesture_preview_close('EXEC_DEFAULT') == {'FINISHED'}
    assert instance._preview_close_requested
    with bpy.context.temp_override(**override):
        assert instance.modal(
            bpy.context,
            preview_event(region, 'TIMER'),
        ) == {'FINISHED'}
    assert_preview_clean(instance)


store = get_gesture_store()
assert store is not None
with suppress_gesture_disk_save():
    store.gesture.clear()
    gesture = store.gesture.add()
    gesture.name = 'Preview Smoke'
    gesture.gesture_type = 'RADIAL'
    first = gesture.element.add()
    first.element_type = 'OPERATOR'
    first.__init_element__()
    first.name = 'First'
    second = gesture.element.add()
    second.element_type = 'BOX'
    second.__init_element__()
    second.name = 'Second'
    nested = second.element.add()
    nested.element_type = 'OPERATOR'
    nested.__init_element__()
    nested.name = 'Nested'
    store.index_gesture = 0
    select_element(first)

    radial_preview = start_preview('GESTURE', 'RADIAL')
    gesture.gesture_type = 'MENU'
    with bpy.context.temp_override(**override):
        assert radial_preview.modal(
            bpy.context,
            preview_event(region, 'TIMER'),
        ) == {'PASS_THROUGH'}
    assert radial_preview._preview_renderer == 'MENU'
    assert not GestureMenuRuntime._active_by_window
    assert not GestureMenuRuntime._active_by_area
    gesture.gesture_type = 'RADIAL'
    with bpy.context.temp_override(**override):
        assert radial_preview.modal(
            bpy.context,
            preview_event(region, 'TIMER'),
        ) == {'PASS_THROUGH'}
    assert radial_preview._preview_renderer == 'RADIAL'
    close_preview(radial_preview)

    gesture.gesture_type = 'MENU'
    menu_preview = start_preview('GESTURE', 'MENU')
    assert not GestureMenuRuntime._active_by_window
    assert not GestureMenuRuntime._active_by_area
    menu_preview._ensure_layout(force=True)
    assert {row.label for row in menu_preview._menu_panels[0].rows} >= {
        'First',
        'Nested',
    }
    root_rect = menu_preview._menu_panels[0].rect
    root_center = (
        (root_rect[0] + root_rect[2]) * 0.5,
        (root_rect[1] + root_rect[3]) * 0.5,
    )
    assert abs(root_center[0] - region.width * 0.5) < 0.01, root_center
    assert abs(root_center[1] - region.height * 0.5) < 0.01, root_center
    close_preview(menu_preview)

    gesture.gesture_type = 'RADIAL'
    select_element(first)
    element_preview = start_preview('ELEMENT', 'ELEMENT')
    first_pointer = element_preview._element_preview_adapter.element.as_pointer()
    select_element(second)
    with bpy.context.temp_override(**override):
        assert element_preview.modal(
            bpy.context,
            preview_event(region, 'TIMER'),
        ) == {'PASS_THROUGH'}
    second_pointer = element_preview._element_preview_adapter.element.as_pointer()
    assert first_pointer != second_pointer
    assert second_pointer == second.as_pointer()
    leaf_pointers = {
        leaf.as_pointer()
        for leaf in element_preview._element_preview_adapter.panel_leaf_items
    }
    assert nested.as_pointer() in leaf_pointers
    assert element_preview.scope == 'ELEMENT'
    close_preview(element_preview)

shutdown_preview = start_preview('GESTURE', 'RADIAL')
assert bpy.ops.preferences.addon_disable(module='gesture_helper') == {'FINISHED'}
assert_preview_globals_clean()
print('BLENDER_PREVIEW_SMOKE_OK')
