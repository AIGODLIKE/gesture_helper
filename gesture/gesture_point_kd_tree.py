import time

from mathutils import Vector
from mathutils.kdtree import KDTree


class GesturePointKDTree:
    """Trajectory points with incremental KD-tree inserts and deferred balance."""

    def __init__(self, size=64):
        self._capacity = max(1, size)
        self.kd_tree = KDTree(self._capacity)
        self.child_element = []
        self.points_list = []
        self.time_list = []
        self._needs_balance = False

    def __str__(self):
        return str(self.points_list) + str(self.child_element)

    def items(self) -> dict["Gesture", Vector]:
        return {element: point for element, point in zip(self.child_element, self.points_list)}

    def _rebuild(self):
        """Rebuild KD-tree from current points (capacity may have grown)."""
        self.kd_tree = KDTree(self._capacity)
        for i, point in enumerate(self.points_list):
            self.kd_tree.insert((*point, 0), i)
        self._needs_balance = True

    def append(self, element, point: Vector):
        idx = len(self.points_list)
        if idx >= self._capacity:
            self._capacity = max(self._capacity * 2, idx + 1)
            self._rebuild()

        self.points_list.append(point)
        self.child_element.append(element)
        self.time_list.append(time.time())
        self.kd_tree.insert((*point, 0), idx)
        self._needs_balance = True

    def set_points(self, points) -> None:
        """Replace trajectory positions and rebuild the spatial index."""
        points = [Vector(point) for point in points]
        if len(points) != len(self.child_element):
            raise ValueError("point count must match trajectory element count")
        self.points_list = points
        self._capacity = max(self._capacity, len(points), 1)
        self._rebuild()

    def translate(self, offset: Vector) -> None:
        """Translate the trajectory without leaving a stale KD-tree."""
        self.set_points(point + offset for point in self.points_list)

    def remove(self, index):
        if index < 0 or not self.points_list:
            return self.last_element
        if index >= len(self.points_list):
            index = len(self.points_list) - 1
        val = index + 1
        self.child_element = self.child_element[:val]
        self.points_list = self.points_list[:val]
        self.time_list = self.time_list[:val]
        self._rebuild()
        if self.points_list:
            self.kd_tree.balance()
            self._needs_balance = False
        return self.child_element[-1] if self.child_element else None

    def find_nearest(self, pos: Vector):
        """Find nearest trajectory point; balances only when dirty."""
        if not self.points_list:
            return None, -1, float('inf')
        if self._needs_balance:
            self.kd_tree.balance()
            self._needs_balance = False
        return self.kd_tree.find((*pos, 0))

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
