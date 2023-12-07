import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.public import PublicOperator, get_pref, PublicProperty
from ..utils.public_ui import space_layout, icon_two


class OperatorSetKeyMaps(PublicOperator, PublicProperty):
    bl_idname = 'gesture.set_key_maps'
    bl_label = '设置键位映射'

    keymap_hierarchy: list

    @property
    def active_gesture_keymaps(self):
        return get_pref().active_gesture.keymaps

    @property
    def selected_keymaps_draw_list(self):  # 绘制
        from ..utils.property import TempDrawProperty
        res = []

        def selected(items):
            for name, space_type, window_type, child in items:
                select = name + '_selected'
                sel = TempDrawProperty.temp_prop(select)
                s = TempDrawProperty.from_name_get_id(select)
                is_sel = getattr(sel, s, False)
                if is_sel:
                    res.append((sel, s, name))
                selected(child)

        selected(self.keymap_hierarchy)
        return res

    @property
    def selected_keymaps(self):  # 仅名称
        return [name for _, _, name in self.selected_keymaps_draw_list]

    def invoke(self, context, event):
        from bl_keymap_utils import keymap_hierarchy
        self.keymap_hierarchy = keymap_hierarchy.generate()
        self.create_temp_prop()
        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 600})

    def create_temp_prop(self):
        key_maps = self.active_gesture_keymaps
        from ..utils.property import TempDrawProperty

        def set_temp_prop(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'
                expand = name + '_expand'

                sel = TempDrawProperty.temp_prop(select)
                s = TempDrawProperty.from_name_get_id(select)

                TempDrawProperty.temp_prop(expand)
                setattr(sel, s, name in key_maps)
                set_temp_prop(child)

        set_temp_prop(self.keymap_hierarchy)

    def execute(self, context):
        self.active_gesture.keymaps = self.selected_keymaps
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout.column()
        layout.emboss = 'NONE'
        layout.label(text=self.pref.active_gesture.name)
        row = layout.row()
        self.draw_keymaps(row.column(), self.keymap_hierarchy, 0)
        self.draw_selected(row.column())

    def draw_selected(self, layout):
        for sel, s, name in self.selected_keymaps_draw_list:
            row = layout.row()
            row.prop(sel, s, text='', icon=icon_two(getattr(sel, s, False), 'RESTRICT_SELECT'))
            row.label(text=name)

    def draw_keymaps(self, layout, items, level):
        from ..utils.property import TempDrawProperty
        for name, space_type, window_type, child in items:
            row = space_layout(layout, 10, level).row(align=True)
            select = name + '_selected'
            expand = name + '_expand'

            sel = TempDrawProperty.temp_prop(select)
            exp = TempDrawProperty.temp_prop(expand)
            s = TempDrawProperty.from_name_get_id(select)
            e = TempDrawProperty.from_name_get_id(expand)
            if child:
                row.prop(exp, e, text='', icon=icon_two(getattr(exp, e, False), 'TRIA'))
            row.prop(sel, s, text='', icon=icon_two(getattr(sel, s, False), 'RESTRICT_SELECT'))
            row.label(text=name)

            if getattr(exp, e, False):
                self.draw_keymaps(layout, child, level + 1)


class OperatorTempModifierKey(Operator):
    bl_idname = 'gesture.temp_kmi'
    bl_label = 'Temp Kmi Key Gesture Helper'

    gesture: StringProperty()

    def execute(self, context):
        return {'PASS_THROUGH'}
