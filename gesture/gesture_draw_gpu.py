import time

import blf
import bpy
import gpu
from mathutils import Vector

from ..utils.public_gpu import PublicGpu, gpu_draw_begin, gpu_draw_end


class DrawDebug(PublicGpu):
    def gpu_draw_debug(self):
        try:
            if self.area is not None and bpy.context.area != self.area:
                return
            if self.is_window_region_type and self.pref.debug_property.debug_draw_gpu_mode:
                gpu_draw_begin()
                try:
                    self.__gpu_draw_debug__()
                finally:
                    gpu_draw_end()
        except ReferenceError:
            ...

    def __gpu_draw_debug__(self):
        """
        Debug overlay (poll may fail when drawn via Blender UI).
         data.append('direction_items:' + str({i: v.name for i, v in self.direction_items.items()}))
         data.append('direction_element:' + str(self.direction_element))
        :return:
        """
        area = bpy.context.area
        region = bpy.context.region
        data = ['area.x:' + str(area.x),
                'area.y:' + str(area.y),
                'area.height:' + str(area.height),
                'area.width:' + str(area.width),
                'area.type:' + str(area.type),
                '--',
                'region.x:' + str(region.x),
                'region.y:' + str(region.y),
                'region.height:' + str(region.height),
                'region.width:' + str(region.width),
                'region.type:' + str(region.type),
                '--',
                'mouse_prev_press_x:' + str(self.event.mouse_prev_press_x),
                'mouse_prev_press_y:' + str(self.event.mouse_prev_press_y),
                'mouse_region_x:' + str(self.event.mouse_region_x),
                'mouse_region_y:' + str(self.event.mouse_region_y),
                'mouse_prev_x:' + str(self.event.mouse_prev_x),
                'mouse_prev_y:' + str(self.event.mouse_prev_y),
                'mouse_x:' + str(self.event.mouse_x),
                'mouse_y:' + str(self.event.mouse_y),
                ]
        if area.type in ('VIEW_3D',):  # 'PREFERENCES'
            data.insert(0, '--')
            data.insert(0, 'event_count:' + str(self.event_count))
            data.insert(0, 'trajectory_mouse_move:' + str(len(self.trajectory_mouse_move)))
            data.insert(0, 'trajectory_mouse_move_time' + str(self.trajectory_mouse_move_time))
            data.insert(0, 'trajectory_tree:' + str(self.trajectory_tree))
            data.insert(0, '--')
            data.insert(0, 'extension_hover:' + str(self.extension_hover))
            data.insert(0, 'extension_element:' + str(self.extension_element))
            data.insert(0, 'extension_offset_distance:' + str(self.extension_offset_distance))
            if self.extension_element:
                data.insert(0, 'extension_offset_start_position:' + str(
                    getattr(self.extension_element, "extension_offset_start_position", None)))
                data.insert(0,
                            'extension_draw_area:' + str(getattr(self.extension_element, "extension_draw_area", None)))
            data.insert(0, '--')
            data.insert(0, 'direction_items:' + str(self.direction_items))
            data.insert(0, 'last_element:' + str(self.trajectory_tree.last_element))
            data.append('--')
            data.append('phase:' + str(self.session.phase))
            data.append('handoff:' + str(self.session.handoff))
            data.append('threshold_zone:' + str(self.session.snapshot.threshold_zone))
            data.append('is_draw_gpu:' + str(self.is_draw_gpu))
            data.append('is_window_region_type:' + str(self.is_window_region_type))
            data.append('--')
            data.append('__last_region_position__:' + str(self.__last_region_position__))
            data.append('__last_window_position__:' + str(self.__last_window_position__))
            data.append('__mouse_position__:' + str(self.__mouse_position__))
            data.append('--')
            data.append('angle:' + str(self.angle))
            data.append('angle_unsigned:' + str(self.angle_unsigned))
            data.append('distance:' + str(self.distance))
            data.append('direction:' + str(self.direction))
            data.append('find_closest_point:' + str(self.find_closest_point))
            data.append('last_move_mouse_timeout:' + str(self.last_move_mouse_timeout))
            data.append('last_mouse_mouse_time:' + str(self.last_mouse_mouse_time))
            data.append('time.time():' + str(time.time()))
            data.append('self.pref.gesture_property.timeout / 1000:' + str(self.pref.gesture_property.timeout / 1000))
            data.append('timeout:' + str(time.time() - self.last_mouse_mouse_time))
        text_size = 15
        self.draw_rectangle(0, 0, 400, len(data) * text_size)
        for index, i in enumerate(data):
            j = index + 1
            self.draw_text(text=i, position=(5, j * text_size), size=text_size)


