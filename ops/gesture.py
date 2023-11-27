# 显示操作符,
# 切换
import math

import bpy
import gpu
from bpy.props import StringProperty, IntProperty
from mathutils import Vector
from mathutils.kdtree import KDTree

from ..utils.public import PublicOperator, PublicProperty, DIRECTION_STOP_DICT
from ..utils.public_gpu import PublicGpu


class GesturePointKDTree:

    def __init__(self, size=114):
        self.kd_true = KDTree(size)
        self.child_element = []
        self.points_list = []

    def __str__(self):
        return str(self.points_list) + str(self.child_element)

    def append(self, element, point: Vector):
        index = len(self.child_element)
        self.kd_true.insert((*point, 0), index)
        self.points_list.append(point)
        self.child_element.append(element)

    def remove(self, index):
        val = index + 1
        # TODO rebuild tree
        self.child_element = self.child_element[:val]
        self.points_list = self.points_list[:val]

    def __len__(self):
        return self.child_element.__len__()

    @property
    def trajectory(self):
        return self.points_list

    def get_last(self):
        if len(self.points_list):
            return self.points_list[-1]


class GestureGpuDraw(PublicGpu, PublicOperator, PublicProperty
                     ):
    __temp_draw_class__ = {}

    @staticmethod
    def refresh_space():
        return list(getattr(bpy.types, i) for i in dir(bpy.types) if 'Space' in i)

    @classmethod
    def space_subclasses(cls):
        cls.refresh_space()
        return bpy.types.Space.__subclasses__()

    def register_draw(self):
        if not GestureGpuDraw.__temp_draw_class__:
            print('register_draw')
            for cls in self.space_subclasses():
                sub_class = {}
                for j in self.region_enum_type:
                    identifier = j.identifier
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
        if self.is_draw_trajectory_mouse_move and self.is_window_region_type:
            self.draw_2d_line(self.trajectory_mouse_move, (0.9, 0, 0, 1))

    def gpu_draw_trajectory_gesture_line(self):
        self.draw_2d_line(self.trajectory_tree.points_list, color=(0, 1, 0, 1))

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
        if area.type == 'VIEW_3D':
            data.insert(0, '--')
            data.insert(0, 'event_count:' + str(self.event_count))
            data.insert(0, 'trajectory_mouse_move:' + str(len(self.trajectory_mouse_move)))
            data.insert(0, 'trajectory_tree:' + str(self.trajectory_tree))
            data.append('--')
            data.append('operator_gesture:' + str(self.operator_gesture))
            data.append('is_draw_gpu:' + str(self.is_draw_gpu))
            data.append('is_window_region_type:' + str(self.is_window_region_type))
            data.append('is_beyond_threshold:' + str(self.is_beyond_threshold))
            data.append('is_beyond_threshold_confirm:' + str(self.is_beyond_threshold_confirm))
            data.append('is_draw_trajectory_mouse_move:' + str(self.is_draw_trajectory_mouse_move))
            data.append('--')
            data.append('last_region_position:' + str(self.last_region_position))
            data.append('last_window_position:' + str(self.last_window_position))
            data.append('event_region_position:' + str(self.event_region_position))
            data.append('event_window_position:' + str(self.event_window_position))
            data.append('--')
            data.append('angle:' + str(self.angle))
            data.append('distance:' + str(self.distance))
            data.append('direction:' + str(self.direction))
            data.append('direction_items:' + str({i: v.name for i, v in self.direction_items.items()}))
            data.append('direction_element:' + str(self.direction_element))
        self.draw_rectangle(0, 0, 400, len(data) * 30)
        for index, i in enumerate(data):
            j = index + 1
            self.draw_text((5, 30 * j), text=i)

    def gpu_draw_gesture(self):
        event = self.event
        gp = self.gesture_property

        self.draw_text(self.event_region_position, text=event.value)  # 绘制当前区域
        self.draw_circle(self.last_region_position, gp.radius)

        area = bpy.context.area
        with gpu.matrix.push_pop():
            gpu.matrix.translate([-area.x, -area.y])
            self.gpu_draw_trajectory_mouse_move()
            self.gpu_draw_trajectory_gesture_line()
            self.gpu_draw_trajectory_gesture_point()

        for d in self.direction_items.values():
            d.draw_gpu_item(self)

    def gpu_draw(self):
        if self.is_window_region_type:
            self.gpu_draw_debug()
        if self.is_draw_gpu:
            self.gpu_draw_gesture()


class GestureProperty(GestureGpuDraw):
    now_element = None

    @property
    def region_enum_type(self):
        return bpy.types.Region.bl_rna.properties['type'].enum_items_static

    @property
    def event_window_position(self):
        return Vector((self.event.mouse_x, self.event.mouse_y))

    @property
    def event_region_position(self):
        region = bpy.context.region
        return Vector((self.event.mouse_x - region.x, self.event.mouse_y - region.y))

    @property
    def last_window_position(self):
        return self.trajectory_tree.get_last()

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
    def direction(self) -> int:  # 方向
        split = 22.5
        angle = self.angle
        if type(angle) == bool:
            return False

        def gesture_index(ang: float) -> int:
            an = abs(ang)
            if split < an < (split + 45):
                return 8 if ang < 0 else 6
            elif (90 - split) < an < (90 + split):
                return 3 if ang < 0 else 4
            elif (90 + split) < an < (90 + split + 45):
                return 7 if ang < 0 else 5

        max_split = 180 - split

        if -split < angle < split:
            return 2
        elif (max_split < angle) | (angle < -max_split):
            return 1
        else:
            return gesture_index(angle)

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
        if self.now_element:
            return self.now_element.gesture_direction_items
        else:
            return self.operator_gesture.gesture_direction_items

    @property
    def is_draw_gpu(self) -> bool:
        return self.trajectory_tree.get_last() is not None

    @property
    def is_window_region_type(self):
        return bpy.context.region.type == 'WINDOW'

    @property
    def is_beyond_threshold(self):
        return self.distance > self.gesture_property.threshold

    @property
    def is_beyond_threshold_confirm(self):
        return self.distance > self.gesture_property.threshold_confirm

    @property
    def is_draw_trajectory_mouse_move(self):  # TODO
        return True


class GestureHandle(GestureProperty):
    trajectory_mouse_move: []  # 鼠标移动轨迹,在每次移动鼠标时就加上
    trajectory_tree: 'GesturePointKDTree'  # 轨迹树
    event_count: IntProperty()

    def init_invoke(self, event):
        self.event_count = 1
        self.trajectory_mouse_move = []
        self.trajectory_tree = GesturePointKDTree()
        return super().init_invoke(event)

    def init_module(self, event):
        self.event_count += 1
        emp = self.event_window_position
        if self.event_count > 2:
            if not len(self.trajectory_mouse_move) or self.trajectory_mouse_move[-1] != emp:
                self.trajectory_mouse_move.append(emp)
            if not len(self.trajectory_tree):
                self.trajectory_tree.append(None, emp)
        return super().init_module(event)

    def update_modal(self, context, event):
        self.init_module(event)
        self.register_draw()
        self.tag_redraw()
        print('modal', context, event, event.value, event.type)


class GestureOperator(GestureHandle):
    bl_idname = 'gesture.operator'
    bl_label = 'Gesture Opeator'

    gesture: StringProperty()

    def invoke(self, context, event):
        self.init_invoke(event)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.update_modal(context, event)
        if self.is_right_mouse and self.is_release:
            return self.exit()
        return {'RUNNING_MODAL'}

    def exit(self):
        self.unregister_draw()
        del self.trajectory_tree
        return {'FINISHED'}
