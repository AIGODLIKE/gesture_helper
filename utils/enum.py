SELECT_STRUCTURE_ELEMENT = ['if', 'elif', 'else']


def from_each_as_enum(enum):
    return [(i.upper(), i, i)
            for i in enum]


ENUM_GESTURE_DIRECTION = [
    ('1', '左', 'TRIA_LEFT'),
    ('2', '右', 'TRIA_RIGHT'),
    ('4', '上', 'TRIA_UP'),
    ('3', '下', 'TRIA_DOWN'),
    ('5', '左上', ''),
    ('6', '右上', ''),
    ('7', '左下', ''),
    ('8', '右下', ''),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', 'Selected Structure', ''),
    ('GESTURE', 'Gesture', ''),
]
ENUM_SELECTED_TYPE = from_each_as_enum(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', 'Root', ''),
    ('SAME', 'Same', ''),
    ('CHILD', 'Child', '')
]
