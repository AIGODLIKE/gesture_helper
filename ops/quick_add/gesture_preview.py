import time

import bpy
from bpy.props import EnumProperty, StringProperty
from mathutils import Vector

from .draw_gpu import DrawGpu
from ...gesture.element_preview import ElementPreviewAdapter
from ...gesture.gesture_draw_gpu import GestureGpuDraw
from ...gesture.gesture_handle import GestureHandle
from ...gesture.gesture_input import (
    clear_gesture_item_memos,
    refresh_poll_context_fingerprint,
    refresh_snapshot,
    update_extension_hover,
)
from ...gesture.gesture_runtime import GestureRuntimeMixin
from ...gesture.gesture_session import GestureSession
from ...gesture.menu import GestureMenuRuntime
from ...gesture.preview_input import PreviewGestureInputProcessor
from ...utils.adapter import operator_setattr
from ...utils.public import PublicOperator
from ...utils.session_state import SessionState


PREVIEW_SCOPE_ITEMS = (
    ('GESTURE', 'Gesture', 'Preview the active gesture or menu'),
    ('ELEMENT', 'Element', 'Preview the active element and its subtree'),
)


def _rna_identity(value) -> int:
    if value is None:
        return 0
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


class GesturePreview(
        PublicOperator,
        GestureHandle,
        GestureGpuDraw,
        GestureRuntimeMixin,
        GestureMenuRuntime,
):
    """One read-only preview lifecycle with interchangeable render backends."""

    bl_idname = 'wm.gesture_preview'
    bl_label = 'Gesture Preview'
    bl_description = 'Preview the active gesture, menu, or selected element without running it'

    gesture: StringProperty(options={'HIDDEN'})
    scope: EnumProperty(items=PREVIEW_SCOPE_ITEMS, default='GESTURE', options={'HIDDEN'})

    # Menu previews must not replace or publish the real persistent-menu runtime.
    _active_by_window = {}
    _active_by_area = {}
    _draw_handles = {}
    _tracks_session_menu_state = False
    preview_read_only = True

    offset = Vector((300, 0))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        operator_setattr(self, 'session', GestureSession())
        operator_setattr(self, 'points_list', None)
        operator_setattr(self, 'mouse_position', None)
        operator_setattr(self, '__difference_mouse__', None)
        operator_setattr(self, 'start_mouse_position', None)
        operator_setattr(self, 'offset_position', Vector((0, 0)))
        operator_setattr(self, 'gpu', DrawGpu())
        operator_setattr(self, '_input_processor', PreviewGestureInputProcessor())
        operator_setattr(self, '_element_preview_adapter', ElementPreviewAdapter())

        operator_setattr(self, '_preview_renderer', '')
        operator_setattr(self, '_preview_target_key', None)
        operator_setattr(self, '_preview_close_requested', False)
        operator_setattr(self, '_preview_cleaned', False)
        operator_setattr(self, '_preview_gpu_registered', False)
        operator_setattr(self, '_preview_menu_registered', False)
        operator_setattr(self, '_preview_event_timer', None)
        operator_setattr(self, '_preview_window_manager', None)
        operator_setattr(self, '_preview_window', None)

        operator_setattr(self, '_menu_area', None)
        operator_setattr(self, '_menu_screen', None)
        operator_setattr(self, '_menu_window', None)
        operator_setattr(self, '_menu_gesture_ref', None)
        operator_setattr(self, '_menu_anchor', (0.0, 0.0))
        operator_setattr(self, '_menu_centered', True)
        operator_setattr(self, '_menu_panels', [])
        operator_setattr(self, '_menu_open_path', [])
        operator_setattr(self, '_menu_hovered_row', None)
        operator_setattr(self, '_menu_layout_key', None)
        operator_setattr(self, '_menu_layout_dirty', True)
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, '_menu_draw_count', 0)
        operator_setattr(self, '_menu_last_draw_error', '')

    @classmethod
    def poll(cls, context):
        if SessionState.gesture_preview_active:
            cls.poll_message_set('A preview is already running')
            return False
        try:
            from ...utils.public import get_pref

            active = get_pref().active_gesture
        except (KeyError, AttributeError, ReferenceError, RuntimeError):
            active = None
        if active is None:
            cls.poll_message_set('Select a gesture to preview')
            return False
        area = getattr(context, 'area', None)
        if (area is None or area.type != 'VIEW_3D') and cls.find_view3d_context(context) is None:
            cls.poll_message_set('Open a 3D View to preview this gesture')
            return False
        return True

    @staticmethod
    def find_view3d_context(context) -> dict | None:
        """Return a VIEW_3D WINDOW override without a temporary screen."""
        wm = getattr(context, 'window_manager', None)
        if wm is None:
            return None
        current_window = getattr(context, 'window', None)
        try:
            windows = list(wm.windows)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return None
        if current_window in windows:
            windows.remove(current_window)
            windows.insert(0, current_window)
        for window in windows:
            try:
                areas = window.screen.areas
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                continue
            for area in areas:
                if area.type != 'VIEW_3D':
                    continue
                region = next((item for item in area.regions if item.type == 'WINDOW'), None)
                if region is not None:
                    return {'window': window, 'area': area, 'region': region}
        return None

    @property
    def mouse_is_in_extension_any_area(self) -> bool:
        if self._preview_renderer == 'MENU':
            return True
        draw_ctx = getattr(self.session, 'draw_ctx', None)
        return bool(draw_ctx is not None and draw_ctx.in_extension_ui)

    @property
    def is_exit(self):
        event = self.event
        if event.type == 'ESC' and event.value == 'PRESS':
            return True
        return self.is_right_mouse and self._mouse_in_window_region(event)

    def _mouse_in_window_region(self, event) -> bool:
        area = self.session.area
        if area is None:
            return True
        from ...utils.region_mouse import find_window_region

        try:
            region = find_window_region(area)
        except ReferenceError:
            return True
        if region is None:
            return True
        return (
            region.x <= event.mouse_x <= region.x + region.width
            and region.y <= event.mouse_y <= region.y + region.height
        )

    def _preview_anchor(self, context, event) -> Vector:
        from ...utils.region_mouse import find_window_region

        region = find_window_region(context.area)
        if region is None:
            return Vector((event.mouse_x, event.mouse_y))
        return Vector((region.x + region.width * 0.5, region.y + region.height * 0.5))

    def _owner_area_is_live(self) -> bool:
        area = self.session.area
        screen = self.session.screen
        window = self._preview_window
        if area is None or screen is None or window is None:
            return False
        try:
            return window.screen == screen and any(candidate == area for candidate in screen.areas)
        except (AttributeError, ReferenceError, RuntimeError, TypeError):
            return False

    def _active_preview_target(self):
        try:
            if self.scope == 'ELEMENT':
                return 'ELEMENT', self.pref.active_element
            gesture = self.pref.active_gesture
        except (AttributeError, KeyError, ReferenceError, RuntimeError):
            return None, None
        if gesture is None:
            return None, None
        try:
            renderer = 'MENU' if gesture.gesture_type == 'MENU' else 'RADIAL'
        except (AttributeError, ReferenceError, RuntimeError):
            return None, None
        return renderer, gesture

    def _enter_radial_renderer(self, context, event, gesture) -> bool:
        anchor = self._preview_anchor(context, event)
        self.gesture = gesture.name
        self.session.reset(event, context.area, context.screen, self.gesture)
        self.start_mouse_position = anchor.copy()
        self.offset_position = anchor.copy()
        self.session._gesture_circle_center = anchor.copy()
        self.session._last_trajectory_mouse = anchor.copy()
        self.trajectory_tree.append(None, anchor.copy())
        self.trajectory_mouse_move.append(anchor.copy())
        self.trajectory_mouse_move_time.append(time.time())
        self._schedule_gesture_timeout_timer()
        refresh_snapshot(self.session, self)
        self.trajectory_event_update(context, event)
        self.register_draw()
        operator_setattr(self, '_preview_gpu_registered', True)
        operator_setattr(
            self,
            '_preview_target_key',
            ('RADIAL', _rna_identity(gesture), gesture.name),
        )
        return True

    def _enter_menu_renderer(self, context, event, gesture) -> bool:
        self.gesture = gesture.name
        self.session.reset(event, context.area, context.screen, self.gesture)
        operator_setattr(self, '_menu_area', context.area)
        operator_setattr(self, '_menu_screen', context.screen)
        operator_setattr(self, '_menu_window', context.window)
        operator_setattr(self, '_menu_gesture_ref', gesture)
        operator_setattr(self, '_menu_open_path', [])
        operator_setattr(self, '_menu_hovered_row', None)
        operator_setattr(self, '_menu_layout_key', None)
        operator_setattr(self, '_menu_layout_dirty', True)
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_menu_runtime_cleaned', False)
        operator_setattr(self, 'event', event)
        if not self._register_menu_runtime(context):
            return False
        operator_setattr(self, '_preview_menu_registered', True)
        self._ensure_layout(force=True)
        operator_setattr(
            self,
            '_preview_target_key',
            ('MENU', _rna_identity(gesture), gesture.name),
        )
        return True

    def _enter_element_renderer(self, context, event, element) -> bool:
        gesture = None
        try:
            gesture = element.parent_gesture if element is not None else self.pref.active_gesture
        except (AttributeError, ReferenceError, RuntimeError):
            ...
        self.gesture = gesture.name if gesture is not None else ''
        self.session.reset(event, context.area, context.screen, self.gesture)
        anchor = self._preview_anchor(context, event)
        self.session._gesture_circle_center = anchor.copy()
        self.session._last_trajectory_mouse = anchor.copy()
        self.trajectory_tree.append(None, anchor.copy())
        self.session.advance_to_ui_visible()
        self.register_draw()
        operator_setattr(self, '_preview_gpu_registered', True)
        self._sync_element_target(element, force=True)
        return True

    def _enter_renderer(self, context, event, renderer, target) -> bool:
        operator_setattr(self, '_preview_renderer', renderer)
        if renderer == 'RADIAL':
            return self._enter_radial_renderer(context, event, target)
        if renderer == 'MENU':
            return self._enter_menu_renderer(context, event, target)
        return self._enter_element_renderer(context, event, target)

    def _leave_renderer(self) -> None:
        renderer = self._preview_renderer
        if renderer in {'RADIAL', 'ELEMENT'}:
            if self._preview_gpu_registered:
                operator_setattr(self, '_preview_gpu_registered', False)
                self.unregister_draw()
            self._cancel_gesture_timeout_timer()
            clear_gesture_item_memos(self.session, self)
        elif renderer == 'MENU' and self._preview_menu_registered:
            operator_setattr(self, '_preview_menu_registered', False)
            operator_setattr(self, '_menu_runtime_cleaned', True)
            self._unregister_menu_runtime()
        operator_setattr(self, '_menu_close_requested', False)
        operator_setattr(self, '_preview_renderer', '')
        operator_setattr(self, '_preview_target_key', None)

    def _switch_renderer(self, context, event, renderer, target) -> bool:
        self._leave_renderer()
        return self._enter_renderer(context, event, renderer, target)

    def _sync_radial_target(self, gesture) -> None:
        key = ('RADIAL', _rna_identity(gesture), gesture.name)
        if key == self._preview_target_key:
            return
        tree = self.trajectory_tree
        center = tree.points_list[0].copy() if tree.points_list else self.offset_position.copy()
        event = self.session.event
        area = self.session.area
        screen = self.session.screen
        self._cancel_gesture_timeout_timer()
        clear_gesture_item_memos(self.session, self)
        self.gesture = gesture.name
        self.session.reset(event, area, screen, self.gesture)
        self.session._gesture_circle_center = center.copy()
        self.session._last_trajectory_mouse = center.copy()
        self.trajectory_tree.append(None, center.copy())
        self.trajectory_mouse_move.append(center.copy())
        self.trajectory_mouse_move_time.append(0.0)
        self._schedule_gesture_timeout_timer()
        refresh_snapshot(self.session, self)
        operator_setattr(self, '_preview_target_key', key)
        self.tag_redraw()

    def _sync_menu_target(self, gesture) -> None:
        key = ('MENU', _rna_identity(gesture), gesture.name)
        if key != self._preview_target_key:
            self.gesture = gesture.name
            operator_setattr(self, '_menu_gesture_ref', gesture)
            operator_setattr(self, '_menu_open_path', [])
            operator_setattr(self, '_menu_hovered_row', None)
            operator_setattr(self, '_menu_layout_key', None)
            operator_setattr(self, '_menu_layout_dirty', True)
            operator_setattr(self, '_preview_target_key', key)
        self._tag_menu_redraw()

    def _sync_element_target(self, element, *, force=False) -> None:
        from ...utils.public_cache import PublicCache, PublicCacheFunc

        gesture = None
        try:
            gesture = element.parent_gesture if element is not None else self.pref.active_gesture
        except (AttributeError, ReferenceError, RuntimeError):
            ...
        if gesture is not None:
            PublicCacheFunc.ensure_gesture_structure(gesture)
        key = (
            'ELEMENT',
            _rna_identity(gesture),
            _rna_identity(element),
            PublicCache.__structure_generation__,
            PublicCache.__derived_generation__,
        )
        if not force and key == self._preview_target_key:
            return

        canonical = self.session.canonical_element(element) if element is not None else None
        self.gesture = gesture.name if gesture is not None else ''
        self.session.layout_token = object()
        self.session.draw_ctx = None
        self.session._element_status_cache = None
        self.session._poll_context_fingerprint = None
        self.session._poll_context_serial = -1
        clear_gesture_item_memos(self.session, self)
        self._element_preview_adapter.set_element(canonical, self.session)
        self.session.snapshot.direction_element = None
        self.session.snapshot.direction_items = {}
        self.session.snapshot.extension_element = self._element_preview_adapter
        self.session.extension_hover = self._element_preview_adapter.initial_hover_path()
        self.session.advance_to_ui_visible()
        operator_setattr(self, '_preview_target_key', key)
        self.tag_redraw()

    def _sync_preview_target(self, context, event) -> bool:
        renderer, target = self._active_preview_target()
        if self.scope == 'GESTURE' and target is None:
            return False
        if renderer != self._preview_renderer:
            return self._switch_renderer(context, event, renderer, target)
        if renderer == 'RADIAL':
            self._sync_radial_target(target)
        elif renderer == 'MENU':
            self._sync_menu_target(target)
        else:
            self._sync_element_target(target)
        return True

    def _add_preview_event_timer(self, context) -> None:
        wm = context.window_manager
        timer = wm.event_timer_add(0.15, window=context.window)
        operator_setattr(self, '_preview_window_manager', wm)
        operator_setattr(self, '_preview_event_timer', timer)

    def _remove_preview_event_timer(self) -> None:
        timer = self._preview_event_timer
        wm = self._preview_window_manager
        operator_setattr(self, '_preview_event_timer', None)
        operator_setattr(self, '_preview_window_manager', None)
        if timer is None or wm is None:
            return
        try:
            wm.event_timer_remove(timer)
        except (ReferenceError, RuntimeError, ValueError):
            ...

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        scope = self.scope if self.scope in {'GESTURE', 'ELEMENT'} else 'GESTURE'
        self.scope = scope
        renderer, target = self._active_preview_target()
        if scope == 'GESTURE' and target is None:
            self.report({'WARNING'}, 'Select a gesture to preview')
            return {'CANCELLED'}
        if scope == 'ELEMENT' and target is None:
            self.report({'WARNING'}, 'Select an element to preview')
            return {'CANCELLED'}

        area = getattr(context, 'area', None)
        if area is None or area.type != 'VIEW_3D':
            override = self.find_view3d_context(context)
            if override is None:
                self.report({'WARNING'}, 'Open a 3D View to preview this item')
                return {'CANCELLED'}
            try:
                with context.temp_override(**override):
                    result = bpy.ops.wm.gesture_preview(
                        'INVOKE_DEFAULT',
                        gesture=getattr(self.pref.active_gesture, 'name', ''),
                        scope=scope,
                    )
            except (AttributeError, RuntimeError, TypeError):
                self.report({'WARNING'}, 'Unable to start the preview in the 3D View')
                return {'CANCELLED'}
            operator_setattr(self, '_preview_cleaned', True)
            return {'FINISHED'} if result and 'RUNNING_MODAL' in result else result

        operator_setattr(self, '_preview_cleaned', False)
        operator_setattr(self, '_preview_close_requested', False)
        operator_setattr(self, '_preview_window', context.window)
        self.init_invoke(event)

        if not SessionState.begin_gesture_preview(self, scope):
            self.report({'WARNING'}, 'A preview is already running')
            return {'CANCELLED'}
        try:
            if not self._enter_renderer(context, event, renderer, target):
                raise RuntimeError('preview renderer registration failed')
            self._add_preview_event_timer(context)
            context.window_manager.modal_handler_add(self)
        except Exception:
            self.__exit_modal__()
            self.report({'WARNING'}, 'Unable to start the preview')
            return {'CANCELLED'}

        self._tag_preview_redraw()
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if self._preview_cleaned:
            return {'FINISHED'}
        if self._preview_close_requested:
            self.__exit_modal__()
            return {'FINISHED'}
        if not self._owner_area_is_live():
            self.__exit_modal__()
            return {'CANCELLED'}

        self.init_modal(event)
        if not self._sync_preview_target(context, event):
            self.__exit_modal__()
            return {'FINISHED'}
        if self.is_exit:
            self.__exit_modal__()
            return {'FINISHED'}

        if self._preview_renderer == 'RADIAL':
            return self._modal_radial(context, event)
        if self._preview_renderer == 'MENU':
            return self._modal_menu(event)
        return self._modal_element(event)

    def _modal_radial(self, context, event):
        self.trajectory_event_update(context, event)
        self.mouse_position = Vector((event.mouse_x, event.mouse_y))
        result = self.gpu.draw_run(self, event)
        if result:
            return result
        drag_result = self._radial_drag_event(event)
        if drag_result:
            return drag_result
        if event.type == 'TIMER':
            self.tag_redraw()
        return {'PASS_THROUGH'}

    def _modal_menu(self, event):
        operator_setattr(self, 'event', event)
        if event.type == 'MOUSEMOVE':
            if self._update_menu_hover(event):
                self._tag_menu_redraw()
            return {'PASS_THROUGH'}
        if event.type == 'TIMER':
            operator_setattr(self, '_menu_layout_dirty', True)
            self._tag_menu_redraw()
            return {'PASS_THROUGH'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._ensure_layout()
            if self._menu_close_hit(event):
                self.__exit_modal__()
                return {'FINISHED'}
            self._update_menu_hover(event)
            if self._menu_contains(self._menu_mouse(event)):
                return {'RUNNING_MODAL'}
        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            self._ensure_layout()
            if self._menu_contains(self._menu_mouse(event)):
                return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}

    def _modal_element(self, event):
        session = self.session
        session.event = event
        session.event_count += 1
        session._input_event_serial += 1
        refresh_poll_context_fingerprint(session)
        session.snapshot.mouse_window = Vector((event.mouse_x, event.mouse_y))
        session.draw_ctx = None
        from ...gesture.draw_frame_context import refresh_draw_frame_context

        refresh_draw_frame_context(session, self)
        before = tuple(session.extension_hover)
        update_extension_hover(session, self)
        from ...gesture.gesture_input import sync_runtime_tooltip

        tooltip_changed = sync_runtime_tooltip(session, self)
        if (
                before != tuple(session.extension_hover)
                or event.type == 'TIMER'
                or tooltip_changed
        ):
            self.tag_redraw()

        if event.type in {'LEFTMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            from ...element.extension_hit import stack_any_ui

            if stack_any_ui(session.extension_hover, self):
                return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}

    def cancel(self, _context):
        self.__exit_modal__()

    def _apply_trajectory_drag(self, diff: Vector) -> None:
        self.trajectory_tree.set_points(pos + diff for pos in self.points_list)
        last = self.trajectory_tree.last_point
        if last is not None:
            self.session._gesture_circle_center = last.copy()
            self.session._last_trajectory_mouse = last.copy()

    def _radial_drag_event(self, event):
        space = event.type == 'SPACE' and not event.alt and not event.ctrl and not event.shift
        moving = event.type == 'MOUSEMOVE' and event.type_prev == 'SPACE'
        if not (space or moving):
            return None
        if event.value == 'PRESS':
            self.__difference_mouse__ = self.start_mouse_position - self.mouse_position
            self.points_list = self.trajectory_tree.points_list
        elif event.value == 'RELEASE':
            next_difference = self.start_mouse_position - self.mouse_position
            diff = self.__difference_mouse__ - next_difference
            self._apply_trajectory_drag(diff)
            self.points_list = None
            self.__difference_mouse__ = None
        elif self.__difference_mouse__:
            next_difference = self.start_mouse_position - self.mouse_position
            diff = self.__difference_mouse__ - next_difference
            self.offset_position = self.mouse_position - diff
            self._apply_trajectory_drag(diff)
        return {'PASS_THROUGH', 'RUNNING_MODAL'}

    def __gpu_draw__(self):
        if self._preview_renderer == 'RADIAL':
            self.gpu.tips.__gpu_draw__()
            self.gpu.gesture_bpu.__gpu_draw__()
        GestureGpuDraw.__gpu_draw__(self)

    def gpu_draw_gesture(self):
        if self._preview_renderer != 'ELEMENT':
            return GestureGpuDraw.gpu_draw_gesture(self)
        region = bpy.context.region
        if region is None:
            return None
        self._element_preview_adapter.draw_centered(
            self,
            (float(region.width) * 0.5, float(region.height) * 0.5),
        )
        self.gpu_draw_runtime_annotation(region)
        return None

    def _tag_preview_redraw(self) -> None:
        if self._preview_renderer == 'MENU':
            self._tag_menu_redraw()
        else:
            self.tag_redraw()
        try:
            from ...utils.public import tag_redraw

            tag_redraw()
        except (AttributeError, ReferenceError, RuntimeError):
            ...

    def _request_preview_close(self) -> None:
        if self._preview_cleaned:
            return
        operator_setattr(self, '_preview_close_requested', True)
        operator_setattr(self, '_menu_close_requested', True)
        self._tag_preview_redraw()

    def _force_preview_cleanup(self) -> None:
        self.__exit_modal__()

    def __exit_modal__(self):
        if self._preview_cleaned:
            return
        operator_setattr(self, '_preview_cleaned', True)
        self._remove_preview_event_timer()
        self._leave_renderer()
        SessionState.end_gesture_preview(self)
        operator_setattr(self, '_preview_window', None)
        try:
            from ...utils.public import tag_redraw

            tag_redraw()
        except (AttributeError, ReferenceError, RuntimeError):
            ...


class GesturePreviewClose(PublicOperator):
    bl_idname = 'wm.gesture_preview_close'
    bl_label = 'Close Preview'
    bl_description = 'Close the active gesture or element preview'
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, _context):
        return SessionState.gesture_preview_active

    def execute(self, _context):
        if not SessionState.request_gesture_preview_close():
            return {'CANCELLED'}
        return {'FINISHED'}


class GesturePreviewFrozen(bpy.types.Operator):
    """Property-free stand-in for disabled preview buttons during a freeze."""

    bl_idname = 'wm.gesture_preview_frozen'
    bl_label = 'Gesture Preview'
    bl_options = {'INTERNAL'}

    def execute(self, _context):
        return {'CANCELLED'}
