"""
Keymap data for each gesture.
No need to record each shortcut's position;
only the shortcut data and keymap spaces are stored.
On add-on startup, shortcuts are recreated from data and cached.
Temporary keymaps are used to edit each shortcut's binding.
"""

import json
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, replace

import bpy
from bpy.app.translations import pgettext
from bpy.props import StringProperty
from idprop.types import IDPropertyGroup

from ..utils.property import set_property, get_kmi_property
from ..utils.public import get_debug, debug_print
from ..utils.public_cache import cache_update_lock
from .addon_keymap import AddonKeymapRegistry, add_addon_kmi, clear_orphan_gesture_kmis
from .temp_keymap import draw_temp_keymap_item, get_temp_kmi

default_key = {'type': 'RIGHTMOUSE', 'value': 'PRESS'}

_key_restart_suppression = 0

_KEY_TEXT_FIELDS = frozenset({
    'type',
    'value',
    'key_modifier',
    'direction',
    'map_type',
})
_KEY_BOOL_FIELDS = frozenset({
    'any',
    'shift',
    'ctrl',
    'alt',
    'oskey',
    'repeat',
    'head',
})


def validate_keymap_data(data: dict) -> None:
    """Validate the JSON shortcut schema before writing it to IDProperties."""
    if not isinstance(data, dict):
        raise ValueError("shortcut data must be an object")
    unknown = set(data) - _KEY_TEXT_FIELDS - _KEY_BOOL_FIELDS
    if unknown:
        raise ValueError(
            "unknown shortcut field(s): " + ", ".join(sorted(map(str, unknown)))
        )
    for key in _KEY_TEXT_FIELDS & data.keys():
        if not isinstance(data[key], str):
            raise ValueError(f"shortcut field {key!r} must be text")
    for key in _KEY_BOOL_FIELDS & data.keys():
        value = data[key]
        if not isinstance(value, bool) and not (
            isinstance(value, int) and value in (0, 1)
        ):
            raise ValueError(f"shortcut field {key!r} must be a boolean")


@contextmanager
def suppress_keymap_restarts():
    """Defer transient shortcut rebuilds while a gesture collection is mutated."""
    global _key_restart_suppression
    _key_restart_suppression += 1
    try:
        yield
    finally:
        _key_restart_suppression -= 1


@dataclass(frozen=True, slots=True)
class KeymapLoadFailure:
    """Serializable failure detail that never retains an RNA gesture proxy."""

    gesture_name: str
    keymap_name: str | None
    reason: str
    gesture_index: int | None = None

    def with_index(self, index: int):
        return replace(self, gesture_index=index)

    def __str__(self):
        location = self.gesture_name
        if self.keymap_name:
            location += f" / {self.keymap_name}"
        return f"{location}: {self.reason}"


class KeymapProperty:
    __key__ = 'key'
    __keymaps__ = 'keymaps'

    def set_key(self, value) -> None:
        self[self.__key__] = value
        self.key_update()

    def get_key(self) -> dict:
        default = default_key.copy()
        key = self.__key__
        if key in self and dict(self[key]):
            default.update(
                {k: dict(value) if value is IDPropertyGroup else value
                 for (k, value) in
                 dict(self[key]).items()}
            )
        return default

    def get_keymap(self) -> list:
        key = self.__keymaps__
        return self[key] if key in self else ['Window', "3D View", "Object Mode", "Mesh"]

    def set_keymap(self, value) -> None:
        self[self.__keymaps__] = value
        self.key_update()

    key = property(fget=get_key, fset=set_key, doc='Stores keymap binding data')
    keymaps = property(fget=get_keymap, fset=set_keymap, doc='Stores keymap spaces where the shortcut is active')

    key_string: StringProperty(get=lambda self: json.dumps(self.get_key()),
                               set=lambda self, value: self.set_key(json.loads(value)))
    keymaps_string: StringProperty(get=lambda self: json.dumps(self.get_keymap()),
                                   set=lambda self, value: self.set_keymap(json.loads(value)))


