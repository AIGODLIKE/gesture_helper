import bpy
from bl_operators.wm import operator_value_undo_return
from bpy.app.translations import pgettext
from bpy.props import StringProperty, FloatProperty, EnumProperty
from bpy.types import Operator
from mathutils import Vector

from ..utils.enum import CREATE_ELEMENT_VALUE_MODE_ENUM
from ..utils.string_eval import try_call_eval


class StoreValue:
    ___value___ = None

    def __store__(self):
        self.___value___ = try_call_eval(f'bpy.context.{self.data_path}')

    def __restore__(self):
        setattr(self, self.data_path, self.___value___)


class ModalMouseOperator(Operator, StoreValue):
    """
    from bl_operators.wm import WM_OT_context_modal_mouse
    scripts/startup/bl_operators/wm.py
    """
    bl_idname = 'gesture.modal_mouse_operator'
    bl_label = 'Mouse Modal Modify Value'
    bl_options = {'GRAB_CURSOR', 'BLOCKING', 'UNDO', 'INTERNAL'}

    data_path: StringProperty(
        name="数据路径",
        options={'SKIP_SAVE'},
    )

    header_text: StringProperty(
        name="Header Text",
        description="Text to display in header during scale",
        options={'SKIP_SAVE'},
        default="Header Text",
    )
    input_scale: FloatProperty(
        description="Scale the mouse movement by this value before applying the delta",
        default=0.01,
        options={'SKIP_SAVE'},
    )
    value_mode: EnumProperty(
        items=CREATE_ELEMENT_VALUE_MODE_ENUM[1:],
        name="Value Mode",
        description="How to interpret the value",
        options={'SKIP_SAVE'},
    )
    mouse = None

    @property
    def __header_text__(self) -> str:
        if self.header_text.count("%") == 1:
            return self.header_text
        else:
            sp = self.data_path.split(".")
            try:
                if len(sp) > 1:
                    a, b = sp[:-1], sp[-1]
                    prop = try_call_eval(f"bpy.context.{'.'.join(a)}").rna_type.properties[b]
                    name = pgettext(prop.name)
                    if prop.type == 'INT':
                        return f"{name} %d"
                    elif prop.type == 'FLOAT':
                        return f"{name} %.2f"

                    return f"{name} %s"
            except Exception as _:
                ...
        return "value %"

    def __init__(self):
        super().__init__()

    def invoke(self, context, event):
        self.__store__()
        print("invoke", self.bl_idname, self.___value___, self.data_path)
        if self.___value___ is None:
            return {'CANCELLED'}
        else:
            self.mouse = Vector((event.mouse_x, event.mouse_y))
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def modal(self, context, event):
        print("modal", self.bl_idname, self.___value___, self.data_path, f"\tmodal\t{event.value}\t{event.type}",
              "\tprev", event.type_prev,
              event.value_prev)
        event_type = event.type

        self.set_cursor(context)

        if event_type == 'MOUSEMOVE':
            delta = self.value_delta(event)
            header_text = self.__header_text__
            if header_text:
                value = try_call_eval(f"bpy.context.{self.data_path}")
                try:
                    if self.___value___ is not None:
                        header_text = header_text % value
                    else:
                        header_text = (self.__header_text__ % delta) + pgettext(" (delta)")
                except Exception:
                    header_text = f"header_text Text Error:{header_text} {value}"
                context.area.header_text_set(header_text)

        elif 'LEFTMOUSE' == event_type or event.value == "RELEASE":
            self.exit()
            return operator_value_undo_return(self.___value___)

        elif event_type in {'RIGHTMOUSE', 'ESC'}:
            self.__restore__()
            self.exit()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    @staticmethod
    def exit():
        bpy.context.area.header_text_set(None)
        bpy.context.window.cursor_set("DEFAULT")

    def set_cursor(self, context):
        cursor = {
            "MOUSE_CHANGES_HORIZONTAL": "MOVE_X",
            "MOUSE_CHANGES_VERTICAL": "MOVE_Y",
            "MOUSE_CHANGES_ARBITRARY": "SCROLL_XY"}
        context.window.cursor_set(cursor[self.value_mode])

    def value_delta(self, event):
        delta = self.get_delta(event) * self.input_scale

        if type(self.___value___) == int:
            exec("bpy.context.{:s} = int({:d})".format(self.data_path, round(self.___value___ + delta)))
        else:
            exec("bpy.context.{:s} = {:f}".format(self.data_path, self.___value___ + delta))
        return delta

    def get_delta(self, event):
        vm = self.value_mode
        if vm == "MOUSE_CHANGES_HORIZONTAL":
            return event.mouse_x - self.mouse.x
        elif vm == "MOUSE_CHANGES_VERTICAL":
            return event.mouse_y - self.mouse.y
        elif vm == "MOUSE_CHANGES_ARBITRARY":
            x = event.mouse_x - self.mouse.x
            y = event.mouse_y - self.mouse.y
            if x > y:
                return max(x, y)
            else:
                return min(x, y)
        else:
            raise ValueError("Invalid value mode: %r" % vm)
            # active_annotation_layer.annotation_opacity
