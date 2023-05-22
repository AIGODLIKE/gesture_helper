import bpy
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import StringProperty
from bpy.types import Operator, PropertyGroup, KeyMapItem
from idprop.types import IDPropertyGroup

from ...utils.property import RegUiProp
from ...utils.public import PublicClass, TempKey
from ...utils.public.public_operator import PublicOperator
from ...utils.public.public_ui import PublicUi

ui_events_keymaps = i18n_contexts.ui_events_keymaps


class OperatorTempModifierKey(PublicOperator):
    _temp_kmi_key = 'temp_kmi_key_gesture_helper'
    bl_idname = PublicOperator.ops_id_name(_temp_kmi_key)
    bl_label = 'Temp Kmi Key Gesture Helper'

    system: StringProperty()

    def execute(self, context):
        return {'PASS_THROUGH'}


class KeyMaps(PropertyGroup):
    _key_maps = 'key_maps'

    @property
    def keymap_hierarchy(self):
        from bl_keymap_utils import keymap_hierarchy
        return keymap_hierarchy.generate()

    @property
    def keymap_hierarchy_dict(self):
        rsc = {}

        def g(items):
            for name, a, b, child in items:
                rsc[name] = (name, a, b)
                g(child)

        g(self.keymap_hierarchy)
        return rsc

    def _get_key_maps(self):
        key = self._key_maps
        return self[key] if key in self and len(self[key]) else ['Window']

    def _set_key_maps(self, value):
        self[self._key_maps] = list(value)

    key_maps = property(fget=_get_key_maps, fset=_set_key_maps)

    @property
    def key_configs(self):
        return bpy.context.window_manager.keyconfigs

    @property
    def active_keyconfig(self):
        return self.key_configs.active


class KeyProperty(PropertyGroup,
                  PublicClass,
                  TempKey,
                  ):
    _key_data = 'key_data'

    @property
    def parent_system(self):
        for s in self.pref.systems:
            if s.key == self:
                return s

    def _get_key_data(self) -> 'dict':
        key = self._key_data
        default = {'type': 'NONE', 'value': 'PRESS'}
        if key in self and dict(self[key]):
            default.update({k: dict(v) if type(v) == IDPropertyGroup else v
                            for (k, v) in
                            dict(self[key]).items()})
        return default

    def _set_key_data(self, value) -> None:
        key = self._key_data
        self[key] = value

    key_data = property(fget=_get_key_data, fset=_set_key_data)

    @property
    def temp_kmi(self) -> 'KeyMapItem':
        return self.get_temp_kmi(OperatorTempModifierKey.bl_idname)

    @property
    def kmi_system(self):
        return self.temp_kmi.properties.system

    @property
    def is_change_system(self) -> bool:
        return self.kmi_system != self.active_system.name or not self.key_data

    @staticmethod
    def set_kmi_system(kmi, value):
        kmi.properties.system = value

    @property
    def kmi_data(self):
        return dict(
            self.props_data(
                self.temp_kmi,
                exclude=('name', 'id', 'show_expanded', 'properties', 'idname')
            )
        )


class SystemKey(KeyMaps, KeyProperty):
    key_maps_kmi = {}  # class static data save kmi data

    def draw_key(self, layout):
        layout.context_pointer_set('system', self.parent_system)

        self.draw_kmi(layout, self.temp_kmi, self.key_maps)
        self.from_temp_key_update_data()

    def from_temp_key_update_data(self):
        data = self.kmi_data
        if self.is_change_system:
            self.set_kmi_system(self.temp_kmi, self.active_system.name)
            if self.key_data:
                self.set_property_data(self.temp_kmi, self.key_data)
            else:
                self.key_data = self.kmi_data
            self.tag_redraw(bpy.context)
        elif self.key_data != data:
            self.key_data = data
            self.update()
            self.tag_redraw(bpy.context)

    @staticmethod
    def draw_kmi(layout: bpy.types.UILayout, kmi: 'bpy', key_maps):
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
        row.operator(OperatorSetKeyMaps.bl_idname)

        row = split.row()
        row.prop(kmi, "map_type", text="")
        if map_type == 'KEYBOARD':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'MOUSE':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'NDOF':
            row.prop(kmi, "type", text="", full_event=True)
        elif map_type == 'TWEAK':
            sub_row = row.row()
            sub_row.prop(kmi, "type", text="")
            sub_row.prop(kmi, "value", text="")
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
                sub_row = sub.row(align=True)

                if map_type == 'KEYBOARD':
                    sub_row.prop(kmi, "type", text="", event=True)
                    sub_row.prop(kmi, "value", text="")
                    sub_row_repeat = sub_row.row(align=True)
                    sub_row_repeat.active = kmi.value in {'ANY', 'PRESS'}
                    sub_row_repeat.prop(kmi, "repeat", text="Repeat")
                elif map_type in {'MOUSE', 'NDOF'}:
                    sub_row.prop(kmi, "type", text="")
                    sub_row.prop(kmi, "value", text="")

                if map_type in {'KEYBOARD', 'MOUSE'} and kmi.value == 'CLICK_DRAG':
                    sub_row = sub.row()
                    sub_row.prop(kmi, "direction")

                sub_row = sub.row()
                sub_row.scale_x = 0.75
                sub_row.prop(kmi, "any", toggle=True)
                # Use `*_ui` properties as integers aren't practical.
                sub_row.prop(kmi, "shift_ui", toggle=True)
                sub_row.prop(kmi, "ctrl_ui", toggle=True)
                sub_row.prop(kmi, "alt_ui", toggle=True)
                sub_row.prop(kmi, "oskey_ui", text="Cmd", toggle=True)

                sub_row.prop(kmi, "key_modifier", text="", event=True)

            col = box.column(align=True)
            for key in key_maps:
                col.label(text=key)

    def get_keymap(self, name, space_type, region_type):
        keymaps = self.active_keyconfig.keymaps
        return keymaps.get(name, keymaps.new(name, space_type=space_type, region_type=region_type))

    def register_key(self):
        from ...ops.system_ops import SystemOps
        if self.parent_system not in SystemKey.key_maps_kmi:
            SystemKey.key_maps_kmi[self.parent_system] = []
        key_data = self.key_data
        for key_map in self.key_maps:
            name, space_type, region_type = self.keymap_hierarchy_dict[key_map]
            keymap = self.get_keymap(name, space_type, region_type)
            kmi = keymap.keymap_items.new(SystemOps.bl_idname, key_data['type'], key_data['value'])

            self.set_property_data(kmi, key_data)
            self.set_kmi_system(kmi, self.parent_system.name)

            print('\t', self.parent_system.name, '\t', keymap.name, kmi.name, kmi.idname)
            SystemKey.key_maps_kmi[self.parent_system].append((keymap, kmi))

    def unregister_key(self):
        if self.parent_system in SystemKey.key_maps_kmi:
            for keymap, kmi in SystemKey.key_maps_kmi[self.parent_system]:
                keymap.keymap_items.remove(kmi)

            del SystemKey.key_maps_kmi[self.parent_system]

    def update(self):
        self.unregister_key()
        self.register_key()


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
    OperatorTempModifierKey,
    OperatorSetKeyMaps,
)
register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
