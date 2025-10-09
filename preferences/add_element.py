from contextlib import contextmanager

import bpy

from ..element.element_property import ElementAddProperty
from ..utils.enum import ENUM_RELATIONSHIP
from ..utils.public import get_pref

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

    @contextmanager
    def active_radio(self):
        last_active_radio = self.add_active_radio
        active = get_pref().active_element
        try:
            self.add_active_radio = True
            yield
        finally:
            self.add_active_radio = last_active_radio
            if active and not last_active_radio:
                active.radio = True
                active.update_radio()
