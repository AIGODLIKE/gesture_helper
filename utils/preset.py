import os


def get_preset_gesture_list() -> {str: str}:
    from .public import PRESET_FOLDER, get_pref
    from ..debug import IS_DEBUG
    items = {}

    pref = get_pref()
    try:
        for f in os.listdir(PRESET_FOLDER):
            path = os.path.join(PRESET_FOLDER, f)
            name = f[:-5]

            # 只允许调试模式有这个test文件,测试用的预设
            if name == "Test":
                if IS_DEBUG or pref.debug_property.debug_mode:
                    pass
                else:
                    continue

            if os.path.isfile(path) and f.lower().endswith('.json'):
                items[name] = path
    except Exception as e:
        print(e.args)
    return items