class GestureKeymap(KeymapProperty):

    @property
    def temp_kmi_data(self) -> dict:
        return get_kmi_property(self.temp_kmi)

    @property
    def temp_kmi(self) -> bpy.types.KeyMapItem:
        from ..ops import set_key
        return get_temp_kmi(set_key.OperatorTempModifierKey.bl_idname, {'gesture': self.name})

    @property
    def add_kmi_data(self) -> dict:
        idname = 'wm.gesture_menu' if self.gesture_type == 'MENU' else 'wm.gesture_operator'
        return {'idname': idname, **self.key}

    @cache_update_lock
    def from_temp_key_update_data(self) -> None:
        data = self.temp_kmi_data
        if self.key != data:
            debug_print("from_temp_key_update_data", key='key')
            debug_print(self.key, key='key')
            debug_print(data, key='key')
            self.key = data
            self.key_restart()

    def to_temp_kmi(self) -> None:
        key = dict(self.key)
        debug_print(f'Gesture -> Temp kmi {self.name} ({key})', key='key')
        # type enum depends on map_type; set map_type first.
        kmi = self.temp_kmi
        t = key.get('type', '')
        mt = key.pop('map_type', None) or (
            'MOUSE' if 'MOUSE' in t or t in {'PEN', 'ERASER'} else 'KEYBOARD'
        )
        if kmi.map_type != mt:
            kmi.map_type = mt
        set_property(kmi, key)

    def draw_key(self, layout) -> None:
        draw_temp_keymap_item(layout, self.temp_kmi, self.keymaps)
        if get_debug():
            layout.label(text=str(self.key))
            layout.label(text=str(self.keymaps))
            layout.label(text=str(self.temp_kmi.id))
            layout.label(text=str(self.temp_kmi))
            layout.label(text=str(self.temp_kmi_data))
        # Do not write RNA / restart keymaps inside draw — debounce instead.
        from ..utils.ui_draw_sync import schedule

        def _flush():
            from ..utils.public import get_pref
            active = get_pref().active_gesture
            if active is not None:
                active.from_temp_key_update_data()

        schedule('gesture_temp_key_sync', _flush)

    def key_load(self, *, force: bool = False) -> list[KeymapLoadFailure]:
        """Load this gesture's shortcuts, returning failures without aborting siblings."""
        try:
            if not force and not self.is_enable:
                return []
            kmi_data = dict(self.add_kmi_data)
            properties = {"gesture": self.name}
            stored_keymaps = self.keymaps
            if isinstance(stored_keymaps, str):
                raise TypeError("keymaps must be a list of keymap names")
            keymap_names = list(stored_keymaps)
            if not all(isinstance(name, str) for name in keymap_names):
                raise TypeError("keymap names must be text")
        except Exception as exc:
            try:
                name = self.name
            except Exception:
                name = '<unknown gesture>'
            failure = KeymapLoadFailure(
                name,
                None,
                f"cannot read shortcut data ({exc})",
            )
            debug_print(str(failure), key='key')
            return [failure]

        if get_debug("key"):
            content = {k: v for k, v in kmi_data.items() if k in ("type", "value")}
            debug_print(f"Add Kmi\t{content} to {keymap_names}", flush=True, key='key')

        failures = []
        for keymap_name in keymap_names:
            try:
                result = add_addon_kmi(keymap_name, kmi_data, properties)
                if force and result is None:
                    raise RuntimeError("add-on key configuration is unavailable")
            except Exception as exc:
                failure = KeymapLoadFailure(self.name, keymap_name, str(exc))
                failures.append(failure)
                debug_print(f"Gesture keymap skipped: {failure}", key='key')
        return failures

    @cache_update_lock
    def key_update(self) -> None:
        self.key_restart()
        if get_debug('key'):
            caller_name = traceback.extract_stack()[-2][2]
            debug_print("Key Update called by {}".format(caller_name), self, key='key')

    @classmethod
    def key_all_load(
            cls,
            *,
            force: bool = False,
            start_index: int = 0,
    ) -> list[KeymapLoadFailure]:
        """Load all keymaps and keep valid items when one binding is invalid."""
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None:
            return []
        failures = []
        for index, g in enumerate(gestures):
            if index < start_index:
                continue
            try:
                failures.extend(
                    failure.with_index(index)
                    for failure in g.key_load(force=force)
                )
            except Exception as exc:
                name = getattr(g, 'name', '<unknown gesture>')
                failure = KeymapLoadFailure(
                    name,
                    None,
                    f"unexpected shortcut load failure ({exc})",
                    gesture_index=index,
                )
                failures.append(failure)
                debug_print(str(failure), key='key')
        return failures

    @classmethod
    def key_all_unload(cls) -> None:
        """Unload all keymaps (registration list only)."""
        AddonKeymapRegistry.clear()

    @classmethod
    def key_clear_legacy(cls) -> int:
        """Clear keymaps, including legacy orphan scan (called on register/unregister)."""
        cls.key_all_unload()
        clear_count = clear_orphan_gesture_kmis()
        if get_debug('key'):
            debug_print("Gesture Clear Legacy Keymap count", clear_count, flush=True, key='key')
        return clear_count

    @classmethod
    def key_restart(
            cls,
            *,
            validate_from_index: int | None = None,
    ) -> tuple[KeymapLoadFailure, ...]:
        """Reset bindings and optionally force-validate newly appended gestures."""
        if _key_restart_suppression:
            return ()
        cls.key_all_unload()
        clear_orphan_gesture_kmis()

        if validate_from_index is None:
            failures = tuple(cls.key_all_load())
        else:
            # Validate even when the gesture or global preference is disabled.
            # These temporary KMIs are removed before restoring normal state.
            validation_failures = cls.key_all_load(
                force=True,
                start_index=max(0, validate_from_index),
            )
            cls.key_all_unload()
            clear_orphan_gesture_kmis()
            normal_failures = cls.key_all_load()
            imported_normal_failures = [
                failure
                for failure in normal_failures
                if (
                    failure.gesture_index is None
                    or failure.gesture_index >= validate_from_index
                )
            ]
            failures = tuple(dict.fromkeys([
                *validation_failures,
                *imported_normal_failures,
            ]))
        if get_debug('key'):
            debug_print("Gesture Key Restart", AddonKeymapRegistry.entry_count(), key='key')
            for i in traceback.extract_stack():
                debug_print(i, key='key')
        return failures

    def restore_key(self):
        """Reset shortcut to default."""
        self.key = default_key
        kmi = self.temp_kmi
        kmi.shift = False
        kmi.ctrl = False
        kmi.alt = False
        kmi.oskey = False
        kmi.any = False
        self.to_temp_kmi()

    @property
    def __key_str__(self) -> str:
        """Return display string for the shortcut."""
        from ..src.translate import __keymap_translate__
        keymap = self.key
        if keymap:
            items = [
                k.title()[0] if isinstance(v, int) else __keymap_translate__(v)
                for k, v in keymap.items()
                if k == 'type' or (k in ('ctrl', 'shift', 'alt') and v == 1)
            ]
            if bpy.context.preferences.view.use_translate_interface:
                return "".join(items)
            else:
                return " ".join(items)
        else:
            return pgettext("No keymap")
