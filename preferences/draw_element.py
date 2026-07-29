import bpy
from bpy.app.translations import pgettext

from ..utils.icons import ui_icon
from ..utils.public import get_pref, get_debug
from ..utils.public_ui import icon_two


_ACTIVE_ELEMENT_UNSET = object()


def draw_label(lay: bpy.types.UILayout, label: str) -> bpy.types.UILayout:
    width = bpy.context.region.width
    if width < 400:
        split = lay.row(align=True)
    else:
        split = lay.split(align=True, factor=0.3)
        split.label(text=label)
        split = split.row(align=True)
    return split


class DrawElement:

    @staticmethod
    def _draw_add_operator(
            layout: 'bpy.types.UILayout',
            text: str,
            *,
            frozen: bool,
            element_type: str,
            selected_type: str | None = None,
    ):
        from ..element import ElementCURE

        operator_id = (
            ElementCURE.FrozenADD.bl_idname
            if frozen
            else ElementCURE.ADD.bl_idname
        )
        operator = layout.operator(operator_id, text=text)
        if not frozen:
            operator.element_type = element_type
            if selected_type is not None:
                operator.selected_type = selected_type
        return operator

    @staticmethod
    def draw_element_cure(layout: bpy.types.UILayout) -> None:
        from ..element import ElementCURE
        pref = get_pref()
        draw_property = pref.draw_property

        column = layout.column(align=True)
        column.enabled = ElementCURE.MOVE.move_item is None
        # Preferences default to EXEC; confirm tips / modifier shortcuts need invoke.
        column.operator_context = "INVOKE_DEFAULT"

        cr = column.column(align=True)
        cut = cr.column(align=True)
        cut.active = cut.enabled = not pref.__is_cut_element__
        cut.operator(ElementCURE.CUT.bl_idname, icon_value=pref.__get_icon__("CUT"), text='')
        cr.operator(ElementCURE.COPY.bl_idname, icon=ui_icon('COPYDOWN'), text='')
        rm = column.column(align=True)
        rm.operator(ElementCURE.REMOVE.bl_idname, icon=ui_icon('REMOVE'), text='')

        column.separator()

        sc = column.column(align=True)
        sc.operator(
            ElementCURE.SORT.bl_idname,
            text='',
            icon=ui_icon('SORT_DESC'),
        ).is_next = False
        sc.operator(ElementCURE.MOVE.bl_idname, icon=ui_icon('GRIP'), text='')
        sc.operator(
            ElementCURE.SORT.bl_idname,
            text='',
            icon=ui_icon('SORT_ASC'),
        ).is_next = True

        if getattr(bpy.context.area, 'type', None) == 'PREFERENCES':
            column.separator()
            icon = ui_icon(icon_two(draw_property.element_show_left_side, style='ALIGN'))
            column.alert = draw_property.element_show_left_side
            column.prop(draw_property, 'element_show_left_side', icon=icon, text='', emboss=False)

    @staticmethod
    def draw_property(
            layout: 'bpy.types.UILayout',
            *,
            include_modal: bool = True,
            active_element=_ACTIVE_ELEMENT_UNSET,
    ) -> None:
        pref = get_pref()
        if active_element is _ACTIVE_ELEMENT_UNSET:
            active_element = pref.active_element
        prop = pref.draw_property
        show_on_preferences_left = (
            getattr(bpy.context.area, 'type', None) == 'PREFERENCES'
            and prop.element_show_left_side
        )
        if pref.__is_cut_element__:
            DrawElement.draw_cut_element(layout)

        elif active_element:
            if pref.__is_move_element__:
                DrawElement.draw_move_element(layout)
            elif not show_on_preferences_left:
                active_element.draw_alert(layout)
                active_element.draw_item_property(layout, include_modal=include_modal)
            if get_debug():
                active_element.draw_debug(layout)
        else:
            layout.label(text='Add or select an element')

    @staticmethod
    def draw_move_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        mi = ElementCURE.MOVE.move_item

        column = layout.column(align=True)
        column.label(text="While moving an element")
        column.separator()
        column.label(text=pgettext("Move element: %s") % mi.name)
        if mi.is_root:
            column.label(text="This item is at the root level")

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.enabled = not mi.is_root  # Not root level
        mr.operator(
            ElementCURE.MOVE.bl_idname,
            icon=ui_icon('GRIP'),
            text='Move to root level',
        ).cancel_move = False
        row.operator(
            ElementCURE.MOVE.bl_idname,
            icon=ui_icon('CANCEL'),
            text='Cancel move',
        ).cancel_move = True

    @staticmethod
    def draw_cut_element(layout: 'bpy.types.UILayout'):
        from ..element.element_cure import ElementCURE
        pref = get_pref()

        column = layout.column(align=True)
        column.label(text="While cutting an element")
        column.separator()

        row = column.row(align=True)
        mr = row.row(align=True)
        mr.operator(
            ElementCURE.CUT.bl_idname,
            icon_value=pref.__get_icon__("CUT"),
            text='Paste to root level'
        ).cancel_cut = False
        row.operator(
            ElementCURE.CUT.bl_idname,
            icon=ui_icon('CANCEL'),
            text='Cancel cut',
        ).cancel_cut = True

    @classmethod
    def draw_element_add_property(
            cls,
            layout: 'bpy.types.UILayout',
            *,
            frozen: bool = False,
    ) -> None:
        from ..utils.enum import (
            ENUM_ELEMENT_TYPE,
            ENUM_LAYOUT_ELEMENT_TYPE,
            ENUM_SELECTED_TYPE,
        )
        from ..ui.menu import (
            GESTURE_MT_add_element_menu,
            GESTURE_MT_layout_preset_menu,
        )

        pref = get_pref()
        add = pref.add_element_property

        add_child = add.is_have_add_child

        column = layout.box().column(align=True)
        column.label(text='Add element')

        relation = column.column(align=True)
        row = draw_label(relation, 'Element relationship:')
        row.prop(add, 'relationship', expand=True)
        row.prop(
            add,
            "add_active_radio",
            icon=ui_icon("LAYER_ACTIVE"),
            icon_only=True,
        )

        # Keep the same control rows for every relationship. When the
        # active element is a leaf and CHILD is selected, disable the controls
        # instead of replacing them with warning rows that change panel height.
        controls_enabled = bool(add_child)

        structure = column.column(align=True)
        row = draw_label(structure, 'Selected Structure:')
        row.enabled = controls_enabled
        for i, n, d in ENUM_SELECTED_TYPE:
            cls._draw_add_operator(
                row,
                n,
                frozen=frozen,
                element_type='SELECTED_STRUCTURE',
                selected_type=i,
            )

        items = column.column(align=True)
        row = draw_label(items, 'Add item:')
        row.enabled = controls_enabled
        for i, n, d in ENUM_ELEMENT_TYPE:
            if i in (
                    'SELECTED_STRUCTURE',
                    'DIVIDING_LINE',
                    'ROW', 'COLUMN', 'BOX', 'LABEL', 'SPLIT',
            ):
                continue
            cls._draw_add_operator(
                row,
                n,
                frozen=frozen,
                element_type=i,
            )

        # Separate the complete two-row Layout group from Add item while
        # keeping the two Layout rows internally aligned with each other.
        column.separator(factor=0.5)
        layout_column = column.column(align=True)
        layout_containers = draw_label(layout_column, 'Layout:')
        layout_containers.enabled = controls_enabled
        for i, n, d in ENUM_LAYOUT_ELEMENT_TYPE:
            if i not in {'ROW', 'COLUMN', 'BOX'}:
                continue
            cls._draw_add_operator(
                layout_containers,
                n,
                frozen=frozen,
                element_type=i,
            )

        # Keep a fixed second row for the narrower/special layout controls.
        # Div and Label always reserve their cells even when the relationship
        # makes them unavailable, so changing relationship cannot reflow the
        # row or move the trailing menu buttons.
        layout_items = draw_label(layout_column, '')
        layout_items.enabled = controls_enabled
        cls.draw_element_add_div_property(layout_items, frozen=frozen)
        cls.draw_element_add_label_property(layout_items, frozen=frozen)
        split_name = next(
            name
            for identifier, name, _description in ENUM_LAYOUT_ELEMENT_TYPE
            if identifier == 'SPLIT'
        )
        cls._draw_add_operator(
            layout_items,
            split_name,
            frozen=frozen,
            element_type='SPLIT',
        )
        layout_items.menu(
            GESTURE_MT_layout_preset_menu.__name__,
            icon=ui_icon('PRESET'),
            text='',
        )
        layout_items.menu(
            GESTURE_MT_add_element_menu.__name__,
            icon=ui_icon('COLLAPSEMENU'),
            text='',
        )

    @classmethod
    def draw_element_add_div_property(
            cls,
            layout: 'bpy.types.UILayout',
            *,
            frozen: bool = False,
    ) -> None:
        cls._draw_element_add_nondirectional_property(
            layout,
            'DIVIDING_LINE',
            'Div',
            frozen=frozen,
        )

    @classmethod
    def draw_element_add_label_property(
            cls,
            layout: 'bpy.types.UILayout',
            *,
            frozen: bool = False,
    ) -> None:
        cls._draw_element_add_nondirectional_property(
            layout,
            'LABEL',
            'Label',
            frozen=frozen,
        )

    @classmethod
    def _draw_element_add_nondirectional_property(
            cls,
            layout: 'bpy.types.UILayout',
            element_type: str,
            text: str,
            *,
            frozen: bool = False,
    ) -> None:
        """Draw an item that is valid only inside a menu/layout collection."""
        pref = get_pref()
        add = pref.add_element_property
        relationship = add.relationship
        active = pref.active_element
        is_alert = False

        # Dividers and labels only make sense inside extension menus or layout
        # containers, not as radial direction slots.
        if relationship == "ROOT":
            is_alert = True
        elif relationship == "SAME":
            if active and active.parent_element and (
                    active.parent_is_extension or active.parent_is_layout
            ):
                ...
            else:
                is_alert = True
        elif relationship == "CHILD":
            if active:
                under_extension = active.is_child_gesture and (
                        active.direction == "9" or active.parent_is_extension
                )
                if under_extension or active.is_selected_structure or active.is_layout_container:
                    ...
                else:
                    is_alert = True
            else:
                is_alert = True

        # Always create the same cell. Only its enabled state changes, keeping
        # the containing row stable as ROOT/SAME/CHILD availability changes.
        layout = layout.row(align=True)
        layout.enabled = not is_alert

        cls._draw_add_operator(
            layout,
            text,
            frozen=frozen,
            element_type=element_type,
        )
