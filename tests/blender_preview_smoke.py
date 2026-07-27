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
from gesture_helper.gesture.runtime_tooltip import (  # noqa: E402
    sync_hover_tooltip,
)
from gesture_helper.element.element_tooltip import (  # noqa: E402
    build_runtime_tooltip,
)
from gesture_helper.ops.quick_add.gesture_preview import GesturePreview  # noqa: E402
from gesture_helper.ui import ui_list  # noqa: E402
from gesture_helper.utils.gesture_persistence import suppress_gesture_disk_save  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402
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
assert bpy.types.Operator.bl_rna_get_subclass_py(
    'WM_OT_gesture_element_tree_page'
) is not None
assert bpy.types.Menu.bl_rna_get_subclass_py(
    'GESTURE_MT_main_action_menu'
) is not None

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
    for element in instance.session._element_proxy_pool.values():
        assert getattr(element, 'ops', None) is not instance
    state = instance.session.tooltip_state
    assert state.target is None
    assert state.timer is None
    menu_state = getattr(instance, '_menu_tooltip_state', None)
    if menu_state is not None:
        assert menu_state.target is None
        assert menu_state.timer is None


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


class FakeUILayout:
    def __init__(self):
        self.enabled = True
        self.ui_units_x = 0.0
        self.labels = []

    def row(self, **_kwargs):
        return self

    def column(self, **_kwargs):
        return self

    def label(self, *, text='', **_kwargs):
        self.labels.append(text)

    def operator(self, *_args, **_kwargs):
        return SimpleNamespace()


