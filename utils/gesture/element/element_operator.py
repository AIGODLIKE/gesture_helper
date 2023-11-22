import ast

import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty, BoolProperty

from ... import PropertySetUtils
from ...enum import ENUM_OPERATOR_CONTEXT


class OperatorProperty:

    def update_operator(self, context) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        TODO 将()里面的属性读取进 properties
        """
        if self.__is_updatable__:
            self.__is_updatable__ = False
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
            self.__is_updatable__ = True

    def update_operator_properties(self, context) -> None:
        if self.__is_updatable__:
            self.__is_updatable__ = False
            print('update_operator_properties', self, context)
            self.to_operator_tmp_kmi()
            self.__is_updatable__ = True

    operator_bl_idname: StringProperty(name='操作符 bl_idname',
                                       description='默认为添加猴头',
                                       default='mesh.primitive_monkey_add',
                                       update=update_operator)
    collection: CollectionProperty

    operator_context: EnumProperty(name='操作符上下文',
                                   default='INVOKE_DEFAULT',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='操作符属性', default=r'{}', update=update_operator_properties)

    def update_operator_properties_sync_from_temp_properties(self, context):
        self.from_tmp_kmi_operator_update_properties()
        self['operator_properties_sync_from_temp_properties'] = False

    def update_operator_properties_sync_to_properties(self, context):
        self.to_operator_tmp_kmi()
        self['operator_properties_sync_to_properties'] = False

    operator_properties_sync_from_temp_properties: BoolProperty(
        name='从属性更新',
        update=update_operator_properties_sync_from_temp_properties)
    operator_properties_sync_to_properties: BoolProperty(
        name='更新到属性',
        update=update_operator_properties_sync_to_properties)

    # 直接将operator的self传给element,让那个来进行操作


class ElementOperator(OperatorProperty):
    @property
    def properties(self):
        try:
            return ast.literal_eval(self.operator_properties)
        except Exception as e:
            print('properties Error', e.args)
            return {}

    @property
    def operator_tmp_kmi(self) -> 'bpy.types.KeyMapItem':
        from ...public_key import get_temp_kmi_by_id_name
        return get_temp_kmi_by_id_name(self.operator_bl_idname)

    def to_operator_tmp_kmi(self) -> None:
        self.operator_tmp_kmi_properties_clear()
        PropertySetUtils.set_operator_property_to(self.operator_tmp_kmi.properties, self.properties)

    def from_tmp_kmi_operator_update_properties(self):
        from ...public_key import get_kmi_operator_properties
        properties = get_kmi_operator_properties(self.operator_tmp_kmi)
        if self.properties != properties:
            self['operator_properties'] = str(properties)

    @property
    def operator_func(self) -> 'bpy.types.Operator':
        """获取操作符的方法

        Returns:
            bpy.types.Operator: _description_
        """
        sp = self.operator_bl_idname.split('.')
        if len(sp) == 2:
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            return func

    def running_operator(self) -> None:
        """运行此self的操作符
        """
        try:
            prop = ast.literal_eval(self.operator_properties)
            func = self.operator_func
            if func:
                func(self.operator_context, True, **prop)
                print(
                    f'running_operator bpy.ops.{self.operator_bl_idname}'
                    f'( "{self.operator_context}", {self.operator_properties[1:-1]})',
                )
        except Exception as e:
            print('running_operator ERROR', e)

    def operator_tmp_kmi_properties_clear(self):
        properties = self.operator_tmp_kmi.properties
        for key in list(properties.keys()):
            properties.pop(key)
