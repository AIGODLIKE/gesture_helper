import bpy

from ..utils.public import get_pref, get_debug
from ..utils.public_ui import icon_two


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
        rm.operator_context = "INVOKE_DEFAULT" if pref.draw_property.element_remove_tips else "EXEC_DEFAULT"
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
        act = pref.active_element
        prop = pref.draw_property
        if pref.__is_cut_element__:
            DrawElement.draw_cut_element(layout)

        elif act:
            from ..element.element_cure import ElementCURE
            if pref.__is_move_element__:
                DrawElement.draw_move_element(layout)
            elif not prop.element_show_left_side:
                act.draw_alert(layout)
                act.draw_item_property(layout)
            if get_debug():
                act.draw_debug(layout)
        else:
            layout.label(text='请 选择或添加 一个手势元素')

    @staticmethod
    def draw_move_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        mi = ElementCURE.MOVE.move_item

        column = layout.column(align=True)
        column.label(text=f"移动手势中")
        column.separator()
        column.label(text=f"移动手势: {mi.name}")
        if mi.is_root:
            column.label(text=f"手势项为根级")

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.enabled = not mi.is_root  # 不是根级的
        mr.operator(ElementCURE.MOVE.bl_idname, icon="GRIP", text='移动到根级').cancel_move = False
        row.operator(ElementCURE.MOVE.bl_idname, icon='CANCEL', text='取消移动').cancel_move = True

    @staticmethod
    def draw_cut_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        pref = get_pref()

        column = layout.column(align=True)
        column.label(text=f"剪切手势中")
        column.separator()

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.operator(
            ElementCURE.CUT.bl_idname,
            icon_value=pref.__get_icon__("CUT"),
            text='粘贴到根级'
        ).cancel_cut = False
        row.operator(ElementCURE.CUT.bl_idname, icon='CANCEL', text='取消粘贴').cancel_cut = True

    @staticmethod
    def draw_element_add_property(layout: 'bpy.types.UILayout') -> None:
        from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
        from ..element import ElementCURE

        pref = get_pref()
        add = pref.add_element_property

        relationship = add.relationship
        add_child = add.is_have_add_child

        if bpy.context.region.width < 2000:
            split = layout.box().column(align=True)
        else:
            split = layout.split(factor=.4)

        row = split.row(align=True)
        row.label(text='元素关系:')
        row.prop(add, 'relationship', expand=True)
        row.prop(add, "add_active_radio", icon="LAYER_ACTIVE", icon_only=True)

        sub_row = split.row(align=True)
        sub_row.enabled = add_child

        if add_child:
            element_row = sub_row.row(align=True)
            element_row.separator()
            element_row.label(text='添加项:')
            for i, n, d in ENUM_ELEMENT_TYPE:
                if i != 'SELECTED_STRUCTURE':
                    ops = element_row.operator(ElementCURE.ADD.bl_idname, text=n)
                    ops.element_type = i
                    ops.relationship = relationship
            element_row.separator()
            for i, n, d in ENUM_SELECTED_TYPE:
                ops = element_row.operator(ElementCURE.ADD.bl_idname, text=n)
                ops.element_type = 'SELECTED_STRUCTURE'
                ops.selected_type = i
                ops.relationship = relationship
        else:
            sub_row.row(align=True).label(text="无法为 '操作符' 添加子级")
