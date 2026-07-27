import bpy
from bpy.props import IntProperty, StringProperty

from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.public_ui import icon_two

_ELEMENT_TREE_FULL_DRAW_LIMIT = 48
_ELEMENT_TREE_PAGE_SIZE = 32
_ELEMENT_TREE_PAGES: dict[tuple[int, int], tuple[int, int]] = {}
_ELEMENT_TREE_DESCENDANTS_CACHE = None


def clear_element_tree_cache(*, clear_pages: bool = False) -> None:
    global _ELEMENT_TREE_DESCENDANTS_CACHE

    _ELEMENT_TREE_DESCENDANTS_CACHE = None
    if clear_pages:
        _ELEMENT_TREE_PAGES.clear()


def _rna_pointer(value) -> int:
    if value is None:
        return 0
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


def _visible_tree_descendants(root) -> list[tuple[object, int]]:
    """Flatten expanded descendants without creating nested UILayout rows."""
    from ..utils.public_cache import PublicCache

    global _ELEMENT_TREE_DESCENDANTS_CACHE
    generation = PublicCache.__structure_generation__
    packed = _ELEMENT_TREE_DESCENDANTS_CACHE
    if packed is None or packed[0] != generation:
        values = {}
        _ELEMENT_TREE_DESCENDANTS_CACHE = (generation, values)
    else:
        values = packed[1]
    root_pointer = _rna_pointer(root)
    cached = values.get(root_pointer)
    if cached is not None:
        return cached

    result = []
    stack = [(item, 1) for item in reversed(tuple(root.element))]
    while stack:
        item, depth = stack.pop()
        result.append((item, depth))
        if item.show_child and len(item.element):
            stack.extend(
                (child, depth + 1)
                for child in reversed(tuple(item.element))
            )
    values[root_pointer] = result
    return result


class ElementTreePage(bpy.types.Operator):
    """Change the bounded row window used for a large expanded element tree."""

    bl_idname = 'wm.gesture_element_tree_page'
    bl_label = 'Change Element Page'
    bl_options = {'INTERNAL'}

    root_pointer: StringProperty(options={'HIDDEN'})
    page: IntProperty(options={'HIDDEN'}, min=0)

    def execute(self, context):
        try:
            root_pointer = int(self.root_pointer)
        except (TypeError, ValueError):
            return {'CANCELLED'}
        area_pointer = _rna_pointer(getattr(context, 'area', None))
        if len(_ELEMENT_TREE_PAGES) > 256:
            _ELEMENT_TREE_PAGES.clear()
        try:
            from ..utils.public import get_pref

            active_pointer = _rna_pointer(get_pref().active_element)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            active_pointer = 0
        _ELEMENT_TREE_PAGES[(root_pointer, area_pointer)] = (
            self.page,
            active_pointer,
        )
        area = getattr(context, 'area', None)
        if area is not None:
            area.tag_redraw()
        return {'FINISHED'}


class GestureUIList(bpy.types.UIList, PrefAccess, ActiveSelection):
    bl_idname = 'GESTURE_UL_gesture_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout)

    def draw_filter(self, context, layout):
        column = layout.column(align=True)
        prop = self.draw_property

        row = column.row(align=True)
        row.active = prop.gesture_show_keymap
        row.prop(prop, "gesture_keymap_split_factor")

        row = column.row(align=True)
        row.prop(prop, "gesture_remove_tips", icon="INFO_LARGE" if bpy.app.version >= (4, 3, 0) else "ERROR")
        row.prop(prop, "enable_name_translation", icon="BLANK1")

        row = column.row(align=True)
        row.prop(prop, 'gesture_show_enabled_button', icon=icon_two(prop.gesture_show_enabled_button, "HIDE"))
        row.prop(prop, 'gesture_show_keymap', icon="BLANK1")
        row.prop(prop, 'gesture_show_description', icon="INFO")


