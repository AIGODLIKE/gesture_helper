from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "gesture" / "gesture_keymap.py"
PACKAGE = "gesture_helper_keymap_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_keymap_module():
    for package_name in (PACKAGE, f"{PACKAGE}.gesture", f"{PACKAGE}.utils"):
        package = _module(package_name)
        package.__path__ = []

    bpy = _module("bpy")
    bpy.types = types.SimpleNamespace(KeyMapItem=object)
    bpy.context = types.SimpleNamespace(
        preferences=types.SimpleNamespace(
            view=types.SimpleNamespace(use_translate_interface=False),
        ),
    )
    bpy_app = _module("bpy.app")
    _module("bpy.app.translations", pgettext=lambda text: text)
    _module("bpy.props", StringProperty=lambda **_kwargs: None)
    bpy.app = bpy_app

    idprop = _module("idprop")
    idprop_types = _module("idprop.types", IDPropertyGroup=type("IDPropertyGroup", (), {}))
    idprop.types = idprop_types

    _module(
        f"{PACKAGE}.utils.property",
        set_property=lambda *_args: None,
        get_kmi_property=lambda _kmi: {},
    )
    _module(
        f"{PACKAGE}.utils.public",
        get_debug=lambda *_args: False,
        debug_print=lambda *_args, **_kwargs: None,
    )
    _module(
        f"{PACKAGE}.utils.public_cache",
        cache_update_lock=lambda func: func,
    )

    class Registry:
        @classmethod
        def clear(cls):
            return None

        @classmethod
        def entry_count(cls):
            return 0

    _module(
        f"{PACKAGE}.gesture.addon_keymap",
        AddonKeymapRegistry=Registry,
        add_addon_kmi=lambda *_args, **_kwargs: None,
        clear_orphan_gesture_kmis=lambda: 0,
    )
    _module(
        f"{PACKAGE}.gesture.temp_keymap",
        draw_temp_keymap_item=lambda *_args: None,
        get_temp_kmi=lambda *_args, **_kwargs: None,
    )
    _module(f"{PACKAGE}.utils.gesture_store", get_gestures=lambda: [])

    name = f"{PACKAGE}.gesture.gesture_keymap"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


keymap_module = _load_keymap_module()


class FakeGesture(keymap_module.GestureKeymap):
    def __init__(self, name, keymaps):
        self.name = name
        self._keymaps = keymaps

    @property
    def is_enable(self):
        return True

    @property
    def add_kmi_data(self):
        return {"idname": "wm.gesture_operator", "type": "A", "value": "PRESS"}

    @property
    def keymaps(self):
        return self._keymaps


