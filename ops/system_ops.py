import time
from math import pi

import bpy
import gpu
from bpy.props import BoolProperty, StringProperty
from mathutils import Vector
from mathutils.kdtree import KDTree

from ..utils.public import PublicData
from ..utils.public.public_gpu import PublicGpu
from ..utils.public.public_operator import PublicOperator


class PointGestureKDTree:
    kd_tree: KDTree

    def __init__(self, size=114):
        self.kd_tree = KDTree(size)
        self.gesture_items = []
        self.points_list = []

    def append(self, gesture, point: Vector, is_root=False):
        index = len(self.gesture_items)
        co = (*point, 0)
        self.kd_tree.insert(co, index)
        self.points_list.append(point)
        self.gesture_items.append(gesture)

    def remove(self, index):
        val = index + 1
        self.gesture_items = self.gesture_items[:val]
        self.points_list = self.points_list[:val]

    def __len__(self):
        return self.gesture_items.__len__()


class GestureProp(PublicOperator,
                  ):
    system: StringProperty()
    show_gesture: BoolProperty(default=False, **PublicData.PROP_DEFAULT_SKIP)
    points_kd_tree: PointGestureKDTree
    start_time: float
    mouse_trajectory: list
    _last_move_mouse_time: float

    @property
    def find_closest_point(self):
        tree = self.points_kd_tree.kd_tree
        tree.balance()
        return tree.find((*self.mouse_co, 0))

    @property
    def last_move_mouse_time(self) -> float:
        return (time.time() - self._last_move_mouse_time) * 100

    @last_move_mouse_time.setter
    def set(self, value):
        self._last_move_mouse_time = value

    @property
    def wait_draw_gesture_items(self):
        src = {i: None for i in range(8)}
        act = self.active_gesture
        items = act.wait_draw_gesture_items if act == self.current_system else act.wait_draw_children_element_items

        for item in items:
            direction = item.gesture_direction
            if item.gesture_is_direction_mode and item not in src.values():
                src[int(direction)] = item
        return src

    @property
    def is_show_gesture(self):  # TODO
        return

    @property
    def gesture_points(self):
        return self.points_kd_tree.points_list

    @property
    def current_system(self):
        return self.pref.systems.get(self.system)

    @property
    def system_type(self):
        return self.current_system.system_type

    @property
    def is_exit(self):
        return self.event.value == 'RELEASE'

    @property
    def gesture_direction(self, split=22.5) -> int:
        def gesture_index(ang: float) -> int:
            an = abs(ang)
            if split < an < (split + 45):
                return 5 if ang < 0 else 7
            elif (90 - split) < an < (90 + split):
                return 4 if ang < 0 else 3
            elif (90 + split) < an < (90 + split + 45):
                return 6 if ang < 0 else 8

        vector = self.mouse_co - self.active_point
        if vector == Vector((0, 0)):
            return -1  # not move mouse
        angle = (180 * vector.angle_signed(
            Vector((-1, 0)),
            Vector((0, 0)))
                 ) / pi

        max_split = 180 - split

        if -split < angle < split:
            return 1
        elif (max_split < angle) | (angle < -max_split):
            return 2
        else:
            return gesture_index(angle)

    @property
    def gesture_distance(self):
        """获取手势相对活动点的移动距离"""
        return (self.mouse_co - self.active_point).magnitude

    @property
    def beyond_distance(self):
        return 110

    def _beyond_distance(self, distance):
        return self.gesture_distance > (distance + distance * 0.3)

    @property
    def gesture_about_beyond_distance(self):
        return self._beyond_distance(self.beyond_distance - 40)

    @property
    def gesture_beyond_distance(self) -> bool:
        return self._beyond_distance(self.beyond_distance)

    @property
    def is_beyond_distance_event(self) -> bool:
        """获取 手势超出距离 并且朝向的项是有效的布尔值
        """
        item = self.gesture_direction_item
        return self.gesture_beyond_distance and item and item.gesture_is_have_child

    @property
    def active_point(self):
        return self.points_kd_tree.points_list[-1]

    @property
    def active_gesture(self):
        return self.points_kd_tree.gesture_items[-1]

    @property
    def gesture_direction_item(self):
        key = self.gesture_direction
        if key in self.wait_draw_gesture_items:
            return self.wait_draw_gesture_items[key]

    @property
    def is_return_previous_item(self):
        point, index, distance = self.find_closest_point
        return (distance < 10) and (index + 1 != len(self.points_kd_tree.gesture_items))


