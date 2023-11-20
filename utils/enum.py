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
    ('1', '左', 'TRIA_LEFT'),
    ('2', '右', 'TRIA_RIGHT'),
    ('4', '上', 'TRIA_UP'),
    ('3', '下', 'TRIA_DOWN'),
    ('5', '左上', ''),
    ('6', '右上', ''),
    ('7', '左下', ''),
    ('8', '右下', ''),

    ('UP', '顶', 'TRIA_UP_BAR'),
    ('DOWN', '底', 'TRIA_DOWN'),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', '选择结构', ''),
    ('CHILD_ELEMENT', '子手势', ''),
    ('OPERATOR', '操作符', ''),
]
ENUM_SELECTED_TYPE = from_each_as_enum_upper(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', '根级', ''),
    ('SAME', '同级', ''),
    ('CHILD', '子级', '')
]
ENUM_OPERATOR_CONTEXT = from_each_as_title(OPERATOR_CONTEXT_ELEMENT)
