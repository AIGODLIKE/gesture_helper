import os


def get_preset_gesture_list() -> {str: str}:
    from .public import PRESET_FOLDER
    items = {}
    try:
        for f in os.listdir(PRESET_FOLDER):
            path = os.path.join(PRESET_FOLDER, f)
            if os.path.isfile(path) and f.lower().endswith('.json'):
                items[f[:-5]] = path
    except Exception as e:
        print(e.args)
    return items
