def translate_event_value(string: str) -> str:
    """翻译Event值"""
    from ..src.translate import __all_translate__
    a = __all_translate__()
    if string in a:
        return a[string]
    return string
