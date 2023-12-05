# 显示操作符,
# 切换
import math
import time

import bpy
import gpu
from bpy.props import StringProperty, IntProperty, BoolProperty
from mathutils import Vector
from mathutils.kdtree import KDTree

from ..utils.public import PublicOperator, PublicProperty
from ..utils.public_gpu import PublicGpu


class GesturePointKDTree:

    def __init__(self, size=114):
        self.kd_tree = KDTree(size)
        self.child_element = []
        self.points_list = []
        self.time_list = []

    def __str__(self):
        return str(self.points_list) + str(self.child_element)

    def append(self, element, point: Vector):
        index = len(self.child_element)
        self.kd_tree.insert((*point, 0), index)
        self.points_list.append(point)
        self.child_element.append(element)
        self.time_list.append(time.time())

    def remove(self, index):
        val = index + 1
        self.child_element = self.child_element[:val]
        self.points_list = self.points_list[:val]
        self.time_list = self.time_list[:val]
        return self.child_element[-1]

    def __len__(self):
        return self.child_element.__len__()

    @property
    def trajectory(self):
        return self.points_list

    @property
    def last_element(self):
        if len(self.child_element):
            return self.child_element[-1]

    @property
    def last_point(self):
        if len(self.points_list):
            return self.points_list[-1]

    @property
    def last_time(self):
        if len(self.time_list):
            return self.time_list[-1]

    @property
    def first_time(self):
        if len(self.time_list):
            return self.time_list[0]


class GestureGpuDraw(PublicGpu, PublicOperator, PublicProperty
                     ):
    __temp_draw_class__ = {}

    @staticmethod
    def refresh_space():
        return list(getattr(bpy.types, i) for i in dir(bpy.types) if 'Space' in i)

    @classmethod
    def space_subclasses(cls):
        cls.refresh_space()
        sub = bpy.types.Space.__subclasses__()
        if bpy.types.SpaceConsole in sub:
            sub.remove(bpy.types.SpaceConsole)
        return sub

    def register_draw(self):
        if not GestureGpuDraw.__temp_draw_class__:
            print('register_draw')
            for cls in self.space_subclasses():
                sub_class = {}
                # bpy.types.Region.bl_rna.properties['type'].enum_items_static
                for identifier in {'WINDOW', 'HEADER', }:  # 'UI', 'TOOLS'
                    try:
                        sub_class[identifier] = cls.draw_handler_add(self.gpu_draw, (), identifier, 'POST_PIXEL')
                    except Exception as e:
                        ...
                GestureGpuDraw.__temp_draw_class__[cls] = sub_class
            self.tag_redraw()

    @classmethod
    def unregister_draw(cls):
        print('unregister_draw')
        for c, sub_class in GestureGpuDraw.__temp_draw_class__.items():
            for key, value in sub_class.items():
                c.draw_handler_remove(value, key)
        GestureGpuDraw.__temp_draw_class__.clear()
        cls.tag_redraw()

    def gpu_draw_trajectory_mouse_move(self):
        self.draw_2d_line(self.trajectory_mouse_move, (0.9, 0, 0, 1))

    def gpu_draw_trajectory_gesture_line(self):
        self.draw_2d_line(self.trajectory_tree.points_list, color=(0, 1, 0.5, 1), line_width=2)

    def gpu_draw_trajectory_gesture_point(self):
        self.draw_2d_points(self.trajectory_tree.points_list)

    def gpu_draw_debug(self):
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
                # '--',
                # 'mouse_prev_press_x:' + str(self.event.mouse_prev_press_x),
                # 'mouse_prev_press_y:' + str(self.event.mouse_prev_press_y),
                # 'mouse_region_x:' + str(self.event.mouse_region_x),
                # 'mouse_region_y:' + str(self.event.mouse_region_y),
                # 'mouse_prev_x:' + str(self.event.mouse_prev_x),
                # 'mouse_prev_y:' + str(self.event.mouse_prev_y),
                # 'mouse_x:' + str(self.event.mouse_x),
                # 'mouse_y:' + str(self.event.mouse_y),
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
            data.append('last_region_position:' + str(self.last_region_position))
            data.append('last_window_position:' + str(self.last_window_position))
            data.append('event_region_position:' + str(self.event_region_position))
            data.append('event_window_position:' + str(self.event_window_position))
            data.append('--')
            data.append('angle:' + str(self.angle))
            data.append('angle_unsigned:' + str(self.angle_unsigned))
            data.append('distance:' + str(self.distance))
            data.append('direction:' + str(self.direction))
            data.append('direction_items:' + str({i: v.name for i, v in self.direction_items.items()}))
            data.append('direction_element:' + str(self.direction_element))
            data.append('find_closest_point:' + str(self.find_closest_point))
            data.append('operator_time:' + str(self.operator_time))
        self.draw_rectangle(0, 0, 400, len(data) * 30)
        for index, i in enumerate(data):
            j = index + 1
            self.draw_text((5, 30 * j), text=i)

    def gpu_draw_gesture(self):
        gp = self.gesture_property

        region = bpy.context.region
        with gpu.matrix.push_pop():
            gpu.matrix.translate([-region.x, -region.y])
            self.gpu_draw_trajectory_gesture_point()
            if self.is_draw_gesture:
                self.gpu_draw_trajectory_gesture_line()
            else:
                if self.is_window_region_type:
                    self.gpu_draw_trajectory_mouse_move()
        if self.is_draw_gesture:
            with gpu.matrix.push_pop():
                gpu.matrix.translate(self.last_region_position)
                if self.is_window_region_type:
                    # self.draw_circle((0, 0), gp.radius, line_width=2, segments=512)
                    self.draw_circle((0, 0), gp.threshold, line_width=2, segments=64)
                    self.draw_arc((0, 0), gp.threshold, self.angle_unsigned, 45, line_width=10, segments=64)
                for d in self.direction_items.values():
                    d.draw_gpu_item(self)

    def gpu_draw(self):
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('ALWAYS')
        gpu.state.depth_mask_set(True)
        if len(bpy.context.screen.areas) > 8:
            if bpy.context.area != self.area:
                return
        if self.is_window_region_type and self.pref.draw_property.element_debug_draw_gpu_mode:
            self.gpu_draw_debug()
        if self.is_draw_gpu:
            self.gpu_draw_gesture()


