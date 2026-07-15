"""
version 0.0.2
Handle API differences across Blender versions.
"""
import bpy

_MISSING = object()


def operator_setattr(op, name: str, value) -> None:
    """Set a non-RNA attribute on an Operator instance (Blender 4.x / 5.x).

    On Blender 4.x, ``object.__setattr__`` raises
    ``TypeError: can't apply this __setattr__`` for bpy_struct wrappers.
    On Blender 5.x, RNA ``__setattr__`` may reject unknown names, so try
    ``object.__setattr__`` first when the instance allows it.
    """
    try:
        object.__setattr__(op, name, value)
    except TypeError:
        setattr(op, name, value)


def operator_getattr(op, name: str, default=_MISSING):
    """Read a non-RNA attribute from an Operator instance."""
    try:
        return getattr(op, name)
    except AttributeError:
        if default is _MISSING:
            raise
        return default


def operator_invoke_confirm(self, event, context, title, message) -> set:
    """Blender 4.1+ requires extra args; new UI shows two buttons."""
    if bpy.app.version >= (4, 1, 0):
        return context.window_manager.invoke_confirm(
            **{
                "operator": self,
                "event": event,
                'title': title,
                'message': message,
            }
        )
    else:
        return context.window_manager.invoke_confirm(
            self, event
        )
