import bpy
from bpy.props import EnumProperty, StringProperty

from ..utils.public import PublicOperator, get_pref, PublicProperty, debug_print
from ..utils.public_ui import icon_two

# Matches default gesture keymaps and other frequent 3D Viewport contexts.
COMMON_GESTURE_KEYMAPS = frozenset({
    "Window",
    "3D View",
    "Object Mode",
    "Mesh",
    "Sculpt",
    "Pose",
    "Weight Paint",
    "Vertex Paint",
    "Image Paint",
    "Curve",
    "Armature",
    "Font",
    "Lattice",
    "Metaball",
    "Grease Pencil Edit Mode",
    "Grease Pencil Paint Mode",
    "Grease Pencil Sculpt Mode",
})


class OperatorSetKeyMaps(PublicOperator, PublicProperty):
    bl_idname = 'wm.gesture_set_key_maps'
    bl_label = 'Set keymaps'

    __temp_selected_keymaps__ = []  # static
    __session_keymap_filter__ = 'COMMON'
    __dialog_keymap_hierarchy__ = None
    __filtered_keymap_hierarchy__ = []
    add_keymap: StringProperty(options={'SKIP_SAVE'})

    def _update_keymap_filter(self, _context):
        OperatorSetKeyMaps.__session_keymap_filter__ = self.keymap_filter
        OperatorSetKeyMaps._rebuild_filtered_hierarchy()
        if self.keymap_filter == 'COMMON':
            OperatorSetKeyMaps._ensure_common_default_expansion()

    @classmethod
    def _rebuild_filtered_hierarchy(cls) -> None:
        items = cls.__dialog_keymap_hierarchy__
        if items is None:
            cls.__filtered_keymap_hierarchy__ = []
            return
        cls.__filtered_keymap_hierarchy__ = cls._filter_keymap_hierarchy(
            items, cls.__session_keymap_filter__,
        )

    keymap_filter: EnumProperty(
        name='Keymap list',
        items=(
            ('COMMON', 'Common', 'Show frequently used keymaps', 'SOLO_ON', 0),
            ('ALL', 'All', 'Show all keymaps', 'PRESET', 1),
        ),
        default='COMMON',
        update=_update_keymap_filter,
    )

    @classmethod
    def _expand_keymap_groups(cls, names: tuple[str, ...]) -> None:
        wm = getattr(bpy.context, "window_manager", None)
        if wm is None:
            return
        keymaps = wm.keyconfigs.default.keymaps
        for name in names:
            keymap = keymaps.get(name)
            if keymap is not None:
                keymap.show_expanded_items = True

    @classmethod
    def _ensure_common_default_expansion(cls) -> None:
        cls._expand_keymap_groups(("3D View",))

    @property
    def active_gesture_keymaps(self):
        return get_pref().active_gesture.keymaps

    def invoke(self, context, _):
        if self.add_keymap:  # Add keymap item
            if self.add_keymap in OperatorSetKeyMaps.__temp_selected_keymaps__:
                OperatorSetKeyMaps.__temp_selected_keymaps__.remove(self.add_keymap)
            else:
                if len(OperatorSetKeyMaps.__temp_selected_keymaps__) == 0:
                    OperatorSetKeyMaps.__temp_selected_keymaps__ = [self.add_keymap, ]
                else:
                    OperatorSetKeyMaps.__temp_selected_keymaps__.append(self.add_keymap)
            return {'FINISHED'}

        from bl_keymap_utils import keymap_hierarchy
        OperatorSetKeyMaps.__dialog_keymap_hierarchy__ = keymap_hierarchy.generate()
        OperatorSetKeyMaps.__temp_selected_keymaps__ = self.active_gesture_keymaps
        self.keymap_filter = OperatorSetKeyMaps.__session_keymap_filter__
        OperatorSetKeyMaps._rebuild_filtered_hierarchy()
        if self.keymap_filter == 'COMMON':
            OperatorSetKeyMaps._ensure_common_default_expansion()
        return context.window_manager.invoke_props_dialog(**{'operator': self, 'width': 600})

    def execute(self, _):
        self.active_gesture.keymaps = OperatorSetKeyMaps.__temp_selected_keymaps__
        OperatorSetKeyMaps.__session_keymap_filter__ = self.keymap_filter
        debug_print(self.bl_idname, "execute", self.active_gesture.keymaps, key='key')
        return {'FINISHED'}

    def draw_keymap_filter(self, layout: bpy.types.UILayout) -> None:
        box = layout.box()
        header = box.row(align=True)
        header.label(text="Keymap list", icon='KEYINGSET')
        row = box.row(align=True)
        row.scale_y = 1.1
        row.prop_enum(self, "keymap_filter", 'COMMON', text="Common", icon='SOLO_ON')
        row.prop_enum(self, "keymap_filter", 'ALL', text="All", icon='PRESET')

    def draw(self, _):
        OperatorSetKeyMaps.__session_keymap_filter__ = self.keymap_filter
        OperatorSetKeyMaps._rebuild_filtered_hierarchy()
        layout = self.layout.column(align=True)
        layout.label(text=self.pref.active_gesture.name)
        self.draw_keymap_filter(layout)
        layout.separator()
        layout.emboss = "NONE"
        split = layout.split(factor=0.65)
        left_col = split.column(align=True)
        right_col = split.column(align=True)
        self.draw_keymaps(left_col, OperatorSetKeyMaps.__filtered_keymap_hierarchy__)
        self.draw_selected_keymap(right_col)

    @classmethod
    def _filter_keymap_hierarchy(cls, items, filter_mode: str):
        if filter_mode == 'ALL':
            return list(items)

        filtered = []
        for item in items:
            name, space_type, window_type, child = item
            filtered_child = cls._filter_keymap_hierarchy(child, filter_mode) if child else []
            if name in COMMON_GESTURE_KEYMAPS or filtered_child:
                filtered.append((name, space_type, window_type, filtered_child))
        return filtered

    def draw_selected_keymap(self, layout):
        selected = OperatorSetKeyMaps.__temp_selected_keymaps__
        if not selected:
            row = layout.row()
            row.enabled = False
            row.label(text="—", icon='BLANK1')
            return
        for name in selected:
            text = bpy.app.translations.pgettext(name)
            layout.operator(self.bl_idname, icon='RESTRICT_SELECT_OFF', text=text).add_keymap = name

    def draw_keymaps(self, layout, items):
        keymaps = bpy.context.window_manager.keyconfigs.default.keymaps
        for name, space_type, window_type, child in items:
            keymap = keymaps.get(name, None)
            if keymap:
                column = layout.column(align=True)
                row = column.row(align=True)
                row.label(text=keymap.name)
                show_child = getattr(keymap, 'show_expanded_items', False)

                if child:
                    row.prop(keymap, 'show_expanded_items', text='')
                select_icon = icon_two(name in OperatorSetKeyMaps.__temp_selected_keymaps__, 'RESTRICT_SELECT')
                row.operator(OperatorSetKeyMaps.bl_idname, text='', icon=select_icon).add_keymap = keymap.name
                if show_child and child:
                    self.draw_keymaps(column.box().column(align=True), child)


class OperatorTempModifierKey(bpy.types.Operator):
    bl_idname = 'wm.gesture_temp_kmi'
    bl_label = 'Temp Kmi Key Gesture Helper'

    gesture: StringProperty()

    def execute(self, _):
        return {'PASS_THROUGH'}
