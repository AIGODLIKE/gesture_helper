import os
from ..utils.debug_util import debug_print

DEBUG_ONLY_PRESET_NAMES = frozenset({
    "Example Elements and Layout",
    "Example Essentials",
    "Example Operator Contexts",
    "Example Property Controls",
    "Example Practical Menu",
    "Example Validation States",
})


def get_preset_gesture_list(*, include_debug_only: bool | None = None) -> dict[str, str]:
    from .public import PRESET_FOLDER

    if include_debug_only is None:
        try:
            from .pref import get_pref
            include_debug_only = bool(
                get_pref().debug_property.show_example_presets
            )
        except (AttributeError, ImportError, KeyError, ReferenceError, RuntimeError):
            include_debug_only = False

    items = {}

    try:
        for f in sorted(os.listdir(PRESET_FOLDER), key=str.casefold):
            path = os.path.join(PRESET_FOLDER, f)
            name = f[:-5]

            if os.path.isfile(path) and f.lower().endswith('.json'):
                if not include_debug_only and name in DEBUG_ONLY_PRESET_NAMES:
                    continue
                items[name] = path
    except Exception as e:
        debug_print(e.args, key='export_import')
    return items
