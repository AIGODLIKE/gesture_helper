import time

import bpy
import gpu
from mathutils import Vector

from ..utils.public_gpu import PublicGpu, gpu_draw_begin, gpu_draw_end
from ..utils.color import color_to_srgb


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
    __active_draw_instances__ = {}
    # A normal gesture removes its GPU handler before dispatching the final
    # operator.  Keep a lightweight finishing marker so panel draws remain on
    # the paused path until that dispatch has completed.
    __finishing_draw_instances__ = {}

    def mark_modal_finishing(self) -> None:
        """Keep heavy editor panels paused during final modal dispatch."""
        GestureGpuDraw.__finishing_draw_instances__[id(self)] = self

    def clear_modal_finishing(self) -> None:
        """Release the final-dispatch pause marker."""
        finishing = GestureGpuDraw.__finishing_draw_instances__.pop(id(self), None)
        if finishing is None:
            return
        session = getattr(self, "session", None)
        if session is not None:
            from ..utils.ui_draw_sync import release_gesture_panel_state
            release_gesture_panel_state(session)

    @staticmethod
    def _context_instance():
        area = bpy.context.area
        if area is None:
            return None
        try:
            return GestureGpuDraw.__active_draw_instances__.get(area.as_pointer())
        except ReferenceError:
            return None

    @staticmethod
    def _gpu_draw_handler():
        inst = GestureGpuDraw._context_instance()
        if inst is None:
            return
        try:
            inst.__gpu_draw__()
        except ReferenceError:
            ...

    @staticmethod
    def _gpu_debug_draw_handler():
        inst = GestureGpuDraw._context_instance()
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
                session = getattr(self, "session", None)
                if session is not None and getattr(session, "draw_ctx", None) is None:
                    refresh_draw_frame_context(session, self)
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
        self.clear_modal_finishing()
        area_key = self.area.as_pointer()
        self._gesture_draw_area_key = area_key
        existing = GestureGpuDraw.__active_draw_instances__.get(area_key)
        identifier = str(getattr(self, "bl_idname", "")).casefold()
        existing_identifier = str(
            getattr(existing, "bl_idname", "")
        ).casefold()
        # Capture the visible panel before replacing an active preview. Closing
        # the preview clears SessionState, but the disabled row must keep the
        # exact label/button content that was visible at gesture entry.
        self._capture_modal_panel_state()
        if (
                existing is not None
                and existing is not self
                and identifier in {"wm.gesture_operator", "wm_ot_gesture_operator"}
                and existing_identifier in {"wm.gesture_preview", "wm_ot_gesture_preview"}
        ):
            # Preview and a real gesture cannot share one draw slot. End the
            # preview through its normal cleanup so its modal handler and
            # SessionState do not survive underneath the real gesture.
            try:
                existing.__exit_modal__()
            except Exception:
                GestureGpuDraw.__active_draw_instances__.pop(area_key, None)
        GestureGpuDraw.__active_draw_instances__[area_key] = self
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

        # Drop any pending N-panel keymap/operator sync so it cannot key_restart
        # mid-draw. Rebuild the UI region once at modal entry so the original
        # layout can be shown disabled; ordinary mouse moves only redraw the
        # gesture WINDOW region and leave this frozen layout untouched.
        from ..utils.ui_draw_sync import cancel_all, tag_gesture_ui_regions
        cancel_all()
        tag_gesture_ui_regions()
        self._tag_redraw_gesture_screen()

    def _capture_modal_panel_state(self) -> None:
        """Capture panel-only state before the gesture owns UI redraws.

        ``GestureModalEventPanel.poll`` normally resolves the selected element
        through the live RNA store. During a gesture that lookup can rebuild
        transient selection/proxy state while input is being dispatched. Keep
        the visibility and element used by the already-visible panel on the
        session instead; it is discarded with the session after modal exit.
        """
        identifier = str(getattr(self, "bl_idname", "")).casefold()
        if identifier not in {"wm.gesture_operator", "wm_ot_gesture_operator"}:
            return
        session = getattr(self, "session", None)
        if session is None:
            return
        try:
            active_gesture = self.pref.active_gesture
            active = self.pref.active_element
            visible = bool(active is not None and active.operator_is_modal)
        except (AttributeError, KeyError, ReferenceError, RuntimeError, TypeError):
            active_gesture = None
            active = None
            visible = False
        try:
            from ..utils.session_state import SessionState
            preview_active = bool(SessionState.gesture_preview_active)
            preview_scope = str(SessionState.gesture_preview_scope or '')
        except (AttributeError, ImportError, ReferenceError, RuntimeError, TypeError):
            preview_active = False
            preview_scope = ''
        session._frozen_active_gesture = active_gesture
        session._frozen_active_element = active
        session._frozen_preview_active = preview_active
        session._frozen_preview_scope = preview_scope
        session._modal_event_panel_element = active if visible else None
        from ..utils.ui_draw_sync import set_frozen_ui_selection
        session._frozen_ui_selection_key = set_frozen_ui_selection(
            active_gesture,
            active,
            area=getattr(session, "area", None),
        )

    @classmethod
    def _remove_all_draw_handlers(cls):
        """Remove every registered GPU draw handler and reset counters."""
        from ..utils.public import tag_redraw as tag_redraw_all

        GestureGpuDraw.__active_draw_instances__.clear()
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

    def unregister_draw(self):
        """Cancel GPU draw handler when the last modal session ends."""
        from ..utils.public import tag_redraw as tag_redraw_all
        from ..utils.ui_draw_sync import tag_gesture_ui_regions

        key = getattr(self, '_gesture_draw_area_key', None)
        if key is None:
            try:
                key = self.area.as_pointer()
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                key = None
        if key is not None and GestureGpuDraw.__active_draw_instances__.get(key) is self:
            GestureGpuDraw.__active_draw_instances__.pop(key, None)
        self._gesture_draw_area_key = None
        if id(self) not in GestureGpuDraw.__finishing_draw_instances__:
            from ..utils.ui_draw_sync import release_gesture_panel_state
            release_gesture_panel_state(getattr(self, "session", None))
            # The owner area can live in a different window from the current
            # bpy.context window during deactivation/system cancellation.
            tag_gesture_ui_regions()
        if GestureGpuDraw.__active_draw_instances__:
            # Must not call cls.tag_redraw() — subclasses override it as an
            # instance method (Blender 4.2 / 5.x both).
            tag_redraw_all()
            return
        self._remove_all_draw_handlers()

    @classmethod
    def force_unregister_draw(cls):
        """Remove all GPU draw handlers (call on add-on unregister)."""
        cls._remove_all_draw_handlers()
        from ..utils.ui_draw_sync import (
            clear_frozen_ui_selections,
            invalidate_playback_panel_state,
        )
        # This is add-on teardown, so all gesture snapshots can be discarded;
        # normal modal completion uses the per-session path above and never
        # touches another window's explicit property-drag snapshot.
        clear_frozen_ui_selections()
        invalidate_playback_panel_state()
        cls.__finishing_draw_instances__.clear()

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
        from ..utils.blf_text import measure_text
        for (el, pos) in zip(tree.child_element, tree.points_list):
            with gpu.matrix.push_pop():
                gpu.matrix.translate(pos)
                if not self.operator_gesture:
                    return
                text = self.operator_gesture.name if (el is None) else el.name
                tn = __name_translate__(text)

                is_last = pos == tree.points_list[-1]
                # Metric line height keeps knot labels at a constant offset
                # regardless of which glyphs the name happens to contain.
                w, line_h = measure_text(tn, size)
                gpu.matrix.translate(Vector((-(w / 2), 0)))
                if is_last:
                    gpu.matrix.translate(Vector((0, -threshold)))
                else:
                    gpu.matrix.translate(Vector((0, -line_h)))

                self.draw_text(tn, size=size)

    def _draw_ui_scale(self) -> float:
        session = getattr(self, "session", None)
        draw_ctx = getattr(session, "draw_ctx", None) if session is not None else None
        if draw_ctx is not None:
            return draw_ctx.ui_scale
        return bpy.context.preferences.view.ui_scale

    def _draw_empty_state(self, text: str, *, warning: bool = False) -> None:
        """Draw a compact Blender-style status row at the gesture center."""
        from ..utils.blf_text import measure_text

        scale = self._draw_ui_scale()
        size = max(10, round(self.draw_property.text_gpu_draw_size * scale * 0.82))
        text_w, text_h = measure_text(text, size)
        pad_x = max(8.0, 8.0 * scale)
        pad_y = max(5.0, 5.0 * scale)
        badge = max(16.0, text_h + 2.0 * scale)
        gap = max(6.0, 6.0 * scale)
        width = text_w + pad_x * 2.0 + badge + gap
        height = max(text_h + pad_y * 2.0, badge + pad_y * 2.0)
        draw = self.draw_property
        stroke = draw.status_warning_color if warning else draw.outline_active_color

        self.draw_rounded_rectangle_outlined(
            (0.0, 0.0),
            fill=draw.background_child_color,
            stroke=stroke,
            radius=min(5.0 * scale, height * 0.2),
            width=width,
            height=height,
            line_width=max(0.75, float(draw.outline_width) * scale),
        )
        left = -width * 0.5 + pad_x
        badge_color = draw.status_warning_color if warning else draw.background_child_active_color
        self.draw_rounded_rectangle_area(
            (left + badge * 0.5, 0.0),
            color=badge_color,
            radius=min(3.0 * scale, badge * 0.22),
            width=badge,
            height=badge,
        )
        mark = "!" if warning else "i"
        mark_w, mark_h = measure_text(mark, size)
        self.draw_text(
            mark,
            position=(left + (badge - mark_w) * 0.5, mark_h * 0.5),
            size=size,
            color=(1.0, 1.0, 1.0, 0.96),
        )
        self.draw_text(
            text,
            position=(left + badge + gap, text_h * 0.5),
            size=size,
            color=color_to_srgb(draw.text_default_color),
        )

    def _runtime_annotation_anchor(self, element):
        """Prefer the hovered row, then fall back to the radial item button."""
        from ..element.extension_hit import point_in_rect

        draw_ctx = getattr(self.session, 'draw_ctx', None)
        mouse = getattr(draw_ctx, 'mouse_region', None)
        row_rect = getattr(element, 'extension_by_child_draw_area', None)
        if point_in_rect(mouse, row_rect):
            return row_rect
        return getattr(element, 'item_draw_area', None) or row_rect

    def gpu_draw_runtime_annotation(self, region) -> None:
        """Draw delayed native RNA metadata and diagnostics for the hover."""
        if not self.session.phase.shows_radial_ui:
            return
        state = getattr(self.session, 'tooltip_state', None)
        element = getattr(state, 'target', None)
        tooltip = getattr(state, 'tooltip', None)
        if element is None or tooltip is None:
            return
        from .runtime_tooltip import tooltip_reveal

        reveal = tooltip_reveal(state, element)
        if reveal <= 0.0:
            return

        draw = self.draw_property
        if tooltip.color_role == 'error':
            accent = draw.status_error_color
        elif tooltip.color_role == 'warning':
            accent = draw.status_warning_color
        elif tooltip.color_role == 'disabled':
            accent = draw.status_disabled_color
        else:
            accent = draw.outline_active_color
        scale = self._draw_ui_scale()
        size = max(10, round(draw.text_gpu_draw_size * scale * 0.78))
        metadata = tuple(color_to_srgb(draw.text_default_color))
        metadata = (*metadata[:3], metadata[3] * 0.62)
        self.draw_runtime_tooltip(
            tooltip,
            anchor_rect=self._runtime_annotation_anchor(element),
            viewport_size=(region.width, region.height),
            size=size,
            scale=scale,
            fill=draw.background_child_color,
            stroke=accent,
            text_color=color_to_srgb(draw.text_default_color),
            metadata_color=metadata,
            issue_color=color_to_srgb(accent),
            reveal=reveal,
        )

    def gpu_draw_gesture(self):
        """Draw gesture overlay; extension_hover is pruned then re-seeded while painting."""
        if getattr(self, 'session', None) is None:
            return
        region = bpy.context.region
        if region is None:
            return

        scale = self._draw_ui_scale()
        session = self.session
        draw_ctx = getattr(session, "draw_ctx", None)
        threshold = draw_ctx.threshold if draw_ctx is not None else (
            self.gesture_property.threshold * scale
        )
        from ..src.translate import __name_translate__

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
                self._prepare_radial_overlay_offsets(draw_items, center, region)
                for item in draw_items:
                    with gpu.matrix.push_pop():
                        item.draw_gpu_item(self)

                og = self.operator_gesture
                if og is None or not len(og.element):
                    text = __name_translate__('This gesture has no elements. Please add some.')
                    self._draw_empty_state(text)
                elif not len(draw_items):
                    self._draw_empty_state(
                        __name_translate__('No gestures match the current conditions. Please add one.'),
                        warning=True,
                    )
        self.gpu_draw_runtime_annotation(region)

    def _prepare_radial_overlay_offsets(self, draw_items, center, region) -> None:
        """Measure and resolve root overlays only when their inputs change."""
        session = self.session
        if not draw_items:
            session.radial_auto_offsets = {}
            session._radial_offset_cache = None
            return

        draw_ctx = getattr(session, 'draw_ctx', None)
        radius = draw_ctx.gesture_radius if draw_ctx is not None else (
            self.gesture_property.radius * self._draw_ui_scale()
        )
        scale = draw_ctx.ui_scale if draw_ctx is not None else self._draw_ui_scale()

        def direction_order(item):
            try:
                return int(item.direction)
            except (AttributeError, TypeError, ValueError):
                return 99

        # Collision placement is independent of the cursor. Keep a compact
        # content/viewport key so ordinary hover motion can reuse the previous
        # result; derived-generation and poll revision cover structure and
        # property-value changes respectively.
        try:
            item_key = tuple(sorted(
                (
                    id(item),
                    str(getattr(item, 'direction', '')),
                    tuple(float(value) for value in getattr(item, 'overlay_offset', (0.0, 0.0))),
                )
                for item in draw_items
            ))
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            item_key = tuple(id(item) for item in draw_items)
        draw_key = (
            item_key,
            float(radius),
            float(scale),
            float(center.x),
            float(center.y),
            int(getattr(region, 'width', 0)),
            int(getattr(region, 'height', 0)),
        )
        from ..utils.public_cache import PublicCache
        cache_key = (
            PublicCache.__derived_generation__,
            getattr(session, '_poll_context_fingerprint', None),
            getattr(session, '_poll_context_revision', 0),
            draw_key,
        )
        cached = getattr(session, '_radial_offset_cache', None)
        if cached is not None and cached[0] == cache_key:
            session.radial_auto_offsets = cached[1]
            return

        records = []
        for item in sorted(draw_items, key=direction_order):
            item.ops = self
            try:
                base_bounds = item.radial_base_bounds(radius)
                manual = item.overlay_offset
                manual_bounds = (
                    base_bounds[0] + float(manual[0]),
                    base_bounds[1] + float(manual[1]),
                    base_bounds[2] + float(manual[0]),
                    base_bounds[3] + float(manual[1]),
                )
                records.append((
                    item,
                    manual_bounds,
                    tuple(item.radial_outward_vector),
                ))
            except (AttributeError, ReferenceError, TypeError, ValueError):
                # One malformed item must not suppress the rest of the overlay.
                continue

        if not records:
            session.radial_auto_offsets = {}
            session._radial_offset_cache = (cache_key, {})
            return

        inset = max(2.0, 4.0 * scale)
        viewport = (
            -float(center.x) + inset,
            -float(center.y) + inset,
            float(region.width) - float(center.x) - inset,
            float(region.height) - float(center.y) - inset,
        )
        from ..utils.radial_collision import resolve_radial_collisions
        offsets = resolve_radial_collisions(
            records,
            viewport=viewport,
            padding=max(2.0, 4.0 * scale),
        )
        session.radial_auto_offsets = offsets
        session._radial_offset_cache = (cache_key, offsets)

    def gpu_draw_direction_element(self):
        """Draw active direction element label."""
        element = self.direction_element
        scale = self._draw_ui_scale()

        if element and not self.session.phase.shows_radial_ui:
            size = self.pref.draw_property.text_gpu_draw_size * scale
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__mouse_position__)
                self.draw_text(element.name_translate, size=size)
