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


def from_each_as_title_items(enum):
    items = []
    for i in enum:
        title = ' '.join(i.title().split('_'))
        items.append((i, title, title))
    return items


def from_rna_get_enum_items(rna_property):
    """通过rna获取枚举的所有项"""
    if rna_property:
        if rna_property.enum_items:
            items = rna_property.enum_items
        elif rna_property.enum_items_static:
            items = rna_property.enum_items_static
        elif rna_property.enum_items_static_ui:
            items = rna_property.enum_items_static_ui
        else:
            items = []
    else:
        items = []
    it = [(item.identifier, item.name, item.description, item.icon, index)
          for (index, item) in enumerate(items)]
    return it


ENUM_GESTURE_DIRECTION = [
    ('5', 'Left', ''),
    ('1', 'Right', ''),
    ('3', 'Up', ''),
    ('7', 'Down', ''),
    ('4', 'Left Top', ''),
    ('2', 'Right Top', ''),
    ('6', 'Left Down', ''),
    ('8', 'Right Down', ''),
    ('9', 'Bottom', ''),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', 'Sel Structure', 'Select structure'),
    ('CHILD_GESTURE', 'Child', 'Child gesture'),
    ('OPERATOR', 'Op', 'Operator'),
    ('DIVIDING_LINE', 'Div', 'Dividing line'),
]
ENUM_SELECTED_TYPE = from_each_as_enum_upper(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', 'Root', 'Add to root'),
    ('SAME', 'Same', 'Add to same'),
    ('CHILD', 'Child', 'Add to child'),
]
ENUM_OPERATOR_CONTEXT = from_each_as_title_items(OPERATOR_CONTEXT_ELEMENT)

ENUM_OPERATOR_TYPE = [
    ('OPERATOR', 'Operator', 'Enter Blender own operator bl_idname'),
    ('SCRIPT', 'Script', 'Use custom script to run'),
    ('MODAL', 'Modal', 'Use modal run operator'),
]

ENUM_NUMBER_VALUE_CHANGE_MODE = [
    ("SET_VALUE", "Set Value", "Setting an attribute to a specified value"),
    ("MOUSE_CHANGES_HORIZONTAL", "Mouse Interaction Change (Horizontal)", "Horizontal Modifier"),
    ("MOUSE_CHANGES_VERTICAL", "Mouse Interaction Change (Vertical)", "Vertical Modifier"),
    ("MOUSE_CHANGES_ARBITRARY", "Mouse Interaction Change (Any Direction)", "Modify Value In Any Direction"),
]
ENUM_BOOL_VALUE_CHANGE_MODE = [
    ('SET_TRUE', 'Set to True', ''),
    ('SET_FALSE', 'Set to False', ''),
    ('SWITCH', 'Switch', '')
]
