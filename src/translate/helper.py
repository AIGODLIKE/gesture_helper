import bpy
from ...utils.debug_util import debug_print, debug_traceback, debug_trace_stack


class TranslationHelper:
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()
        # "*" covers pgettext / pgettext_iface; "Operator" covers bl_label / report().
        contexts = bpy.app.translations.contexts
        msgctxts = (contexts.default, contexts.operator_default)

        bucket = self.translations_dict.setdefault(lang, {})
        for src, src_trans in data.items():
            for msgctxt in msgctxts:
                bucket[(msgctxt, src)] = src_trans

    def register(self) -> bool:
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
            return True
        except ValueError as e:
            debug_print(e.args, key='operator')
            debug_trace_stack(key='operator')
            debug_traceback(key='operator')
            return False

    def unregister(self):
        try:
            bpy.app.translations.unregister(self.name)
        except ValueError as e:
            # A duplicate-name registration failure must not abort the rest
            # of the unregister chain.
            debug_print(e.args, key='operator')