class GestureGpuDraw(DrawDebug):
    __temp_draw_class__ = {}
    __temp_debug_draw_class__ = {}
    __modal_draw_count__ = 0
    __active_draw_instance__ = None

    @staticmethod
    def _gpu_draw_handler():
        inst = GestureGpuDraw.__active_draw_instance__
        if inst is None:
            return
        try:
            inst.__gpu_draw__()
        except ReferenceError:
            ...

    @staticmethod
    def _gpu_debug_draw_handler():
        inst = GestureGpuDraw.__active_draw_instance__
        if inst is None:
            return
        try:
            inst.gpu_draw_debug()
        except ReferenceError:
            ...

    def __gpu_draw__(self):
        """Main GPU draw entry — only paint in the area that owns this gesture."""
        try:
            # Space draw handlers run for every area of that type; always bind to
            # the invoke area so multi-window / multi-VIEW_3D layouts do not
            # duplicate or misplace the overlay.
            if self.area is not None and bpy.context.area != self.area:
                return
            if self.is_draw_gpu:
                from .draw_frame_context import refresh_draw_frame_context
                if getattr(self, "session", None) is not None:
                    refresh_draw_frame_context(self.session, self)
                gpu_draw_begin()
                try:
                    self.gpu_draw_gesture()
                finally:
                    gpu_draw_end()
        except ReferenceError:
            ...

    def register_draw(self):
        """
        bpy.types.Region.bl_rna.properties['type'].enum_items_static
        """
        space = bpy.context.space_data
        if not space:
            return
        cls = space.rna_type
        GestureGpuDraw.__active_draw_instance__ = self
        debug_gpu = False
        try:
            debug_gpu = bool(self.pref.debug_property.debug_draw_gpu_mode)
        except (AttributeError, KeyError, TypeError):
            ...

        if cls not in GestureGpuDraw.__temp_draw_class__:
            sub_class = {}
            for identifier in {'WINDOW'}:  # 'TOOLS', 'HEADER', 'UI',
                try:
                    sub_class[identifier] = cls.draw_handler_add(
                        GestureGpuDraw._gpu_draw_handler, (), identifier, 'POST_PIXEL')
                except Exception as e:
                    from ..utils.public import get_debug, debug_print
                    from ..utils.debug_util import debug_traceback, debug_trace_stack
                    debug_print(e.args, key='gpu')
                    if get_debug('gpu'):
                        debug_print(space, key='gpu')
                        debug_traceback(key='gpu')
                        debug_trace_stack(key='gpu')

            GestureGpuDraw.__temp_draw_class__[cls] = sub_class

        if debug_gpu and cls not in GestureGpuDraw.__temp_debug_draw_class__:
            debug_class = {}
            for identifier in {'WINDOW'}:
                try:
                    debug_class[identifier] = cls.draw_handler_add(
                        GestureGpuDraw._gpu_debug_draw_handler, (), identifier, 'POST_PIXEL')
                except Exception:
                    ...
            if debug_class:
                GestureGpuDraw.__temp_debug_draw_class__[cls] = debug_class

        GestureGpuDraw.__modal_draw_count__ += 1
        GestureGpuDraw.__active_draw_instance__ = self
        # Drop any pending N-panel keymap/operator sync so it cannot key_restart mid-draw.
        from ..utils.ui_draw_sync import cancel_all
        cancel_all()
        self._tag_redraw_gesture_screen()

    @classmethod
    def _remove_all_draw_handlers(cls):
        """Remove every registered GPU draw handler and reset counters."""
        from ..utils.public import tag_redraw as tag_redraw_all

        GestureGpuDraw.__modal_draw_count__ = 0
        GestureGpuDraw.__active_draw_instance__ = None
        for c, sub_class in GestureGpuDraw.__temp_draw_class__.items():
            for key, value in sub_class.items():
                try:
                    c.draw_handler_remove(value, key)
                except (ValueError, RuntimeError):
                    ...
        for c, debug_class in GestureGpuDraw.__temp_debug_draw_class__.items():
            for key, value in debug_class.items():
                try:
                    c.draw_handler_remove(value, key)
                except (ValueError, RuntimeError):
                    ...
        GestureGpuDraw.__temp_draw_class__.clear()
        GestureGpuDraw.__temp_debug_draw_class__.clear()
        tag_redraw_all()

    @classmethod
    def unregister_draw(cls):
        """Cancel GPU draw handler when the last modal session ends."""
        from ..utils.public import tag_redraw as tag_redraw_all

        GestureGpuDraw.__modal_draw_count__ = max(0, GestureGpuDraw.__modal_draw_count__ - 1)
        if GestureGpuDraw.__modal_draw_count__ > 0:
            # Must not call cls.tag_redraw() — subclasses override it as an
            # instance method (Blender 4.2 / 5.x both).
            tag_redraw_all()
            return
        cls._remove_all_draw_handlers()

    @classmethod
    def force_unregister_draw(cls):
        """Remove all GPU draw handlers (call on add-on unregister)."""
        cls._remove_all_draw_handlers()

    def gpu_draw_trajectory_mouse_move(self):
        """Draw mouse-move trajectory line."""
        draw = self.draw_property
        color = draw.trajectory_mouse_color
        scale = self._draw_ui_scale()
        line_width = draw.line_width * scale
        self.draw_2d_line(self.trajectory_mouse_move, color=color, line_width=line_width)

    def gpu_draw_trajectory_gesture_line(self):
        """Draw gesture trajectory polyline."""
        draw = self.draw_property
        scale = self._draw_ui_scale()
        color = draw.trajectory_gesture_color
        line_width = draw.line_width * scale
        self.draw_2d_line(self.trajectory_tree.points_list, color=color, line_width=line_width)

    def gpu_draw_trajectory_gesture_point(self):
        """Draw gesture trajectory origin/knot markers as circles."""
        tree = self.trajectory_tree
        if not tree.points_list:
            return
        scale = self._draw_ui_scale()
        size = max(6.0, 8.0 * scale)
        self.draw_2d_points(tree.points_list, point_size=size, color=(1.0, 1.0, 1.0, 1.0))

    def gpu_draw_last_item_name(self):
        """Draw last element label."""
        from ..src.translate import __name_translate__

        scale = self._draw_ui_scale()
        tree = self.trajectory_tree
        size = self.pref.draw_property.gesture_point_name_size * scale
        session = getattr(self, "session", None)
        draw_ctx = getattr(session, "draw_ctx", None) if session is not None else None
        threshold = draw_ctx.threshold if draw_ctx is not None else (
            self.pref.gesture_property.threshold * scale
        )
        for (el, pos) in zip(tree.child_element, tree.points_list):
            with gpu.matrix.push_pop():
                gpu.matrix.translate(pos)
                if not self.operator_gesture:
                    return
                text = self.operator_gesture.name if (el is None) else el.name
                tn = __name_translate__(text)

                is_last = pos == tree.points_list[-1]
                font_id = 0
                blf.size(font_id, size)
                (w, h) = blf.dimensions(font_id, tn)
                gpu.matrix.translate(Vector((-(w / 2), 0)))
                if is_last:
                    gpu.matrix.translate(Vector((0, -threshold)))
                else:
                    gpu.matrix.translate(Vector((0, -h)))

                self.draw_text(tn, size=size)

    def _draw_ui_scale(self) -> float:
        session = getattr(self, "session", None)
        draw_ctx = getattr(session, "draw_ctx", None) if session is not None else None
        if draw_ctx is not None:
            return draw_ctx.ui_scale
        return bpy.context.preferences.view.ui_scale

    def gpu_draw_gesture(self):
        """Draw gesture overlay; extension_hover is pruned then re-seeded while painting."""
        if getattr(self, 'session', None) is None:
            return
        region = bpy.context.region
        if region is None:
            return

        from .gesture_input import extension_rollback

        scale = self._draw_ui_scale()
        session = self.session
        draw_ctx = getattr(session, "draw_ctx", None)
        threshold = draw_ctx.threshold if draw_ctx is not None else (
            self.gesture_property.threshold * scale
        )
        from ..src.translate import __name_translate__

        # Prune stack from previous-frame hit boxes before redraw (legacy contract).
        for el in self.session.extension_hover:
            el.ops = self
        extension_rollback(self.session)
        from .draw_frame_context import refresh_draw_ctx_extension_flag
        refresh_draw_ctx_extension_flag(self.session, self)

        with gpu.matrix.push_pop():
            gpu.matrix.translate([-region.x, -region.y])
            self.gpu_draw_direction_element()
            if self.session.phase.shows_radial_ui:
                self.gpu_draw_trajectory_gesture_line()
            else:
                if self.is_window_region_type:
                    self.gpu_draw_trajectory_mouse_move()
            self.gpu_draw_trajectory_gesture_point()
            self.gpu_draw_last_item_name()
        if self.session.phase.shows_radial_ui:
            center = self.__circle_center_region_position__
            if center is None:
                return
            with gpu.matrix.push_pop():
                gpu.matrix.translate(center)
                if self.is_window_region_type:
                    # Two rings: start threshold + confirm (threshold + confirm delta).
                    # The band between them is the BEYOND transition zone.
                    draw = self.draw_property
                    ring_color = draw.text_default_color
                    ring_width = max(2.5, 2.75 * scale)
                    confirm_r = threshold + (
                        draw_ctx.threshold_confirm if draw_ctx is not None else (
                            self.gesture_property.threshold_confirm * scale
                        )
                    )
                    self.draw_circle(
                        (0, 0), threshold,
                        color=ring_color,
                        line_width=ring_width,
                        segments=72,
                    )
                    confirm_ring = (*ring_color[:3], 0.003)
                    self.draw_circle(
                        (0, 0), confirm_r,
                        color=confirm_ring,
                        line_width=max(1.5, 1.75 * scale),
                        segments=72,
                    )
                    angle = self.angle_unsigned
                    zone = self.session.snapshot.threshold_zone
                    if zone.is_beyond and angle is not None:
                        # Direction tip grows inside the start (inner) ring only —
                        # BEYOND maps progress → 0..threshold; CONFIRM sits on threshold.
                        tip_color = draw.trajectory_gesture_color
                        if zone.is_confirm:
                            tip_width = max(5.0, 5.5 * scale)
                            tip_r = threshold
                        else:
                            tip_width = max(2.5, 3.0 * scale)
                            tip_color = (
                                *tip_color[:3],
                                tip_color[3] * 0.55 if len(tip_color) > 3 else 0.55,
                            )
                            dist = float(self.session.snapshot.distance)
                            span = max(1e-6, confirm_r - threshold)
                            t = (dist - threshold) / span
                            tip_r = max(1.0, threshold * min(1.0, max(0.0, t)))
                        self.draw_arc(
                            (0, 0), tip_r, angle, 45,
                            color=tip_color,
                            line_width=tip_width,
                            segments=48,
                        )

                draw_items = list(self.direction_items.values())
                for item in draw_items:
                    with gpu.matrix.push_pop():
                        item.draw_gpu_item(self)

                og = self.operator_gesture
                if og is None or not len(og.element):
                    text = __name_translate__('This gesture has no elements. Please add some.')
                    self.draw_text(text)
                elif not len(draw_items):
                    self.draw_text(__name_translate__('No gestures match the current conditions. Please add one.'))

    def gpu_draw_direction_element(self):
        """Draw active direction element label."""
        element = self.direction_element
        scale = self._draw_ui_scale()

        if element and not self.session.phase.shows_radial_ui:
            size = self.pref.draw_property.text_gpu_draw_size * scale
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__mouse_position__)
                self.draw_text(element.name_translate, size=size)
