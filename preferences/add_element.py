import bpy

from ..element.element_property import ElementAddProperty
from ..utils.enum import ENUM_RELATIONSHIP


class AddElementProperty(ElementAddProperty, bpy.types.PropertyGroup):
    add_active_radio: bpy.props.BoolProperty(name="Whether or not to set it as an active item when adding an element",
                                             default=False)

    relationship: bpy.props.EnumProperty(
        name='Relationship',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )

    @property
    def is_child_relationship(self) -> bool:
        return self.relationship == 'CHILD'
