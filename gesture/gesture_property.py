"""Gesture PropertyGroup data mixin (configuration only — no modal runtime)."""

from bpy.props import BoolProperty, EnumProperty, IntProperty

from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.structure_cache_ops import StructureCacheOps
from ..utils.public_cache import cache_update_lock


GESTURE_TYPE_ITEMS = (
    ('RADIAL', 'Gesture', 'Draw directions to choose an action', 'MOUSE_MOVE', 0),
    ('MENU', 'Menu', 'Open a persistent menu at the mouse position', 'MENU_PANEL', 1),
)

MENU_STYLE_ITEMS = (
    ('PANEL', 'Panel', 'Framed Blender-style menu with a title bar', 'WINDOW', 0),
    ('COMPACT', 'Compact', 'Tighter menu rows and spacing', 'ALIGN_JUSTIFY', 1),
    ('BORDERLESS', 'Borderless', 'Minimal menu surface without an outer outline', 'SELECT_SET', 2),
)


def _update_gesture_type(self, _context) -> None:
    """Persist the new type and rebuild its shortcut with the matching operator."""
    self.key_update()
    self.structure_changed(self)


def _update_menu_style(self, _context) -> None:
    self.structure_changed(self)
    try:
        from .menu import GestureMenuRuntime

        GestureMenuRuntime.redraw_gesture(self)
    except (ImportError, ReferenceError, RuntimeError):
        ...


class GestureProperty(PrefAccess, ActiveSelection, StructureCacheOps):
    """Persisted gesture fields used by the Gesture PropertyGroup."""

    timer = None

    gesture_type: EnumProperty(
        name='Type',
        description='Runtime presentation chosen when this item is created',
        items=GESTURE_TYPE_ITEMS,
        default='RADIAL',
        update=_update_gesture_type,
    )
    menu_style: EnumProperty(
        name='Menu Style',
        description='Visual density used by persistent menu gestures',
        items=MENU_STYLE_ITEMS,
        default='PANEL',
        update=_update_menu_style,
    )

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
