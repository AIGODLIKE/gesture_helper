# 绘制手势
# 预览绘制
import bpy

from ... import icon_two, space_layout


class ElementDraw:

    def __getitem__(self, item):
        return item

    def draw_ui(self, layout: 'bpy.types.UILayout', level: int) -> None:
        column = layout.column(align=True)
        row = column.row(align=True)
        row.label(text=str(level))
        row.label(text=str(self.index))
        row.prop(self, 'enabled', text='')
        if len(self.element):
            row.prop(self,
                     'show_child',
                     text='',
                     icon=icon_two(self.show_child, 'TRI'),
                     emboss=False)
        else:
            row.separator()

        row.prop(self,
                 'selected',
                 text='',
                 icon=icon_two(self.selected, 'RESTRICT_SELECT'),
                 emboss=False)
        row.prop(self, 'name')
        if self.show_child:
            self.draw_child_element(column, level)

    def draw_child_element(self, layout, level: int):
        for element in self.element:
            space = space_layout(layout, 1, level)
            element.draw_ui(space, level + 1)

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
        layout.label(text='gesture_direction_items\t' + str(self.gesture_direction_items))
        layout.separator()
        for i in self.bl_rna.properties.keys():
            if i not in ('rna_type', 'name', 'relationship'):
                row = layout.row()
                row.label(text=i)
                row.prop(self, i, expand=True, )
