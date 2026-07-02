import os

DEBUG_ONLY_PRESET_NAMES = frozenset({"Example Preset"})


def get_preset_gesture_list(*, include_debug_only: bool | None = None) -> dict[str, str]:
    from .public import PRESET_FOLDER
    from .debug_util import get_debug

    if include_debug_only is None:
        include_debug_only = get_debug()

    items = {}

    try:
        for f in os.listdir(PRESET_FOLDER):
            path = os.path.join(PRESET_FOLDER, f)
            name = f[:-5]

            if os.path.isfile(path) and f.lower().endswith('.json'):
                if not include_debug_only and name in DEBUG_ONLY_PRESET_NAMES:
                    continue
                items[name] = path
    except Exception as e:
        print(e.args)
    return items
