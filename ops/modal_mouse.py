import bpy
import gpu
from bl_operators.wm import operator_value_undo_return
from bpy.app.translations import pgettext
from bpy.props import StringProperty, EnumProperty
from mathutils import Vector

from ..utils.enum import ENUM_NUMBER_VALUE_CHANGE_MODE
from ..utils.public import (
    by_path_set_value,
    PublicMouseModal,
    debug_print,
    poll_addon_preferences,
    tag_redraw,
)
from ..utils.expression import resolve_context_path
from ..utils.public_gpu import PublicGpu


class StoreValue:
    ___value___ = None

    def __store__(self):
        self.___value___ = resolve_context_path(bpy.context, self.data_path)

    def __restore__(self):
        by_path_set_value(bpy.context, self.data_path.split("."), self.___value___)


class ModalMouseOperator(bpy.types.Operator, StoreValue, PublicMouseModal, PublicGpu):
    """
    from bl_operators.wm import WM_OT_context_modal_mouse
    scripts/startup/bl_operators/wm.py
    """
    bl_idname = 'wm.gesture_modal_mouse_operator'
    bl_label = 'Adjust Value with Mouse'
    bl_description = 'Drag the mouse to change a property value on a data path'
    bl_options = {'GRAB_CURSOR', 'BLOCKING', 'UNDO', 'INTERNAL'}

    data_path: StringProperty(
        name="Data Path",
        options={'SKIP_SAVE'},
    )
    header_text: StringProperty(
        name="Header Text",
        description="Text to display in the header while dragging",
        options={'SKIP_SAVE'},
        default="Header Text",
    )
    value_mode: EnumProperty(
        items=ENUM_NUMBER_VALUE_CHANGE_MODE[1:],
        name="Value Mode",
        description="How to interpret the value",
        options={'SKIP_SAVE'},
    )
    mouse = None
    last_mouse = None
    _draw_handle = None
    _draw_space_cls = None
    _display_text = ""
    _overlay_mouse = None

    @classmethod
    def poll(cls, context):
        if not poll_addon_preferences(cls):
            return False
        if context.window is None:
            cls.poll_message_set("A window context is required")
            return False
        if context.area is None:
            cls.poll_message_set("An editor area is required")
            return False
        return True

    @property
    def __header_text__(self) -> str:
        if self.header_text.count("%") == 1:
            return self.header_text
        else:
            sp = self.data_path.split(".")
            try:
                if len(sp) > 1:
                    a, b = sp[:-1], sp[-1]
                    prop = resolve_context_path(bpy.context, '.'.join(a)).rna_type.properties[b]
                    name = pgettext(prop.name)
                    if prop.type == 'INT':
                        return f"{name} %d"
                    elif prop.type == 'FLOAT':
                        return f"{name} %.2f"

                    return f"{name} %s"
            except Exception as _:
                ...
        return "value %"

    def _format_display_text(self, *, value=None, delta=None) -> str:
        header_text = self.__header_text__
        if not header_text:
            return ""
        try:
            if value is not None and self.___value___ is not None:
                return header_text % value
            if delta is not None:
                return (header_text % delta) + pgettext(" (delta)")
        except Exception as e:
            return f"header_text Text Error:{header_text} {value} {e.args}"
        return header_text

    def _set_display_text(self, context, text: str, *, mouse: Vector | None = None) -> None:
        self._display_text = text
        if mouse is not None:
            self._overlay_mouse = mouse.copy()
        if context.area is not None:
            context.area.header_text_set(text or None)
        tag_redraw()

    def _mouse_overlay_position(self) -> Vector | None:
        mouse = self._overlay_mouse
        if mouse is None:
            return None
        scale = bpy.context.preferences.view.ui_scale
        return Vector((mouse.x + 12 * scale, mouse.y + 18 * scale))

    def draw_mouse_overlay(self):
        text = self._display_text
        if not text:
            return

        position = self._mouse_overlay_position()
        if position is None:
            return

        scale = bpy.context.preferences.view.ui_scale
        size = int(12 * scale)

        gpu.state.blend_set('ALPHA')
        from ..utils.blf_text import measure_text
        # Metric line height: the pill no longer jumps while the value text
        # changes between digits, descenders, or CJK property names.
        width, line_h = measure_text(text, size)
        padding = 8 * scale
        # draw_rounded_rectangle_area is centered on `position`; keep text in the same space.
        box_w = width + padding * 2
        box_h = line_h + padding
        self.draw_rounded_rectangle_area(
            position,
            color=(0.0, 0.0, 0.0, 0.65),
            width=box_w,
            height=box_h,
            radius=int(4 * scale),
        )
        # draw_text places the line-box top at the given position.
        text_x = position.x - width / 2
        text_y = position.y + line_h / 2
        self.draw_text(text, position=(text_x, text_y), size=size)

    def register_draw(self, context):
        if self._draw_handle is not None:
            return
        space_type = getattr(context.area, "type", "VIEW_3D")
        space_cls = getattr(bpy.types, f"Space{space_type}", None)
        if space_cls is None:
            space_cls = bpy.types.SpaceView3D
        self._draw_space_cls = space_cls
        self._draw_handle = space_cls.draw_handler_add(
            self.draw_mouse_overlay, (), 'WINDOW', 'POST_PIXEL')

    def unregister_draw(self):
        if self._draw_handle is None:
            return
        space_cls = self._draw_space_cls or bpy.types.SpaceView3D
        try:
            space_cls.draw_handler_remove(self._draw_handle, 'WINDOW')
        except (ValueError, RuntimeError):
            pass
        self._draw_handle = None
        self._draw_space_cls = None
        tag_redraw()

    def invoke(self, context, event):
        self.__store__()
        debug_print("invoke", self.bl_idname, self.___value___, self.data_path, key='modal')
        if self.___value___ is None:
            return {'CANCELLED'}

        self.start_mouse(event)
        self._overlay_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        initial_value = resolve_context_path(context, self.data_path)
        self._set_display_text(
            context,
            self._format_display_text(value=initial_value),
            mouse=self._overlay_mouse,
        )
        self.register_draw(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        et = event.type

        vm = self.value_mode
        self.set_cursor(context, vm)
        overlay_mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        if et == 'MOUSEMOVE':
            delta = self.value_delta(event, vm)
            if type(self.___value___) == int:
                value = int(round(self.___value___ + delta))
            else:
                value = self.___value___ + delta
            by_path_set_value(bpy.context, self.data_path.split("."), value)
            current_value = resolve_context_path(context, self.data_path)
            self._set_display_text(
                context,
                self._format_display_text(value=current_value),
                mouse=overlay_mouse,
            )

        elif 'LEFTMOUSE' == et or event.value == "RELEASE":
            self.exit()
            return operator_value_undo_return(self.___value___)

        elif et in {'RIGHTMOUSE', 'ESC'}:
            self.__restore__()
            self.exit()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def exit(self):
        self.unregister_draw()
        self._display_text = ""
        self._overlay_mouse = None
        super().exit()
