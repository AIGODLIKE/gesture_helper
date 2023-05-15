import bpy
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator, PropertyGroup
from idprop.types import IDPropertyGroup

from ...utils.property import RegUiProp
from ...utils.public import PublicClass, PublicOperator
from ...utils.public.public_ui import PublicUi

ui_events_keymaps = i18n_contexts.ui_events_keymaps


class TempModifierKeyOps(PublicOperator):
    _temp_kmi_key = 'temp_kmi_key_gesture_helper'
    bl_idname = PublicOperator.ops_id_name(_temp_kmi_key)
    bl_label = 'emm'

    system: StringProperty()

    def execute(self, context):
        return {'FINISHED'}


class KeyProperty(PropertyGroup,
                  PublicClass):
    _key_data = 'data'

    @property
    def parent_system(self):
        for s in self.pref.systems:
            if s.key == self:
                return s

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
    key_maps: list

    def draw(self, layout):
        layout.context_pointer_set('system', self.parent_system)

        self.draw_kmi(layout, self.temp_kmi)
        self.from_temp_key_update_data()

    def from_temp_key_update_data(self):

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
        row.operator(SetKeyMaps.bl_idname)

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


class SetKeyMaps(Operator, PublicClass, PublicUi):
    bl_idname = PublicOperator.ops_id_name('set_key_maps')
    bl_label = 'Set Key Maps'
    keymap_hierarchy: list
    layout: 'bpy.types.UILayout'

    def invoke(self, context, event):
        from bl_keymap_utils import keymap_hierarchy
        self.keymap_hierarchy = keymap_hierarchy.generate()
        self.init_invoke()
        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 300})

    @property
    def key_maps(self):
        k = self.active_system.key
        key = 'key_maps'
        items = list(k[key]) if key in k else []
        return items

    def init_invoke(self):
        key_maps = self.key_maps

        def _d(it):
            for name, space_type, window_type, child in it:
                select = name + '_selected'
                expand = name + '_expand'

                sel = RegUiProp.temp_prop(select)
                exp = RegUiProp.temp_prop(expand)
                s = RegUiProp.from_name_get_id(select)
                e = RegUiProp.from_name_get_id(expand)
                setattr(sel, s, name in key_maps)
                _d(child)

        _d(self.keymap_hierarchy)

    def execute(self, context):
        rsc = []

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


classes_tuple = (
    SystemKey,
    TempModifierKeyOps,
    SetKeyMaps,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
