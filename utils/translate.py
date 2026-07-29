from bpy.app.translations import pgettext_iface


def translate_lines_text(*args, split="\n"):
    return split.join([pgettext_iface(line) for line in args])


def translate_rna_text(text: str, context=None, *, tooltip: bool = False) -> str:
    """Translate RNA text without overriding an explicit RNA context."""
    if not text:
        return ''

    try:
        import bpy
        from bpy.app.translations import pgettext_tip

        translate = pgettext_tip if tooltip else pgettext_iface
        if context is not None:
            contexts = (context,)
        else:
            contexts = (None, *tuple(bpy.app.translations.contexts))

        seen = set()
        for msgctxt in contexts:
            if msgctxt in seen:
                continue
            seen.add(msgctxt)
            try:
                translated = translate(text, msgctxt)
            except TypeError:
                if context is not None:
                    return text
                translated = translate(text)
            if translated != text:
                return translated
    except (AttributeError, ImportError, TypeError):
        pass
    return text
