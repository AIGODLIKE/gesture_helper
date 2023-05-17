import ast
import re

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Euler, Matrix, Vector

from ...utils.public import PublicData, TempKey


class UILayoutProp(PublicData):
    # UILayout Property
    default_float = {'min': 0,
                     'soft_max': 20,
                     'soft_min': 0.15,
                     }
    activate_init: BoolProperty()
    active: BoolProperty()
    scale_x: FloatProperty(**default_float)
    scale_y: FloatProperty(**default_float)
    ui_units_x: FloatProperty(**default_float)
    ui_units_y: FloatProperty(**default_float)
    active_default: BoolProperty()

    alert: BoolProperty()
    use_property_decorate: BoolProperty()
    use_property_split: BoolProperty(name='使用属性拆分')

    emboss_enum: EnumProperty(name='emboss enum',
                              description='有两个emboss 这个用于UILayout的输入枚举项',
                              **PublicData.PROP_UI_LAYOUT_EMBOSS,
                              default='NORMAL')
    enabled: BoolProperty(name='启用')

    alignment: EnumProperty('对齐模式', **PublicData.PROP_UI_LAYOUT_ALIGNMENT)
    direction: EnumProperty(name='方向', **PublicData.PROP_UI_LAYOUT_DIRECTION)

    # UILayout property

    # def _update_text(self, context):
    #     self._by_text_set_name()

    text: StringProperty(name='文字',
                         default='text',
                         # update=_update_text,
                         )

    # enum
    ctext: EnumProperty(items=PublicData.ENUM_CTEXT, name='翻译类型')
    text_ctxt: EnumProperty(items=PublicData.ENUM_CTEXT, name='翻译类型')
    heading_ctxt: EnumProperty(items=PublicData.ENUM_CTEXT, name='翻译类型')

    # int
    columns: IntProperty()

    row_major: IntProperty()

    toggle: IntProperty(name='切换',
                        max=1, min=-1, default=1)

    # float

    factor: FloatProperty(name='系数',
                          min=0.01,
                          max=100,
                          soft_max=0.8,
                          soft_min=0.1,
                          step=0.01,
                          default=0.5)

    # bool
    def _update_heading(self, context):
        """更新标题文字
        并自动更新元素名称

        Args:
            context (_type_): _description_
        """

        self._by_heading_set_name()

    align: BoolProperty(name='对齐')
    heading: StringProperty(name='标题',
                            # update=_update_heading,
                            )
    translate: BoolProperty(name='翻译文字')
    invert_checkbox: BoolProperty(name='反转复选框')
    emboss: BoolProperty(name='浮雕')

    expand: BoolProperty(name='扩展')

    slider: BoolProperty()

    depress: BoolProperty()

    even_columns: BoolProperty()
    even_rows: BoolProperty()


class IconProp:
    icon_only: BoolProperty(name='仅显示图标',
                            description='''
                            prop,
                            operator,
                            label,
                            menu,
                            icon_value,
                            template_icon,🚩
                            operator_menu_hold🚩
                            ''')  # 只显示图标
    custom_icon: StringProperty(name='自定义图标', default='')
    icon: StringProperty(name='图标', default='NONE')
    icon_value: IntProperty()


class MenuProp:
    menu_contents: BoolProperty(name='直接显示菜单内容', description='但是此方法绘制出来的会有间隔')
    menu: StringProperty(name='菜单', default='WM_MT_splash_about')


class GestureProp:
    gestures_direction: EnumProperty(items=PublicData.ENUM_GESTURES_DIRECTION,
                                     default='NONE',
                                     name='手势朝向',
                                     )


