from functools import cache

import bpy

from ..preferences.draw import PreferencesDraw
from ..preferences.draw_gesture import GestureDraw
from ..utils.active_selection import ActiveSelection
from ..utils.pref_access import PrefAccess
from ..utils.public import get_pref
from ..utils.rna_register import register_classes_safe, unregister_classes_safe
from ..utils.icons import ui_icon

_MODAL_EVENT_VISIBILITY: dict[int, bool] = {}


def _panel_area_key(context) -> int:
    area = getattr(context, 'area', None)
    try:
        return int(area.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(area)


class GesturePanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = ""
    bl_idname = "GESTURE_PT_Layout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"

    @classmethod
    def poll(cls, context):
        try:
            return get_pref().draw_property.panel_enable
        except (KeyError, AttributeError):
            return False

    def draw_label_ang_version(self, layout):
        @cache
        def text():
            from .. import ADDON_VERSION
            label = f"{bpy.app.translations.pgettext_iface('Gesture')} {'.'.join(map(str, ADDON_VERSION))}"
            return label

        layout.label(text=text())

    def draw_header(self, context):
        from ..utils.ui_draw_sync import (
            heavy_panel_skip_message,
            is_panel_pause_source_active,
        )

        pref = self.pref
        row = self.layout.row(align=True)
        message = heavy_panel_skip_message(context)
        rr = row.row(align=True)
        rr.enabled = not message
        rr.operator_context = "EXEC_DEFAULT"
        rr.prop(pref, 'enabled', text="", emboss=True)
        rr.operator(
            "wm.gesture_save_userpref",
            text="",
            icon=ui_icon("FILE_TICK"),
        )
        self.draw_label_ang_version(row)

        if message:
            status = row.row(align=True)
            status.enabled = False
            status.label(text=message, icon=ui_icon("PAUSE"))
        if is_panel_pause_source_active(context):
            toggle = row.row(align=True)
            toggle.enabled = True
            toggle.prop(
                pref.draw_property,
                'force_show_panels_during_modal',
                text="Update panels",
                toggle=True,
            )

    def draw_header_preset(self, context):
        """Right side of the panel title — open add-on preferences."""
        from ..utils.ui_draw_sync import heavy_panel_skip_message

        layout = self.layout
        layout.enabled = not heavy_panel_skip_message(context)
        layout.operator_context = "EXEC_DEFAULT"
        layout.operator(
            "wm.gesture_show_preferences",
            text="",
            icon=ui_icon("PREFERENCES"),
        )

    def draw(self, context):
        ...


class GestureItemPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Item"
    bl_idname = "GESTURE_PT_Item"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        from ..utils.ui_draw_sync import (
            draw_heavy_panel_paused,
            get_frozen_active_element,
            get_frozen_preview_state,
            panel_pause_state,
        )
        msg, layout_frozen = panel_pause_state(context)
        if layout_frozen:
            from ..utils.ui_draw_sync import get_frozen_active_gesture
            active_gesture = get_frozen_active_gesture(context)
            active_element = get_frozen_active_element(context)
            preview_active, preview_scope = get_frozen_preview_state(context)
        else:
            active_gesture = self.pref.active_gesture
            active_element = self.pref.active_element
            preview_active = None
            preview_scope = None
        preview_column = self.layout.column()
        preview_column.enabled = not msg
        GestureDraw.draw_gesture_preview_button(
            preview_column,
            active_gesture=active_gesture,
            active_element=active_element,
            frozen=bool(msg),
            preview_active=preview_active,
            preview_scope=preview_scope,
        )
        if msg and not layout_frozen:
            draw_heavy_panel_paused(self.layout, msg)
            return

        column = self.layout.column()
        column.enabled = self.pref.enabled and not msg
        layout = column.row(align=True)
        layout.enabled = self.pref.enabled and not msg
        if not active_gesture:
            GestureDraw.draw_gesture_cure(layout)
        GestureDraw.draw_gesture(layout, active_gesture=active_gesture)


class GestureElementPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Element"
    bl_idname = "GESTURE_PT_Element"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = set()

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        # ElementUIList walks the same Element RNA the GPU overlay stores hit
        # boxes against; drawing it mid-modal can wipe those transient attrs.
        # Also skip during animation play (UI redraws every frame while playing).
        from ..utils.ui_draw_sync import (
            draw_heavy_panel_paused,
            panel_pause_state,
        )
        msg, layout_frozen = panel_pause_state(context)
        if msg and not layout_frozen:
            draw_heavy_panel_paused(self.layout, msg)
            return
        layout = self.layout
        layout.enabled = self.pref.enabled and not msg
        GestureDraw.draw_element(
            layout,
            include_modal=False,
            allow_frozen=layout_frozen,
        )


class GestureModalEventPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Modal Event"
    bl_idname = "GESTURE_PT_Modal_Event"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    # bl_parent_id = GestureElementPanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        if not GesturePanel.poll(context):
            return False
        from ..utils.ui_draw_sync import (
            get_frozen_active_element,
            get_gesture_modal_session,
            is_gesture_panel_frozen,
            panel_pause_state,
        )

        message, layout_frozen = panel_pause_state(context)
        if layout_frozen:
            if is_gesture_panel_frozen(context):
                session = get_gesture_modal_session(context)
                active = getattr(session, "_modal_event_panel_element", None)
            else:
                active = get_frozen_active_element(context)
            return bool(active is not None and active.operator_is_modal)

        area_key = _panel_area_key(context)
        if message is not None:
            if area_key in _MODAL_EVENT_VISIBILITY:
                return _MODAL_EVENT_VISIBILITY[area_key]
        pref = get_pref()
        active = pref.active_element
        visible = active is not None and active.operator_is_modal
        _MODAL_EVENT_VISIBILITY[area_key] = visible
        return visible

    def draw(self, context):
        from ..utils.ui_draw_sync import (
            draw_heavy_panel_paused,
            is_gesture_panel_frozen,
            panel_pause_state,
        )
        msg, layout_frozen = panel_pause_state(context)
        gesture_frozen = is_gesture_panel_frozen(context)
        if msg and not layout_frozen:
            draw_heavy_panel_paused(self.layout, msg)
            return
        layout = self.layout
        layout.enabled = not msg
        if layout_frozen:
            if gesture_frozen:
                from ..utils.ui_draw_sync import get_gesture_modal_session
                session = get_gesture_modal_session(context)
                active = getattr(session, "_modal_event_panel_element", None)
            else:
                from ..utils.ui_draw_sync import get_frozen_active_element
                active = get_frozen_active_element(context)
        else:
            active = get_pref().active_element
        if active is not None:
            active.draw_operator_modal(layout)


class GesturePropertyPanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Property"
    bl_idname = "GESTURE_PT_Property"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw(self, context):
        from ..utils.ui_draw_sync import (
            draw_heavy_panel_paused,
            panel_pause_state,
        )

        msg, layout_frozen = panel_pause_state(context)
        if msg and not layout_frozen:
            draw_heavy_panel_paused(self.layout, msg)
            return
        layout = self.layout
        layout.scale_y = 1.2
        layout.enabled = not msg
        PreferencesDraw.draw_ui_property(layout)


class GestureStylePanel(bpy.types.Panel, PrefAccess, ActiveSelection):
    bl_label = "Style"
    bl_idname = "GESTURE_PT_Style"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gesture"
    bl_parent_id = GesturePanel.bl_idname
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return GesturePanel.poll(context)

    def draw_header_preset(self, context):
        from ..utils.ui_draw_sync import heavy_panel_skip_message

        self.layout.enabled = not heavy_panel_skip_message(context)
        self.layout.prop(get_pref().draw_property, 'theme_preset', text='')

    def draw(self, context):
        from ..utils.ui_draw_sync import (
            draw_heavy_panel_paused,
            panel_pause_state,
        )

        msg, layout_frozen = panel_pause_state(context)
        if msg and not layout_frozen:
            draw_heavy_panel_paused(self.layout, msg)
            return
        layout = self.layout
        layout.scale_y = 1.2
        layout.enabled = not msg
        PreferencesDraw.draw_ui_style(
            layout,
            compact=True,
            show_theme=False,
        )


panel_list = (
    GesturePanel,
    GestureItemPanel,
    GestureElementPanel,
    GestureModalEventPanel,
    GesturePropertyPanel,
    GestureStylePanel,
)


def register():
    pref = get_pref()
    for panel in panel_list:
        panel.bl_category = pref.draw_property.panel_name
    if pref.draw_property.panel_enable:
        register_classes_safe(panel_list)


def unregister():
    _MODAL_EVENT_VISIBILITY.clear()
    unregister_classes_safe(panel_list)


def update_panel():
    unregister()
    register()
