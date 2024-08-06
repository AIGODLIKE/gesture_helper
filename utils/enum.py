SELECT_STRUCTURE_ELEMENT = ['if', 'elif', 'else']
OPERATOR_CONTEXT_ELEMENT = [
    "INVOKE_DEFAULT",
    "INVOKE_REGION_WIN",
    "INVOKE_REGION_CHANNELS",
    "INVOKE_REGION_PREVIEW",
    "INVOKE_AREA",
    "INVOKE_SCREEN",
    "EXEC_DEFAULT",
    "EXEC_REGION_WIN",
    "EXEC_REGION_CHANNELS",
    "EXEC_REGION_PREVIEW",
    "EXEC_AREA", ]


def from_each_as_enum_upper(enum):
    return [(i.upper(), i.title(), i.title())
            for i in enum]


def from_each_as_title(enum):
    items = []
    for i in enum:
        title = ' '.join(i.title().split('_'))
        items.append((i, title, title))
    return items


ENUM_GESTURE_DIRECTION = [
    ('5', '左', ''),
    ('1', '右', ''),
    ('3', '上', ''),
    ('7', '下', ''),
    ('4', '左上', ''),
    ('2', '右上', ''),
    ('6', '左下', ''),
    ('8', '右下', ''),

    # ('UP', '顶', 'TRIA_UP_BAR'), TODO
    # ('DOWN', '底', 'TRIA_DOWN'),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', '选择结构', ''),
    ('CHILD_GESTURE', '子手势', ''),
    ('OPERATOR', '操作符', ''),
]
ENUM_SELECTED_TYPE = from_each_as_enum_upper(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', '根级', ''),
    ('SAME', '同级', ''),
    ('CHILD', '子级', '')
]
ENUM_OPERATOR_CONTEXT = from_each_as_title(OPERATOR_CONTEXT_ELEMENT)

ENUM_OPERATOR_TYPE = [
    ('OPERATOR', '操作符', '输入Blender自带的操作符bl_idname'),
    ('SCRIPT', '脚本', '使用自定义脚本运行操作符'),
]

CREATE_ELEMENT_VALUE_MODE_ENUM = [
    ("SET_VALUE", "设置值", "直接将属性设置为指定值"),
    ("MOUSE_CHANGES_HORIZONTAL", "鼠标互动更改(水平方向)", "水平方向修改值"),
    ("MOUSE_CHANGES_VERTICAL", "鼠标互动更改(垂直方向)", "垂直方向修改值"),
    ("MOUSE_CHANGES_ARBITRARY", "鼠标互动更改(任意方向)", "任意方向修改值"),
]