class KeymapRestartTests(unittest.TestCase):
    def test_shortcut_schema_rejects_non_scalar_and_unknown_fields(self):
        keymap_module.validate_keymap_data({
            "type": "A",
            "value": "PRESS",
            "ctrl": True,
        })
        with self.assertRaisesRegex(ValueError, "must be text"):
            keymap_module.validate_keymap_data({
                "type": [1, "A"],
                "value": "PRESS",
            })
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            keymap_module.validate_keymap_data({
                "type": "A",
                "value": "PRESS",
                "ctrl": [],
            })
        with self.assertRaisesRegex(ValueError, "unknown shortcut field"):
            keymap_module.validate_keymap_data({
                "type": "A",
                "value": "PRESS",
                "mystery": True,
            })

    def test_key_load_keeps_valid_keymaps_after_failures(self):
        attempted = []
        original = keymap_module.add_addon_kmi

        def add(keymap_name, _kmi_data, _properties):
            attempted.append(keymap_name)
            if keymap_name.startswith("Bad"):
                raise ValueError("invalid binding")

        keymap_module.add_addon_kmi = add
        try:
            failures = FakeGesture(
                "Mixed",
                ["Bad One", "Window", "Bad Two", "3D View"],
            ).key_load()
        finally:
            keymap_module.add_addon_kmi = original

        self.assertEqual(attempted, ["Bad One", "Window", "Bad Two", "3D View"])
        self.assertEqual(len(failures), 2)
        self.assertIn("Bad One", str(failures[0]))
        self.assertIn("Bad Two", str(failures[1]))

    def test_forced_validation_rejects_an_unavailable_keyconfig(self):
        original = keymap_module.add_addon_kmi
        keymap_module.add_addon_kmi = lambda *_args, **_kwargs: None
        try:
            failures = FakeGesture("Disabled", ["Window"]).key_load(force=True)
        finally:
            keymap_module.add_addon_kmi = original

        self.assertEqual(len(failures), 1)
        self.assertIn("unavailable", str(failures[0]))

    def test_key_all_load_continues_after_unexpected_gesture_failure(self):
        calls = []

        class Broken:
            name = "Broken"

            def key_load(self, **_kwargs):
                calls.append(self.name)
                raise RuntimeError("broken")

        class Valid:
            name = "Valid"

            def key_load(self, **_kwargs):
                calls.append(self.name)
                return []

        store_module = sys.modules[f"{PACKAGE}.utils.gesture_store"]
        original = store_module.get_gestures
        store_module.get_gestures = lambda: [Broken(), Valid()]
        try:
            failures = keymap_module.GestureKeymap.key_all_load()
        finally:
            store_module.get_gestures = original

        self.assertEqual(calls, ["Broken", "Valid"])
        self.assertEqual(len(failures), 1)
        self.assertIn("Broken", str(failures[0]))

    def test_restart_suppression_is_nested_and_requires_one_final_restart(self):
        calls = []

        class Harness(keymap_module.GestureKeymap):
            @classmethod
            def key_all_unload(cls):
                calls.append("unload")

            @classmethod
            def key_all_load(cls, **_kwargs):
                calls.append("load")
                return [keymap_module.KeymapLoadFailure("Gesture", None, "invalid")]

        original_clear = keymap_module.clear_orphan_gesture_kmis
        keymap_module.clear_orphan_gesture_kmis = lambda: calls.append("orphans") or 0
        try:
            with keymap_module.suppress_keymap_restarts():
                self.assertEqual(Harness.key_restart(), ())
                with keymap_module.suppress_keymap_restarts():
                    self.assertEqual(Harness.key_restart(), ())
            self.assertEqual(calls, [])
            failures = Harness.key_restart()
        finally:
            keymap_module.clear_orphan_gesture_kmis = original_clear

        self.assertEqual(calls, ["unload", "orphans", "load"])
        self.assertEqual([str(failure) for failure in failures], ["Gesture: invalid"])

    def test_import_validation_ignores_old_failures_and_forces_new_disabled_items(self):
        calls = []
        old_failure = keymap_module.KeymapLoadFailure(
            "Old", "Window", "old invalid", gesture_index=0,
        )
        new_failure = keymap_module.KeymapLoadFailure(
            "New", "Window", "new invalid", gesture_index=2,
        )

        class Harness(keymap_module.GestureKeymap):
            @classmethod
            def key_all_unload(cls):
                calls.append("unload")

            @classmethod
            def key_all_load(cls, *, force=False, start_index=0):
                calls.append(("load", force, start_index))
                if force:
                    return [new_failure]
                return [old_failure, new_failure]

        original_clear = keymap_module.clear_orphan_gesture_kmis
        keymap_module.clear_orphan_gesture_kmis = lambda: calls.append("orphans") or 0
        try:
            failures = Harness.key_restart(validate_from_index=2)
        finally:
            keymap_module.clear_orphan_gesture_kmis = original_clear

        self.assertEqual(failures, (new_failure,))
        self.assertEqual(
            calls,
            [
                "unload",
                "orphans",
                ("load", True, 2),
                "unload",
                "orphans",
                ("load", False, 0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
