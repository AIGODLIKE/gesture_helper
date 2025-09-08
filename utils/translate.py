import bpy


def translate_lines_text(*args, split="\n"):
    from bpy.app.translations import pgettext_iface
    return split.join([pgettext_iface(line) for line in args])


def is_zh() -> bool:
    view = bpy.context.preferences.view
    return view.use_translate_interface and view.language in ("zh_HANS", "zh_CN")
