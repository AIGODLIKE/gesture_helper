"""Debug flags from add-on preferences (no imports from public_cache)."""


def get_debug(key=None) -> bool:
    """Return debug flag from preferences; optional *key* selects a sub-flag."""
    try:
        from .pref import get_pref
        prop = get_pref().debug_property
    except (KeyError, AttributeError, ImportError):
        return False
    if not prop.debug_mode:
        return False
    if not key:
        return True
    kl = key.lower()
    flags = {
        'key': prop.debug_key,
        'kmi': prop.debug_kmi_sync,
        'kmi_sync': prop.debug_kmi_sync,
        'draw_gpu': prop.debug_draw_gpu_mode,
        'gpu': prop.debug_draw_gpu_mode,
        'export_import': prop.debug_export_import,
        'operator': prop.debug_operator,
        'modal': prop.debug_modal,
        'poll': prop.debug_poll,
        'cache': prop.debug_cache,
        'extension': prop.debug_extension,
        'panel': prop.debug_panel,
    }
    return flags.get(kl, True)


def debug_print(*args, key=None, **kwargs) -> None:
    """Print only when the matching debug flag is enabled."""
    if get_debug(key):
        print(*args, **kwargs)


def debug_traceback(key=None) -> None:
    """Print stack trace only when debug is enabled."""
    if not get_debug(key):
        return
    import traceback
    traceback.print_exc()


def debug_trace_stack(key=None) -> None:
    """Print stack only when debug is enabled."""
    if not get_debug(key):
        return
    import traceback
    traceback.print_stack()
