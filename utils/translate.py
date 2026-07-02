from bpy.app.translations import pgettext_iface


def translate_lines_text(*args, split="\n"):
    return split.join([pgettext_iface(line) for line in args])
