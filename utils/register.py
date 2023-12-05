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
    icons.Icons.init()
    for module in module_list:
        module.register()
    public_cache.PublicCacheFunc.cache_clear()
    gesture_keymap.GestureKeymap.key_init()

    pref = get_pref()
    pref.other_property.is_move_element = False

    ag = pref.active_gesture
    ae = pref.active_element
    if ag:
        ag.to_temp_kmi()
    if ae:
        ae.to_operator_tmp_kmi()


def unregister():
    gesture_keymap.GestureKeymap.key_remove()
    for module in module_list:
        module.unregister()
