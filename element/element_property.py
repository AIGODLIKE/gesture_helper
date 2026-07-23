from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from ..utils.enum import (
    ENUM_ELEMENT_TYPE,
    ENUM_GESTURE_DIRECTION,
    ENUM_NUMBER_VALUE_CHANGE_MODE,
    ENUM_SELECTED_TYPE,
    LAYOUT_CONTAINER_TYPES,
)
from ..utils.public import get_pref
from ..utils.public_cache import PublicCacheFunc, cache_update_lock


class ElementAddProperty:
    element_type: EnumProperty(
        name='Type',
        default='CHILD_GESTURE',
        items=ENUM_ELEMENT_TYPE,
    )
    selected_type: EnumProperty(
        name='Structure type',
        items=ENUM_SELECTED_TYPE,
        update=lambda self, context: ElementAddProperty.update_selected_type()
    )

    @property
    def is_have_add_child(self) -> bool:
        """Return whether child items can be added
        @return: bool
        """
        pref = get_pref()
        act = pref.active_element
        is_leaf = act and (act.is_operator or act.is_property_display)
        return not (is_leaf and pref.add_element_property.is_child_relationship)

    @staticmethod
    @cache_update_lock
    def update_selected_type():
        PublicCacheFunc.clear_derived_only()

    @property
    def is_selected_structure(self) -> bool:
        return self.element_type == 'SELECTED_STRUCTURE'

    @property
    def is_child_gesture(self) -> bool:
        return self.element_type == 'CHILD_GESTURE'

    @property
    def is_operator(self) -> bool:
        return self.element_type == 'OPERATOR'

    @property
    def is_dividing_line(self) -> bool:
        return self.element_type == 'DIVIDING_LINE'

    @property
    def is_property_display(self) -> bool:
        return self.element_type == 'PROPERTY'

    @property
    def is_layout_container(self) -> bool:
        return self.element_type in LAYOUT_CONTAINER_TYPES

    @property
    def is_row(self) -> bool:
        return self.element_type == 'ROW'

    @property
    def is_column(self) -> bool:
        return self.element_type == 'COLUMN'

    @property
    def is_box(self) -> bool:
        return self.element_type == 'BOX'

    @property
    def is_selected_if(self) -> bool:
        return self.selected_type == 'IF'

    @property
    def is_selected_elif(self) -> bool:
        return self.selected_type == 'ELIF'

    @property
    def is_selected_else(self) -> bool:
        return self.selected_type == 'ELSE'


class ElementIcon:
    icon: StringProperty(name='Icon', default='COLOR_ERROR')
    enabled_icon: BoolProperty(name='Show Icon', default=False)

    @property
    def is_have_icon(self):
        """Return whether this element can currently display an icon."""
        return (
            self.is_operator
            or self.is_child_gesture
            or (self.is_property_display and self.display_property_type == 'BOOLEAN')
        )

    @property
    def all_icons(self) -> list[str]:
        from ..utils.icons import get_all_icons
        return get_all_icons()

    @property
    def icon_is_validity(self) -> bool:
        """Return whether the icon identifier is valid."""
        from ..utils.icons import check_icon
        return check_icon(self.icon)

    @property
    def is_show_icon(self) -> bool:
        """Return whether icon should be shown."""
        if self.is_property_display:
            return bool(self.property_state_icon)
        return self.enabled_icon and self.icon_is_validity

    @property
    def is_draw_icon(self):
        """Return whether to draw the icon."""
        if self.is_draw_context_toggle_operator_bool:  # Draw context-toggle operator icon
            return self.draw_property.element_draw_property_toggle_icon
        return self.is_have_icon and self.is_show_icon

    @property
    def is_draw_child_icon(self):
        """Return whether to draw the child/panel chevron badge icon."""
        return get_pref().draw_property.element_draw_child_icon and self.is_child_gesture


# Display properties using custom parameters, not Blender defaults
class ElementDirectionProperty:
    direction: EnumProperty(
        name='Direction',
        items=ENUM_GESTURE_DIRECTION,
        default='8'
    )

    def __init_child_gesture__(self):
        self.__init_direction_by_sort__()
        self.selected_type = 'IF'


