import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ....public import PublicClass, PublicUi, PublicOperator


class OperatorSetKeyMaps(Operator, PublicClass, PublicUi):
    bl_idname = PublicOperator.ops_id_name('set_key_maps')
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
        k = self.active_system.key
        key = 'key_maps'
        items = list(k[key]) if key in k else ['Window', ]
        return items

    def init_invoke(self):
        key_maps = self.key_maps
        from ....utils.property import RegUiProp

        def _d(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'
                expand = name + '_expand'

                sel = RegUiProp.temp_prop(select)
                s = RegUiProp.from_name_get_id(select)

                RegUiProp.temp_prop(expand)
                setattr(sel, s, name in key_maps)
                _d(child)

        _d(self.keymap_hierarchy)

    def execute(self, context):
        rsc = []
        from ....utils.property import RegUiProp

        def _d(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'

                sel = RegUiProp.temp_prop(select)
                s = RegUiProp.from_name_get_id(select)
                if getattr(sel, s, False):
                    rsc.append(name)
                _d(child)

        _d(self.keymap_hierarchy)
        self.active_system.key['key_maps'] = rsc
        print(rsc)
        self.active_system.key.update()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout.column()
        layout.emboss = 'NONE'
        layout.label(text=self.pref.active_system.name)
        row = layout.row()
        self.selected_list = []
        self.draw_key(row.column(), self.keymap_hierarchy, 0)
        self.draw_selected(row.column())

    def draw_selected(self, layout):
        for sel, s, name in self.selected_list:
            row = layout.row()
            row.prop(sel, s, text='', icon=self.icon_two(getattr(sel, s, False), 'RESTRICT_SELECT'))
            row.label(text=name)

    def draw_key(self, layout, items, level):
        from ....utils.property import RegUiProp
        for name, space_type, window_type, child in items:
            row = self.space_layout(layout, self.ui_prop.child_element_office, level).row(align=True)
            select = name + '_selected'
            expand = name + '_expand'

            sel = RegUiProp.temp_prop(select)
            exp = RegUiProp.temp_prop(expand)
            s = RegUiProp.from_name_get_id(select)
            e = RegUiProp.from_name_get_id(expand)
            if child:
                row.prop(exp, e, text='', icon=self.icon_two(getattr(exp, e, False), 'TRIA'))
            row.prop(sel, s, text='', icon=self.icon_two(getattr(sel, s, False), 'RESTRICT_SELECT'))
            row.label(text=name)
            is_sel = getattr(sel, s, False)

            if is_sel:
                self.selected_list.append((sel, s, name))

            if getattr(exp, e, False):
                self.draw_key(layout, child, level + 1)


class OperatorTempModifierKey(PublicOperator):
    _temp_kmi_key = 'temp_kmi_key_gesture_helper'
    bl_idname = PublicOperator.ops_id_name(_temp_kmi_key)
    bl_label = 'Temp Kmi Key Gesture Helper'

    system: StringProperty()

    def execute(self, context):
        return {'PASS_THROUGH'}
