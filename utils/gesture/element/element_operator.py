from bpy.props import StringProperty, EnumProperty, CollectionProperty

from ...enum import ENUM_OPERATOR_CONTEXT


# 直接将operator的self传给element,让那个来进行操作
class ElementOperator:
    operator_bl_idname: StringProperty(name='操作符 Id Name',
                                       description='默认为添加猴头',
                                       default='mesh.primitive_monkey_add')
    collection: CollectionProperty

    def _get_properties(self):
        if 'operator_properties' not in self:
            return dict()
        return self['operator_properties']

    def _set_properties(self, value):
        self['operator_properties'] = value

    operator_properties = property(fget=_get_properties, fset=_set_properties)

    operator_context: EnumProperty(name='操作符上下文',
                                   default='INVOKE_DEFAULT',
                                   items=ENUM_OPERATOR_CONTEXT)

    @property
    def gesture_direction_items(self):
        direction = {}
        for i in self.collection:
            if i.is_selected_structure:
                direction.update(i.gesture_direction_items)
            elif i.is_child_gesture:
                direction[i.gesture_direction] = i
        return direction
