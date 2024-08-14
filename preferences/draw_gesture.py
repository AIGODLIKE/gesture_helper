import bpy

from .draw_element import DrawElement
from ..ops import export_import
from ..utils.public import get_pref


class GestureDraw:

    @staticmethod
    def draw_gesture_cure(layout: 'bpy.types.UILayout') -> None:
        from ..ops.gesture_cure import GestureCURE

        column = layout.column(align=True)

        column.operator(GestureCURE.ADD.bl_idname, icon='ADD', text='')
        column.operator(GestureCURE.COPY.bl_idname, text='', icon='COPYDOWN')
        column.operator(GestureCURE.REMOVE.bl_idname, text='', icon='REMOVE')
        column.separator()

        sort_column = column.column(align=True)
        sort_column.operator(GestureCURE.SORT.bl_idname, icon='SORT_DESC', text='').is_next = False

        sort_column.operator(GestureCURE.SORT.bl_idname, icon='SORT_ASC', text='').is_next = True

        column.separator()

        import_id_name = export_import.Import.bl_idname
        column.operator(export_import.Export.bl_idname, icon='EXPORT', text='')
        column.operator(import_id_name, icon='ASSET_MANAGER', text='').preset_show = True
        column.operator(import_id_name, icon='IMPORT', text='').preset_show = False

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
        row.enabled = row.active = not pref.__is_move_element__

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

            DrawElement.draw_element_cure(row)
        else:
            layout.label(text='请添加或选择一个手势')

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
