from enum import Enum


class BPUType(Enum):
    ROW = 10
    COLUMN = 20
    # SPLIT = 40
    LABEL = 50
    # PROPERTY = 60
    SEPARATOR = 70

    MENU = 100

    OPERATOR = 200
    PROP = 300

    PARENT = 500

    UNKNOWN = 1000

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def is_prop(self) -> bool:
        return self.name == "PROP"

    @property
    def is_separator(self) -> bool:
        """Return whether node is a separator."""
        return self.name == "SEPARATOR"

    @property
    def is_menu(self) -> bool:
        """Return whether node is a menu."""
        return self.name == "MENU"

    @property
    def is_layout(self) -> bool:
        """Return whether node is a layout container."""
        return self.name in ['ROW', 'COLUMN', 'BOX', 'SPLIT']

    @property
    def is_parent(self) -> bool:
        """Return whether node is a parent."""
        return self.name == "PARENT"

    @property
    def is_draw_text(self) -> bool:
        """Return whether node draws text."""
        return self.name in ['LABEL', 'OPERATOR']

    @property
    def is_draw_child(self) -> bool:
        """Return whether node can have children."""
        return self.is_layout or self.is_parent

    @property
    def is_horizontal_layout(self) -> bool:
        """Return whether layout is horizontal
        -----------
        """
        return self.name in ['ROW', 'BOX']

    @property
    def is_vertical_layout(self) -> bool:
        """Return whether layout is vertical
        ¦
        ¦
        ¦
        ¦
        ¦
        """
        return self.name in ['COLUMN', 'BOX']

    @property
    def is_draw_item(self) -> bool:
        """Return whether node is a draw item."""
        return self.name in ['LABEL', 'OPERATOR']

    @property
    def is_clickable(self) -> bool:
        """Return whether node is clickable."""
        return self.name == 'OPERATOR'

    @property
    def is_operator(self) -> bool:
        """Return whether node is an operator."""
        return self.name == 'OPERATOR'


class Quadrant(Enum):
    """Draw quadrant position."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4

    LIFT = 5
    RIGHT = 6
    TOP = 7
    BOTTOM = 8