class ElementUIList(bpy.types.UIList, PrefAccess, ActiveSelection):
    bl_idname = 'GESTURE_UL_element_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        from ..utils.ui_draw_sync import get_frozen_ui_selection

        # Keep every row tied to the selection captured at modal entry.  The
        # live ``pref.active_element`` resolver traverses the element tree on a
        # cache miss and must not run once per UIList row during a forced redraw.
        snapshot = get_frozen_ui_selection(data, context)
        frozen = snapshot is not None
        active = snapshot[1] if frozen else self.pref.active_element
        item_layout = layout.column(align=True)
        descendants = (
            _visible_tree_descendants(item)
            if item.show_child and len(item.element)
            else []
        )
        if len(descendants) <= _ELEMENT_TREE_FULL_DRAW_LIMIT:
            item.draw_item(
                item_layout,
                _active_element=active,
                _frozen=frozen,
            )
            return

        item.draw_item(
            item_layout,
            _active_element=active,
            _frozen=frozen,
            _draw_children=False,
        )
        self._draw_tree_page(
            context,
            item_layout,
            item,
            descendants,
            active=active,
            frozen=frozen,
        )

    @staticmethod
    def _draw_tree_page(
        context, layout, root, descendants, *, active, frozen,
    ) -> None:
        root_pointer = _rna_pointer(root)
        key = (root_pointer, _rna_pointer(getattr(context, 'area', None)))
        page_count = (
                         len(descendants) + _ELEMENT_TREE_PAGE_SIZE - 1
                     ) // _ELEMENT_TREE_PAGE_SIZE
        active_pointer = _rna_pointer(active) if active is not None else 0
        state = _ELEMENT_TREE_PAGES.get(key)
        if state is None:
            page, previous_active_pointer = 0, 0
        else:
            page, previous_active_pointer = state
        page = min(page, page_count - 1)

        if (
            active_pointer
            and active_pointer != root_pointer
            and active_pointer != previous_active_pointer
        ):
            for active_index, (element, _depth) in enumerate(descendants):
                if _rna_pointer(element) == active_pointer:
                    page = active_index // _ELEMENT_TREE_PAGE_SIZE
                    break
        _ELEMENT_TREE_PAGES[key] = (page, active_pointer)

        start = page * _ELEMENT_TREE_PAGE_SIZE
        end = min(len(descendants), start + _ELEMENT_TREE_PAGE_SIZE)
        pager = layout.row(align=True)
        previous = pager.row(align=True)
        previous.enabled = page > 0
        operator = previous.operator(
            ElementTreePage.bl_idname,
            text='',
            icon='TRIA_LEFT',
        )
        operator.root_pointer = str(root_pointer)
        operator.page = max(0, page - 1)
        pager.label(text=f'{start + 1}-{end} / {len(descendants)}')
        following = pager.row(align=True)
        following.enabled = page + 1 < page_count
        operator = following.operator(
            ElementTreePage.bl_idname,
            text='',
            icon='TRIA_RIGHT',
        )
        operator.root_pointer = str(root_pointer)
        operator.page = min(page_count - 1, page + 1)

        rows = layout.column(align=True)
        for element, depth in descendants[start:end]:
            row = rows.row(align=True)
            indent = row.row(align=True)
            indent.ui_units_x = min(6.0, max(0.75, depth * 0.75))
            indent.label(text='')
            element.draw_item(
                row.column(align=True),
                _active_element=active,
                _frozen=frozen,
                _draw_children=False,
            )

    def draw_filter(self, context, layout):
        from ..element.element_cure import ElementCURE
        column = layout.column(align=True)

        row = column.row(align=True)
        prop = self.draw_property
        icon = icon_two(prop.element_show_enabled_button, 'HIDE')
        row.prop(prop, 'element_show_enabled_button', icon=icon)
        if getattr(context.area, 'type', None) == 'PREFERENCES':
            icon = icon_two(prop.element_show_left_side, 'ALIGN')
            row.prop(prop, 'element_show_left_side', icon=icon)

        row = column.row(align=True)
        icon = icon_two(prop.element_show_icon, 'HIDE')
        row.prop(prop, 'element_show_icon', icon=icon)

        row = column.row(align=True)
        row.prop(prop, "element_remove_tips", icon="INFO_LARGE" if bpy.app.version >= (4, 3, 0) else "ERROR")
        row.operator(ElementCURE.SwitchShowChild.bl_idname)
        row.prop(prop, "enable_name_translation", icon="BLANK1")


class ElementModalEventUIList(bpy.types.UIList, PrefAccess, ActiveSelection):
    bl_idname = 'GESTURE_UL_element_modal_items'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        item.draw_item(layout.column(align=True))


class ImportPresetUIList(bpy.types.UIList, PrefAccess, ActiveSelection):
    bl_idname = 'GESTURE_UL_preset'

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_property, index,
                  flt_flag):
        layout.emboss = 'NONE'

        left = layout.row()
        left.alignment = 'LEFT'
        left.prop(item, 'selected', text=item.name, translate=False, icon='NONE')

        right = layout.row()
        right.alignment = 'RIGHT'
        right.prop(item, 'selected', icon=icon_two(item.selected, 'RESTRICT_SELECT'), text='')