class GestureDraw(GestureProp,
                  PublicGpu):
    data = {}
    _handler_draw_gesture = []

    def register_draw_gesture(self):
        if not GestureDraw._handler_draw_gesture:
            GestureDraw._handler_draw_gesture.append(
                bpy.types.SpaceView3D.draw_handler_add(
                    self.draw_gesture_system, (),
                    'WINDOW', 'POST_PIXEL'))

    @staticmethod
    def unregister_draw_gesture():
        while len(GestureDraw._handler_draw_gesture):
            bpy.types.SpaceView3D.draw_handler_remove(GestureDraw._handler_draw_gesture.pop(), 'WINDOW')

    def draw_gesture_system(self):
        gpu.state.blend_set('MULTIPLY')

        if self.show_gesture:
            self.draw_gesture_points()
            self.draw_gesture_line(self.gesture_points + [self.mouse_co, ])
            self.draw_gesture_items()
            self.draw_test()
        else:
            self.draw_gesture_points()
            self.draw_gesture_line(self.mouse_trajectory)

    def draw_gesture_line(self, points):
        self.draw_2d_line(points, (1.0, 0.5, 0.5, 1), 3.4)

    def draw_gesture_points(self):
        self.draw_2d_points(self.gesture_points)

    def draw_gesture_items(self):
        for index, gesture in self.wait_draw_gesture_items.items():
            if gesture:
                direction = self.gesture_direction == int(gesture.gesture_direction)
                is_about_beyond = direction and self.gesture_about_beyond_distance
                gesture.draw_gesture(self, is_about_beyond)

    def draw_test(self):
        import blf
        import bpy

        font_info = {
            "font_id": 0,
            "handler": None,
        }

        import os
        # Create a new font object, use external ttf file.
        font_path = bpy.path.abspath('//Zeyada.ttf')
        # Store the font indice - to use later.
        if os.path.exists(font_path):
            font_info["font_id"] = blf.load(font_path)
        else:
            # Default font.
            font_info["font_id"] = 0

        # set the font drawing routine to run every frame
        # def draw_callback_px(self, context):
        #     """Draw on the viewports"""
        #     # BLF drawing routine
        font_id = font_info["font_id"]
        blf.position(font_id, 200, 60, 0)
        blf.size(font_id, 20)
        blf.draw(font_id, str(self.gesture_direction_item))
        blf.position(font_id, 200, 80, 0)
        blf.draw(font_id, str(self.wait_draw_gesture_items))
        blf.position(font_id, 200, 100, 0)
        blf.draw(font_id,
                 str([
                     self.is_beyond_distance_event,
                     self.gesture_about_beyond_distance,
                     self.gesture_beyond_distance,
                     int(self.gesture_distance),
                 ]))
        blf.position(font_id, 200, 120, 0)
        blf.draw(font_id, str([self.is_return_previous_item, self.find_closest_point]))
        blf.position(font_id, 200, 140, 0)
        blf.draw(font_id, str([self.active_gesture, self.last_move_mouse_time]))


class GestureOps(GestureDraw):
    def update_data(self, context, event):
        GestureDraw.data['ops'] = self
        GestureDraw.data['event'] = event
        GestureDraw.data['context'] = context

    def invoke_gesture(self, context, event):
        self.update_data(context, event)
        self.init_kd_tree()
        self.points_kd_tree.append(self.current_system, self.start_mouse_co)
        self._last_move_mouse_time = self.start_time = time.time()
        self.mouse_trajectory = [self.mouse_co, ]
        self.register_draw_gesture()

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def update_modal(self):
        if self.mouse_co != self.mouse_trajectory[-1]:
            self.mouse_trajectory.append(self.mouse_co)
            self._last_move_mouse_time = time.time()

        self.last_mouse_co = self.mouse_co

    def modal_gesture(self, context, event):
        self.update_data(context, event)
        if self.is_exit:
            return self.exit()
        elif self.is_beyond_distance_event:
            self.points_kd_tree.append(self.gesture_direction_item, self.mouse_co)
        elif self.is_return_previous_item:
            point, index, distance = self.find_closest_point
            self.points_kd_tree.remove(index)
        if self.last_move_mouse_time > 200:  # 200ms
            self.show_gesture = True

        self.tag_redraw(context)
        self.update_modal()
        return {'RUNNING_MODAL'}

    def exit_gesture(self):
        self.unregister_draw_gesture()
        item = self.gesture_direction_item
        if item and item.gesture_is_operator and self.gesture_about_beyond_distance:
            item.running_operator()
            return {'FINISHED'}
        else:
            return {'FINISHED'}
            return {'PASS_THROUGH'}

    def init_kd_tree(self):
        self.points_kd_tree = PointGestureKDTree()


class SystemOps(GestureOps,
                ):
    bl_idname = PublicOperator.ops_id_name('gesture_ops')
    bl_label = 'Gesture Ui Operator'

    def invoke(self, context, event):
        self.init_invoke(context, event)
        self.tag_redraw(context)
        if not self.current_system:
            self.report({'WARNING': f'Not Find System {self.system}'})
        else:
            return getattr(self, f'invoke_{self.system_type.lower()}')(context, event)

    def modal(self, context, event):
        self.init_modal(context, event)
        return getattr(self, f'modal_{self.system_type.lower()}')(context, event)

    def exit(self):

        self.tag_redraw(bpy.context)
        return getattr(self, f'exit_{self.system_type.lower()}')()


classes_tuple = (
    SystemOps,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
