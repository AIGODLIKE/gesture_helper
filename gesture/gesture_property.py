"""Gesture PropertyGroup data mixin (configuration only — no modal runtime)."""

from bpy.props import IntProperty, BoolProperty

from ..utils.public import PublicProperty
from ..utils.public_cache import cache_update_lock


class GestureProperty(PublicProperty):
    """Persisted gesture fields used by the Gesture PropertyGroup."""

    timer = None

    @cache_update_lock
    def copy(self) -> None:
        """Copy this gesture."""
        from ..utils.property import get_property, __set_prop__
        from ..utils.selection import strip_radio_from_copy_data

        copy_data = strip_radio_from_copy_data(get_property(self))
        from ..utils.gesture_store import get_gesture_store
        store = get_gesture_store()
        if store is not None:
            __set_prop__(store, 'gesture', {'0': copy_data})

    def update_index(self, _) -> None:
        """Update element index selection."""
        from ..utils.selection import is_syncing_selection_indexes

        if is_syncing_selection_indexes():
            return
        try:
            el = self.element.values()[self.index_element]
            if el and not el.radio:
                el.radio = True
        except IndexError:
            ...

    index_element: IntProperty(name='Index', update=update_index, options={"HIDDEN"})

    enabled: BoolProperty(
        default=True,
        update=lambda self, context: self.key_update(),
        options={"HIDDEN"}
    )

    @property
    def is_active(self) -> bool:
        """Return whether this gesture is active."""
        return self.pref.active_gesture == self
