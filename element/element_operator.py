import bpy
from bpy.app.translations import pgettext
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ..utils import PropertySetUtils
from ..utils.enum import ENUM_OPERATOR_CONTEXT, ENUM_OPERATOR_TYPE
from ..utils.public_cache import cache_update_lock
from ..utils.secure_call import secure_call_eval, secure_call_exec


class OperatorProperty:
    def __analysis_operator_properties__(self, properties_string):
        """解析操作符属性"""
        try:
            ps = f"dict{properties_string}"
            print("__analysis_operator_properties__\n", ps)
            properties = secure_call_eval(ps)  # 高危
            if properties:
                self["operator_properties"] = str(properties)
        except Exception as e:
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    @cache_update_lock
    def update_operator(self) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        bpy.ops.transform.translate(value=(0.109431, 2.16517, 0), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False, snap_target='CLOSEST', use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True, use_snap_selectable=False)
        """
        if self.is_operator:
            value = self.operator_bl_idname
            key = 'operator_bl_idname'
            if value.startswith('bpy.ops.'):
                self[key] = value = value[8:]
            if ('(' in value) and (')' in value):
                if value.endswith('()'):
                    self[key] = value[:-2]
                else:
                    index = value.index('(')
                    self[key] = value[:index]  # 将后面的切掉
                    self.__analysis_operator_properties__(value[index:])
            self.to_operator_tmp_kmi()

    @cache_update_lock
    def update_operator_properties(self) -> None:
        self.to_operator_tmp_kmi()

    operator_bl_idname: StringProperty(name='Operator bl_idname',
                                       description='Default is to add the monkey head \n only take the back identifier \nbpy.ops.mesh.primitive_monkey_add -> mesh.primitive_monkey_add',
                                       update=lambda self, context: self.update_operator())

    operator_context: EnumProperty(name='Operator Context',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='Operator Property',
                                        update=lambda self, context: self.update_operator_properties())

    operator_type: EnumProperty(name='Operator Type',
                                items=ENUM_OPERATOR_TYPE,
                                default='OPERATOR'
                                )
    operator_script: StringProperty(name='Operator Script', default='print("Emm")')

    preview_operator_script: BoolProperty(name='Preview Script', default=True)

    def update_operator_properties_sync_from_temp_properties(self, _):
        if self.is_operator:
            self.from_tmp_kmi_operator_update_properties()
            self['operator_properties_sync_from_temp_properties'] = False

    def update_operator_properties_sync_to_properties(self, _):
        if self.is_operator:
            self.to_operator_tmp_kmi()
            self['operator_properties_sync_to_properties'] = False

    operator_properties_sync_from_temp_properties: BoolProperty(
        name='From Prop Update',
        update=update_operator_properties_sync_from_temp_properties)
    operator_properties_sync_to_properties: BoolProperty(
        name='Update To Prop',
        update=update_operator_properties_sync_to_properties)

    # 直接将operator的self传给element,让那个来进行操作

    @property
    def properties(self):
        """获取操作符的属性"""
        try:
            return secure_call_eval(self.operator_properties)
        except Exception as e:
            print('Properties Error', self.operator_properties, e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return {}

    @property
    def operator_tmp_kmi(self) -> 'bpy.types.KeyMapItem':
        """操作符临时 keymap item"""
        from ..utils.public_key import get_temp_kmi_by_id_name
        return get_temp_kmi_by_id_name(self.operator_bl_idname)

    @property
    def operator_tmp_kmi_properties(self) -> dict:
        """操作符临时 keymap item 属性"""
        from ..utils.public_key import get_kmi_operator_properties
        properties = get_kmi_operator_properties(self.operator_tmp_kmi)
        return properties

    @property
    def operator_func(self) -> 'bpy.types.Operator':
        """获取操作符

        Returns:
            bpy.types.Operator: _description_
        """
        sp = self.operator_bl_idname.split('.')
        if len(sp) == 2:
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            return func

    @property
    def __operator_id_name_is_validity__(self) -> bool:
        """反回操作符id_name是否有效的布尔值"""
        try:
            fun = self.operator_func
            fun.get_rna_type()
            return fun is not None
        except Exception as e:
            from ..utils.public import get_debug
            if get_debug("operator"):
                print(e.args)
                import traceback
                traceback.print_stack()
                traceback.print_exc()
            return False

    @property
    def __operator_properties_is_validity__(self) -> bool:
        """反回操作符属性是否有效的布尔值"""
        try:
            secure_call_eval(self.operator_properties)
            return True
        except Exception as e:
            from ..utils.public import get_debug
            if get_debug("operator"):
                print(e.args)
                import traceback
                traceback.print_stack()
                traceback.print_exc()
            return False


class ElementOperator(OperatorProperty):

    def to_operator_tmp_kmi(self) -> None:
        """从此元素的属性更新到临时 keymap item"""
        if not self.is_operator:
            Exception(f'{self}不是操作符')
        self.operator_tmp_kmi_properties_clear()
        PropertySetUtils.set_operator_property_to(self.operator_tmp_kmi.properties, self.properties)

    def from_tmp_kmi_operator_update_properties(self) -> None:
        """从临时 keymap item 更新到属性"""
        properties = self.operator_tmp_kmi_properties
        if self.properties != properties:
            self['operator_properties'] = str(properties)

    def running_operator(self) -> Exception:
        """运行此元素的操作符
        """
        if self.operator_type == "OPERATOR":
            return self.__running_by_bl_idname__()
        elif self.operator_type == "SCRIPT":
            return self.__running_by_script__()
        else:
            return Exception(f'{self}操作符类型错误')

    @property
    def __operator_name__(self) -> str:
        if self.operator_type == "OPERATOR":
            func = self.operator_func
            if func:
                rna = func.get_rna_type()
                return pgettext(rna.name, rna.translation_context)

    def __running_by_bl_idname__(self):
        """通过bl_idname运行操作符
        """
        try:
            prop = secure_call_eval(self.operator_properties)
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
            return e

    def __running_by_script__(self):
        """运行自定义脚本"""
        try:
            secure_call_exec(self.operator_script)
        except Exception as e:
            print(f"running_operator_script ERROR\t\n{self.operator_script}\n", e)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            return e

    def operator_tmp_kmi_properties_clear(self):
        """清空临时 keymap item 属性"""
        properties = self.operator_tmp_kmi.properties
        for key in list(properties.keys()):
            properties.pop(key)

    def __init_operator__(self):
        """添加元素时初始化操作符属性"""
        self.__init_direction_by_sort__()
        self.operator_context = 'INVOKE_DEFAULT'
        self.operator_bl_idname = 'mesh.primitive_monkey_add'
        self.operator_properties = r'{}'
