import bpy
from bpy.app.translations import pgettext, pgettext_n
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty
from mathutils import Vector

from .element_modal_operator import ElementModalOperatorEventItem
from ..debug import TMP_KMI_SYNC_DEBUG
from ..utils.enum import ENUM_OPERATOR_CONTEXT, ENUM_OPERATOR_TYPE
from ..utils.property import set_property_to_kmi_properties
from ..utils.public_cache import cache_update_lock
from ..utils.secure_call import secure_call_eval, secure_call_exec


class ModalProperty:
    modal_events_index: bpy.props.IntProperty(name='Modal Event Index', default=-1)
    modal_events: CollectionProperty(type=ElementModalOperatorEventItem)

    last_modal_operator_property: bpy.props.StringProperty(name='Last Modal Operator Property', default="{}")

    @property
    def is_not_recommended_as_modal(self):
        """一部分操作符不建议使用模态来控制
        列如已经有modal操作写法的操作符
        移动旋转等操作
        is_array不推荐使用
        """
        if self.operator_is_modal:
            if self.operator_bl_idname in [
                "transform.translate",
                "transform.rotate",
                "transform.resize",
            ]:
                return True
            if self.operator_func:
                if rna := self.operator_func.get_rna_type():
                    for prop in rna.properties:
                        if getattr(prop, "is_array", False):
                            return True
        return False

    @property
    def active_event(self) -> ElementModalOperatorEventItem | None:
        """活动事件项"""
        if len(self.modal_events) > self.modal_events_index and self.modal_events:
            return self.modal_events[self.modal_events_index]
        return None

    def __running_by_modal__(self):
        with bpy.context.temp_override(element=self, gesture=self.parent_gesture):
            bpy.ops.gesture.element_modal_event("INVOKE_DEFAULT", False)

    def draw_modal_property(self, layout):
        if self.active_event:
            self.active_event.draw_modal(layout)
        else:
            layout.label(text='No active modal event')

    @property
    def modal_properties(self):
        """获取操作符的属性"""
        try:
            return secure_call_eval(self.last_modal_operator_property)
        except Exception as e:
            print('Properties Error')
            print(self.name)
            print(f"bpy.ops.{self.operator_bl_idname}")
            print(self.last_modal_operator_property)
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            self['last_modal_operator_property'] = "{}"
            return {}

    @property
    def last_properties(self):
        """反回上一次的属性
        没有则反回默认的"""
        if self.modal_properties:
            return self.modal_properties
        return self.properties

    def run_element_modal_event(self, ops, context, event) -> bool:
        # print("run_element_modal_event", event.type, event.value)
        if event.type in ("MOUSEMOVE", "INBETWEEN_MOUSEMOVE"):
            last_mouse = getattr(ops, "mouse", None)
            mouse = Vector((event.mouse_x, event.mouse_y))
            is_change = False
            for e in self.modal_events:
                if e.is_mouse_move_event and last_mouse != mouse:
                    is_change |= e.number_mouse_move_execute(ops, context, event)  # 鼠标事件时不反回
            if is_change:  # 如果鼠标值移动并且修改了值的
                ops.start_mouse(event)
            return is_change  # 修改了值就要更新一下操作符再执行一次
        else:
            for e in self.modal_events:
                if not e.is_mouse_move_event:
                    if e.modal_execute(ops, context, event):
                        return True
            return False

    def get_header_text(self, properties: dict):
        def gkn(k):
            text = self.operator_func.get_rna_type().properties[k].name
            return bpy.app.translations.pgettext_iface(text)

        return "  ".join([f"{gkn(k)}:{v}" for k, v in properties.items()])


class ScriptOperator:
    """脚本操作符"""
    operator_script: StringProperty(name='Operator Script', default='print("Emm")')

    preview_operator_script: BoolProperty(name='Preview Script', default=True)

    def __running_by_script__(self):
        """运行自定义脚本"""
        try:
            res = secure_call_exec(self.operator_script)
            if res is None:
                ...
            elif isinstance(res, str):
                return res

        except Exception as e:
            print(f"running_operator_script ERROR\t\n{self.operator_script}\n", e)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            print("运行错误,")
            return e


class RunOperatorPropertiesSync:
    def to_operator_tmp_kmi(self) -> None:
        """从此元素的属性更新到临时 keymap item"""
        if not self.is_operator:
            Exception(f'{self}不是操作符')
        self.operator_tmp_kmi_properties_clear()
        set_property_to_kmi_properties(self.operator_tmp_kmi.properties, self.properties)

    def from_tmp_kmi_operator_update_properties(self) -> None:
        """从临时 keymap item 更新到属性"""
        if TMP_KMI_SYNC_DEBUG:
            print("from_tmp_kmi_operator_update_properties", )
        temp_kmi_properties = self.operator_tmp_kmi_properties
        if TMP_KMI_SYNC_DEBUG:
            print(temp_kmi_properties)
            print(self.properties)
        if self.properties != temp_kmi_properties:
            self['operator_properties'] = str(temp_kmi_properties)

    def operator_tmp_kmi_properties_clear(self):
        """清空临时 keymap item 属性"""
        properties = self.operator_tmp_kmi.properties
        for key in list(properties.keys()):
            properties.pop(key)

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


