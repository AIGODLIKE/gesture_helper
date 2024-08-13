import time

from mathutils import Vector
from mathutils.kdtree import KDTree


class GesturePointKDTree:

    def __init__(self, size=114):
        self.kd_tree = KDTree(size)
        self.child_element = []
        self.points_list = []
        self.time_list = []

    def __str__(self):
        return str(self.points_list) + str(self.child_element)

    def append(self, element, point: Vector):
        self.points_list.append(point)
        self.child_element.append(element)
        self.time_list.append(time.time())
        
        self.kd_tree = KDTree(len(self.points_list))
        for i, point in enumerate(self.points_list):
            self.kd_tree.insert((*point, 0), i)

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
