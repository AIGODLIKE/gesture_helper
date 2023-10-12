from __future__ import annotations

import ast

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from .element_prop_poll import ElementPropPoll
from ...public import PublicData, PublicClass, ElementType, PublicPropertyGroup, TempKey


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

    alignment: EnumProperty(name='对齐模式', **PublicData.PROP_UI_LAYOUT_ALIGNMENT)
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

        # self._by_heading_set_name()
        ...

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
    # gesture_type: str
    # is_gesture_type: bool

    @property
    def gesture_type_is_direction(self):
        return self.gesture_position == 'DIRECTION'

    @property
    def gesture_position_is_down(self):
        return self.gesture_position == 'DOWN'

    @property
    def gesture_is_direction_mode(self):
        return self.gesture_position == 'DIRECTION'

    gesture_position: EnumProperty(items=PublicData.ENUM_GESTURES_TYPE,
                                   default='DIRECTION',
                                   name='',
                                   )
    gesture_direction: EnumProperty(items=PublicData.ENUM_GESTURE_DIRECTION)


class PanelProp(PropertyGroup):
    def _update_panel(self, context) -> None:
        """更新面板数据,更改名称或是标题时更新"""
        # self._refresh_panel()

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

    # def _space_items(self, context):
    #     """反回空间类型的枚举
    #
    #     Args:
    #         context (_type_): _description_
    #
    #     Returns:
    #         _type_: _description_
    #     """
    #     space_items = map(
    #         lambda i: i[:-1] + ((1 << i[-1]),), PublicData.ENUM_SPACE_TYPE)
    #
    #     return [i for i in space_items if i[0] not in PublicData.SPACE_MATCHING_REGION_TYPE[self.region_type]]
    #
    # space_type: EnumProperty(name='空间类型',
    #                          items=_space_items,
    #                          update=_update_panel,
    #                          get=_get_space,
    #                          set=_set_space,
    #                          )

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
                            #  'Multiple panels with this type can be used as part of a list depending on data external
                             to the UI. Used to create panels for the modifiers and other stacks.'),
                            ''',
                             options={'ENUM_FLAG'},
                             update=_update_panel,
                             )


class OperatorProp(PropertyGroup, TempKey):
    last_operator_element = None
    last_operator_element_idname = None

    def get_operator_func(self) -> 'bpy.types.Operator':
        """获取操作符的方法

        Returns:
            bpy.types.Operator: _description_
        """
        sp = self.operator.split('.')
        if len(sp) == 2:
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            return func

    def running_operator(self) -> None:
        """运行此self的操作符
        """
        try:
            prop = ast.literal_eval(self.operator_property)
            func = self.get_operator_func()
            if func:
                func(self.operator_context, True, **prop)
                print(
                    f'running_operator bpy.ops.{self.operator}'
                    f'( "{self.operator_context}", {self.operator_property[1:-1]})',
                )
        except Exception as e:
            print('running_operator ERROR', e)

    @property
    def temp_kmi(self):
        return self.get_temp_kmi(self.operator)

    def _set_operator(self, value: str) -> None:
        """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
        掐头去尾
        """
        self['operator'] = value
        if value.startswith('bpy.ops.'):
            self['operator'] = value = value[8:]
        if ('(' in value) and (')' in value):
            if value.endswith('()'):
                self['operator'] = value[:-2]
            else:
                index = value.index('(')
                self['operator'] = value[:index]
                self._from_copy_operator_info_get_operator_property(value[index:])

    def _get_operator(self) -> str:
        if 'operator' not in self:
            return 'mesh.primitive_monkey_add'
        return self['operator']

    def _from_copy_operator_info_get_operator_property(self, string):
        """从复制的操作符信息获取操作符属性"""
        prop_dict = ast.literal_eval(self.operator_property)
        prop_dict.update(self._get_operator_property(string))
        self.operator_property = str(prop_dict)
        self.set_operator_property_to(self.operator_property, self.temp_kmi.properties)

    operator: StringProperty(name='操作符',
                             description='输入操作符,将会自动格式化\n'
                                         'bpy.ops.screen.back_to_previous() >> mesh.primitive_monkey_add',
                             set=_set_operator,
                             get=_get_operator,
                             )

    operator_property: StringProperty(name='操作符属性', default=r'{}',
                                      )

    operator_context: EnumProperty(name='操作符上下文',
                                   **PublicData.PROP_OPERATOR_CONTEXT,
                                   )

    def draw_operator_property_set_layout(self, layout):
        layout.template_keymap_item_properties(self.temp_kmi)
        self.from_draw_update_operator_stats()

    def from_draw_update_operator_stats(self):
        kmi = self.temp_kmi
        temp_kmi_prop = self.from_kmi_get_operator_properties(kmi)

        if OperatorProp.last_operator_element != self:  # change element
            OperatorProp.last_operator_element = self
            print('change operator element', self.name)
            self.set_operator_property_to(self.operator_property, kmi.properties)

        elif OperatorProp.last_operator_element_idname != kmi.idname:  # change idname
            OperatorProp.last_operator_element_idname = kmi.idname
            self.set_operator_property_to(self.operator_property, kmi.properties)
            print('change operator idname', kmi.idname)
        elif temp_kmi_prop != self.operator_property:  # change properties
            self['operator_property'] = temp_kmi_prop

            print('change operator property', )


class PollProp(ElementPropPoll):
    is_available_select_structure: BoolProperty(name='是有效的选择结构,', default=True, )

    @property
    def poll_bool(self) -> bool:
        """反回当前self的poll

        Returns:
            bool: _description_
        """

        try:
            poll = self._from_poll_string_get_bool(self.poll_string)
            return poll
        except Exception as e:
            print(f'ERROR:\tpoll_bool  {self.poll_string}\t', e.args, self.poll_args)
            return False

    def _update_string(self, context):
        a = self.poll_bool

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
        update=_update_string,
    )


class PropertyProp:
    property: StringProperty(
        # set=set_property,
        # get=get_property,
        default='bpy.context.object.scale',
    )

    data: StringProperty(default='bpy.context.object')
    property_suffix: StringProperty(default='scale', name='属性后缀')


class ElementProp(
    IconProp,
    MenuProp,
    PollProp,
    PanelProp,
    GestureProp,
    PropertyProp,
    OperatorProp,
    UILayoutProp,

    PublicClass,
    ElementType,
    PublicPropertyGroup,
):
    _selected_key = 'is_selected'
    children_element: 'list[ElementProp]'

    def _get_selected(self) -> bool:
        key = self._selected_key
        if key in self:
            return self[key]
        return False

    def _set_selected(self, value) -> None:
        key = self._selected_key
        for element in self.parent_system.children_element_recursion:
            element['is_selected'] = (element == self)
        self[key] = value

    def _update_selected(self, context) -> None:
        ...

    is_expand: BoolProperty(name='Expand Show Child Element',
                            default=True)
    is_enabled: BoolProperty(name='Enabled Element Show, If False Not Show Child And Draw',
                             default=True)
    is_selected: BoolProperty(get=_get_selected,
                              set=_set_selected,
                              update=_update_selected,
                              )

    @property
    def is_draw(self) -> bool:
        """是否可绘制"""
        return self.is_enabled

    @property
    def is_allow_have_child(self) -> bool:
        """允许拥有子级的"""
        return self.type.lower() in self.TYPE_ALLOW_CHILD

    @property
    def is_draw_child(self):
        """需要绘制子级的"""
        return self.is_allow_have_child and self.is_enabled

    @property
    def gesture_is_have_child(self) -> bool:
        return self.gesture_type.lower() in ('child_gestures',) and self.is_gesture_type

    @property
    def gesture_is_operator(self) -> bool:
        return self.gesture_type.lower() == 'operator'
