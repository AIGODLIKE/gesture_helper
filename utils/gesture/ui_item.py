from bpy.props import BoolProperty, FloatProperty, EnumProperty, StringProperty, IntProperty
from bpy.types import PropertyGroup

from utils.property import ui_emboss_enum, ui_alignment, ui_direction
from utils.utils import PublicClass, PublicName


class UiItem(PropertyGroup,
             PublicClass,
             PublicName,
             ):

    @property
    def _items(self):
        return self.ui_element_items[self['parent_element_items']]

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
                              **ui_emboss_enum,
                              default='NORMAL')
    enabled: BoolProperty(name='启用')

    alignment: EnumProperty('对齐模式', **ui_alignment)
    direction: EnumProperty(name='方向', **ui_direction)

    # UILayout property

    def _update_text(self, context):
        self._by_text_set_name()

    text: StringProperty(name='文字', default='text', update=_update_text)

    # enum
    # ctext: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
    # text_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
    # heading_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')

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
    heading: StringProperty(name='标题', update=_update_heading)
    translate: BoolProperty(name='翻译文字')
    invert_checkbox: BoolProperty(name='反转复选框')
    emboss: BoolProperty(name='浮雕')

    expand: BoolProperty(name='扩展')

    slider: BoolProperty()

    depress: BoolProperty()

    even_columns: BoolProperty()
    even_rows: BoolProperty()
