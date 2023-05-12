import bpy
from bpy.props import CollectionProperty, StringProperty
from bpy.types import PropertyGroup
from bpy.app.translations import contexts as i18n_contexts

ui_events_keymaps = i18n_contexts.ui_events_keymaps


class KeyMapItem(PropertyGroup):
    emm: StringProperty()


class SystemKey(PropertyGroup):
    _temp_kmi_key = 'temp_kmi_key_gesture_helper'

    key_maps: CollectionProperty(type=KeyMapItem)

    @property
    def keyconfig(self):
        return bpy.context.window_manager.keyconfigs.active

    @property
    def keymaps(self):
        return self.keyconfig.keymaps['Window']

    @property
    def temp_kmi(self) -> 'KeyMapItem':
        key = self._temp_kmi_key
        keymap_items = self.keymaps.keymap_items
        if key not in keymap_items:
            return keymap_items.new(key, 'NONE', 'PRESS')
        return keymap_items[key]

    def draw(self, layout):
        self.draw_kmi(layout, self.temp_kmi)

    @staticmethod
    def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy'):
        map_type = kmi.map_type

        sub = layout.column()
        sub_row = sub.row(align=True)
        if map_type == 'KEYBOARD':
            sub_row.prop(kmi, "type", text="", event=True,
                         text_ctxt=ui_events_keymaps)
            sub_row.prop(kmi, "value", text="",
                         text_ctxt=ui_events_keymaps)
            sub_row_repeat = sub_row.row(align=True)
            sub_row_repeat.active = kmi.value in {'ANY', 'PRESS'}

            sub_row_repeat.prop(kmi, "repeat", text="Repeat")
        elif map_type in {'MOUSE', 'NDOF'}:
            sub_row.prop(kmi, "type", text="",
                         text_ctxt=ui_events_keymaps)
            sub_row.prop(kmi, "value", text="",
                         text_ctxt=ui_events_keymaps)

        if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
            sub_row = sub.row()
            sub_row.prop(kmi, "direction", text_ctxt=ui_events_keymaps)

        sub_row = sub.row()
        sub_row.scale_x = 0.75
        sub_row.prop(kmi, "any", text='Any', toggle=True)
        # Use `*_ui` properties as integers aren't practical.
        sub_row.prop(kmi, "shift_ui", toggle=True)
        sub_row.prop(kmi, "ctrl_ui", toggle=True)
        sub_row.prop(kmi, "alt", toggle=True)
        sub_row.prop(kmi, "oskey", text="Cmd", toggle=True)

        sub_row.prop(kmi, "key_modifier", text="", event=True,
                     text_ctxt=ui_events_keymaps)


classes_tuple = (
    KeyMapItem,
    SystemKey,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
