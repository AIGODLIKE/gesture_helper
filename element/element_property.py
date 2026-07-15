from bpy.props import EnumProperty, BoolProperty, CollectionProperty, IntProperty, StringProperty

from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE, ENUM_GESTURE_DIRECTION
from ..utils.public import get_pref
from ..utils.public_cache import PublicCacheFunc, cache_update_lock


class ElementAddProperty:
    element_type: EnumProperty(
        name='Type',
        default='CHILD_GESTURE',
        items=ENUM_ELEMENT_TYPE,
    )
    selected_type: EnumProperty(
        name='Select structure type',
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
        is_operator = act and act.is_operator
        return not (is_operator and pref.add_element_property.is_child_relationship)

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
    def is_selected_if(self) -> bool:
        return self.selected_type == 'IF'

    @property
    def is_selected_elif(self) -> bool:
        return self.selected_type == 'ELIF'

    @property
    def is_selected_else(self) -> bool:
        return self.selected_type == 'ELSE'


class ElementIcon:
    icon: StringProperty(name='Show icon', default='COLOR_ERROR')
    enabled_icon: BoolProperty(name='Show Icon', default=False)

    @property
    def is_have_icon(self):
        """Return whether icon display is supported (operators and child gestures only)."""
        return self.is_operator or self.is_child_gesture

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
        return self.enabled_icon and self.icon_is_validity

    @property
    def is_draw_icon(self):
        """Return whether to draw the icon."""
        if self.is_draw_context_toggle_operator_bool:  # Draw context-toggle operator icon
            return self.draw_property.element_draw_property_toggle_icon
        return self.is_have_icon and self.is_show_icon

    @property
    def is_draw_child_icon(self):
        """Return whether to draw child gesture badge icon."""
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


class ElementProperty(
    ElementDirectionProperty,
    ElementIcon,
    ElementAddProperty,
    ElementExtension
):
    collection: CollectionProperty
    enabled: BoolProperty(
        name='Enabled',
        default=True,
        update=lambda self, context: self.clear_derived_cache(),
    )

    show_child: BoolProperty(name='Show Children', default=False)
    level: IntProperty(name="Element Level", default=0)
