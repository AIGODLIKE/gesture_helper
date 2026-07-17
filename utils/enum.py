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
    # Keep IF/ELIF/ELSE uppercase so UI labels are not translated.
    return [(i.upper(), i.upper(), i.upper()) for i in enum]


def from_each_as_title_items(enum):
    items = []
    for i in enum:
        title = ' '.join(i.title().split('_'))
        items.append((i, title, title))
    return items


def from_rna_get_enum_items(rna_property):
    """Get all enum items from RNA property."""
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
    return [
        (item.identifier, item.name, item.description, item.icon, index)
        for index, item in enumerate(items)
    ]


ENUM_GESTURE_DIRECTION = [
    ('5', 'Left', ''),
    ('1', 'Right', ''),
    ('3', 'Up', ''),
    ('7', 'Down', ''),
    ('4', 'Up Left', ''),
    ('2', 'Up Right', ''),
    ('6', 'Bottom Left', ''),
    ('8', 'Bottom Right', ''),
    ('9', 'Bottom', ''),
]
ENUM_ELEMENT_TYPE = [
    ('SELECTED_STRUCTURE', 'Structure', 'Structure element'),
    ('CHILD_GESTURE', 'Child', 'Child gesture'),
    ('OPERATOR', 'Op', 'Operator'),
    ('DIVIDING_LINE', 'Div', 'Dividing line'),
]
ENUM_SELECTED_TYPE = from_each_as_enum_upper(SELECT_STRUCTURE_ELEMENT)

ENUM_RELATIONSHIP = [
    ('ROOT', 'Root', 'Add to root'),
    ('SAME', 'Same', 'Add as sibling'),
    ('CHILD', 'Child', 'Add as child'),
]
ENUM_OPERATOR_CONTEXT = from_each_as_title_items(OPERATOR_CONTEXT_ELEMENT)

ENUM_OPERATOR_TYPE = [
    ('OPERATOR', 'Operator', 'Use a Blender operator by bl_idname'),
    ('MODAL', 'Modal', 'Use a modal operator'),
]

ENUM_NUMBER_VALUE_CHANGE_MODE = [
    ("SET_VALUE", "Set Value", "Set the property to a fixed value"),
    ("MOUSE_CHANGES_HORIZONTAL", "Change with horizontal mouse movement", "Adjust with horizontal mouse movement"),
    ("MOUSE_CHANGES_VERTICAL", "Change with vertical mouse movement", "Adjust with vertical mouse movement"),
    ("MOUSE_CHANGES_ARBITRARY", "Change with mouse movement in any direction", "Adjust with mouse movement in any direction"),
]
ENUM_BOOL_VALUE_CHANGE_MODE = [
    ('SET_TRUE', 'Set to True', ''),
    ('SET_FALSE', 'Set to False', ''),
    ('SWITCH', 'Switch', '')
]