class PanelProp:
    def _update_panel(self, context) -> None:
        """更新面板数据,更改名称或是标题时更新"""
        self._refresh_panel()

    def _set_space(self, value) -> None:
        """设置空间类型

        Args:
            value (_type_): _description_
        """
        self['space_type'] = value

    def _get_space(self) -> int:
        """反回空间类型的枚举项id（int）

        Returns:
            int: _description_
        """
        if ('space_type' not in self) or (not self['space_type']):
            return 2
        return self['space_type']

    def _space_items(self, context):
        """反回空间类型的枚举

        Args:
            context (_type_): _description_

        Returns:
            _type_: _description_
        """
        space_items = map(
            lambda i: i[:-1] + ((1 << i[-1]),), PublicData.ENUM_SPACE_TYPE)

        return [i for i in space_items if i[0] not in PublicData.SPACE_MATCHING_REGION_TYPE[self.region_type]]

    space_type: EnumProperty(name='空间类型',
                             items=_space_items,
                             update=_update_panel,
                             get=_get_space,
                             set=_set_space,
                             )

    def _get_region(self):
        return self['region_type']

    def _set_region(self, value):
        self['region_type'] = value

    region_type: EnumProperty(name='区域类型',
                              items=PublicData.ENUM_REGION_TYPE,
                              update=_update_panel,
                              default='UI',
                              #   get=_get_region,
                              #   set=_set_region,
                              )

    bl_category: StringProperty(
        name='分类', default='Custom Panel Category', update=_update_panel)
    bl_label: StringProperty(
        name='标签', default='Custom Panel Label', update=_update_panel)

    bl_options: EnumProperty(items=PublicData.ENUM_BL_OPTIONS,
                             description='''Options for this panel type
                            # WARNING 闪退 ('INSTANCED', 'Instanced Panel',
                            #  'Multiple panels with this type can be used as part of a list depending on data external to the UI. Used to create panels for the modifiers and other stacks.'),
                            ''',
                             options={'ENUM_FLAG'},
                             update=_update_panel,
                             )


