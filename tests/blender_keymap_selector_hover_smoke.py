"""Focused Blender smoke for example keymaps and preview hover treatments."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
from mathutils import Vector


REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY.parent))

assert bpy.ops.preferences.addon_enable(module="gesture_helper") == {"FINISHED"}
print("KEYMAP_SELECTOR_HOVER_SMOKE_STAGE addon_enabled", flush=True)

from gesture_helper.gesture.gesture_keymap import GestureKeymap  # noqa: E402
from gesture_helper.ops.export_import import Export  # noqa: E402
from gesture_helper.ops.quick_add.draw_gpu import DrawGpu  # noqa: E402
from gesture_helper.src.translate import __name_translate__  # noqa: E402
from gesture_helper.utils import gesture_persistence  # noqa: E402
from gesture_helper.utils.gesture_store import get_gesture_store  # noqa: E402
from gesture_helper.utils.public import get_pref  # noqa: E402


def view3d_override():
    window = bpy.context.window
    screen = window.screen
    area = next(area for area in screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    return {
        "window": window,
        "screen": screen,
        "area": area,
        "region": region,
    }


store = get_gesture_store()
assert store is not None
store.gesture.clear()
GestureKeymap.key_all_unload()
view_preferences = bpy.context.preferences.view
show_number_arrows_property = view_preferences.bl_rna.properties.get(
    "show_number_arrows"
)
original_show_number_arrows = (
    bool(view_preferences.show_number_arrows)
    if show_number_arrows_property is not None
    else None
)

try:
    if show_number_arrows_property is not None:
        view_preferences.show_number_arrows = True
    gesture = store.gesture.add()
    gesture.name = "Focused Object Mode Smoke"
    gesture.enabled = False
    gesture.key_string = json.dumps({"type": "RIGHTMOUSE", "value": "PRESS"})
    gesture.keymaps_string = json.dumps(["3D View", "Object Mode"])

    assert not gesture.key_load(force=True)
    addon_config = bpy.context.window_manager.keyconfigs.addon
    registered = {
        keymap.name
        for keymap in addon_config.keymaps
        for item in keymap.keymap_items
        if (
            item.idname == "wm.gesture_operator"
            and getattr(item.properties, "gesture", "") == gesture.name
        )
    }
    assert registered == {"3D View", "Object Mode"}, registered
    print("KEYMAP_SELECTOR_HOVER_SMOKE_STAGE keymaps_registered", flush=True)

    override = view3d_override()
    region = override["region"]
    draw_gpu = DrawGpu()
    fake_ops = SimpleNamespace(
        offset_position=Vector((
            region.x + region.width - 20.0,
            region.y + region.height * 0.5,
        )),
        offset=Vector((0.0, 0.0)),
        mouse_position=Vector((-1e6, -1e6)),
        _preview_renderer="RADIAL",
        tag_redraw=lambda: None,
    )
    event = SimpleNamespace(
        type="TIMER",
        value="NOTHING",
        mouse_x=-1000000,
        mouse_y=-1000000,
    )
    with bpy.context.temp_override(**override):
        assert draw_gpu.draw_run(fake_ops, event) == set()
        selector = draw_gpu.gesture_bpu
        selector._ensure_layout()
        close = next(
            node
            for node in selector._walk()
            if node.operator == "wm.gesture_preview_close"
        )
        assert abs(close.rect[2] - selector.root.rect[2]) < 0.001
        assert close.tooltip == __name_translate__("Close Preview")
        close_center = (
            (close.rect[0] + close.rect[2]) * 0.5,
            (close.rect[1] + close.rect[3]) * 0.5,
        )
        assert selector.sync_input(
            fake_ops.offset_position - fake_ops.offset,
            close_center,
        )
        assert selector.hover_tooltip == __name_translate__("Close Preview")
        print("KEYMAP_SELECTOR_HOVER_SMOKE_STAGE selector_verified", flush=True)

        numeric = gesture.element.add()
        numeric.element_type = "PROPERTY"
        numeric.__init_element__()
        assert numeric.numeric_arrows_visible
        token = object()
        numeric._gesture_layout_token = token
        numeric.publish_numeric_arrow_areas((10.0, 20.0, 110.0, 44.0), 24.0)
        numeric.ops = SimpleNamespace(
            direction_element=None,
            distance=0.0,
            session=SimpleNamespace(
                layout_token=token,
                draw_ctx=SimpleNamespace(mouse_region=(50.0, 32.0)),
                _numeric_pressed_element=None,
            ),
        )
        numeric.ops.session.draw_ctx.mouse_region = (12.0, 32.0)
        assert tuple(numeric.text_color) == tuple(
            get_pref().draw_property.text_default_color
        )
        numeric.ops.session.draw_ctx.mouse_region = (50.0, 32.0)
        assert tuple(numeric.text_color) == tuple(
            get_pref().draw_property.text_active_color
        )
        print("KEYMAP_SELECTOR_HOVER_SMOKE_STAGE numeric_hover_verified", flush=True)
finally:
    if original_show_number_arrows is not None:
        view_preferences.show_number_arrows = original_show_number_arrows
    GestureKeymap.key_all_unload()
    store.gesture.clear()
    gesture_persistence.save_gestures_to_disk = lambda **_kwargs: None
    Export.backups = lambda *_args, **_kwargs: None
    assert bpy.ops.preferences.addon_disable(module="gesture_helper") == {"FINISHED"}

print(
    "KEYMAP_SELECTOR_HOVER_SMOKE_OK "
    f"Blender {bpy.app.version_string}"
)
