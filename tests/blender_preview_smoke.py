"""Blender background smoke test for the unified preview lifecycle."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))


assert bpy.ops.preferences.addon_enable(module='gesture_helper') == {'FINISHED'}

from gesture_helper.gesture.gesture_draw_gpu import GestureGpuDraw  # noqa: E402
from gesture_helper.gesture.gesture_session import GestureSession  # noqa: E402
from gesture_helper.gesture.menu import GestureMenuRuntime  # noqa: E402
from gesture_helper.gesture.runtime_tooltip import (  # noqa: E402
    sync_hover_tooltip,
)
from gesture_helper.element.element_tooltip import (  # noqa: E402
    build_runtime_tooltip,
)
from gesture_helper.element.extension_hit import (  # noqa: E402
    numeric_property_arrow_direction,
    numeric_property_arrow_part,
)
from gesture_helper.ops.quick_add.draw_gpu import (  # noqa: E402
    SELECTOR_INACTIVE_ALPHA,
    SELECTOR_SCALE,
)
from gesture_helper.ops.quick_add.gesture_preview import GesturePreview  # noqa: E402
from gesture_helper.ops.export_import import Export  # noqa: E402
from gesture_helper.ui import ui_list  # noqa: E402
from gesture_helper.utils.gesture_persistence import suppress_gesture_disk_save  # noqa: E402
from gesture_helper.utils import gesture_persistence  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.input_event import POINTER_MOVE_EVENT_TYPES  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402
from gesture_helper.utils.public_cache import PublicCacheFunc  # noqa: E402
from gesture_helper.utils.color import color_to_gpu, color_to_srgb  # noqa: E402
from gesture_helper.utils.number_arrows import (  # noqa: E402
    NUMBER_PART_DECREMENT,
    NUMBER_PART_INCREMENT,
    NUMBER_PART_VALUE,
    show_number_arrows,
)
from gesture_helper.utils.layout_alignment import (  # noqa: E402
    resolve_extension_row_bounds,
    resolve_split_line,
    separator_line_width,
)
from gesture_helper.utils.selection import select_element  # noqa: E402
from gesture_helper.utils.session_state import SessionState  # noqa: E402
from gesture_helper.utils.ui_theme import THEME_PRESETS  # noqa: E402


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
assert bpy.types.Operator.bl_rna_get_subclass_py(
    'WM_OT_gesture_element_select'
) is not None
assert bpy.types.Menu.bl_rna_get_subclass_py(
    'GESTURE_MT_main_action_menu'
) is not None
live_event_types = {
    item.identifier
    for item in bpy.types.Event.bl_rna.properties['type'].enum_items
}
assert POINTER_MOVE_EVENT_TYPES == {
    'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE',
}
assert POINTER_MOVE_EVENT_TYPES <= live_event_types

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
    assert getattr(instance, '_menu_animation_timer', None) is None
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
    if instance._preview_renderer == 'MENU':
        assert instance._menu_closing_at > 0.0
        # A synthetic background close may occur in the first clock tick of
        # the open transition, in which case there is no visible alpha to
        # fade. The regular elapsed-open close path is covered by unit tests.
        assert 0.0 <= instance._menu_close_start_reveal <= 1.0
        assert instance._menu_animation_timer is not None
        assert bpy.app.timers.is_registered(instance._menu_animation_timer)
        # The reveal curve itself is unit-tested. Finish through the normal
        # modal cleanup path without sleeping in this background smoke test.
        instance._menu_close_requested = True
    else:
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
gesture_preferences = get_pref().gesture_property
assert gesture_preferences.bl_rna.properties['hover_tooltip_delay'].default == 300
gesture_preferences.hover_tooltip_delay = 300
draw_preferences = get_pref().draw_property
theme_rna = draw_preferences.bl_rna.properties['theme_preset']
assert theme_rna.default == 'BLENDER_DARK'
assert {
    item.identifier for item in theme_rna.enum_items
} == {*THEME_PRESETS, 'CUSTOM'}
draw_preferences.theme_preset = 'MINIMAL_DARK'
assert all(
    abs(actual - expected) < 1e-6
    for actual, expected in zip(
        draw_preferences.overlay_background_color,
        THEME_PRESETS['MINIMAL_DARK']['overlay_background_color'],
    )
)
draw_preferences.interaction_hover_color = (0.31, 0.19, 0.47, 1.0)
assert draw_preferences.theme_preset == 'CUSTOM'
draw_preferences.theme_preset = 'BLENDER_DARK'
view_preferences = bpy.context.preferences.view
if view_preferences.bl_rna.properties.get('show_number_arrows') is not None:
    view_preferences.show_number_arrows = True
assert show_number_arrows(bpy.context)
with suppress_gesture_disk_save():
    store.gesture.clear()
    gesture = store.gesture.add()
    gesture.name = 'Preview Smoke'
    gesture.gesture_type = 'RADIAL'
    assert gesture.menu_keep_open is True
    assert gesture.bl_rna.properties['menu_keep_open'].default is True
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

    single_flyout = gesture.element.add()
    single_flyout.element_type = 'CHILD_GESTURE'
    single_flyout.__init_element__()
    single_flyout.name = 'Single Surface'
    single_action = single_flyout.element.add()
    single_action.element_type = 'OPERATOR'
    single_action.__init_element__()
    single_action.name = 'Single Action'
    single_action.operator_bl_idname = 'view3d.view_all'
    flyout_ops = SimpleNamespace(session=None)
    single_flyout.ops = flyout_ops
    assert single_flyout._uses_single_extension_surface()
    flyout_layout = single_flyout._compute_extension_layout()
    panel_rect = (
        -flyout_layout.margin_x,
        -flyout_layout.content_h - flyout_layout.margin_y,
        flyout_layout.content_w + flyout_layout.margin_x,
        flyout_layout.margin_y,
    )
    action_rect = resolve_extension_row_bounds(
        flyout_layout.content_w,
        flyout_layout.row_h,
        flyout_layout.margin_x,
        flyout_layout.margin_y,
        fill_outer_surface=True,
    )
    assert panel_rect == action_rect, (panel_rect, action_rect)
    gesture.element.remove(len(gesture.element) - 1)

    view = bpy.context.preferences.view
    previous_language = view.language
    previous_translate_interface = view.use_translate_interface
    view.language = 'zh_HANS'
    view.use_translate_interface = True
    assert bpy.app.translations.pgettext_iface('Preview Gesture') != 'Preview Gesture'
    assert bpy.app.translations.pgettext_iface('Preview Element') != 'Preview Element'
    assert bpy.app.translations.pgettext_iface('Gesture Preview') != 'Gesture Preview'
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
    assert second.layout_round_corners is True
    assert second.layout_align_separators is True
    assert second.bl_rna.properties['layout_round_corners'] is not None
    assert second.bl_rna.properties['layout_align_separators'] is not None
    alignment_items = {
        item.identifier
        for item in second.bl_rna.properties['layout_alignment'].enum_items
    }
    assert alignment_items == {
        'EXPAND',
        'LEFT',
        'CENTER',
        'RIGHT',
        'TEXT_LEFT',
        'TEXT_CENTER',
        'TEXT_RIGHT',
    }
    layout_type_items = {
        item.identifier
        for item in bpy.ops.wm.gesture_layout_type_set.get_rna_type()
        .properties['layout_type'].enum_items
    }
    assert layout_type_items == {'ROW', 'COLUMN', 'BOX', 'SPLIT'}
    nested = second.element.add()
    nested.element_type = 'OPERATOR'
    nested.__init_element__()
    nested.name = 'Nested'
    divider = second.element.add()
    divider.element_type = 'DIVIDING_LINE'
    divider.__init_element__()
    layout_metrics = second._layout_metrics()
    divider_size = second._layout_node_size(divider, layout_metrics)
    expected_divider_height = second._layout_separator_height(layout_metrics)
    assert abs(divider_size.y - expected_divider_height) < 0.001
    assert abs(
        divider_size.y
        - separator_line_width(
            draw_preferences.dividing_line_height,
            second._element_ui_scale(),
        )
    ) < 0.001
    assert divider_size.y < layout_metrics.sep_h

    label = second.element.add()
    label.element_type = 'LABEL'
    label.__init_element__()
    label.name = 'Split Ratio'
    assert label.is_label
    assert not label.is_layout_container
    label_size = second._layout_node_size(label, layout_metrics)
    assert abs(label_size.x - label.text_dimensions[0]) < 0.001
    assert abs(label_size.y - layout_metrics.row_h) < 0.001

    split = second.element.add()
    split.___set_properties___({
        'name': 'Native Split',
        'element_type': 'SPLIT',
        'split_factor': 0.35,
    })
    assert split.is_split
    assert split.is_layout_container
    assert split.layout_align is False
    assert abs(split.split_factor - 0.35) < 0.001
    split_label = split.element.add()
    split_label.element_type = 'LABEL'
    split_label.__init_element__()
    split_label.name = '35%'
    split_action = split.element.add()
    split_action.element_type = 'OPERATOR'
    split_action.__init_element__()
    split_action.name = '65% Action'
    split_action.operator_bl_idname = 'view3d.view_all'
    split_size = second._layout_node_size(split, layout_metrics)
    split_gap = second._layout_gap_for(split, layout_metrics)
    assert split_gap > 0.0
    split_slots = resolve_split_line(
        2,
        split_size.x,
        split_gap,
        split.split_factor,
    )
    assert abs(
        split_slots[0][1] - (split_size.x - split_gap) * 0.35
    ) < 0.001

    render_session = GestureSession()
    render_ops = SimpleNamespace(session=render_session)
    second.ops = render_ops
    assert second._layout_node_is_stable(second)
    # Blender 4.3 disables GPU matrix queries in background mode. The visual
    # matrix is an independent cache-key input, so pin only that boundary while
    # exercising the real registered RNA/style/hover signature.
    with patch.object(
            type(second),
            '_layout_matrix_signature',
            return_value=(1.0,) * 16,
    ):
        first_render_key = second._layout_render_signature(
            layout_metrics,
            render_session,
        )
        render_session.extension_hover = [nested]
        hover_render_key = second._layout_render_signature(
            layout_metrics,
            render_session,
        )
    assert hover_render_key != first_render_key
    render_session.layout_token = object()
    second._restore_retained_layout_hits(render_session, (nested, split_action))
    assert second._layout_visible_token is render_session.layout_token
    assert nested._gesture_layout_token is render_session.layout_token
    assert split_action._gesture_layout_token is render_session.layout_token
    render_session._layout_render_cache[
        second._layout_node_cache_key(second)
    ] = (first_render_key, object(), ())
    render_session.release_element_proxies(owner=render_ops)
    assert not render_session._layout_render_cache
    second.ops = None

    numeric = gesture.element.add()
    numeric.element_type = 'PROPERTY'
    numeric.__init_element__()
    numeric.ops = render_ops
    assert not numeric._layout_node_is_stable(numeric)
    numeric.ops = None
    assert numeric.display_property_type in {'INT', 'FLOAT'}
    assert numeric.numeric_arrows_visible

    original_path = numeric.property_data_path
    resolution = bpy.context.scene.render
    original_percentage = resolution.resolution_percentage
    numeric.property_data_path = 'scene.render.resolution_percentage'
    percentage_default = resolution.bl_rna.properties[
        'resolution_percentage'
    ].default
    resolution.resolution_percentage = max(1, percentage_default - 1)
    assert numeric.reset_display_property_to_default()
    assert resolution.resolution_percentage == percentage_default
    assert not numeric.reset_display_property_to_default()
    resolution.resolution_percentage = original_percentage

    original_transparency = resolution.film_transparent
    numeric.property_data_path = 'scene.render.film_transparent'
    transparency_default = resolution.bl_rna.properties[
        'film_transparent'
    ].default
    resolution.film_transparent = not transparency_default
    assert numeric.reset_display_property_to_default()
    assert resolution.film_transparent is transparency_default
    assert not numeric.reset_display_property_to_default()
    resolution.film_transparent = original_transparency

    previous_active = bpy.context.view_layer.objects.active
    previous_selected = tuple(bpy.context.selected_objects)
    light_data = bpy.data.lights.new('Gesture Helper Numeric Smoke', 'POINT')
    light_object = bpy.data.objects.new('Gesture Helper Numeric Smoke', light_data)
    bpy.context.scene.collection.objects.link(light_object)
    for selected_object in previous_selected:
        selected_object.select_set(False)
    light_object.select_set(True)
    bpy.context.view_layer.objects.active = light_object
    try:
        numeric.property_data_path = 'object.data.energy'
        numeric.property_wheel_step = 1.0
        energy_rna = light_data.bl_rna.properties['energy']
        assert energy_rna.hard_min < energy_rna.soft_min
        assert energy_rna.hard_max > energy_rna.soft_max

        light_data.energy = 10.0
        assert numeric.apply_property_drag(10.0, 1.0)
        assert abs(light_data.energy - 10.1) < 1e-4
        assert numeric.apply_property_drag(light_data.energy, -1_000_000_000.0)
        assert light_data.energy == energy_rna.soft_min
        assert not numeric.apply_property_wheel(-1)

        light_data.energy = energy_rna.soft_max
        assert not numeric.apply_property_drag(energy_rna.soft_max, 1.0)
        assert not numeric.apply_property_wheel(1)

        light_data.energy = energy_rna.soft_max + 10.0
        outside_soft_start = light_data.energy
        assert numeric.apply_property_drag(outside_soft_start, 1.0)
        assert outside_soft_start < light_data.energy <= outside_soft_start + 0.25
    finally:
        bpy.data.objects.remove(light_object, do_unlink=True)
        bpy.data.lights.remove(light_data)
        for selected_object in previous_selected:
            selected_object.select_set(True)
        bpy.context.view_layer.objects.active = previous_active
    numeric.property_data_path = original_path

    token = object()
    numeric._gesture_layout_token = token
    numeric.publish_numeric_arrow_areas((10.0, 20.0, 110.0, 44.0), 24.0)
    numeric_ops = SimpleNamespace(session=SimpleNamespace(layout_token=token))
    assert numeric_property_arrow_direction(
        numeric,
        numeric_ops,
        mouse=(12.0, 32.0),
    ) == -1
    assert numeric_property_arrow_direction(
        numeric,
        numeric_ops,
        mouse=(108.0, 32.0),
    ) == 1
    assert numeric_property_arrow_part(
        numeric,
        numeric_ops,
        mouse=(12.0, 32.0),
    ) == NUMBER_PART_DECREMENT
    assert numeric_property_arrow_part(
        numeric,
        numeric_ops,
        mouse=(50.0, 32.0),
    ) == NUMBER_PART_VALUE
    assert numeric_property_arrow_part(
        numeric,
        numeric_ops,
        mouse=(108.0, 32.0),
    ) == NUMBER_PART_INCREMENT
    numeric_ops.direction_element = None
    numeric_ops.distance = 0.0
    numeric_ops.session.draw_ctx = SimpleNamespace(mouse_region=(12.0, 32.0))
    numeric.ops = numeric_ops
    assert tuple(numeric.text_color) == tuple(draw_preferences.text_default_color)
    numeric_ops.session.draw_ctx = SimpleNamespace(mouse_region=(50.0, 32.0))
    numeric.ops = numeric_ops
    assert tuple(numeric.text_color) == tuple(draw_preferences.text_active_color)

    exported_gesture = next(iter(get_pref().get_gesture_data(get_all=True).values()))
    exported_box = next(
        item for item in exported_gesture['element'].values()
        if item.get('name') == 'Second'
    )
    assert 'layout_align' not in exported_box
    assert 'layout_round_corners' not in exported_box
    assert 'layout_align_separators' not in exported_box
    exported_split = next(
        item for item in exported_box['element'].values()
        if item.get('element_type') == 'SPLIT'
    )
    assert abs(exported_split['split_factor'] - 0.35) < 0.001
    assert 'layout_align' not in exported_split
    second.layout_align = False
    second.layout_round_corners = False
    second.layout_align_separators = False
    exported_gesture = next(iter(get_pref().get_gesture_data(get_all=True).values()))
    exported_box = next(
        item for item in exported_gesture['element'].values()
        if item.get('name') == 'Second'
    )
    assert exported_box['layout_align'] is False
    assert exported_box['layout_round_corners'] is False
    assert exported_box['layout_align_separators'] is False
    second.layout_align = True
    second.layout_round_corners = True
    second.layout_align_separators = True

    page_root = gesture.element.add()
    page_root.element_type = 'COLUMN'
    page_root.__init_element__()
    page_root.name = 'Paged Tree'
    page_root.show_child = True
    nested_select_parent = page_root.element.add()
    nested_select_parent.element_type = 'COLUMN'
    nested_select_parent.__init_element__()
    nested_select_parent.name = 'Nested Select Parent'
    nested_select_parent.show_child = True
    nested_select_group = nested_select_parent.element.add()
    nested_select_group.element_type = 'COLUMN'
    nested_select_group.__init_element__()
    nested_select_group.name = 'Nested Select Group'
    nested_select_group.show_child = True
    nested_select_target = nested_select_group.element.add()
    nested_select_target.element_type = 'OPERATOR'
    nested_select_target.__init_element__()
    nested_select_target.name = 'Nested Select Target'
    nested_select_target.operator_bl_idname = 'view3d.view_all'
    for index in range(61):
        item = page_root.element.add()
        item.element_type = 'OPERATOR'
        item.__init_element__()
        item.name = f'Paged {index + 1}'

    store.index_gesture = 0
    PublicCacheFunc.cache_clear()
    select_element(first)

    descendants = ui_list._visible_tree_descendants(page_root)
    assert len(descendants) == 64
    assert ui_list._visible_tree_descendants(page_root) is descendants
    page_root.show_child = False
    page_root.show_child = True
    refreshed_descendants = ui_list._visible_tree_descendants(page_root)
    assert refreshed_descendants is not descendants
    descendants = refreshed_descendants
    select_context = SimpleNamespace(
        gesture_select_element=nested_select_target,
    )
    assert ui_list.ElementSelect.execute(None, select_context) == {'FINISHED'}
    assert nested_select_target.radio
    assert (
        get_pref().active_element.as_pointer()
        == nested_select_target.as_pointer()
    )
    assert sum(item.radio for item in gesture.element_iteration) == 1
    # A radio action is one-way: clicking the selected row again must not
    # toggle it off and leave the property editor without a visible element.
    assert ui_list.ElementSelect.execute(None, select_context) == {'FINISHED'}
    assert nested_select_target.radio
    assert (
        get_pref().active_element.as_pointer()
        == nested_select_target.as_pointer()
    )
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
    assert abs(
        radial_preview.session.draw_ctx.ui_scale
        - view_preferences.ui_scale
    ) < 0.001
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
    enum_property = gesture.element.add()
    enum_property.element_type = 'PROPERTY'
    enum_property.__init_element__()
    enum_property.name = 'Shading'
    enum_property.property_data_path = 'space_data.shading.type'
    with bpy.context.temp_override(**override):
        assert enum_property.display_property_type == 'ENUM'
    menu_preview = start_preview('GESTURE', 'MENU')
    assert abs(
        menu_preview._metrics().scale
        - view_preferences.ui_scale
    ) < 0.001
    menu_colors = menu_preview._colors()
    assert menu_colors.row == menu_colors.background
    assert not GestureMenuRuntime._active_by_window
    assert not GestureMenuRuntime._active_by_area
    assert GesturePreview._active_by_area.get(area.as_pointer()) == (menu_preview,)
    selector = menu_preview.gpu.gesture_bpu
    assert selector.root.children
    assert abs(selector.font_size - 12 * SELECTOR_SCALE) < 0.001
    assert abs(selector.padding - 3 * SELECTOR_SCALE) < 0.001
    assert abs(selector.min_row_height - 20 * SELECTOR_SCALE) < 0.001
    assert abs(selector.gap - 2 * SELECTOR_SCALE) < 0.001
    assert abs(selector.corner_radius - 4 * SELECTOR_SCALE) < 0.001
    assert selector.root_draggable
    selector._cached_batch_sig = ('stale-theme',)
    draw_preferences.theme_preset = 'MINIMAL_DARK'
    selector._sync_theme()
    assert selector._cached_batch_sig is None
    assert all(
        abs(component - reference) < 1e-6
        for component, reference in zip(
            selector.background,
            color_to_gpu(draw_preferences.overlay_background_color),
        )
    )
    draw_preferences.theme_preset = 'BLENDER_DARK'
    selector._sync_theme()
    for actual, expected in (
        (selector.background, color_to_gpu(draw_preferences.overlay_background_color)),
        (selector.row_color, color_to_gpu(draw_preferences.background_operator_color)),
        (selector.header_color, color_to_gpu(draw_preferences.overlay_header_color)),
        (selector.hover_color, color_to_gpu(draw_preferences.interaction_hover_color)),
        (selector.pressed_color, color_to_gpu(draw_preferences.interaction_pressed_color)),
        (
            selector.active_color,
            color_to_gpu(draw_preferences.background_operator_active_color),
        ),
        (selector.text_color, color_to_srgb(draw_preferences.text_default_color)),
        (selector.text_hover_color, color_to_srgb(draw_preferences.text_active_color)),
        (selector.separator_color, color_to_gpu(draw_preferences.dividing_line_color)),
    ):
        assert all(
            abs(component - reference) < 1e-6
            for component, reference in zip(actual, expected)
        ), (actual, expected)
    selector_nodes = tuple(selector._walk())
    selector_close = next(
        node
        for node in selector_nodes
        if (
            node.kind == 'OPERATOR'
            and node.operator == 'wm.gesture_preview_close'
        )
    )
    assert selector_close.text == 'X'
    assert selector_close.tooltip == 'Close Preview'
    selector_title = selector.root.children[0].children[0]
    assert selector_title.kind == 'LABEL'
    assert not selector_title.draggable
    assert not any(
        node.draggable
        for node in selector_nodes
    )
    selector_items = tuple(
        node
        for node in selector_nodes
        if node.kind == 'OPERATOR' and node.operator == 'wm.context_set_int'
    )
    assert selector_items
    assert all(node.fill_width for node in selector_items)
    assert all(
        abs(node.alpha_multiplier - SELECTOR_INACTIVE_ALPHA) < 0.001
        for node in selector_items
    )
    assert menu_preview.gpu.tips.root.children
    assert menu_preview.gpu.tips.anchor == 'TOP_LEFT_REGION'
    assert menu_preview.gpu.tips.root_draggable
    assert 0.0 <= menu_preview._menu_animation_reveal() < 1.0
    assert menu_preview._menu_animation_timer is not None
    assert bpy.app.timers.is_registered(menu_preview._menu_animation_timer)
    with bpy.context.temp_override(**override):
        selector._ensure_layout()
        menu_preview.gpu.tips._ensure_layout()
    selector_title_row = selector.root.children[0]
    assert abs(selector_title_row.rect[2] - selector.root.rect[2]) < 0.001
    assert abs(selector_close.rect[2] - selector.root.rect[2]) < 0.001
    selector.sync_input(
        selector._base_offset_position,
        (
            (selector_close.rect[0] + selector_close.rect[2]) * 0.5,
            (selector_close.rect[1] + selector_close.rect[3]) * 0.5,
        ),
    )
    assert selector.hover_tooltip == 'Close Preview'
    tips = menu_preview.gpu.tips
    assert abs(tips.root.rect[0] - (region.x + tips.padding * 2)) < 0.001
    assert abs(
        tips.root.rect[3]
        - (region.y + region.height - tips.padding * 2)
    ) < 0.001
    assert all(
        abs(node.rect[2] - selector.root.rect[2]) < 0.001
        for node in selector_items
    )
    tips_before = tips.drag_offset.copy()
    tips_x = int((tips.root.rect[0] + tips.root.rect[2]) * 0.5)
    tips_y = int((tips.root.rect[1] + tips.root.rect[3]) * 0.5)
    tips_press = preview_event(region, 'LEFTMOUSE')
    tips_press.mouse_x = tips_x
    tips_press.mouse_y = tips_y
    tips_press.value = 'PRESS'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, tips_press) == {'RUNNING_MODAL'}
    tips_move = preview_event(region, 'MOUSEMOVE')
    tips_move.mouse_x = tips_x + 18
    tips_move.mouse_y = tips_y - 9
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, tips_move) == {'RUNNING_MODAL'}
    assert tuple(tips.drag_offset) == (
        tips_before.x + 18,
        tips_before.y - 9,
    )
    tips_release = preview_event(region, 'LEFTMOUSE')
    tips_release.mouse_x = tips_move.mouse_x
    tips_release.mouse_y = tips_move.mouse_y
    tips_release.value = 'RELEASE'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, tips_release) == {'RUNNING_MODAL'}
    assert tips._drag_mouse is None
    for overlay in (menu_preview.gpu.gesture_bpu, menu_preview.gpu.tips):
        x1, y1, x2, y2 = overlay.root.rect
        assert x2 > region.x and x1 < region.x + region.width, overlay.root.rect
        assert y2 > region.y and y1 < region.y + region.height, overlay.root.rect
    with bpy.context.temp_override(**override):
        menu_preview._ensure_layout(force=True)
        assert menu_preview._menu_panels
        assert {row.label for row in menu_preview._menu_panels[0].rows} >= {
            'First',
            'Nested',
        }
        assert any(
            row.element == enum_property
            for row in menu_preview._menu_panels[0].rows
        )
        enum_row = next(
            row
            for row in menu_preview._menu_panels[0].rows
            if row.element == enum_property
        )
        assert menu_preview._toggle_menu_enum_dropdown(enum_row)
        assert len(menu_preview._menu_panels) >= 2
        assert any(
            row.kind == 'ENUM_ITEM' and row.enum_active
            for row in menu_preview._menu_panels[-1].rows
        )
        assert menu_preview._close_menu_enum_dropdown()
    numeric_row = next(
        row
        for row in menu_preview._menu_panels[0].rows
        if row.kind == 'PROPERTY'
    )
    nx1, ny1, nx2, ny2 = numeric_row.rect
    center_y = (ny1 + ny2) * 0.5
    assert menu_preview._menu_number_part(
        numeric_row,
        (nx1 + 3.0, center_y),
    ) == NUMBER_PART_DECREMENT
    assert menu_preview._menu_number_part(
        numeric_row,
        ((nx1 + nx2) * 0.5, center_y),
    ) == NUMBER_PART_VALUE
    assert menu_preview._menu_number_part(
        numeric_row,
        (nx2 - 3.0, center_y),
    ) == NUMBER_PART_INCREMENT
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

    selector = menu_preview.gpu.gesture_bpu
    selector._ensure_layout()
    selector_action = next(
        node
        for node in selector._walk()
        if node.operator == 'wm.context_set_int'
    )
    ax1, ay1, ax2, ay2 = selector_action.rect
    action_press = preview_event(region, 'LEFTMOUSE')
    action_press.mouse_x = int((ax1 + ax2) * 0.5)
    action_press.mouse_y = int((ay1 + ay2) * 0.5)
    action_press.value = 'PRESS'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, action_press) == {'RUNNING_MODAL'}
    assert selector._pressed is selector_action
    assert selector._node_fill(selector_action) == selector.pressed_color
    action_release = preview_event(region, 'LEFTMOUSE')
    action_release.mouse_x = int(ax2 + 50.0)
    action_release.mouse_y = int(ay2 + 50.0)
    action_release.value = 'RELEASE'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, action_release) == {'RUNNING_MODAL'}
    assert selector._pressed is None

    sx1, sy1, sx2, sy2 = selector_title.rect
    selector_press = preview_event(region, 'LEFTMOUSE')
    selector_press.mouse_x = int((sx1 + sx2) * 0.5)
    selector_press.mouse_y = int((sy1 + sy2) * 0.5)
    selector_press.value = 'PRESS'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, selector_press) == {'RUNNING_MODAL'}
    selector_before = selector.drag_offset.copy()
    selector_move = preview_event(region, 'MOUSEMOVE')
    selector_move.mouse_x = selector_press.mouse_x + 18
    selector_move.mouse_y = selector_press.mouse_y - 9
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, selector_move) == {'RUNNING_MODAL'}
    assert tuple(selector.drag_offset) == (
        selector_before.x + 18,
        selector_before.y - 9,
    )
    assert selector.drag_revision > 0
    selector_release = preview_event(region, 'LEFTMOUSE')
    selector_release.mouse_x = selector_move.mouse_x
    selector_release.mouse_y = selector_move.mouse_y
    selector_release.value = 'RELEASE'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, selector_release) == {'RUNNING_MODAL'}
    assert selector._drag_mouse is None

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
    menu_preview._ensure_layout(force=True)
    header_rect = menu_preview._menu_panels[0].header_rect
    hx1, hy1, hx2, hy2 = header_rect
    header_press = preview_event(region, 'LEFTMOUSE')
    # Menu geometry is region-local; wmEvent coordinates are window-local.
    header_press.mouse_x = int(region.x + hx1 + (hx2 - hx1) * 0.35)
    header_press.mouse_y = int(region.y + (hy1 + hy2) * 0.5)
    header_press.value = 'PRESS'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, header_press) == {'RUNNING_MODAL'}
    header_anchor = menu_preview._menu_anchor
    header_move = preview_event(region, 'INBETWEEN_MOUSEMOVE')
    header_move.mouse_x = header_press.mouse_x - 11
    header_move.mouse_y = header_press.mouse_y + 7
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, header_move) == {'RUNNING_MODAL'}
    assert menu_preview._menu_anchor == (
        header_anchor[0] - 11,
        header_anchor[1] + 7,
    )
    header_release = preview_event(region, 'LEFTMOUSE')
    header_release.mouse_x = header_move.mouse_x
    header_release.mouse_y = header_move.mouse_y
    header_release.value = 'RELEASE'
    with bpy.context.temp_override(**override):
        assert menu_preview.modal(bpy.context, header_release) == {'RUNNING_MODAL'}
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
    assert split_action.as_pointer() in leaf_pointers
    assert element_preview.scope == 'ELEMENT'
    close_preview(element_preview)

shutdown_preview = start_preview('GESTURE', 'RADIAL')
# The preview smoke owns synthetic gesture data and must not persist it while
# verifying unregister cleanup. This also keeps the smoke independent of user
# folder permissions.
gesture_persistence.save_gestures_to_disk = lambda **_kwargs: None
Export.backups = lambda *_args, **_kwargs: None
assert bpy.ops.preferences.addon_disable(module='gesture_helper') == {'FINISHED'}
assert_preview_globals_clean()
print('BLENDER_PREVIEW_SMOKE_OK')
