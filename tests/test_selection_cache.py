from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "utils" / "selection.py"
PACKAGE = "_gesture_selection_cache_test"


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


scan_count = 0


def _iter_elements(gesture):
    global scan_count
    scan_count += 1
    yield from gesture.element


package = _module(PACKAGE)
package.__path__ = [str(MODULE_PATH.parents[1])]
utils_package = _module(f"{PACKAGE}.utils")
utils_package.__path__ = [str(MODULE_PATH.parent)]
_module(f"{PACKAGE}.utils.iteration", iter_elements=_iter_elements)
_module(
    f"{PACKAGE}.utils.public_cache",
    PublicCache=type(
        "PublicCache",
        (),
        {"_suppress_radio_update": False},
    ),
    PublicCacheFunc=type("PublicCacheFunc", (), {}),
)

name = f"{PACKAGE}.utils.selection"
spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
selection = importlib.util.module_from_spec(spec)
sys.modules[name] = selection
assert spec.loader is not None
spec.loader.exec_module(selection)


class GestureProxy:
    def __init__(self, pointer, elements):
        self.pointer = pointer
        self.element = elements

    def as_pointer(self):
        return self.pointer


class ElementProxy:
    def __init__(self, parent_gesture, *, radio=True):
        self.radio = radio
        self.parent_gesture = parent_gesture


class ActiveElementCacheTests(unittest.TestCase):
    def setUp(self):
        global scan_count
        scan_count = 0
        selection._ACTIVE_ELEMENT_CACHE.clear()

    def test_equivalent_gesture_proxies_share_the_active_element_cache(self):
        first_gesture = GestureProxy(101, [])
        element = ElementProxy(first_gesture)
        first_gesture.element.append(element)
        second_gesture = GestureProxy(101, [element])

        first = selection.resolve_active_element(first_gesture)
        second = selection.resolve_active_element(second_gesture)

        self.assertIs(first, element)
        self.assertIs(second, element)
        self.assertEqual(scan_count, 1)

    def test_clear_works_through_an_equivalent_gesture_proxy(self):
        first_gesture = GestureProxy(202, [])
        element = ElementProxy(first_gesture)
        first_gesture.element.append(element)
        second_gesture = GestureProxy(202, [element])

        selection.resolve_active_element(first_gesture)
        selection.clear_active_element_cache(second_gesture)
        selection.resolve_active_element(second_gesture)

        self.assertEqual(scan_count, 2)

    def test_missing_selection_is_cached_until_explicitly_cleared(self):
        gesture = GestureProxy(303, [])
        gesture.element.extend((
            ElementProxy(gesture, radio=False),
            ElementProxy(gesture, radio=False),
        ))

        self.assertIsNone(selection.resolve_active_element(gesture))
        self.assertIsNone(selection.resolve_active_element(gesture))
        self.assertEqual(scan_count, 1)

        selection.clear_active_element_cache(gesture)
        self.assertIsNone(selection.resolve_active_element(gesture))
        self.assertEqual(scan_count, 2)


if __name__ == "__main__":
    unittest.main()
