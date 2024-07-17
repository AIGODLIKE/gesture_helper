from enum import Enum


class BPUType(Enum):
    ROW = 10
    COLUMN = 20
    BOX = 30
    SPLIT = 40
    # PROPERTY = 60
    # SEPARATOR = 70
    LABEL = 50
    OPERATOR = 200

    PARENT = 500

    UNKNOWN = 1000

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def is_layout(self):
        """是布局"""
        return self.name in ['ROW', 'COLUMN', 'BOX', 'SPLIT']

    @property
    def is_parent(self):
        """是父级"""
        return self.name == "PARENT"

    @property
    def is_draw_text(self):
        """是需要绘制文字类型"""
        return self.name in ['LABEL', 'OPERATOR']

    @property
    def is_draw_child(self):
        return self.is_layout or self.is_parent

    @property
    def is_horizontal_layout(self):
        """是水平布局
        -----------
        """
        return self.name in ['ROW', 'BOX']

    @property
    def is_vertical_layout(self):
        """是垂直布局
        ¦
        ¦
        ¦
        ¦
        ¦
        """
        return self.name in ['COLUMN', 'BOX']

    @property
    def is_draw_item(self):
        """是绘制项"""
        return self.name in ['LABEL', 'OPERATOR']


class Quadrant(Enum):
    """绘制的象限位置"""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
