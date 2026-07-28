"""Independent persistent menu operator."""

from bpy.app.translations import pgettext
from bpy.props import StringProperty

from ..gesture.gesture_executor import GestureExecutor
from ..gesture.menu import GestureMenuRuntime
from ..utils.adapter import operator_setattr
from ..utils.public import PublicOperator, debug_print


class GestureMenuOperator(PublicOperator, GestureMenuRuntime):
    bl_idname = 'wm.gesture_menu'
    bl_label = 'Gesture Menu'
    bl_description = 'Open a persistent Gesture Helper menu at the mouse position'
    bl_options = {'INTERNAL'}

    gesture: StringProperty()

    @classmethod
    def poll(cls, context):
        from ..utils.pref import poll_addon_preferences

        return poll_addon_preferences(cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        operator_setattr(self, '_menu_area', None)
        operator_setattr(self, '_menu_screen', None)
        operator_setattr(self, '_menu_window', None)
        operator_setattr(self, '_menu_gesture_ref', None)
        operator_setattr(self, '_menu_anchor', (0.0, 0.0))
        operator_setattr(self, '_menu_panels', [])
        operator_setattr(self, '_menu_open_path', [])
        operator_setattr(self, '_menu_hovered_row', None)
        operator_setattr(self, '_menu_hovered_part', None)
        operator_setattr(self, '_menu_hovered_close', False)
        operator_setattr(self, '_menu_pressed_row', None)
        operator_setattr(self, '_menu_pressed_part', None)
        operator_setattr(self, '_menu_pressed_close', False)
        operator_setattr(self, '_menu_enum_dropdown', None)
        operator_setattr(self, '_menu_layout_key', None)
        operator_setattr(self, '_menu_layout_dirty', True)
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_external_modal_active', False)
        operator_setattr(self, '_menu_initial_modal_keys', frozenset())
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, '_menu_draw_count', 0)
        operator_setattr(self, '_menu_last_draw_error', '')
        operator_setattr(self, '_menu_drag_mouse', None)
        operator_setattr(self, '_menu_drag_button', None)
        operator_setattr(self, '_menu_opened_at', 0.0)
        operator_setattr(self, '_menu_closing_at', 0.0)
        operator_setattr(self, '_menu_close_start_reveal', 1.0)
        operator_setattr(self, '_menu_animation_timer', None)
        operator_setattr(self, '_menu_animation_serial', 0)
        operator_setattr(self, '_menu_animation_event_timer', None)
        operator_setattr(self, '_menu_window_manager', None)

    @staticmethod
    def _draw_error(menu, _context):
        menu.layout.label(text='Menu gesture not found', icon='ERROR')
        menu.layout.label(text='Restore or recreate its shortcut in preferences')

    def invoke(self, context, event):
        area = context.area
        if area is None or area.type in {'PREFERENCES', 'FILE_BROWSER'}:
            return {'CANCELLED'}

        from ..utils.session_state import SessionState

        SessionState.request_gesture_preview_close()

        from ..utils.gesture_store import get_gestures

        gestures = get_gestures()
        gesture = gestures.get(self.gesture) if gestures is not None else None
        if gesture is None or gesture.gesture_type != 'MENU':
            context.window_manager.popup_menu(
                self.__class__._draw_error,
                title=pgettext('Error'),
                icon='ERROR',
            )
            return {'CANCELLED'}

        from ..utils.public_cache import PublicCacheFunc
        from ..utils.region_mouse import mouse_in_window_region

        PublicCacheFunc.ensure_gesture_structure(gesture)
        mouse = mouse_in_window_region(event, area)
        if mouse is None:
            return {'CANCELLED'}

        operator_setattr(self, '_menu_area', area)
        operator_setattr(self, '_menu_screen', context.screen)
        operator_setattr(self, '_menu_window', context.window)
        operator_setattr(self, '_menu_window_manager', context.window_manager)
        operator_setattr(self, '_menu_gesture_ref', gesture)
        operator_setattr(self, '_menu_anchor', (mouse[0] + 6.0, mouse[1] + 6.0))
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_enum_dropdown', None)
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, 'event', event)
        operator_setattr(
            self,
            '_menu_initial_modal_keys',
            frozenset(
                key for _operator, key in self._window_modal_operators(context.window)
            ),
        )

        if not self._register_menu_runtime(context):
            return {'CANCELLED'}
        self._ensure_layout(force=True)
        self._start_menu_open_animation()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _ensure_menu_animation_event_timer(self) -> None:
        if self._menu_animation_event_timer is not None:
            return
        wm = self._menu_window_manager
        window = self._menu_window
        if wm is None or window is None:
            operator_setattr(self, '_menu_close_requested', True)
            return
        try:
            from ..gesture.menu import MENU_FRAME_SECONDS

            timer = wm.event_timer_add(MENU_FRAME_SECONDS, window=window)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            operator_setattr(self, '_menu_close_requested', True)
            return
        operator_setattr(self, '_menu_animation_event_timer', timer)

    def _remove_menu_animation_event_timer(self) -> None:
        timer = self._menu_animation_event_timer
        wm = self._menu_window_manager
        operator_setattr(self, '_menu_animation_event_timer', None)
        if timer is None or wm is None:
            return
        try:
            wm.event_timer_remove(timer)
        except (AttributeError, ReferenceError, RuntimeError, ValueError):
            ...

    def _area_is_live(self) -> bool:
        area = self._menu_area
        screen = self._menu_screen
        if area is None or screen is None:
            return False
        try:
            return any(candidate == area for candidate in screen.areas)
        except (AttributeError, ReferenceError, RuntimeError):
            return False

    @staticmethod
    def _modal_operator_key(operator):
        """Return a stable identity for an entry in Window.modal_operators."""
        try:
            pointer = operator.as_pointer()
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            pointer = 0
        if pointer:
            return ('RNA', pointer)
        try:
            if getattr(operator, 'bl_rna', None) is not None:
                return None
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        return ('PYTHON', id(operator))

    @classmethod
    def _window_modal_operators(cls, window):
        if window is None:
            return ()
        try:
            operators = tuple(window.modal_operators)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return ()
        result = []
        for operator in operators:
            try:
                key = cls._modal_operator_key(operator)
                if key is not None:
                    result.append((operator, key))
            except ReferenceError:
                continue
        return tuple(result)

    def _has_external_modal(self, context) -> bool:
        window = self._menu_window or context.window
        initial_keys = self._menu_initial_modal_keys
        self_key = self._modal_operator_key(self)
        for operator, key in self._window_modal_operators(window):
            try:
                if key == self_key or operator == self:
                    continue
                identifier = getattr(operator, 'bl_idname', '') or type(operator).__name__
                if identifier in {'wm.gesture_menu', 'WM_OT_gesture_menu'}:
                    continue
                if key in initial_keys:
                    continue
                return True
            except ReferenceError:
                continue
        return False

    def _finish_menu(self, *, cancelled=False, pass_through=False):
        if not self._menu_runtime_cleaned:
            operator_setattr(self, '_menu_runtime_cleaned', True)
            try:
                self._remove_menu_animation_event_timer()
            finally:
                self._unregister_menu_runtime()
        result = {'CANCELLED'} if cancelled else {'FINISHED'}
        if pass_through:
            result.add('PASS_THROUGH')
        return result

    def _execute_menu_row(self, row) -> None:
        element = row.element
        if element is None:
            return
        element.ops = self
        if row.kind == 'PROPERTY':
            GestureExecutor._run_property_element(self, element)
            self._menu_mark_context_changed()
            return
        if row.kind != 'OPERATOR':
            return
        if element.operator_func is None:
            self.report(
                {'ERROR'},
                pgettext('Operator not found: %s') % element.operator_bl_idname,
            )
            return
        if not element.check_operator_poll():
            self.report(
                {'WARNING'},
                pgettext('Operator unavailable in this context: %s') % element.operator_bl_idname,
            )
            self._menu_mark_context_changed()
            return
        try:
            error = element.running_operator()
        except Exception as exc:
            error = exc
        if error is not None:
            debug_print('Persistent menu operator error', error, key='operator')
            self.report({'ERROR'}, pgettext('Operator error. Check the console for details.'))
        else:
            self.report({'INFO'}, element.name_translate)
        self._menu_mark_context_changed()

    def _repair_menu_row(self, row):
        """Close the menu before opening the existing element editor."""
        result = self._finish_menu()
        from ..utils.selection import reveal_element_settings
        if reveal_element_settings(row.element):
            result.add('INTERFACE')
        return result

    def _copy_hover_tooltip(self, context, event) -> bool:
        """Consume Ctrl+C only while a hover tooltip is actually visible."""
        if event.type != 'C' or event.value != 'PRESS' or not event.ctrl:
            return False
        from ..gesture.runtime_tooltip import copy_displayed_tooltip

        if not copy_displayed_tooltip(
                getattr(self, '_menu_tooltip_state', None),
                getattr(context, 'window_manager', None),
        ):
            return False
        self.report({'INFO'}, pgettext('Hover information copied'))
        return True

    def modal(self, context, event):
        operator_setattr(self, 'event', event)
        if self._menu_close_requested:
            return self._finish_menu(pass_through=True)
        if not self._area_is_live():
            return self._finish_menu(cancelled=True)
        if event.type == 'WINDOW_DEACTIVATE':
            if not self._menu_keep_open():
                return self._finish_menu(cancelled=True)
            drag_button = getattr(self, '_menu_drag_button', None)
            if drag_button is not None:
                self._finish_menu_drag(button=drag_button)
            self._clear_menu_press()
            operator_setattr(self, '_menu_enum_dropdown', None)
            operator_setattr(self, '_menu_layout_dirty', True)
            return {'PASS_THROUGH'}
        if self._menu_closing_at:
            return {'RUNNING_MODAL'}

        external_modal = self._has_external_modal(context)
        if external_modal:
            operator_setattr(self, '_menu_external_modal_active', True)
            if self._clear_menu_press():
                self._tag_menu_redraw()
            self._close_menu_enum_dropdown()
            return {'PASS_THROUGH'}
        if self._menu_external_modal_active:
            operator_setattr(self, '_menu_external_modal_active', False)
            self._menu_mark_context_changed()

        if event.value == 'PRESS' and event.type in {'ESC', 'RIGHTMOUSE'}:
            if self._close_menu_enum_dropdown():
                return {'RUNNING_MODAL'}
            self._begin_menu_close()
            return {'RUNNING_MODAL'}

        if self._copy_hover_tooltip(context, event):
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            if self._move_menu_drag(event):
                return {'RUNNING_MODAL'}
            if self._update_menu_hover(event):
                self._tag_menu_redraw()
            return {'PASS_THROUGH'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            self._ensure_layout()
            hover_changed = self._update_menu_hover(event)
            point = self._menu_mouse(event)
            if not self._menu_contains(point):
                return {'PASS_THROUGH'}
            row = getattr(self, '_menu_hovered_row', None)
            try:
                is_numeric = bool(
                    row is not None
                    and row.enabled
                    and row.kind == 'PROPERTY'
                    and row.element.display_property_is_editable
                    and row.element.display_property_type in {'INT', 'FLOAT'}
                )
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                is_numeric = False
            if is_numeric:
                direction = 1 if event.type == 'WHEELUPMOUSE' else -1
                changed = row.element.apply_property_wheel(
                    direction,
                    precise=getattr(event, 'shift', False),
                )
                if changed:
                    self._menu_mark_context_changed()
                    hover_changed = False
            if hover_changed:
                self._tag_menu_redraw()
            # Menu-owned wheel input must never zoom the editor underneath it.
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self._finish_menu_drag(button='LEFTMOUSE'):
                return {'RUNNING_MODAL'}
            if self._clear_menu_press():
                self._tag_menu_redraw()
                return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._ensure_layout()
            if self._menu_close_hit(event):
                self._press_menu_close()
                self._begin_menu_close()
                return {'RUNNING_MODAL'}
            if self._menu_header_hit(event):
                self._start_menu_drag(event, button='LEFTMOUSE')
                return {'RUNNING_MODAL'}
            row = self._menu_clicked_row(event)
            if row is not None:
                status = getattr(row.status_info, 'status', None)
                if status is not None and status.is_error:
                    return self._repair_menu_row(row)
                if row.kind == 'ENUM_ITEM':
                    self._set_menu_enum_choice(row)
                    if not self._menu_keep_open():
                        self._begin_menu_close()
                    return {'RUNNING_MODAL'}
                if self._is_enum_property_row(row):
                    self._toggle_menu_enum_dropdown(row)
                    return {'RUNNING_MODAL'}
                if self._press_menu_row(row, event):
                    self._tag_menu_redraw()
                arrow_direction = self._menu_property_arrow_direction(row, event)
                if arrow_direction:
                    changed = row.element.apply_property_wheel(
                        arrow_direction,
                        precise=getattr(event, 'shift', False),
                    )
                    if changed:
                        self._menu_mark_context_changed()
                    if not self._menu_keep_open():
                        self._begin_menu_close()
                    return {'RUNNING_MODAL'}
                self._execute_menu_row(row)
                # Numeric body clicks may start a second modal that owns the
                # release event. Do not leave its visual press latched behind.
                if (
                        row.kind == 'PROPERTY'
                        and getattr(self, '_menu_pressed_part', None) == 'VALUE'
                        and self._clear_menu_press()
                ):
                    self._tag_menu_redraw()
                if not self._menu_keep_open():
                    self._begin_menu_close()
                return {'RUNNING_MODAL'}
            if not self._menu_contains(self._menu_mouse(event)):
                if self._close_menu_enum_dropdown():
                    return {'PASS_THROUGH'}
                if not self._menu_keep_open():
                    self._begin_menu_close()
                return {'PASS_THROUGH'}
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def cancel(self, _context):
        # Blender invokes cancel() as a cleanup callback and requires None.
        # Returning an operator status set here raises during add-on disable or
        # application shutdown while a menu is still modal.
        self._finish_menu(cancelled=True)
