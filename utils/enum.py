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
    ('5', 'left', ''),
    ('1', 'right', ''),
    ('3', 'above', ''),
    ('7', 'under', ''),
    ('4', 'topLeft', ''),
    ('2', 'topRight', ''),
    ('6', 'lowerLeft', ''),
    ('8', 'bottomRight', ''),

    # ('UP', '顶', 'TRIA_UP_BAR'), TODO
    # ('DOWN', '底', 'TRIA_DOWN'),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', 'select the structure', ''),
    ('CHILD_GESTURE', 'subgesture', ''),
    ('OPERATOR', 'operator', ''),
]
ENUM_SELECTED_TYPE = from_each_as_enum_upper(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', 'root', ''),
    ('SAME', 'same', ''),
    ('CHILD', 'child', '')
]
ENUM_OPERATOR_CONTEXT = from_each_as_title(OPERATOR_CONTEXT_ELEMENT)