store = get_gesture_store()
assert store is not None
assert get_pref().gesture_property.hover_tooltip_delay == 100
with suppress_gesture_disk_save():
    store.gesture.clear()
    gesture = store.gesture.add()
    gesture.name = 'Preview Smoke'
    gesture.gesture_type = 'RADIAL'
    first = gesture.element.add()
    first.element_type = 'OPERATOR'
    first.__init_element__()
    first.name = 'First'
    first.operator_bl_idname = 'object.metaball_add'
    first.operator_properties = "{'type': 'CAPSULE'}"
    first.operator_context = 'EXEC_DEFAULT'
    first.enabled_icon = True
    first.icon = 'GESTURE_HELPER_SMOKE_MISSING_ICON'

    tooltip = build_runtime_tooltip(first, preview_read_only=True)
    details = {detail.label: detail.value for detail in tooltip.details}
    assert details['Operator ID'] == 'object.metaball_add'
    assert "'type': 'CAPSULE'" in details['Parameters']
    assert details['Context'] == 'EXEC_DEFAULT'
    assert details['Python'] == "bpy.ops.object.metaball_add(type='CAPSULE')"
    assert details['Icon'] == 'GESTURE_HELPER_SMOKE_MISSING_ICON'
    assert 'Icon not found: GESTURE_HELPER_SMOKE_MISSING_ICON' in tooltip.issues
    assert tooltip.color_role == 'warning'

    empty_layout = gesture.element.add()
    empty_layout.element_type = 'BOX'
    empty_layout.__init_element__()
    empty_layout.name = 'Empty Layout'
    empty_nested = empty_layout.element.add()
    empty_nested.element_type = 'COLUMN'
    empty_nested.__init_element__()
    assert tuple(empty_nested.layout_panel_content_size) == (0.0, 0.0)
    assert tuple(empty_layout.layout_panel_content_size) == (0.0, 0.0)
    empty_layout.draw_gpu_layout_panel(SimpleNamespace(session=None))
    assert empty_layout.extension_draw_area is None
    gesture.element.remove(len(gesture.element) - 1)

    view = bpy.context.preferences.view
    previous_language = view.language
    previous_translate_interface = view.use_translate_interface
    view.language = 'zh_HANS'
    view.use_translate_interface = True
    native_rna = first.operator_func.get_rna_type()
    assert first.source_name_translate != native_rna.name
    assert first.source_description != native_rna.description
    view.language = previous_language
    view.use_translate_interface = previous_translate_interface

    second = gesture.element.add()
    second.element_type = 'BOX'
    second.__init_element__()
    second.name = 'Second'
    assert second.layout_align is True
    assert second.bl_rna.properties['layout_align'] is not None
    alignment_items = {
        item.identifier
        for item in second.bl_rna.properties['layout_alignment'].enum_items
    }
    assert alignment_items == {'EXPAND', 'LEFT', 'CENTER', 'RIGHT'}
    nested = second.element.add()
    nested.element_type = 'OPERATOR'
    nested.__init_element__()
    nested.name = 'Nested'

    exported_gesture = next(iter(get_pref().get_gesture_data(get_all=True).values()))
    exported_box = next(
        item for item in exported_gesture['element'].values()
        if item.get('name') == 'Second'
    )
    assert 'layout_align' not in exported_box
    second.layout_align = False
    exported_gesture = next(iter(get_pref().get_gesture_data(get_all=True).values()))
    exported_box = next(
        item for item in exported_gesture['element'].values()
        if item.get('name') == 'Second'
    )
    assert exported_box['layout_align'] is False
    second.layout_align = True

    page_root = gesture.element.add()
    page_root.element_type = 'COLUMN'
    page_root.__init_element__()
    page_root.name = 'Paged Tree'
    page_root.show_child = True
    for index in range(64):
        item = page_root.element.add()
        item.element_type = 'OPERATOR'
        item.__init_element__()
        item.name = f'Paged {index + 1}'

    store.index_gesture = 0
    select_element(first)

    descendants = ui_list._visible_tree_descendants(page_root)
    assert len(descendants) == 64
    assert ui_list._visible_tree_descendants(page_root) is descendants
    page_root.show_child = False
    page_root.show_child = True
    refreshed_descendants = ui_list._visible_tree_descendants(page_root)
    assert refreshed_descendants is not descendants
    descendants = refreshed_descendants
    page_context = SimpleNamespace(area=area)
    original_draw_item = type(page_root).draw_item
    type(page_root).draw_item = lambda self, layout, **kwargs: None
    try:
        page_layout = FakeUILayout()
        ui_list.ElementUIList._draw_tree_page(
            page_context,
            page_layout,
            page_root,
            descendants,
            active=first,
            frozen=False,
        )
        assert '1-32 / 64' in page_layout.labels
        with bpy.context.temp_override(**override):
            assert bpy.ops.wm.gesture_element_tree_page(
                'EXEC_DEFAULT',
                root_pointer=str(page_root.as_pointer()),
                page=1,
            ) == {'FINISHED'}
        page_layout = FakeUILayout()
        ui_list.ElementUIList._draw_tree_page(
            page_context,
            page_layout,
            page_root,
            descendants,
            active=first,
            frozen=False,
        )
        assert '33-64 / 64' in page_layout.labels
    finally:
        type(page_root).draw_item = original_draw_item
    gesture.element.remove(len(gesture.element) - 1)
    ui_list.clear_element_tree_cache(clear_pages=True)

    radial_preview = start_preview('GESTURE', 'RADIAL')
    assert radial_preview.session.phase.shows_radial_ui
    assert radial_preview.session._gesture_timeout_timer is None
    assert not radial_preview.trajectory_mouse_move
    radial_tooltip_state = radial_preview.session.tooltip_state
    assert sync_hover_tooltip(
        radial_tooltip_state,
        first,
        delay_ms=100,
        redraw=lambda: None,
    )
    assert radial_tooltip_state.timer is not None
    assert bpy.app.timers.is_registered(radial_tooltip_state.timer)
    gesture.gesture_type = 'MENU'
    with bpy.context.temp_override(**override):
        assert radial_preview.modal(
            bpy.context,
            preview_event(region, 'TIMER'),
        ) == {'PASS_THROUGH'}
    assert radial_preview._preview_renderer == 'MENU'
    assert radial_tooltip_state.target is None
    assert radial_tooltip_state.timer is None
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
    assert GesturePreview._active_by_area.get(area.as_pointer()) is menu_preview
    assert menu_preview.gpu.gesture_bpu.root.children
    assert menu_preview.gpu.tips.root.children
    with bpy.context.temp_override(**override):
        menu_preview.gpu.gesture_bpu._ensure_layout()
        menu_preview.gpu.tips._ensure_layout()
    for overlay in (menu_preview.gpu.gesture_bpu, menu_preview.gpu.tips):
        x1, y1, x2, y2 = overlay.root.rect
        assert x2 > region.x and x1 < region.x + region.width, overlay.root.rect
        assert y2 > region.y and y1 < region.y + region.height, overlay.root.rect
    menu_preview._ensure_layout(force=True)
    assert menu_preview._menu_panels
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
    original_draw_menu = GestureMenuRuntime._draw_menu
    overlay_layout_type = type(menu_preview.gpu.gesture_bpu)
    original_draw_overlay = overlay_layout_type.__gpu_draw__
    drawn_overlays = []
    GestureMenuRuntime._draw_menu = (
        lambda self: setattr(self, '_menu_draw_count', self._menu_draw_count + 1)
    )
    overlay_layout_type.__gpu_draw__ = lambda self: drawn_overlays.append(self)
    try:
        with bpy.context.temp_override(**override):
            assert bpy.context.area == area
            assert GesturePreview._menu_context_instance() is menu_preview
            GesturePreview._draw_callback()
    finally:
        GestureMenuRuntime._draw_menu = original_draw_menu
        overlay_layout_type.__gpu_draw__ = original_draw_overlay
    assert menu_preview._menu_last_draw_error == '', menu_preview._menu_last_draw_error
    assert menu_preview._menu_draw_count > 0
    assert menu_preview.gpu.tips in drawn_overlays
    assert menu_preview.gpu.gesture_bpu in drawn_overlays

    press = preview_event(region, 'SPACE')
    press.value = 'PRESS'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, press) == {'RUNNING_MODAL'}
    old_anchor = menu_preview._menu_anchor
    move = preview_event(region, 'MOUSEMOVE')
    move.mouse_x += 24
    move.mouse_y -= 12
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, move) == {'RUNNING_MODAL'}
    assert menu_preview._menu_anchor == (old_anchor[0] + 24, old_anchor[1] - 12)
    release = preview_event(region, 'SPACE')
    release.value = 'RELEASE'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, release) == {'RUNNING_MODAL'}
    assert menu_preview._menu_drag_mouse is None
    assert menu_preview._sync_menu_tooltip(first)
    menu_tooltip_state = menu_preview._menu_tooltip_state
    assert menu_tooltip_state.timer is not None
    assert bpy.app.timers.is_registered(menu_tooltip_state.timer)
    close_preview(menu_preview)
    assert menu_tooltip_state.target is None
    assert menu_tooltip_state.timer is None

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