class GestureProperty(GestureGpuDraw):

    @property
    def event_window_position(self):
        return Vector((self.event.mouse_x, self.event.mouse_y))

    @property
    def event_region_position(self):
        region = bpy.context.region
        return Vector((self.event.mouse_x - region.x, self.event.mouse_y - region.y))

    @property
    def last_window_position(self):
        return self.trajectory_tree.last_point

    @property
    def last_region_position(self):
        region = bpy.context.region
        if self.is_draw_gpu:
            x, y = self.last_window_position
            return Vector(((x - region.x), (y - region.y)))
        return False

    @property
    def operator_gesture(self):  # 当前操作符执行的手势
        return self.pref.gesture.get(self.gesture)

    @property
    def angle(self) -> float:  # 角度
        if self.is_draw_gpu:
            vector = self.last_window_position - self.event_window_position
            if vector == Vector((0, 0)):
                return False  # not move mouse
            angle = (180 * vector.angle_signed(Vector((-1, 0)), Vector((0, 0)))) / math.pi
            return angle
        return False

    @property
    def angle_unsigned(self):
        angle = self.angle
        if angle is not None:
            aa = abs(angle)
            if aa == angle:
                return angle
            else:
                return 360 + angle

    @property
    def direction(self) -> int:  # 方向
        angle = self.angle_unsigned
        if type(angle) == bool:
            return False
        if angle > 337.5:
            return 1
        return int((angle + 22.5) // 45 + 1)

    @property
    def distance(self) -> float:
        if self.is_draw_gpu:
            return (self.last_window_position - self.event_window_position).magnitude
        return False

    @property
    def direction_element(self):  # 当前方向上的元素;
        return self.direction_items.get(str(self.direction), None)

    @property
    def direction_items(self):
        element = self.trajectory_tree.last_element
        og = self.operator_gesture
        if element:
            return element.gesture_direction_items
        elif og:
            return og.gesture_direction_items
        else:
            return {}

    @property
    def is_draw_gpu(self) -> bool:
        return self.trajectory_tree.last_point is not None

    @property
    def is_window_region_type(self):
        return bpy.context.region.type == 'WINDOW'

    @property
    def is_beyond_threshold(self):
        return self.distance > self.gesture_property.threshold

    @property
    def is_beyond_threshold_confirm(self):
        gesture_property = self.gesture_property
        return self.distance > (gesture_property.threshold_confirm + gesture_property.threshold)

    @property
    def is_access_child_gesture(self):  # 是可以进入子手势的
        element = self.direction_element
        return self.is_beyond_threshold_confirm and element and element.is_child_gesture

    @property
    def operator_time(self):
        move_time = self.first_mouse_move_time
        if move_time:
            return time.time() - self.first_mouse_move_time

    @property
    def is_draw_gesture(self):
        if self.draw_trajectory_mouse_move:
            return self.draw_trajectory_mouse_move
        operator_time = self.operator_time
        if not operator_time:
            return False
        is_timeout = operator_time > (self.pref.gesture_property.timeout / 1000)
        if is_timeout:
            self.draw_trajectory_mouse_move = True
        return is_timeout

    @property
    def find_closest_point(self):
        tree = self.trajectory_tree.kd_tree
        tree.balance()
        return tree.find((*self.event_window_position, 0))

    @property
    def first_mouse_move_time(self) -> float:
        move_time = self.trajectory_mouse_move_time
        if len(move_time):
            return move_time[-1]


class GestureHandle(GestureProperty):
    trajectory_mouse_move: []  # 鼠标移动轨迹,在每次移动鼠标时就加上
    trajectory_mouse_move_time: []  # 鼠标移动时间
    trajectory_tree: 'GesturePointKDTree'  # 轨迹树
    event_count: IntProperty()
    draw_trajectory_mouse_move: BoolProperty(options={'SKIP_SAVE'})

    def check_return_previous(self):
        point, index, distance = self.find_closest_point
        points_kd_tree = self.trajectory_tree
        if (distance < 10) and (index + 1 != len(points_kd_tree.child_element)):
            points_kd_tree.remove(index)

    def try_running_operator(self):
        element = self.direction_element
        if self.is_beyond_threshold_confirm and element and element.is_operator:
            element.running_operator()
            return True

    def init_invoke(self, event):
        self.event_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_mouse_move_time = []
        self.trajectory_tree = GesturePointKDTree()
        self.draw_trajectory_mouse_move = False
        return super().init_invoke(event)

    def init_module(self, event):
        self.event_count += 1
        emp = self.event_window_position
        if self.event_count > 2:
            if not len(self.trajectory_mouse_move) or self.trajectory_mouse_move[-1] != emp:
                self.trajectory_mouse_move.append(emp)
                self.trajectory_mouse_move_time.append(time.time())
            if not len(self.trajectory_tree):
                self.trajectory_tree.append(None, emp)
            if self.is_access_child_gesture:
                self.trajectory_tree.append(self.direction_element, emp)
            self.check_return_previous()
        return super().init_module(event)

    def update_modal(self, context, event):
        self.area = context.area
        self.init_module(event)
        self.register_draw()
        self.tag_redraw()


class GestureOperator(GestureHandle):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Opeator'

    gesture: StringProperty()

    timer = None

    def invoke(self, context, event):
        self.init_invoke(event)
        self.cache_clear()
        wm = context.window_manager
        self.timer = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.update_modal(context, event)
        if self.is_exit:
            return self.exit()
        return {'RUNNING_MODAL'}

    def exit(self):
        self.unregister_draw()
        ops = self.try_running_operator()
        wm = bpy.context.window_manager
        wm.event_timer_remove(self.timer)
        print('ops', ops)
        if not ops:
            if not self.is_draw_gesture and not self.is_beyond_threshold_confirm:
                return {'FINISHED', 'PASS_THROUGH'}
        else:
            ...
        return {'FINISHED'}
