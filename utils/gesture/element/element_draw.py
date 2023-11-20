# 绘制手势
# 预览绘制
import bpy

from ... import icon_two
from ...public import get_pref


def split_layout(layout: 'bpy.types.UILayout', level: int):
    prop = get_pref().draw_property
    factor = prop.element_split_factor
    space = prop.element_split_space
    indent = (level + 1) * space / bpy.context.region.width * factor + .1
    return layout.split(factor=indent)

class ElementDraw:
    def draw_ui(self, layout: 'bpy.types.UILayout'):
        column = layout.column(align=True)

        split = split_layout(column, self.level)

        left = split.row(align=True)
        left.prop(self,
                  'radio',
                  text='',
                  icon=icon_two(self.radio, 'RESTRICT_SELECT'),
                  emboss=False)
        left.prop(self, 'enabled', text='')
        left.label(text=str(self.level))

        right = split.row(align=True)
        right.prop(self, 'name', text='')

        right.label(text=str(self.index))

        if len(self.element):
            right.prop(self,
                       'show_child',
                       text='',
                       icon=icon_two(self.show_child, 'TRI'),
                       emboss=False)

        if self.show_child:
            for element in self.element:
                element.draw_ui(column.column(align=True))

    def draw_ui_property(self, layout: 'bpy.types.UILayout') -> None:
        layout.prop(self, 'name')
        self.draw_debug(layout)

    def draw_debug(self, layout):
        layout.separator()
        layout.label(text=str(self))
        layout.label(text='index\t' + str(self.index))
        layout.label(text='parent_gesture\t' + str(self.parent_gesture))
        layout.label(text='parent_element\t' + str(self.parent_element))
        layout.label(text='operator_properties\t' + str(self.operator_properties))
        layout.label(text='collection_iteration\t' + str(self.collection_iteration))
        # layout.label(text='gesture_direction_items\t' + str(self.gesture_direction_items))
        layout.separator()
        for i in self.bl_rna.properties.keys():
            if i not in ('rna_type', 'name', 'relationship'):
                row = layout.row()
                row.label(text=i)
                row.prop(self, i, expand=True, )