class RunOperator:
    """Blender操作符"""

    @property
    def __operator_name__(self) -> str | None:
        if self.operator_type == "OPERATOR":
            func = self.operator_func
            if func:
                rna = func.get_rna_type()
                return pgettext(rna.name, rna.translation_context)
        return None

    @property
    def __operator_original_name__(self) -> str | None:
        """原名称"""
        if self.operator_type == "OPERATOR":
            func = self.operator_func
            if func:
                rna = func.get_rna_type()
                return pgettext_n(rna.name, rna.translation_context)
        return None

    def __running_by_bl_idname__(self, operator_properties: str = None):
        """通过bl_idname运行操作符"""
        if operator_properties is None:
            operator_properties = self.operator_properties
        try:
            if func := self.operator_func:
                if isinstance(operator_properties, dict):
                    prop = operator_properties
                else:
                    prop = secure_call_eval(operator_properties)

                func(self.operator_context, True, **prop)

                def g(v):
                    return f'"{v}"' if type(v) is str else v

                ops_property = ", ".join(
                    (f"{key}={g(value)}" for key, value in prop.items()))
                print(
                    f'running_operator bpy.ops.{self.operator_bl_idname}'
                    f'("{self.operator_context}"{", " + ops_property if ops_property else ops_property})',
                    prop
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            traceback.print_stack()
            print('__running_by_bl_idname__ ERROR', e)
            return e


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
        print("update_operator_properties:", self.operator_properties)
        self.to_operator_tmp_kmi()

    operator_bl_idname: StringProperty(name='Operator bl_idname',
                                       description='Default is to add the monkey head \n only take the back identifier \nbpy.ops.mesh.primitive_monkey_add -> mesh.primitive_monkey_add',
                                       update=lambda self, context: self.update_operator())

    operator_context: EnumProperty(name='Operator Context',
                                   items=ENUM_OPERATOR_CONTEXT)

    operator_properties: StringProperty(name='Operator Property',
                                        default="{}",
                                        update=lambda self, context: self.update_operator_properties())

    operator_type: EnumProperty(name='Operator Type',
                                items=ENUM_OPERATOR_TYPE,
                                default='OPERATOR'
                                )

    # 直接将operator的self传给element,让那个来进行操作

    @property
    def properties(self):
        """获取操作符的属性"""
        try:
            return secure_call_eval(self.operator_properties)
        except Exception as e:
            print('Properties Error')
            print(self.name)
            print(f"bpy.ops.{self.operator_bl_idname}")
            print(self.operator_properties)
            print(e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()
            self['operator_properties'] = "{}"
            return {}

    @property
    def operator_func(self) -> 'bpy.types.Operator | None':
        """获取操作符

        Returns:
            bpy.types.Operator: _description_
        """
        sp = self.operator_bl_idname.split('.')
        if len(sp) == 2:
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            return func
        return None

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


class ElementOperator(OperatorProperty, ModalProperty, RunOperator, ScriptOperator, RunOperatorPropertiesSync):

    @property
    def operator_is_script(self):
        return self.operator_type == "SCRIPT"

    @property
    def operator_is_operator(self):
        return self.operator_type == "OPERATOR"

    @property
    def operator_is_modal(self):
        return self.operator_type == "MODAL"

    def running_operator(self) -> Exception:
        """运行此元素的操作符"""
        if self.operator_is_operator:
            return self.__running_by_bl_idname__()
        elif self.operator_is_script:
            return self.__running_by_script__()
        elif self.operator_is_modal:
            return self.__running_by_modal__()
        else:
            return Exception(f'{self}操作符类型错误')

    def __init_operator__(self):
        """添加元素时初始化操作符属性"""
        self.__init_direction_by_sort__()
        self.operator_context = 'INVOKE_DEFAULT'
        self.operator_bl_idname = 'mesh.primitive_monkey_add'
        self.operator_properties = r'{}'

    def check_operator_poll(self):
        if self.operator_is_operator or self.operator_is_modal:
            # 需要检查是否需要运行操作符
            poll = self.operator_func.poll()
            if not poll:
                context = bpy.context
                at = context.area.type
                print(
                    f"Gesture Poll 失败 {self.parent_gesture} {self.operator_bl_idname} area:{at} mode:{context.mode}")
            return poll
        return True
