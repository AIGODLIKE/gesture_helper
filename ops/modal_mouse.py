import bpy
from bl_operators.wm import operator_value_undo_return
from bpy.app.translations import pgettext
from bpy.props import StringProperty, EnumProperty

from ..utils.enum import ENUM_NUMBER_VALUE_CHANGE_MODE
from ..utils.public import by_path_set_value, PublicMouseModal
from ..utils.secure_call import secure_call_eval


class StoreValue:
    ___value___ = None

    def __store__(self):
        self.___value___ = secure_call_eval(f'bpy.context.{self.data_path}')

    def __restore__(self):
        setattr(self, self.data_path, self.___value___)


class ModalMouseOperator(bpy.types.Operator, StoreValue, PublicMouseModal):
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
    value_mode: EnumProperty(
        items=ENUM_NUMBER_VALUE_CHANGE_MODE[1:],
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
                    prop = secure_call_eval(f"bpy.context.{'.'.join(a)}").rna_type.properties[b]
                    name = pgettext(prop.name)
                    if prop.type == 'INT':
                        return f"{name} %d"
                    elif prop.type == 'FLOAT':
                        return f"{name} %.2f"

                    return f"{name} %s"
            except Exception as _:
                ...
        return "value %"

    def invoke(self, context, event):
        self.__store__()
        print("invoke", self.bl_idname, self.___value___, self.data_path)
        if self.___value___ is None:
            return {'CANCELLED'}
        else:
            self.start_mouse(event)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def modal(self, context, event):
        et = event.type

        vm = self.value_mode
        self.set_cursor(context, vm)

        if et == 'MOUSEMOVE':
            delta = self.value_delta(event, vm)
            if type(self.___value___) == int:
                value = int(round(self.___value___ + delta))
            else:
                value = self.___value___ + delta
            by_path_set_value(bpy.context, self.data_path.split("."), value)
            header_text = self.__header_text__
            if header_text:
                value = secure_call_eval(f"bpy.context.{self.data_path}")
                try:
                    if self.___value___ is not None:
                        header_text = header_text % value
                    else:
                        header_text = (self.__header_text__ % delta) + pgettext(" (delta)")
                except Exception as e:
                    header_text = f"header_text Text Error:{header_text} {value} {e.args}"
                context.area.header_text_set(header_text)

        elif 'LEFTMOUSE' == et or event.value == "RELEASE":
            self.exit()
            return operator_value_undo_return(self.___value___)

        elif et in {'RIGHTMOUSE', 'ESC'}:
            self.__restore__()
            self.exit()
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

