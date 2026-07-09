"""Add-on keymap registration and KMI property helpers."""

from __future__ import annotations

import bpy
from mathutils import Euler, Matrix, Vector

from ..utils.debug_util import debug_print

_GESTURE_OPERATOR_IDNAMES = frozenset({
    "wm.gesture_operator",
    "gesture.operator",  # legacy
})

_WARNED_UNKNOWN_PROP_TYPES: set[type] = set()


class AddonKeymapRegistry:
    """Track keymap items created by this add-on for list-based unload."""

    _entries: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []

    @classmethod
    def add(cls, keymap: bpy.types.KeyMap, kmi: bpy.types.KeyMapItem) -> None:
        cls._entries.append((keymap, kmi))

    @classmethod
    def clear(cls) -> None:
        for keymap, kmi in cls._entries:
            if kmi is not None and keymap is not None:
                try:
                    keymap.keymap_items.remove(kmi)
                except (RuntimeError, ValueError):
                    ...
        cls._entries.clear()

    @classmethod
    def entry_count(cls) -> int:
        return len(cls._entries)


def _set_kmi_properties(prop: dict, kmi_properties) -> None:
    for key, value in prop.items():
        setattr(kmi_properties, key, value)


def get_kmi_operator_properties(kmi: bpy.types.KeyMapItem) -> dict:
    properties = kmi.properties
    if properties is None:
        return {}
    prop_keys = dict(properties.items()).keys()
    dictionary = {i: getattr(properties, i, None) for i in prop_keys}
    del_key = []
    for item in dictionary:
        prop = getattr(properties, item, None)
        typ = type(prop)
        if prop:
            if typ == Vector:
                dictionary[item] = dictionary[item].to_tuple()
            elif typ == Euler:
                dictionary[item] = dictionary[item][:]
            elif typ == Matrix:
                dictionary[item] = tuple(i[:] for i in dictionary[item])
            elif typ == bpy.types.bpy_prop_array:
                dictionary[item] = dictionary[item][:]
            elif typ in (str, bool, float, int, set, list, tuple):
                ...
            elif typ.__name__ in [
                'TRANSFORM_OT_shrink_fatten',
                'TRANSFORM_OT_translate',
                'TRANSFORM_OT_edge_slide',
                'NLA_OT_duplicate',
                'ACTION_OT_duplicate',
                'GRAPH_OT_duplicate',
                'OBJECT_OT_duplicate',
                'MESH_OT_loopcut',
                'MESH_OT_rip_edge',
                'MESH_OT_rip',
                'MESH_OT_duplicate',
                'MESH_OT_offset_edge_loops',
                'MESH_OT_extrude_faces_indiv',
                'MESH_OT_select_linked_pick',
            ]:
                del_key.append(item)
            else:
                if typ not in _WARNED_UNKNOWN_PROP_TYPES:
                    _WARNED_UNKNOWN_PROP_TYPES.add(typ)
                    debug_print('Unknown operator property type', typ, dictionary[item], key='key')
                del_key.append(item)
    for i in del_key:
        dictionary.pop(i)
    return dictionary


def get_addon_keymap(keymap: str) -> bpy.types.KeyMap | None:
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return None
    kc = wm.keyconfigs
    if kc is None:
        return None
    keymaps = kc.addon.keymaps.get(keymap)
    if keymaps is not None:
        return keymaps

    km = kc.default.keymaps.get(keymap)
    if km:
        return kc.addon.keymaps.new(km.name, space_type=km.space_type, region_type=km.region_type)
    return kc.addon.keymaps.new(keymap, space_type='EMPTY', region_type='WINDOW')


_KMI_DATA_KEYS = frozenset({
    "idname",
    "type",
    "value",
    "any",
    "shift",
    "ctrl",
    "alt",
    "oskey",
    "key_modifier",
    "direction",
    "repeat",
    "head",
})


def add_addon_kmi(
        keymap_name: str,
        kmi_data: dict,
        properties: dict,
) -> tuple[bpy.types.KeyMap, bpy.types.KeyMapItem] | None:
    keymap = get_addon_keymap(keymap_name)
    if keymap is None:
        return None
    kmi_data = {k: v for k, v in kmi_data.items() if k in _KMI_DATA_KEYS}

    kmi = keymap.keymap_items.new(**kmi_data)
    _set_kmi_properties(properties, kmi.properties)
    AddonKeymapRegistry.add(keymap, kmi)
    return keymap, kmi


def clear_orphan_gesture_kmis() -> int:
    """One-time cleanup for legacy KMIs not tracked in the registry."""
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return 0
    kcs = wm.keyconfigs
    if kcs is None:
        return 0
    registered = {id(kmi) for _, kmi in AddonKeymapRegistry._entries}
    clear_count = 0

    for km in kcs.addon.keymaps.values():
        for kmi in list(km.keymap_items):
            if kmi.idname not in _GESTURE_OPERATOR_IDNAMES:
                continue
            if id(kmi) in registered:
                continue
            km.keymap_items.remove(kmi)
            clear_count += 1

    return clear_count
