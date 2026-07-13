import bpy
from bpy.app.translations import pgettext

from ..ops.quick_add.create_element_operator import CreateElementOperator
from ..ops.quick_add.create_element_property import CreateElementProperty
from ..utils.public import get_pref
from ..utils.session_state import SessionState


class ContextMenu:
    """Draw callback for Blender's button context menu (append only)."""

    @staticmethod
    def context_menu(self, context):
        from ..src.translate import __name_translate__
        SessionState.context_menu_from_button = True
        show_operator = CreateElementOperator.poll(context)
        show_property = CreateElementProperty.poll(context)

        show = not getattr(context, "show_gesture_add_menu", False)
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        button_operator = getattr(context, "button_operator", None)

        if button_operator and button_operator.bl_rna.identifier.startswith("WM_OT_gesture_"):
            return
        layout = self.layout

        if button_pointer and button_pointer.__class__.__name__ == "BlExtDummyGroup":
            layout.label(text="Add gesture", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")
            layout.label(text="Dynamic enumeration properties cannot be added!!")
        elif (show_operator or show_property) and show:
            layout.context_pointer_set('show_gesture_add_menu', self)
            layout.label(text="Add gesture", icon="GEOMETRY_SET" if bpy.app.version >= (4, 3, 0) else "VIEW_PAN")
            layout.enabled = get_pref().active_gesture is not None
            if show_property:
                layout.operator(
                    CreateElementProperty.bl_idname,
                    text=pgettext("Add Property %s") % __name_translate__(button_prop.name)
                )

            if show_operator:
                br = button_operator.bl_rna
                text = __name_translate__(br.name)
                row = layout.column(align=True)
                rr = row
                rr.operator_context = "EXEC_DEFAULT"
                rr.operator(CreateElementOperator.bl_idname, text=pgettext("Add Operator %s To Gesture") % text)
                rr = row
                rr.operator_context = "INVOKE_DEFAULT"
                rr.operator(CreateElementOperator.bl_idname, text="Modal Operator", icon="PRESET_NEW")


def register():
    menu = getattr(bpy.types, "WM_MT_button_context", None)
    if menu is None:
        return
    menu.append(ContextMenu.context_menu)


def unregister():
    menu = getattr(bpy.types, "WM_MT_button_context", None)
    if menu is None:
        return
    try:
        menu.remove(ContextMenu.context_menu)
    except (ValueError, AttributeError):
        pass
