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
from ..utils.public_cache import PublicCache, PublicCacheFunc, cache_update_lock
from ..utils.number_arrows import number_drag_value, number_step_value
from ..utils.translate import translate_rna_text


_UI_PANEL_LEAF_ITEMS_CACHE = None


def _update_show_child(_self, _context) -> None:
    try:
        from ..ui.ui_list import clear_element_tree_cache

        clear_element_tree_cache()
    except (AttributeError, ImportError, RuntimeError):
        pass


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
        is_leaf = act and (
            act.is_operator or act.is_property_display or act.is_label
        )
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
    def is_label(self) -> bool:
        return self.element_type == 'LABEL'

    @property
    def is_split(self) -> bool:
        return self.element_type == 'SPLIT'

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
            or self.is_label
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
    """Layout containers/items and interactive property rows."""

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
            ('TEXT_LEFT', 'Text Left', 'Keep item placement but align text to the left'),
            ('TEXT_CENTER', 'Text Center', 'Keep item placement but center the text'),
            ('TEXT_RIGHT', 'Text Right', 'Keep item placement but align text to the right'),
        ),
        default='EXPAND',
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_align: BoolProperty(
        name='Align',
        description='Remove spacing between adjacent layout items like Blender align=True',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_round_corners: BoolProperty(
        name='Round Corners',
        description='Round the layout and its child surfaces',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_align_separators: BoolProperty(
        name='Align Divider Corners',
        description='Keep items separated by dividers in the same rounded corner group',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )
    split_factor: FloatProperty(
        name='Factor',
        description=(
            'Percentage of width assigned to the first split item; '
            'zero calculates equal widths automatically'
        ),
        default=0.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_scale: FloatProperty(
        name='Legacy Scale',
        description='Legacy uniform layout scale used by older presets',
        default=1.0,
        min=0.25,
        max=4.0,
        soft_min=0.5,
        soft_max=2.0,
        step=10,
        precision=2,
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_scale_x: FloatProperty(
        name='Scale X',
        description='Horizontal layout scale',
        default=1.0,
        min=0.25,
        max=4.0,
        soft_min=0.5,
        soft_max=2.0,
        step=10,
        precision=2,
        update=lambda self, context: self.clear_derived_cache(),
    )
    layout_scale_y: FloatProperty(
        name='Scale Y',
        description='Vertical layout scale',
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
    property_wheel_step: FloatProperty(
        name='Wheel Step',
        description='Value changed by one mouse-wheel notch on numeric properties',
        default=1.0,
        min=0.000001,
        max=1000000.0,
        soft_min=0.01,
        soft_max=100.0,
        step=1,
        precision=4,
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
        default='CHECKBOX_HLT',
        update=lambda self, context: self.clear_derived_cache(),
    )
    property_false_icon: StringProperty(
        name='Off Icon',
        description='Icon shown when a boolean property is disabled',
        default='CHECKBOX_DEHLT',
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
        """True when any ancestor is a layout container."""
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
    def source_description(self) -> str:
        """Translated native RNA description for an operator or property."""
        source = None
        if self.is_operator:
            func = self.operator_func
            if func is not None:
                try:
                    source = func.get_rna_type()
                except (AttributeError, ReferenceError, RuntimeError, TypeError):
                    source = None
        elif self.is_property_display:
            resolved = self.resolve_property()
            if resolved is not None:
                source = resolved[1]
        if source is None:
            return ''

        description = getattr(source, 'description', '') or ''
        if not description:
            return ''
        context = (
            getattr(source, 'translation_context', None)
            if self.is_property_display
            else None
        )
        return translate_rna_text(description, context, tooltip=True)

    @property
    def source_name_translate(self) -> str:
        """Translated native operator/property name for runtime tooltips."""
        source = None
        if self.is_operator:
            func = self.operator_func
            if func is not None:
                try:
                    source = func.get_rna_type()
                except (AttributeError, ReferenceError, RuntimeError, TypeError):
                    source = None
        elif self.is_property_display:
            resolved = self.resolve_property()
            if resolved is not None:
                source = resolved[1]
        if source is None:
            return ''
        context = (
            getattr(source, 'translation_context', None)
            if self.is_property_display
            else None
        )
        return translate_rna_text(
            getattr(source, 'name', '') or '',
            context,
            tooltip=False,
        )

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

    def capture_selected_property_values(self):
        """Snapshot matching values on other selected objects for Alt editing."""
        import bpy

        resolved = self.resolve_property()
        if resolved is None:
            return []
        from ..utils.selected_property import capture_selected_object_values

        owner, rna_prop = resolved
        return capture_selected_object_values(
            bpy.context,
            self.property_context_path,
            owner,
            rna_prop,
        )

    @staticmethod
    def restore_selected_property_values(snapshots) -> bool:
        from ..utils.selected_property import restore_snapshot_values

        return restore_snapshot_values(snapshots)

    def set_display_property_value(
            self,
            value,
            *,
            copy_to_selected: bool = False,
            selected_targets=None,
    ) -> bool:
        if not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        if copy_to_selected and selected_targets is None:
            selected_targets = self.capture_selected_property_values()
        changed = False
        try:
            current = getattr(owner, rna_prop.identifier)
            if current != value:
                setattr(owner, rna_prop.identifier, value)
                changed = getattr(owner, rna_prop.identifier) != current
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            pass
        if selected_targets is not None:
            from ..utils.selected_property import set_snapshot_values

            changed = set_snapshot_values(selected_targets, value) or changed
        return changed

    def reset_display_property_to_default(
            self, *, copy_to_selected: bool = False, selected_targets=None,
    ) -> bool:
        """Restore a writable scalar number or boolean to its RNA default."""
        if not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        _owner, rna_prop = resolved
        if (
                rna_prop.type not in {'BOOLEAN', 'INT', 'FLOAT'}
                or getattr(rna_prop, 'is_array', False)
        ):
            return False
        try:
            default = rna_prop.default
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            return False
        return self.set_display_property_value(
            default,
            copy_to_selected=copy_to_selected,
            selected_targets=selected_targets,
        )

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
                rna_prop = resolved[1]
                if getattr(rna_prop, 'is_enum_flag', False):
                    try:
                        labels = [
                            translate_rna_text(
                                rna_prop.enum_items[key].name,
                                rna_prop.translation_context,
                            )
                            for key in sorted(value)
                            if rna_prop.enum_items.get(key) is not None
                        ]
                        return self._format_property_label(name, ', '.join(labels))
                    except (KeyError, TypeError):
                        return self._format_property_label(name, str(value))
                item = rna_prop.enum_items.get(value)
                if item is not None:
                    return self._format_property_label(
                        name,
                        translate_rna_text(item.name, rna_prop.translation_context),
                    )
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

    def rebase_property_drag_start(
            self, start_mouse, mouse, applied_delta: float,
    ) -> None:
        """Discard limit overshoot like Blender updates ``dragstartx``."""
        raw_delta = -applied_delta if self.property_drag_invert else applied_delta
        mode = self.property_drag_mode
        if mode == 'MOUSE_CHANGES_VERTICAL':
            start_mouse.y = mouse.y - raw_delta
        elif mode == 'MOUSE_CHANGES_ARBITRARY':
            delta_x = mouse.x - start_mouse.x
            delta_y = mouse.y - start_mouse.y
            if abs(delta_x) >= abs(delta_y):
                start_mouse.x = mouse.x - raw_delta
            else:
                start_mouse.y = mouse.y - raw_delta
        else:
            start_mouse.x = mouse.x - raw_delta

    def apply_property_wheel(
            self,
            direction: int,
            *,
            precise: bool = False,
            copy_to_selected: bool = False,
    ) -> bool:
        """Apply one wheel notch to the displayed scalar numeric property."""
        if direction == 0 or not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        if rna_prop.type not in {'INT', 'FLOAT'} or getattr(rna_prop, 'is_array', False):
            return False

        try:
            current = getattr(owner, rna_prop.identifier)
            sign = 1 if direction > 0 else -1
            if self.property_drag_invert:
                sign = -sign
            value = number_step_value(
                current,
                sign,
                property_type=rna_prop.type,
                configured_step=getattr(self, 'property_wheel_step', 1.0),
                hard_min=getattr(rna_prop, 'hard_min', None),
                hard_max=getattr(rna_prop, 'hard_max', None),
                soft_min=getattr(rna_prop, 'soft_min', None),
                soft_max=getattr(rna_prop, 'soft_max', None),
                precise=precise,
            )
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            return False
        return self.set_display_property_value(
            value,
            copy_to_selected=copy_to_selected,
        )

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

    def apply_property_drag(
            self,
            start_value,
            delta_px: float,
            *,
            precise: bool = False,
            return_applied_delta: bool = False,
            selected_targets=None,
    ) -> bool | tuple[bool, float]:
        """Set a scrubbed value and report whether the RNA value changed."""
        def result(changed: bool, applied_delta=delta_px):
            if return_applied_delta:
                return changed, applied_delta
            return changed

        if not self.display_property_is_editable:
            return result(False)
        resolved = self.resolve_property()
        if resolved is None:
            return result(False)
        owner, rna_prop = resolved
        if rna_prop.type not in {'INT', 'FLOAT'} or getattr(rna_prop, 'is_array', False):
            return result(False)
        value, applied_delta = number_drag_value(
            start_value,
            delta_px,
            property_type=rna_prop.type,
            rna_step=getattr(rna_prop, 'step', 1.0),
            hard_min=getattr(rna_prop, 'hard_min', None),
            hard_max=getattr(rna_prop, 'hard_max', None),
            soft_min=getattr(rna_prop, 'soft_min', None),
            soft_max=getattr(rna_prop, 'soft_max', None),
            precise=precise,
            return_applied_delta=True,
        )
        try:
            changed = self.set_display_property_value(
                value,
                selected_targets=selected_targets,
            )
            return result(changed, applied_delta)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            return result(False)

    def toggle_display_property(self, *, copy_to_selected: bool = False) -> bool:
        """Cycle the value in place (bool toggle / enum cycle). Returns success."""
        if not self.display_property_is_editable:
            return False
        resolved = self.resolve_property()
        if resolved is None:
            return False
        owner, rna_prop = resolved
        if rna_prop.type == 'BOOLEAN' and not getattr(rna_prop, 'is_array', False):
            return self.set_display_property_value(
                not getattr(owner, rna_prop.identifier),
                copy_to_selected=copy_to_selected,
            )
        if rna_prop.type == 'ENUM' and not getattr(rna_prop, 'is_enum_flag', False):
            identifiers = [item.identifier for item in rna_prop.enum_items]
            if not identifiers:
                return False
            current = getattr(owner, rna_prop.identifier)
            try:
                index = identifiers.index(current)
            except ValueError:
                index = -1
            return self.set_display_property_value(
                identifiers[(index + 1) % len(identifiers)],
                copy_to_selected=copy_to_selected,
            )
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
        from ..utils.gesture_items import iter_panel_leaves, poll_context_fingerprint
        try:
            ops = getattr(self, 'ops', None)
            session = getattr(ops, 'session', None)
        except ReferenceError:
            self.ops = None
            session = None
        if session is None:
            global _UI_PANEL_LEAF_ITEMS_CACHE
            try:
                poll_key = poll_context_fingerprint()
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                poll_key = ()
            key = (
                PublicCache.__structure_generation__,
                PublicCache.__derived_generation__,
                poll_key,
            )
            packed = _UI_PANEL_LEAF_ITEMS_CACHE
            if packed is None or packed[0] != key:
                values = {}
                _UI_PANEL_LEAF_ITEMS_CACHE = (key, values)
            else:
                values = packed[1]
            try:
                element_key = int(self.as_pointer())
            except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
                element_key = id(self)
            cached = values.get(element_key)
            if cached is not None:
                return cached
            result = list(iter_panel_leaves(self.extension_items))
            values[element_key] = result
            return result

        key = (
            PublicCache.__derived_generation__,
            getattr(session, '_poll_context_fingerprint', None),
            getattr(session, '_poll_context_revision', 0),
        )
        packed = getattr(session, '_gpu_panel_leaf_items_cache', None)
        if packed is None or packed[0] != key:
            values = {}
            session._gpu_panel_leaf_items_cache = (key, values)
        else:
            values = packed[1]
        cached = values.get(self)
        if cached is not None:
            return cached
        # Stable proxies: hit boxes stamped by the panel draw must be visible.
        result = [
            session.canonical_element(item)
            for item in iter_panel_leaves(self.extension_items)
        ]
        values[self] = result
        return result


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

    show_child: BoolProperty(
        name='Show Children',
        default=False,
        update=_update_show_child,
    )
    level: IntProperty(name="Element Level", default=0)
