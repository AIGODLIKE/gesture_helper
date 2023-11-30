import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.public import PublicOperator, get_pref, PublicProperty
from ..utils.public_ui import space_layout, icon_two


class OperatorSetKeyMaps(PublicOperator, PublicProperty):
    bl_idname = 'gesture.set_key_maps'
    bl_label = 'Set Key Maps'

    layout: 'bpy.types.UILayout'

    keymap_hierarchy: list
    selected_list: list

    def invoke(self, context, event):
        from bl_keymap_utils import keymap_hierarchy
        self.keymap_hierarchy = keymap_hierarchy.generate()
        self.init_invoke()
        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 300})

    @property
    def key_maps(self):
        return get_pref().active_gesture.keymaps

    def init_invoke(self):
        key_maps = self.key_maps
        from ..utils.property import TempDrawProperty

        def _d(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'
                expand = name + '_expand'

                sel = TempDrawProperty.temp_prop(select)
                s = TempDrawProperty.from_name_get_id(select)

                TempDrawProperty.temp_prop(expand)
                setattr(sel, s, name in key_maps)
                _d(child)

        _d(self.keymap_hierarchy)

    def execute(self, context):
        rsc = []
        from ..utils.property import TempDrawProperty

        def _d(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'

                sel = TempDrawProperty.temp_prop(select)
                s = TempDrawProperty.from_name_get_id(select)
                if getattr(sel, s, False):
                    rsc.append(name)
                _d(child)

        _d(self.keymap_hierarchy)
        self.active_gesture.keymaps = rsc
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout.column()
        layout.emboss = 'NONE'
        layout.label(text=self.pref.active_gesture.name)
        row = layout.row()
        self.selected_list = []
        self.draw_keymaps(row.column(), self.keymap_hierarchy, 0)
        self.draw_selected(row.column())

    def draw_selected(self, layout):
        for sel, s, name in self.selected_list:
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
            is_sel = getattr(sel, s, False)

            if is_sel:
                self.selected_list.append((sel, s, name))

            if getattr(exp, e, False):
                self.draw_keymaps(layout, child, level + 1)


class OperatorTempModifierKey(Operator):
    bl_idname = 'gesture.temp_kmi'
    bl_label = 'Temp Kmi Key Gesture Helper'

    gesture: StringProperty()

    def execute(self, context):
        return {'PASS_THROUGH'}
