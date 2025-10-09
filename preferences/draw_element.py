import bpy
from bpy.app.translations import pgettext

from ..utils.public import get_pref, get_debug
from ..utils.public_ui import icon_two


def draw_label(lay: bpy.types.UILayout, label: str) -> bpy.types.UILayout:
    width = bpy.context.region.width
    if width < 600:
        split = lay.row(align=True)
    else:
        split = lay.split(align=True, factor=0.3)
        split.label(text=label)
        split = split.row(align=True)
    return split


class DrawElement:

    @staticmethod
    def draw_element_cure(layout: bpy.types.UILayout) -> None:
        from ..element import ElementCURE
        pref = get_pref()
        draw_property = pref.draw_property

        column = layout.column(align=True)
        column.enabled = ElementCURE.MOVE.move_item is None

        cr = column.column(align=True)
        cut = cr.column(align=True)
        cut.active = cut.enabled = not pref.__is_cut_element__
        cut.operator(ElementCURE.CUT.bl_idname, icon_value=pref.__get_icon__("CUT"), text='')
        cr.operator(ElementCURE.COPY.bl_idname, icon='COPYDOWN', text='')
        rm = column.column(align=True)
        rm.operator(ElementCURE.REMOVE.bl_idname, icon='REMOVE', text='')

        column.separator()

        sc = column.column(align=True)
        sc.operator(ElementCURE.SORT.bl_idname, text='', icon='SORT_DESC').is_next = False
        sc.operator(ElementCURE.MOVE.bl_idname, icon="GRIP", text='')
        sc.operator(ElementCURE.SORT.bl_idname, text='', icon='SORT_ASC').is_next = True

        column.separator()
        icon = icon_two(draw_property.element_show_left_side, style='ALIGN')
        column.alert = draw_property.element_show_left_side
        column.prop(draw_property, 'element_show_left_side', icon=icon, text='', emboss=False)

    @staticmethod
    def draw_property(layout: 'bpy.types.UILayout') -> None:
        pref = get_pref()
        active_element = pref.active_element
        prop = pref.draw_property
        if pref.__is_cut_element__:
            DrawElement.draw_cut_element(layout)

        elif active_element:
            from ..element.element_cure import ElementCURE
            if pref.__is_move_element__:
                DrawElement.draw_move_element(layout)
            elif not prop.element_show_left_side:
                active_element.draw_alert(layout)
                active_element.draw_item_property(layout)
            if get_debug():
                active_element.draw_debug(layout)
        else:
            layout.label(text='Add or select a element')

    @staticmethod
    def draw_move_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        mi = ElementCURE.MOVE.move_item

        column = layout.column(align=True)
        column.label(text="In mobile gestures")
        column.separator()
        column.label(text=pgettext("Move gesture: %s") % mi.name)
        if mi.is_root:
            column.label(text="The gesture term is the root level")

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.enabled = not mi.is_root  # 不是根级的
        mr.operator(ElementCURE.MOVE.bl_idname, icon="GRIP", text='Moving to the root level').cancel_move = False
        row.operator(ElementCURE.MOVE.bl_idname, icon='CANCEL', text='Cancel move').cancel_move = True

    @staticmethod
    def draw_cut_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        pref = get_pref()

        column = layout.column(align=True)
        column.label(text="In the cut gesture")
        column.separator()

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.operator(
            ElementCURE.CUT.bl_idname,
            icon_value=pref.__get_icon__("CUT"),
            text='Paste to root level'
        ).cancel_cut = False
        row.operator(ElementCURE.CUT.bl_idname, icon='CANCEL', text='Cancel paste').cancel_cut = True

    @classmethod
    def draw_element_add_property(cls, layout: 'bpy.types.UILayout') -> None:
        from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
        from ..element import ElementCURE
        from ..ui.menu import GESTURE_MT_add_element_menu

        pref = get_pref()
        add = pref.add_element_property

        add_child = add.is_have_add_child

        column = layout.box().column(align=True)
        column.label(text='Add element')

        row = draw_label(column, 'Elemental Relationship:')
        row.prop(add, 'relationship', expand=True)
        row.prop(add, "add_active_radio", icon="LAYER_ACTIVE", icon_only=True)

        if add_child:
            row = draw_label(column, 'Selected Structure:')
            for i, n, d in ENUM_SELECTED_TYPE:
                ops = row.operator(ElementCURE.ADD.bl_idname, text=n)
                ops.element_type = 'SELECTED_STRUCTURE'
                ops.selected_type = i
            column.separator()
            row = draw_label(column, 'Add item:')
            for i, n, d in ENUM_ELEMENT_TYPE:
                if i != 'SELECTED_STRUCTURE':
                    if i == "DIVIDING_LINE":
                        cls.draw_element_add_div_property(row)
                    else:
                        ops = row.operator(ElementCURE.ADD.bl_idname, text=n)
                        ops.element_type = i
            row.menu(GESTURE_MT_add_element_menu.__name__, icon='COLLAPSEMENU', text="")
        else:
            column.separator()
            row = column.row(align=True)
            row.enabled = False
            row.row(align=True).label(text="Cannot add child to 'Operator'")
            column.label(text="Operator should not have children")

    @classmethod
    def draw_element_add_div_property(cls, layout: 'bpy.types.UILayout') -> None:
        from ..element import ElementCURE
        pref = get_pref()
        add = pref.add_element_property
        relationship = add.relationship
        active = pref.active_element
        is_alert = False

        if relationship == "ROOT":
            is_alert = True
        elif relationship == "SAME":
            if active and active.parent_element and active.parent_is_extension:
                ...
            else:
                is_alert = True
        elif relationship == "CHILD":
            if active:
                is_e = active.is_child_gesture and (active.direction == "9" or active.parent_is_extension)
                if is_e or active.is_selected_structure:
                    ...
                else:
                    is_alert = True
            else:
                is_alert = True

        if is_alert:
            layout = layout.row(align=True)
            layout.enabled = False

        ops = layout.operator(ElementCURE.ADD.bl_idname, text="Div")
        ops.element_type = "DIVIDING_LINE"
