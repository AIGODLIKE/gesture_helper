import bpy

from ..utils.public import get_pref, get_debug


class DrawElement:
    @staticmethod
    def draw_property(layout: 'bpy.types.UILayout') -> None:
        pref = get_pref()
        act = pref.active_element
        prop = pref.draw_property
        if act:
            if not prop.element_show_left_side:
                act.draw_item_property(layout)
            if get_debug():
                act.draw_debug(layout)
        else:
            layout.label(text='请 选择或添加 一个手势元素')

    @staticmethod
    def draw_element_cure(layout: 'bpy.types.UILayout', cls) -> None:
        column = layout.column(align=True)
        column.operator(
            cls.COPY.bl_idname,
            icon='COPYDOWN',
            text=''
        )
        column.operator(
            cls.REMOVE.bl_idname,
            icon='REMOVE',
            text=''
        )

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
