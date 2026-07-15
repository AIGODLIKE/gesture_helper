from contextlib import contextmanager

import bpy

from ..element.element_property import ElementAddProperty
from ..utils.enum import ENUM_RELATIONSHIP

class AddElementProperty(ElementAddProperty, bpy.types.PropertyGroup):
    add_active_radio: bpy.props.BoolProperty(
        name="Activate new element when added",
        description='Select the newly added element after it is created',
        default=False,
    )

    relationship: bpy.props.EnumProperty(
        name='Relationship',
        description='Where to insert the new element relative to the current selection',
        default='SAME',
        items=ENUM_RELATIONSHIP,
    )

    @property
    def is_child_relationship(self) -> bool:
        return self.relationship == 'CHILD'

    @contextmanager
    def active_radio(self):
        last_active_radio = self.add_active_radio
        try:
            self.add_active_radio = True
            yield
        finally:
            self.add_active_radio = last_active_radio
