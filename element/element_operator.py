import ast

import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ..utils import PropertySetUtils
from ..utils.enum import ENUM_OPERATOR_CONTEXT, ENUM_OPERATOR_TYPE
from ..utils.public_cache import cache_update_lock
from ..utils.string_eval import try_call_exec


class OperatorProperty:
    @cache_update_lock
    def update_operator(self) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        """
        if self.is_operator:
            value = self.operator_bl_idname.replace(' ', '')
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

    @cache_update_lock
    def update_operator_properties(self) -> None:
        self.to_operator_tmp_kmi()

    operator_bl_idname: StringProperty(name='操作符 bl_idname',
                                       description='默认为添加猴头',
                                       update=lambda self, context: self.update_operator())

    operator_context: EnumProperty(name='操作符上下文',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='操作符属性',
                                        update=lambda self, context: self.update_operator_properties())
    
    operator_type: EnumProperty(name='操作类型',
                                description='操作的类型',
                                items=ENUM_OPERATOR_TYPE,
                                default='OPERATOR'
                                )
    operator_script: StringProperty(name='操作脚本', description='操作符的脚本', default='print("Emm")')

    preview_operator_script: BoolProperty(name='预览脚本', default=True)

    def update_operator_properties_sync_from_temp_properties(self, _):
        if self.is_operator:
            self.from_tmp_kmi_operator_update_properties()
            self['operator_properties_sync_from_temp_properties'] = False

    def update_operator_properties_sync_to_properties(self, _):
        if self.is_operator:
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
            print('Properties Error', e.args)
            import traceback
            traceback.print_stack()
            return {}

    @property
    def operator_tmp_kmi(self) -> 'bpy.types.KeyMapItem':
        from ..utils.public_key import get_temp_kmi_by_id_name
        return get_temp_kmi_by_id_name(self.operator_bl_idname)

    @property
    def operator_tmp_kmi_properties(self):
        from ..utils.public_key import get_kmi_operator_properties
        properties = get_kmi_operator_properties(self.operator_tmp_kmi)
        return properties

    def to_operator_tmp_kmi(self) -> None:
        if self.is_operator:
            self.operator_tmp_kmi_properties_clear()
            PropertySetUtils.set_operator_property_to(self.operator_tmp_kmi.properties, self.properties)

    def from_tmp_kmi_operator_update_properties(self):
        properties = self.operator_tmp_kmi_properties
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
        if self.operator_type == "OPERATOR":
            self.running_by_bl_idname()
        else:
            self.running_by_script()

    def running_by_bl_idname(self):
        try:
            prop = ast.literal_eval(self.operator_properties)
            func = self.operator_func
            if func:
                func(self.operator_context, True, **prop)

                def g(v):
                    return f'"{v}"' if type(v) is str else v

                ops_property = ", ".join(
                    (f"{key}={g(value)}" for key, value in prop.items()))
                print(
                    f'running_operator bpy.ops.{self.operator_bl_idname}'
                    f'("{self.operator_context}"{", " + ops_property if ops_property else ops_property})',
                )
        except Exception as e:
            print('running_operator ERROR', e)

    def running_by_script(self):
        try:
            try_call_exec(self.operator_script)
        except Exception as e:
            print(f"running_operator_script ERROR\t\n{self.operator_script}\n", e)
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    def operator_tmp_kmi_properties_clear(self):
        properties = self.operator_tmp_kmi.properties
        for key in list(properties.keys()):
            properties.pop(key)

    def __init_operator__(self):
        self.__init_direction_by_sort__()
        self.operator_context = 'INVOKE_DEFAULT'
        self.operator_bl_idname = 'mesh.primitive_monkey_add'
        self.operator_properties = r'{}'
