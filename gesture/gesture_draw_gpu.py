import blf
import bpy
import gpu
from bpy.app.translations import pgettext
from mathutils import Vector

from ..utils.public_gpu import PublicGpu


class DrawDebug(PublicGpu):
    def gpu_draw_debug(self):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        if self.is_window_region_type and self.pref.debug_property.debug_draw_gpu_mode:
            self.__gpu_draw_debug__()

    def __gpu_draw_debug__(self):
        """
        Bug pool 失效
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
            data.insert(0, 'trajectory_tree:' + str(self.trajectory_tree))
            data.append('--')
            data.append('operator_gesture:' + str(self.operator_gesture))
            data.append('is_draw_gpu:' + str(self.is_draw_gpu))
            data.append('is_draw_gesture:' + str(self.is_draw_gesture))
            data.append('is_window_region_type:' + str(self.is_window_region_type))
            data.append('is_beyond_threshold:' + str(self.is_beyond_threshold))
            data.append('is_beyond_threshold_confirm:' + str(self.is_beyond_threshold_confirm))
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
            data.append('operator_time:' + str(self.operator_time))
        self.draw_rectangle(0, 0, 400, len(data) * 30)
        for index, i in enumerate(data):
            j = index + 1
            self.draw_text((5, 30 * j), text=i)


class GestureGpuDraw(DrawDebug):
    __temp_draw_class__ = {}
    __temp_debug_draw_class__ = {}

    def __gpu_draw__(self):
        """绘制主入口"""
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)

        if len(bpy.context.screen.areas) > 8:
            if bpy.context.area != self.area:
                return
        if self.is_draw_gpu:
            self.gpu_draw_gesture()

    @staticmethod
    def refresh_space():
        return list(getattr(bpy.types, i) for i in dir(bpy.types) if 'Space' in i)

    @classmethod
    def space_subclasses(cls):
        cls.refresh_space()
        sub = bpy.types.Space.__subclasses__()
        return sub

    def register_draw(self):
        """
        bpy.types.Region.bl_rna.properties['type'].enum_items_static
        """
        if not GestureGpuDraw.__temp_draw_class__:
            # for cls in self.space_subclasses():
            space = bpy.context.space_data
            if space:
                cls = space.rna_type.bl_rna
                sub_class = {}
                debug_class = {}
                for identifier in {'WINDOW'}:  # 'TOOLS', 'HEADER', 'UI',
                    try:
                        sub_class[identifier] = cls.draw_handler_add(self.__gpu_draw__, (), identifier, 'POST_PIXEL')
                        debug_class[identifier] = cls.draw_handler_add(self.gpu_draw_debug, (), identifier,
                                                                       'POST_PIXEL')
                    except Exception as e:
                        if self.is_debug:
                            print(e.args)
                GestureGpuDraw.__temp_draw_class__[cls] = sub_class
                GestureGpuDraw.__temp_debug_draw_class__[cls] = debug_class

                self.tag_redraw()

    @classmethod
    def unregister_draw(cls):
        """取消绘制"""
        for c, sub_class in GestureGpuDraw.__temp_draw_class__.items():
            for key, value in sub_class.items():
                c.draw_handler_remove(value, key)
        for c, debug_class in GestureGpuDraw.__temp_debug_draw_class__.items():
            for key, value in debug_class.items():
                c.draw_handler_remove(value, key)
        GestureGpuDraw.__temp_draw_class__.clear()
        GestureGpuDraw.__temp_debug_draw_class__.clear()
        cls.tag_redraw()

    def gpu_draw_trajectory_mouse_move(self):
        """绘制轨迹鼠标移动的线"""
        draw = self.draw_property
        color = draw.trajectory_mouse_color
        self.draw_2d_line(self.trajectory_mouse_move, color=color, line_width=draw.line_width)

    def gpu_draw_trajectory_gesture_line(self):
        """绘制手势的轨迹线"""
        draw = self.draw_property
        color = draw.trajectory_gesture_color
        self.draw_2d_line(self.trajectory_tree.points_list, color=color, line_width=draw.line_width)

    def gpu_draw_trajectory_gesture_point(self):
        """绘制手势的轨迹点"""
        tree = self.trajectory_tree
        self.draw_2d_points(tree.points_list)

    def gpu_draw_last_item_name(self):
        """绘制最后一个元素名称"""
        tree = self.trajectory_tree
        size = self.pref.draw_property.gesture_point_name_size
        for (el, pos) in zip(tree.child_element, tree.points_list):
            with gpu.matrix.push_pop():
                gpu.matrix.translate(pos)
                text = self.operator_gesture.name if (el is None) else el.name
                tn = self.__tn__(text)

                is_last = pos == tree.points_list[-1]
                font_id = 0
                blf.size(font_id, size)
                (w, h) = blf.dimensions(font_id, tn)
                gpu.matrix.translate(Vector((-(w / 2), 0)))
                if is_last:
                    gpu.matrix.translate(Vector((0, -self.pref.gesture_property.threshold)))
                else:
                    gpu.matrix.translate(Vector((0, -h)))

                self.draw_text([0, 0], text=tn, size=size)

    def gpu_draw_gesture(self):
        """绘制手势"""
        gp = self.gesture_property

        region = bpy.context.region
        with gpu.matrix.push_pop():
            gpu.matrix.translate([-region.x, -region.y])
            self.gpu_draw_direction_element()
            if self.is_draw_gesture:
                self.gpu_draw_trajectory_gesture_line()
            else:
                if self.is_window_region_type:
                    self.gpu_draw_trajectory_mouse_move()
            self.gpu_draw_trajectory_gesture_point()
            self.gpu_draw_last_item_name()
        if self.is_draw_gesture:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__last_region_position__)
                if self.is_window_region_type:
                    self.draw_circle((0, 0), gp.threshold, line_width=2, segments=64)
                    if self.is_beyond_threshold:
                        self.draw_arc((0, 0), gp.threshold, self.angle_unsigned, 45, line_width=10, segments=64)
                draw_items = self.direction_items.values()
                for d in draw_items:
                    d.draw_gpu_item(self)
                if not len(draw_items):
                    self.draw_text((0, 0), pgettext('No gestures, please add'))

    def gpu_draw_direction_element(self):
        """绘制活动方向元素名称"""
        element = self.direction_element

        if element and not self.is_draw_gesture:
            size = self.pref.draw_property.text_gpu_draw_size
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.__mouse_position__)
                self.draw_text((0, 0), text=element.name_translate, size=size)