class ElementExtension:
    @property
    def parent_is_extension(self) -> bool:  # Parent is extension item (bottom menu)
        pe = self.parent_element
        if pe:
            if pe.parent_is_extension:
                return True
            if pe.direction == "9":
                return True
        return False

    def _ops_mouse_xy(self, ops=None):
        from .extension_hit import _mouse_for
        return _mouse_for(self, ops or getattr(self, "ops", None))

    def _extension_hit_flags(self) -> int:
        from .extension_hit import hit_test_extension
        return hit_test_extension(self)

    @property
    def extension_by_child_is_hover(self) -> bool:
        """Return whether extension child is hovered."""
        from .extension_hit import hit_test_child_row
        return hit_test_child_row(self)

    @property
    def mouse_is_in_area(self) -> bool:
        from .extension_hit import point_in_rect
        return point_in_rect(self._ops_mouse_xy(), getattr(self, "item_draw_area", None))

    @property
    def mouse_is_in_extension_area(self) -> bool:
        """Return whether mouse is inside extension panel draw area."""
        from .extension_hit import PANEL
        return bool(self._extension_hit_flags() & PANEL)

    @property
    def mouse_is_in_extension_vertical_outside_area(self) -> bool:
        """Return whether mouse is in vertical travel tolerance outside the panel."""
        from .extension_hit import VERTICAL_TRAVEL
        return bool(self._extension_hit_flags() & VERTICAL_TRAVEL)

    @property
    def mouse_is_in_extension_vertical_area(self) -> bool:
        """Return whether mouse is in extension vertical band."""
        from .extension_hit import VERTICAL_BAND
        return bool(self._extension_hit_flags() & VERTICAL_BAND)

    @property
    def mouse_is_in_extension_right_outside_area(self) -> bool:
        """Return whether mouse is in the right tolerance band (or next flyout)."""
        from .extension_hit import RIGHT_BAND
        return bool(self._extension_hit_flags() & RIGHT_BAND)


