import ast

import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty

from ... import PropertySetUtils
from ...enum import ENUM_OPERATOR_CONTEXT


class OperatorProperty:

    def update_operator(self, context) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        TODO 将()里面的属性读取进 properties
        """
        value = self.operator_bl_idname
        key = 'operator_bl_idname'
        if value.startswith('bpy.ops.'):
            self[key] = value = value[8:]
        if ('(' in value) and (')' in value):
            if value.endswith('()'):
                self[key] = value[:-2]
            else:  # 将后面的切掉
                index = value.index('(')
                self[key] = value[:index]
        self.to_operator_tmp_kmi()

    def update_operator_properties(self, context) -> None:
        print('update_operator_properties', self, context)
        self.to_operator_tmp_kmi()

    operator_bl_idname: StringProperty(name='操作符 bl_idname',
                                       description='默认为添加猴头',
                                       default='mesh.primitive_monkey_add',
                                       update=update_operator)
    collection: CollectionProperty

    operator_context: EnumProperty(name='操作符上下文',
                                   default='INVOKE_DEFAULT',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='操作符属性', default=r'{}', update=update_operator_properties)


# 直接将operator的self传给element,让那个来进行操作
class ElementOperator(OperatorProperty):
    @property
    def properties(self):
        try:
            return ast.literal_eval(self.operator_properties)
        finally:
            return {}

    @property
    def operator_tmp_kmi(self) -> 'bpy.types.KeyMapItem':
        from ...public_key import get_temp_kmi
        return get_temp_kmi(self.operator_bl_idname, self.properties)

    def to_operator_tmp_kmi(self) -> None:
        print('to_operator_tmp_kmi', self)  # TODO 同步操作符属性
        PropertySetUtils.set_property_data(self.operator_tmp_kmi.properties, self.properties)

    def run_operator(self):
        ...