class OperatorProp(TempKey):
    # def get_operator_func(self) -> 'bpy.types.Operator':
    #     """获取操作符的方法
    #
    #     Returns:
    #         bpy.types.Operator: _description_
    #     """
    #     sp = self.operator.split('.')
    #     if len(sp) == 2:
    #         prefix, suffix = sp
    #         func = getattr(getattr(bpy.ops, prefix), suffix)
    #         return func
    #
    # def running_operator(self) -> None:
    #     """运行此self的操作符
    #     """
    #     try:
    #         prop = ast.literal_eval(self.operator_property)
    #         func = self.get_operator_func()
    #         if func:
    #             func(self.operator_context, True, **prop)
    #             print(f'running_operator Element:{self}\t{self.operator}({self.operator_property[1:-1]})\t{func}\n',
    #                   self.operator_property, self.operator_context,
    #                   )
    #     except Exception as e:
    #         print('running_operator ERROR', e)
    #
    def _get_operator_property(self, string: str) -> dict:
        """将输入的字符串操作符属性转成字典
        用于传入操作符执行操作符用

        Args:
            string (str): _description_

        Returns:
            dict: _description_
        """
        tmp_index = 0
        brackets_index = 0
        property_dict = {}
        for index, value in enumerate(string):

            is_zero = (brackets_index == 0)
            if brackets_index < 0:
                print(Exception('输入数据错误,无法解析', string))
            elif value == '(':
                brackets_index += 1
            elif value == ')':
                brackets_index -= 1
            elif is_zero and value == ',':
                data = string[tmp_index:index]
                print(data)
                sp = data.split('=')
                if len(sp) == 2:
                    property_dict[sp[0]] = ast.literal_eval(sp[1])
            elif is_zero and value == ' ':
                tmp_index = index + 1
            else:
                ...
        return property_dict

    def _set_operator(self, value: str) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.wm.tool_set_by_id(name="builtin.measure")
         p  = r'*(*)'
        Args:
            value (str): _description_
        """

        self['operator'] = value

        if value[:8] == 'bpy.ops.':
            self['operator'] = value = value[8:]
        if ('(' in value) and (')' in value):
            suffix = value[-2:]
            if suffix == '()':
                self['operator'] = value[:-2]
            else:
                self['operator'] = value[:value.index('(')]
                r = re.search(r'[(].*[)]', value)  # 操作符参数
                prop_dict = ast.literal_eval(self.operator_property)
                prop_dict.update(self._get_operator_property(r.group()[1:-1]))
                self.operator_property = str(prop_dict)

    def _get_operator_string(self) -> str:
        """获取操作符的字符串

        Returns:
            str: _description_
        """
        if 'operator' not in self:
            return 'mesh.primitive_monkey_add'
        return self['operator']

    def get_tmp_kmi_operator_property(self) -> str:
        """获取临时kmi操作符的属性

        Returns:
            str: _description_
        """
        properties = self.temp_kmi.properties
        prop_keys = dict(properties.items()).keys()
        dictionary = {i: getattr(properties, i, None) for i in prop_keys}
        for item in dictionary:
            prop = getattr(properties, item, None)
            typ = type(prop)
            if prop and typ == Vector:
                # 属性阵列-浮点数组
                dictionary[item] = dictionary[item].to_tuple()
            elif prop and typ == Euler:
                dictionary[item] = dictionary[item][:]
            elif prop and typ == Matrix:
                dictionary[item] = tuple(i[:] for i in dictionary[item])
        return str(dictionary)

    def from_tmp_kmi_get_operator_property(self) -> None:
        """从临时kmi里面获取操作符属性
        """
        self.operator_property = self.get_tmp_kmi_operator_property()

    @staticmethod
    def _for_set_prop(prop, pro, pr):
        for index, j in enumerate(pr):
            try:
                getattr(prop, pro)[index] = j
            except Exception as e:
                print(e.args)

    def set_operator_property_to(self, properties: 'bpy.types.KeyMapItem.properties') -> None:
        """注入operator property
        在绘制项时需要使用此方法
        set operator property
        self.operator_property:

        Args:
            properties (bpy.types.KeyMapItem.properties): _description_
        """
        props = ast.literal_eval(self.operator_property)
        for pro in props:
            pr = props[pro]
            if hasattr(properties, pro):
                if type(pr) == tuple:
                    # 阵列参数
                    self._for_set_prop(properties, pro, pr)
                else:
                    try:
                        setattr(properties, pro, props[pro])
                    except Exception as e:
                        print(e.args)

    def set_operator_property_to_tmp_kmi(self) -> None:
        r"""
        将ui.operator.property设置到tmp_kmi里面
        """
        self.set_operator_property_to(self.temp_kmi.properties)

    @property
    def temp_kmi(self):
        return self.get_temp_kmi(self.operator)

    operator: StringProperty(name='操作符',
                             description='输入操作符,将会自动格式化 bpy.ops.screen.back_to_previous() >> mesh.primitive_monkey_add',
                             set=_set_operator,
                             get=_get_operator_string,
                             )
    operator_context: EnumProperty(name='操作符上下文',
                                   **PublicData.PROP_OPERATOR_CONTEXT,
                                   )
    operator_property: StringProperty(name='操作符属性', default=r'{}', )

    def draw_operator_property_set_layout(self, layout):
        if self.get_tmp_kmi_operator_property
        # layout.template_keymap_item_properties(self.temp_kmi)

    def udpate_(self):


class PollProp:
    poll_string: StringProperty(
        name='条件',
        default='True',
        description='''poll表达式
    {'bpy': bpy,
    'C': bpy.context,
    'D': bpy.data,
    'O': bpy.context.object,
    'mode': bpy.context.mode,
    'tool': bpy.context.tool_settings,
    }
    ''',
    )


class PropertyProp:
    property: StringProperty(
        # set=set_property,
        # get=get_property,
        default='bpy.context.object.scale',
    )

    data: StringProperty(default='bpy.context.object')
    property_suffix: StringProperty(default='scale', name='属性后缀')


class ElementUILayoutProp(
    IconProp,
    MenuProp,
    PollProp,
    PanelProp,
    GestureProp,
    PropertyProp,
    OperatorProp,
    UILayoutProp,
):
    ...


class UIProp:
    ...

