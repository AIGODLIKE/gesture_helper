from bpy.app.translations import pgettext
from mathutils import Vector

from .bpu_color import BpuColor
from .bpu_type import BPUType, Quadrant


class BpuProperty(BpuColor):
    type: BPUType = BPUType.UNKNOWN  # Node type
    parent: "BpuLayout" = None  # Parent layout

    __quadrant__: Quadrant = Quadrant.ONE

    __show_separator_line__: bool  # Draw separator line
    __menu_id__: str  # Menu id

    level: int = 0  # Draw nesting level

    offset_position: Vector  # Layout offset
    mouse_position: Vector  # Mouse position

    text: str = None  # Label/operator text
    font_id: int = 0  # Font id
    font_color = (1, 1, 1, 1)  # Font color
    font_size = 50  # Font size

    text_margin = 8  # Text margin
    layout_margin = 20  # Layout margin
    # Shared menu hover map (legacy); cleared on each parent __gpu_draw__.
    __menu_haver__ = {}

    active = False  # Active item
    alert = False  # Alert styling

    # Property metadata
    __property_data__ = None
    __property_rna__ = None
    __property_value__ = None
    __property_name_string__ = None
    __property_identifier__ = None
    __property_type__ = None
    # https://docs.blender.org/api/master/bpy_types_enum_items/property_type_items.html#rna-enum-property-type-items
    only_icon = False
    icon = None
    translate = True

    @property
    def ___last_haver___(self) -> "BpuLayout":
        if self.parent_top.__layout_haver_histories__:
            last = self.parent_top.__layout_haver_histories__[0]
            return last
        return None

    @property
    def __active_operator__(self) -> "BpuLayout":
        lh = self.___last_haver___
        if lh and lh.type.is_operator:
            return lh
        return None

    @property
    def __active_property__(self) -> "BpuLayout":
        lh = self.___last_haver___
        if lh and lh.type.is_prop:
            return lh
        return None

    @property
    def __quadrant_translate__(self) -> Vector:
        """Quadrant offset."""
        w, h = self.__draw_size__
        if self.__quadrant__ == Quadrant.ONE:
            return Vector([0, 0])
        elif self.__quadrant__ == Quadrant.TWO:
            return Vector([-w, 0])
        elif self.__quadrant__ == Quadrant.THREE:
            return Vector([-w, -h])
        elif self.__quadrant__ == Quadrant.FOUR:
            return Vector([0, -h])

        elif self.__quadrant__ == Quadrant.LIFT:
            return Vector([-w, -h / 2])
        elif self.__quadrant__ == Quadrant.RIGHT:
            return Vector([0, -h / 2])
        elif self.__quadrant__ == Quadrant.TOP:
            return Vector([-w / 2, 0])
        elif self.__quadrant__ == Quadrant.BOTTOM:
            return Vector([-w / 2, -h])
        return Vector([0, 0])

    @property
    def ___property_translation_context___(self):
        """Property translation context."""
        return self.__property_rna__.translation_context

    @property
    def ___translation_context___(self):
        """Translation context."""
        if self.__property_rna__:
            return self.___property_translation_context___
        elif self.type.is_operator:
            return "Operator"
        return "*"

    def ___translation_text___(self, text: str) -> str:
        """Translated text."""
        return text
        if not self.translate:
            return text
        return pgettext(text, self.___translation_context___)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__layout_haver__ = []
        self.__layout_haver_histories__ = []
        self.__clear_children__()
        self.active = False
        self.alert = False
        self.offset_position = self.mouse_position = Vector((0, 0))

    @property
    def __text__(self):
        """Get text to draw."""
        if self.text:
            return self.text
        if self.__property_name_string__:
            return self.__property_name_string__
        text = getattr(self, "__operator_text__", None)
        if text:
            return text
        return "Error"

    @property
    def parent_top(self):
        """Return root parent layout."""
        if self.parent:
            if self.parent.parent_top:
                return self.parent.parent_top
            else:
                return self.parent
        elif self.type.is_parent:
            return self

    @property
    def __layout_margin_vector__(self) -> Vector:
        """Spacing as Vector."""
        return Vector((self.layout_margin, self.layout_margin))

    @property
    def __lmt__(self):
        """Spacing value."""
        return self.layout_margin * 2

    @property
    def __margin_vector__(self) -> Vector:
        """Spacing as Vector."""
        return Vector((self.__margin__, self.__margin__))

    @property
    def __child_margin_vector__(self):
        if self.type.is_menu:
            return self.__layout_margin_vector__
        return self.__margin_vector__

    @property
    def __margin__(self) -> int:
        """Spacing value."""
        if self.type.is_parent:
            return self.layout_margin
        elif self.type.is_layout:
            if self.parent and self.parent.type.is_parent:
                return 0
            return self.layout_margin
        return self.text_margin

    @property
    def __mt__(self):
        return self.__margin__ * 2

    def __clear_children__(self) -> None:
        """Clear child layouts."""
        self.__draw_children__ = []
        self.__temp_children__ = []
        self.__layout_haver__ = []

    @property
    def __children__(self):
        if self.type.is_parent:
            # During build items land in temp; after __exit__ draw aliases temp.
            return self.__temp_children__ or self.__draw_children__
        return self.__draw_children__

    @property
    def is_layout(self) -> bool:
        """Return whether node is a layout."""
        return self.type.is_layout

    @property
    def is_draw_child(self) -> bool:
        """Return whether node can have children."""
        return self.__children__ and self.type.is_draw_child
