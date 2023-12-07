from . import preferences, public_cache, property, icons
from .gesture import gesture_keymap
from .public import get_pref
from .. import ops, ui

module_list = (
    ui,
    ops,
    property,
    preferences,
)


def register():
    icons.Icons.register()
    for module in module_list:
        module.register()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_init()

    pref = get_pref()
    pref.other_property.is_move_element = False
    pref.update_state()


def unregister():
    from ..ops.export_import import Export
    Export.backups()

    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
    icons.Icons.unregister()
# TODO 修改自定义样式
