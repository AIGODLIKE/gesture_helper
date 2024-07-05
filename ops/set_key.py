import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.public import PublicOperator, get_pref, PublicProperty
from ..utils.public_ui import icon_two


class OperatorSetKeyMaps(PublicOperator, PublicProperty):
    bl_idname = 'gesture.set_key_maps'
    bl_label = '设置键位映射'

    __temp_selected_keymaps__ = []  # static
    add_keymap: StringProperty(options={'SKIP_SAVE'})

    @property
    def active_gesture_keymaps(self):
        return get_pref().active_gesture.keymaps

    def invoke(self, context, _):
        if self.add_keymap:  # 添加项
            if self.add_keymap in OperatorSetKeyMaps.__temp_selected_keymaps__:
                OperatorSetKeyMaps.__temp_selected_keymaps__.remove(self.add_keymap)
            else:
                if len(OperatorSetKeyMaps.__temp_selected_keymaps__) == 0:
                    OperatorSetKeyMaps.__temp_selected_keymaps__ = [self.add_keymap, ]
                else:
                    OperatorSetKeyMaps.__temp_selected_keymaps__.append(self.add_keymap)
            return {'FINISHED'}

        from bl_keymap_utils import keymap_hierarchy
        self.keymap_hierarchy = keymap_hierarchy.generate()
        OperatorSetKeyMaps.__temp_selected_keymaps__ = self.active_gesture.keymaps
        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 600})

    def execute(self, _):
        self.active_gesture.keymaps = self.__class__.__temp_selected_keymaps__
        return {'FINISHED'}

    def draw(self, _):
        layout = self.layout.column()
        layout.emboss = 'NONE'
        layout.label(text=self.pref.active_gesture.name)
        row = layout.row()
        self.draw_keymaps(row.column(align=True), self.keymap_hierarchy)
        self.draw_selected_keymap(row.column(align=True))

    def draw_selected_keymap(self, layout):
        for name in self.__class__.__temp_selected_keymaps__:
            text = bpy.app.translations.pgettext(name)
            layout.operator(self.bl_idname, icon='RESTRICT_SELECT_OFF', text=text).add_keymap = name

    def draw_keymaps(self, layout, items):
        keymaps = bpy.context.window_manager.keyconfigs.default.keymaps
        for name, space_type, window_type, child in items:
            keymap = keymaps.get(name, None)
            if keymap:
                layout.emboss = 'NORMAL'
                column = layout.column()
                row = column.row(align=True)
                row.emboss = "NORMAL"
                row.label(text=keymap.name)
                show_child = getattr(keymap, 'show_expanded_items', False)

                if len(child):
                    row.prop(keymap, 'show_expanded_items', text='')
                select_icon = icon_two(name in self.__class__.__temp_selected_keymaps__, 'RESTRICT_SELECT')
                row.operator(OperatorSetKeyMaps.bl_idname, text='', icon=select_icon).add_keymap = keymap.name
                if show_child:
                    self.draw_keymaps(column.box().column(align=True), child)


class OperatorTempModifierKey(Operator):
    bl_idname = 'gesture.temp_kmi'
    bl_label = 'Temp Kmi Key Gesture Helper'

    gesture: StringProperty()

    def execute(self, _):
        return {'PASS_THROUGH'}
