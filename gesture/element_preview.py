"""Centered, read-only rendering adapter for one selected element subtree."""

from __future__ import annotations

import gpu
from mathutils import Vector

from ..element.element_gpu_draw import ElementGpuDraw
from ..element.element_layout_gpu import ElementLayoutGpu
from ..utils.gesture_items import get_gesture_extension_items, iter_panel_leaves


class ElementPreviewAdapter(ElementGpuDraw, ElementLayoutGpu):
    """Present an arbitrary element as the child of an invisible column.

    The adapter deliberately uses the existing panel renderer. Direction and
    radial offsets therefore do not affect placement, while every real child
    keeps its normal icon, status, property value, layout, and flyout logic.
    """

    is_layout_container = True
    is_row = False
    is_column = True
    is_box = False
    is_split = False
    is_label = False
    is_dividing_line = False
    is_child_gesture = False
    is_operator = False
    is_property_display = False
    layout_scale = 1.0
    layout_scale_x = 1.0
    layout_scale_y = 1.0
    layout_align = False

    def __init__(self):
        self.ops = None
        self.element = None
        self._items = []
        self._panel_leaf_items = []

    @property
    def draw_property(self):
        return self.ops.draw_property

    @property
    def layout_alignment(self):
        return 'EXPAND' if self._only_dividers else 'CENTER'

    @property
    def _only_dividers(self) -> bool:
        return bool(self._items) and all(item.is_dividing_line for item in self._items)

    def _layout_children(self):
        return self._items

    @property
    def panel_leaf_items(self):
        session = getattr(getattr(self, 'ops', None), 'session', None)
        if (
                session is not None
                and getattr(self, '_layout_visible_token', None) is session.layout_token
        ):
            return getattr(self, '_layout_visible_leaf_items', ())
        return self._panel_leaf_items

    @property
    def layout_panel_content_size(self):
        size = ElementLayoutGpu.layout_panel_content_size.fget(self).copy()
        if self._only_dividers:
            size.x = max(size.x, 120.0 * self._element_ui_scale())
        return size

    def set_element(self, element, session) -> None:
        self.element = element
        if element is None:
            items = ()
        elif element.is_selected_structure:
            items = get_gesture_extension_items(element.element)
        else:
            items = (element,)
        self._items = [session.canonical_element(item) for item in items]
        self._panel_leaf_items = [
            session.canonical_element(item)
            for item in iter_panel_leaves(self._items)
        ]

    def initial_hover_path(self) -> list:
        path = [self]
        if self.element is not None and self.element.is_child_gesture:
            path.append(self.element)
        return path

    def draw_centered(self, ops, center) -> None:
        self.ops = ops
        size = self.layout_panel_content_size
        with gpu.matrix.push_pop():
            gpu.matrix.translate(
                Vector((float(center[0]), float(center[1])))
                + Vector((-float(size.x) * 0.5, float(size.y) * 0.5))
            )
            self.draw_gpu_layout_panel(ops)
