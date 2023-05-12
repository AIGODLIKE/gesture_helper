import bpy
from bpy.props import CollectionProperty, StringProperty
from bpy.types import PropertyGroup
from bpy.app.translations import contexts as i18n_contexts
from idprop.types import IDPropertyGroup

from ...utils.public import PublicClass, PublicOperator

ui_events_keymaps = i18n_contexts.ui_events_keymaps


class TempModifierKeyOps(PublicOperator):
    _temp_kmi_key = 'temp_kmi_key_gesture_helper'
    bl_idname = PublicOperator.ops_id_name(_temp_kmi_key)
    bl_label = 'emm'

    system: StringProperty()

    def execute(self, context):
        return {'FINISHED'}


class KeyMapItem(PropertyGroup):
    emm: StringProperty()


class KeyProperty(PropertyGroup,
                  PublicClass):
    _key_data = 'data'

    def _get_key_data(self) -> 'dict':
        key = self._key_data
        if key in self:
            return {k: dict(v) if type(v) == IDPropertyGroup else v
                    for (k, v) in
                    dict(self[key]).items()}

    def _set_key_data(self, value) -> None:
        key = self._key_data
        self[key] = value

    key_data = property(fget=_get_key_data, fset=_set_key_data)

    @property
    def keyconfig(self):
        return bpy.context.window_manager.keyconfigs.active

    @property
    def keymaps(self):
        return self.keyconfig.keymaps['Window']

    @property
    def temp_kmi(self) -> 'KeyMapItem':
        key = TempModifierKeyOps.bl_idname
        keymap_items = self.keymaps.keymap_items
        if key not in keymap_items:
            return keymap_items.new(key, 'NONE', 'PRESS')
        return keymap_items[key]

    @property
    def kmi_system(self):
        return self.temp_kmi.properties.system

    @property
    def is_change_system(self) -> bool:
        return self.kmi_system != self.active_system.name or not self.key_data

    def set_kmi_system(self, value):
        self.temp_kmi.properties.system = value

    @property
    def kmi_data(self):
        return dict(
            self.props_data(
                self.temp_kmi,
                exclude=('name', 'id', 'show_expanded', 'properties', 'idname')
            )
        )


class SystemKey(KeyProperty):
    key_maps: CollectionProperty(type=KeyMapItem)

    def draw(self, layout):
        self.draw_kmi(layout, self.temp_kmi)
        self.update_key()

    def update_key(self):

        data = self.kmi_data
        if self.is_change_system:
            self.set_kmi_system(self.active_system.name)
            print('is_change_system')
            if self.key_data:
                self.set_property_data(self.temp_kmi, self.key_data)
            else:
                self.key_data = self.kmi_data
            self.tag_redraw(bpy.context)
        elif self.key_data != data:
            print('change key')
            print(data)
            print(self.key_data)
            self.key_data = data
            self.tag_redraw(bpy.context)

    @staticmethod
    def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy'):
        map_type = kmi.map_type

        col = layout.column()

        if kmi.show_expanded:
            col = col.column(align=True)
            box = col.box()
        else:
            box = col.column()

        split = box.split()

        # header bar
        row = split.row(align=True)
        row.prop(kmi, "show_expanded", text="", emboss=False)
        row.prop(kmi, "active", text="", emboss=False)

        row = split.row()
        row.prop(kmi, "map_type", text="")
        if map_type == 'KEYBOARD':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'MOUSE':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'NDOF':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'TWEAK':
            subrow = row.row()
            subrow.prop(kmi, "type", text="")
            subrow.prop(kmi, "value", text="")
        elif map_type == 'TIMER':
            row.prop(kmi, "type", text="")
        else:
            row.label()

        row.operator("preferences.keyitem_restore", text="", icon='BACK').item_id = kmi.id
        # Expanded, additional event settings
        if kmi.show_expanded:
            box = col.box()

            if map_type not in {'TEXTINPUT', 'TIMER'}:
                sub = box.column()
                subrow = sub.row(align=True)

                if map_type == 'KEYBOARD':
                    subrow.prop(kmi, "type", text="", event=True)
                    subrow.prop(kmi, "value", text="")
                    subrow_repeat = subrow.row(align=True)
                    subrow_repeat.active = kmi.value in {'ANY', 'PRESS'}
                    subrow_repeat.prop(kmi, "repeat", text="Repeat")
                elif map_type in {'MOUSE', 'NDOF'}:
                    subrow.prop(kmi, "type", text="")
                    subrow.prop(kmi, "value", text="")

                if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
                    subrow = sub.row()
                    subrow.prop(kmi, "direction")

                subrow = sub.row()
                subrow.scale_x = 0.75
                subrow.prop(kmi, "any", toggle=True)
                # Use `*_ui` properties as integers aren't practical.
                subrow.prop(kmi, "shift_ui", toggle=True)
                subrow.prop(kmi, "ctrl_ui", toggle=True)
                subrow.prop(kmi, "alt_ui", toggle=True)
                subrow.prop(kmi, "oskey_ui", text="Cmd", toggle=True)

                subrow.prop(kmi, "key_modifier", text="", event=True)


classes_tuple = (
    KeyMapItem,
    SystemKey,
    TempModifierKeyOps,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