class ElementLayoutProperty:
    """Layout containers (row/column/box) and interactive property rows."""

    DEFAULT_PROPERTY_PATH = 'scene.cycles.samples'
    FALLBACK_PROPERTY_PATH = 'scene.render.resolution_percentage'

    main_item: BoolProperty(
        name='Main Action',
        description='Run this item when the parent layout is confirmed without opening it',
        default=False,
        update=lambda self, context: self.update_main_item(),
    )
    layout_alignment: EnumProperty(
        name='Alignment',
        description='Align items inside this layout',
        items=(
            ('EXPAND', 'Expand', 'Expand items to fill the available space'),
            ('LEFT', 'Left', 'Align items to the left'),
            ('CENTER', 'Center', 'Center items'),
            ('RIGHT', 'Right', 'Align items to the right'),
        ),
        default='EXPAND',
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_scale: FloatProperty(
        name='Scale',
        description='Scale this layout and its contents',
        default=1.0,
        min=0.25,
        max=4.0,
        soft_min=0.5,
        soft_max=2.0,
        step=10,
        precision=2,
        update=lambda self, context: self.clear_derived_cache(),
    )
    show_layout_advanced: BoolProperty(
        name='Advanced',
        description='Show advanced layout settings',
        default=False,
        options={'SKIP_SAVE'},
    )
    property_data_path: StringProperty(
        name='Property Data Path',
        description='Context data path of the property to show (e.g. object.show_wire)',
        default=DEFAULT_PROPERTY_PATH,
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_drag_mode: EnumProperty(
        name='Drag Direction',
        description='Mouse direction used to adjust numeric values',
        items=ENUM_NUMBER_VALUE_CHANGE_MODE[1:],
        default='MOUSE_CHANGES_HORIZONTAL',
    )
    property_drag_invert: BoolProperty(
        name='Invert',
        description='Reverse the direction used to adjust numeric values',
        default=False,
    )
    property_show_value: BoolProperty(
        name='Show Value',
        description='Include the current property value in the gesture label',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_value_format: StringProperty(
        name='Value Format',
        description='Label template; available fields are {name} and {value}',
        default='{name}: {value}',
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_value_precision: IntProperty(
        name='Precision',
        description='Number of decimal places used for floating-point values',
        default=2,
        min=0,
        max=8,
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_true_text: StringProperty(
        name='On Text',
        description='Text shown when a boolean property is enabled',
        default='On',
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_false_text: StringProperty(
        name='Off Text',
        description='Text shown when a boolean property is disabled',
        default='Off',
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_bool_icons_enabled: BoolProperty(
        name='State Icons',
        description='Show a different icon for each boolean state',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_true_icon: StringProperty(
        name='On Icon',
        description='Icon shown when a boolean property is enabled',
        default='TICK',
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_false_icon: StringProperty(
        name='Off Icon',
        description='Icon shown when a boolean property is disabled',
        default='COLOR_CLOSE',
        update=lambda self, context: self.clear_derived_cache(),
    )
    show_property_advanced: BoolProperty(
        name='Advanced',
        description='Show property display and interaction settings',
        default=False,
        options={'SKIP_SAVE'},
    )
    overlay_offset: FloatVectorProperty(
        name='Draw Offset',
        description='Additional horizontal and vertical drawing offset in UI pixels',
        size=2,
        default=(0.0, 0.0),
        soft_min=-500.0,
        soft_max=500.0,
        step=10,
        precision=1,
        update=lambda self, context: self.clear_derived_cache(),
    )

    @property
    def parent_is_layout(self) -> bool:
        """True when any ancestor is a row/column/box container."""
        pe = self.parent_element
        while pe is not None:
            if pe.is_layout_container:
                return True
            pe = pe.parent_element
        return False

    @property
    def main_action_layout(self):
        """Outermost layout containing this item without crossing a flyout."""
        layout = None
        parent = self.parent_element
        while parent is not None:
            if parent.is_child_gesture:
                break
            if parent.is_layout_container:
                layout = parent
            parent = parent.parent_element
        return layout

    def update_main_item(self) -> None:
        """Keep the explicit main action exclusive within one layout panel."""
        if self.main_item:
            layout = self.main_action_layout
            if layout is not None:
                for item in layout.panel_leaf_items:
                    if item != self and item.main_item:
                        item.main_item = False
        self.clear_derived_cache()

    @property
    def property_context_path(self) -> str:
        """Data path relative to ``bpy.context`` (prefix stripped)."""
        path = self.property_data_path.strip()
        if path.startswith('bpy.context.'):
            return path[len('bpy.context.'):]
        if path.startswith('context.'):
            return path[len('context.'):]
        return path

    def initialize_property_display(self) -> None:
        """Initialize a generic property element with a useful Blender value."""
        self.property_data_path = self.DEFAULT_PROPERTY_PATH
        if self.resolve_property() is None:
            self.property_data_path = self.FALLBACK_PROPERTY_PATH
        self.sync_name_from_source()

    @property
    def source_name(self) -> str:
        """Name supplied by the configured operator or RNA property."""
        if self.is_property_display:
            resolved = self.resolve_property()
            if resolved is None:
                return ''
            from bpy.app.translations import pgettext_n
            rna_prop = resolved[1]
            return pgettext_n(rna_prop.name, rna_prop.translation_context)
        if self.is_operator:
            return self.__operator_original_name__ or ''
        return ''

    @property
    def can_sync_name(self) -> bool:
        return bool(self.source_name)

    def sync_name_from_source(self) -> bool:
        name = self.source_name
        if not name:
            return False
        self.name = name
        return True

    def resolve_property(self):
        """Return ``(owner, rna_property)`` for the data path, or None."""
        import bpy
        path = self.property_context_path
        if not path or '.' not in path:
            return None
        owner_path, prop_id = path.rsplit('.', 1)
        try:
            owner = bpy.context.path_resolve(owner_path)
        except (ValueError, AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        if owner is None:
            return None
        rna = getattr(owner, 'bl_rna', None)
        rna_prop = rna.properties.get(prop_id) if rna is not None else None
        if rna_prop is None:
            return None
        return owner, rna_prop

    @property
    def __property_path_is_validity__(self) -> bool:
        return self.resolve_property() is not None

    @property
    def display_property_type(self) -> str | None:
        """'BOOLEAN' / 'INT' / 'FLOAT' / 'ENUM' / 'STRING', or None."""
        resolved = self.resolve_property()
        if resolved is None:
            return None
        return resolved[1].type

    @property
    def display_property_value(self):
        resolved = self.resolve_property()
        if resolved is None:
            return None
        owner, rna_prop = resolved
        try:
            return getattr(owner, rna_prop.identifier)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None

    @property
    def display_property_is_editable(self) -> bool:
        """Whether this RNA value can be changed by the gesture controls."""
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        if rna_prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'ENUM'}:
            return False
        if getattr(rna_prop, 'is_array', False):
            return False
        if rna_prop.type == 'ENUM' and getattr(rna_prop, 'is_enum_flag', False):
            return False
        if getattr(rna_prop, 'is_readonly', False):
            return False
        try:
            return not owner.is_property_readonly(rna_prop.identifier)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return True

    def set_display_property_value(self, value) -> bool:
        if not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        try:
            setattr(owner, rna_prop.identifier, value)
            return True
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            return False

    @property
    def display_property_text(self) -> str:
        """Formatted live-value label used by GPU draw."""
        name = self.name_translate
        if not self.property_show_value:
            return name
        value = self.display_property_value
        if value is None:
            value_text = '?'
            return self._format_property_label(name, value_text)
        prop_type = self.display_property_type
        resolved = self.resolve_property()
        if resolved is not None and getattr(resolved[1], 'is_array', False):
            try:
                if prop_type == 'FLOAT':
                    precision = self.property_value_precision
                    text = ', '.join(f'{float(item):.{precision}f}' for item in value)
                else:
                    text = ', '.join(str(item) for item in value)
                return self._format_property_label(name, f'[{text}]')
            except (TypeError, ValueError):
                return self._format_property_label(name, str(value))
        if prop_type == 'FLOAT':
            value_text = f'{value:.{self.property_value_precision}f}'
            return self._format_property_label(name, value_text)
        if prop_type == 'BOOLEAN':
            from bpy.app.translations import pgettext_iface
            state_text = self.property_true_text if value else self.property_false_text
            return self._format_property_label(name, pgettext_iface(state_text))
        if prop_type == 'ENUM':
            if resolved is not None:
                from bpy.app.translations import pgettext_iface
                rna_prop = resolved[1]
                if getattr(rna_prop, 'is_enum_flag', False):
                    try:
                        labels = [
                            pgettext_iface(rna_prop.enum_items[key].name)
                            for key in sorted(value)
                            if rna_prop.enum_items.get(key) is not None
                        ]
                        return self._format_property_label(name, ', '.join(labels))
                    except (KeyError, TypeError):
                        return self._format_property_label(name, str(value))
                item = rna_prop.enum_items.get(value)
                if item is not None:
                    return self._format_property_label(name, pgettext_iface(item.name))
        return self._format_property_label(name, str(value))

    def _format_property_label(self, name: str, value: str) -> str:
        template = self.property_value_format or '{name}: {value}'
        try:
            return template.format(name=name, value=value)
        except (IndexError, KeyError, ValueError):
            return f'{name}: {value}'

    @property
    def property_state_icon(self) -> str:
        """Configured icon for the current boolean state, or an empty string."""
        if not self.property_bool_icons_enabled or self.display_property_type != 'BOOLEAN':
            return ''
        icon = self.property_true_icon if self.display_property_value else self.property_false_icon
        from ..utils.icons import check_icon
        return icon if check_icon(icon) else ''

    def property_drag_delta(self, start_mouse, mouse) -> float:
        """Convert two mouse positions to the configured signed drag distance."""
        delta_x = mouse.x - start_mouse.x
        delta_y = mouse.y - start_mouse.y
        if self.property_drag_mode == 'MOUSE_CHANGES_VERTICAL':
            delta = delta_y
        elif self.property_drag_mode == 'MOUSE_CHANGES_ARBITRARY':
            delta = delta_x if abs(delta_x) >= abs(delta_y) else delta_y
        else:
            delta = delta_x
        return -delta if self.property_drag_invert else delta

    @property
    def display_property_fraction(self) -> float | None:
        """Value position inside the soft range (slider fill), or None."""
        resolved = self.resolve_property()
        if resolved is None:
            return None
        owner, rna_prop = resolved
        if rna_prop.type not in {'INT', 'FLOAT'} or getattr(rna_prop, 'is_array', False):
            return None
        try:
            value = getattr(owner, rna_prop.identifier)
            soft_min = rna_prop.soft_min
            soft_max = rna_prop.soft_max
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        span = soft_max - soft_min
        if not span or span <= 0 or span > 1e9:
            return None
        return min(1.0, max(0.0, (value - soft_min) / span))

    def apply_property_drag(self, start_value, delta_px: float, *, precise: bool = False) -> None:
        """Set value from a horizontal drag distance in pixels."""
        if not self.display_property_is_editable:
            return
        resolved = self.resolve_property()
        if resolved is None:
            return
        owner, rna_prop = resolved
        if rna_prop.type not in {'INT', 'FLOAT'} or getattr(rna_prop, 'is_array', False):
            return
        soft_min = rna_prop.soft_min
        soft_max = rna_prop.soft_max
        span = soft_max - soft_min
        if not span or span <= 0 or span > 1e9:
            # Unbounded property: 1px == step (fallback 1 int / 0.01 float).
            if rna_prop.type == 'INT':
                per_px = max(1, int(getattr(rna_prop, 'step', 1))) * 0.1
            else:
                per_px = max(getattr(rna_prop, 'step', 3) / 100.0, 0.001) * 0.5
        else:
            per_px = span / 200.0  # full soft range over ~200px
        if precise:
            per_px *= 0.1
        value = start_value + delta_px * per_px
        value = min(max(value, rna_prop.hard_min), rna_prop.hard_max)
        if rna_prop.type == 'INT':
            value = int(round(value))
        try:
            setattr(owner, rna_prop.identifier, value)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            ...

    def toggle_display_property(self) -> bool:
        """Cycle the value in place (bool toggle / enum cycle). Returns success."""
        if not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        if rna_prop.type == 'BOOLEAN' and not getattr(rna_prop, 'is_array', False):
            return self.set_display_property_value(not getattr(owner, rna_prop.identifier))
        if rna_prop.type == 'ENUM' and not getattr(rna_prop, 'is_enum_flag', False):
            identifiers = [item.identifier for item in rna_prop.enum_items]
            if not identifiers:
                return False
            current = getattr(owner, rna_prop.identifier)
            try:
                index = identifiers.index(current)
            except ValueError:
                index = -1
            return self.set_display_property_value(identifiers[(index + 1) % len(identifiers)])
        return False

    @property
    def main_element(self):
        """Runnable main leaf: first main-flagged operator/property, else first one.

        Child gestures cannot be a main action — they only open deeper levels.
        """
        if not self.is_layout_container:
            return None
        fallback = None
        for item in self.panel_leaf_items:
            if not (item.is_operator or item.is_property_display):
                continue
            if item.main_item:
                return item
            if fallback is None:
                fallback = item
        return fallback

    @property
    def panel_leaf_items(self) -> list:
        """Interactive leaves of this element's panel, flattened through containers."""
        from ..utils.gesture_items import iter_panel_leaves
        leaves = iter_panel_leaves(self.extension_items)
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if session is None:
            return list(leaves)
        # Stable proxies — hit boxes stamped by the panel draw must be visible.
        return [session.canonical_element(item) for item in leaves]


class ElementProperty(
    ElementDirectionProperty,
    ElementIcon,
    ElementAddProperty,
    ElementExtension,
    ElementLayoutProperty,
):
    collection: CollectionProperty
    enabled: BoolProperty(
        name='Enabled',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )

    show_child: BoolProperty(name='Show Children', default=False)
    level: IntProperty(name="Element Level", default=0)
