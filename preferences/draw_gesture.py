import bpy

from .draw_element import DrawElement
from ..ops import export_import
from ..utils.public import get_pref
from ..utils.public_ui import icon_two


class GestureDraw:

    @staticmethod
    def draw_gesture_cure(layout: 'bpy.types.UILayout') -> None:
        from ..ops import gesture_cure
        GestureDraw.public_cure(layout, gesture_cure.GestureCURE)

    @staticmethod
    def draw_gesture_key(layout) -> None:
        from ..utils.public import get_pref
        pref = get_pref()
        active = pref.active_gesture
        if active:
            column = layout.column()
            column.active = active.is_enable
            active.draw_key(column)
        else:
            layout.label(text='Not Select Gesture')

    @staticmethod
    def draw_gesture_item(layout: bpy.types.UILayout) -> None:
        pref = get_pref()
        row = layout.row(align=True)
        GestureDraw.draw_gesture_cure(row)
        column = row.column(align=True)
        from ..ui.ui_list import GestureUIList
        column.template_list(
            GestureUIList.bl_idname,
            GestureUIList.bl_idname,
            pref,
            'gesture',
            pref,
            'index_gesture',
        )
        ag = pref.active_gesture
        if ag is not None:
            column.prop(ag, 'description')
        GestureDraw.draw_gesture_key(column)

    @staticmethod
    def draw_element(layout: bpy.types.UILayout) -> None:
        from ..ui.ui_list import ElementUIList
        pref = get_pref()
        ag = pref.active_gesture
        if ag:
            column = layout.column()

            DrawElement.draw_element_add_property(column)
            row = column.row(align=True)

            sub_column = row.column()
            sub_column.template_list(
                ElementUIList.bl_idname,
                ElementUIList.bl_idname,
                ag,
                'element',
                ag,
                'index_element',
            )
            DrawElement.draw_property(sub_column)

            GestureDraw.draw_element_cure(row)
        else:
            layout.label(text='请添加或选择一个手势')

    @staticmethod
    def draw_element_cure(layout: bpy.types.UILayout) -> None:
        from ..element import ElementCURE
        GestureDraw.public_cure(layout, ElementCURE)

    @staticmethod
    def public_cure(layout, cls) -> None:
        is_element = cls.__name__ == 'ElementCURE'
        pref = get_pref()
        draw_property = pref.draw_property
        other = pref.other_property

        column = layout.column(align=True)
        if is_element:
            DrawElement.draw_element_cure(column, cls)
            column.separator()
        else:
            column.operator(
                cls.ADD.bl_idname,
                icon='ADD',
                text=''
            )
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

        column.separator()

        column.operator(
            cls.SORT.bl_idname,
            icon='SORT_DESC',
            text=''
        ).is_next = False

        if is_element:
            moving = other.is_move_element
            icon = 'DOT' if moving else 'GRIP'

            row = column.row()
            if moving:
                move_item = cls.MOVE.move_item
                row.enabled = bool(move_item and not move_item.is_root)
            row.operator(
                cls.MOVE.bl_idname,
                icon=icon,
                text=''
            )
            if moving:
                column.operator(
                    cls.MOVE.bl_idname,
                    icon='CANCEL',
                    text=''
                ).cancel = True

        column.operator(
            cls.SORT.bl_idname,
            icon='SORT_ASC',
            text=''
        ).is_next = True

        if is_element:
            column.separator()
            icon = icon_two(draw_property.element_show_left_side, style='ALIGN')
            column.prop(draw_property, 'element_show_left_side', icon=icon, text='', emboss=False)
        else:
            column.separator()
            column.separator()

            import_id_name = export_import.Import.bl_idname
            column.operator(export_import.Export.bl_idname, icon='EXPORT', text='')
            column.operator(import_id_name, icon='ASSET_MANAGER', text='').preset_show = True
            column.operator(import_id_name, icon='IMPORT', text='').preset_show = False

    @staticmethod
    def draw_ui_gesture(layout):
        """
        绘制手势部分
        :param layout:
        :return:
        """
        pref = get_pref()
        draw_property = pref.draw_property
        act = pref.active_element

        column = layout.column()
        split = column.split()

        if draw_property.element_show_left_side:  # 绘制属性在左侧
            box = split.box()
            if act:
                act.draw_item_property(box)
            else:
                box.label(text='请 选择或添加 一个手势元素')
        else:
            GestureDraw.draw_gesture_item(split)
        GestureDraw.draw_element(split)
