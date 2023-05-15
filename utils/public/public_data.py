from os.path import basename, dirname, realpath

from bpy.app.translations import contexts as i18n_contexts
from bpy.props import EnumProperty
from bpy.types import EnumPropertyItem, UILayout, PreferencesView

from ..utils import get_rna_data


def get_i18n_enum():
    data = []
    for item in dir(i18n_contexts):
        prop = getattr(i18n_contexts, item, None)
        if prop and type(prop) == str:
            if item in ('__doc__',):
                continue
            if 'id_' == item[:3]:
                add = item[3:].replace('_', ' ')
            else:
                add = item.replace('_', ' ')
            data.append((item, add.title(), ''))
    return data


class PublicTuple:
    SELECT_STRUCTURE_ELEMENT = ('if', 'elif', 'else')
    TYPE_ALLOW_CHILD = [
        *SELECT_STRUCTURE_ELEMENT,
        'box', 'row', 'split', 'column', 'menu_pie'
    ]

    CANNOT_ACT_AS_CHILD = ['menu_pie', ]  # 无法作为子级 除选择结构外
    UI_LAYOUT_INCOMING_ARGUMENTS = {
        'box': [],
        'menu_pie': [],  # 用column的数据
        'separator_spacer': [],
        'separator': ['factor'],
        'row': ['heading', 'align', 'translate',
                # 'heading_ctxt',# TODO ctxt
                ],
        'prop': ['text', 'property', 'expand', 'translate', 'slider', 'emboss', 'index', 'icon_value',
                 'invert_checkbox', 'toggle',
                 # 'data', #自动获取
                 #  'icon',
                 #  'icon_only',
                 #  'text_ctxt',
                 #  'event',
                 #  'full_event',
                 ],
        'split': ['factor', 'align', ],
        'label': ['text', 'translate', 'icon',
                  #   'text_ctxt',
                  # 'icon_value',
                  ],

        'menu': ['menu', 'text', 'translate', 'icon',
                 #  'text_ctxt',
                 #  'icon_value',
                 ],
        'menu_contents': ['menu'],

        'column': ['heading', 'align', 'translate',
                   #    'heading_ctxt',
                   ],
        'operator': ['operator', 'text', 'translate', 'icon', 'emboss', 'depress',
                     #  'text_ctxt',
                     #  'icon_value',
                     ],
        'uilayout': ['activate_init', 'active', 'scale_x', 'scale_y', 'ui_units_x', 'ui_units_y', 'active_default',
                     'alert', 'use_property_decorate', 'use_property_split', 'emboss_enum', 'nabled', 'alignment',
                     #  'direction', only read
                     #  'operator_context', operator
                     ],
        # 选择结构
        'if': ['poll_string'],
        'elif': ['poll_string'],
        'else': ['poll_string'],
    }


class PublicEnum:
    @staticmethod
    def from_each_as_enum(enum):
        return [(i.upper(), i, i)
                for i in enum]

    ENUM_SELECT_STRUCTURE_TYPE = from_each_as_enum(PublicTuple.SELECT_STRUCTURE_ELEMENT)

    ENUM_UI_TYPE = [
        ('UI_LAYOUT', 'UI Layout', ''),
        ('SELECT_STRUCTURE', 'Select Structure', ''),
    ]
    ENUM_UI_SYSTEM_TYPE = [
        ('GESTURE', 'Gesture', 'emm'),
        ('MENU', 'Menu', 'menu'),
        ('MENU_PIE', 'Pie Panel', '饼菜单,指定快捷键设置弹出饼菜单,也可设置为手势系统,通过手势来'),
        ('LAYOUT', 'Layout', 'layout'),
    ]
    ENUM_UI_LAYOUT_TYPE = [
        ('', 'General', '',),
        ('LABEL', 'Label', '',),
        ('SEPARATOR', 'Separator', '',),
        ('SEPARATOR_SPACER', 'Separator Spacer', ''),  # TODO 用作Separator的附加属性

        ('', 'Layout', '',),
        ('ROW', 'Row', '',),
        ('COLUMN', 'Column', '',),
        ('BOX', 'Box', '',),
        ('SPLIT', 'Split', '',),

        ('', 'Emm', '',),
        ('PROP', 'Prop', '',),
        ('OPERATOR', 'Operator', '',),

        ('', 'other', '',),
        ('MENU_PIE', 'Menu Pie', '',),
        ('MENU', 'Menu', '',),

        # operator_menu_hold
        # operator_enum
        # operator_menu_enum
        # template_operator_search
        # popup_menu_pie
        # ('',            'popup_menu', ''),
    ]

    ENUM_ICON = get_rna_data(EnumPropertyItem, 'icon')

    ENUM_UI_LAYOUT_EMBOSS = get_rna_data(UILayout, 'emboss')
    ENUM_UI_LAYOUT_ALIGNMENT = get_rna_data(UILayout, 'alignment')
    ENUM_UI_LAYOUT_DIRECTION = get_rna_data(UILayout, 'direction')
    ENUM_OPERATOR_CONTEXT = get_rna_data(UILayout, 'operator_context')
    ENUM_CTEXT = get_i18n_enum()


class PublicData(PublicEnum, PublicTuple):
    DEFAULT_KEYMAPS = {'3D View', 'Window'}  # 默认添加keymaps

    PROP_DEFAULT_TIME = {'max': 2000, 'min': -1, 'default': 300}
    PROP_DEFAULT_SKIP = {'options': {'HIDDEN', 'SKIP_SAVE', }}

    G_ADDON_NAME = basename(dirname(dirname(dirname(realpath(__file__)))))  # addon folder path name


class PieProperty:
    PIE_PROPERTY_ITEMS = ['pie_animation_timeout',
                          'pie_tap_timeout',
                          'pie_initial_timeout',
                          'pie_menu_radius',
                          'pie_menu_threshold',
                          'pie_menu_confirm',
                          ]
    PIE_ANIMATION_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_animation_timeout', fill_copy=True)
    PIE_TAP_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_tap_timeout', fill_copy=True)
    PIE_INITIAL_TIMEOUT_DATA = get_rna_data(
        PreferencesView, 'pie_initial_timeout', fill_copy=True)
    PIE_MENU_RADIUS_DATA = get_rna_data(
        PreferencesView, 'pie_menu_radius', fill_copy=True)
    PIE_MENU_THRESHOLD_DATA = get_rna_data(
        PreferencesView, 'pie_menu_threshold', fill_copy=True)
    PIE_MENU_CONFIRM_DATA = get_rna_data(
        PreferencesView, 'pie_menu_confirm', fill_copy=True)
    # custom element property   default
    PIE_ANIMATION_TIMEOUT_DATA['default'] = 6
    PIE_TAP_TIMEOUT_DATA['default'] = 20
    PIE_INITIAL_TIMEOUT_DATA['default'] = 0
    PIE_MENU_RADIUS_DATA['default'] = 100
    PIE_MENU_THRESHOLD_DATA['default'] = 20
    PIE_MENU_CONFIRM_DATA['default'] = 60

    PIE_ANIMATION_TIMEOUT_DATA['min'] = PIE_TAP_TIMEOUT_DATA['min'] = PIE_INITIAL_TIMEOUT_DATA['min'] = \
        PIE_MENU_RADIUS_DATA['min'] = PIE_MENU_THRESHOLD_DATA['min'] = PIE_MENU_CONFIRM_DATA['min'] = -1
    PIE_ANIMATION_TIMEOUT_DATA['soft_min'] = PIE_TAP_TIMEOUT_DATA['soft_min'] = PIE_INITIAL_TIMEOUT_DATA['soft_min'] = \
        PIE_MENU_RADIUS_DATA['soft_min'] = PIE_MENU_THRESHOLD_DATA['soft_min'] = PIE_MENU_CONFIRM_DATA['soft_min'] = 0


class ElementType:
    """在添加项和元素中继承使用"""
    ui_type: EnumProperty(items=PublicData.ENUM_UI_TYPE)
    ui_layout_type: EnumProperty(items=PublicData.ENUM_UI_LAYOUT_TYPE)
    select_structure_type: EnumProperty(items=PublicData.ENUM_SELECT_STRUCTURE_TYPE)

    @property
    def enum_type_data(self) -> 'list[tuple[str,str,str]]':
        return PublicData.ENUM_UI_LAYOUT_TYPE if self.is_ui_layout_type else PublicData.ENUM_SELECT_STRUCTURE_TYPE

    @property
    def is_select_structure_type(self) -> bool:
        return self.ui_type == 'SELECT_STRUCTURE'

    @property
    def is_ui_layout_type(self) -> bool:
        return self.ui_type == 'UI_LAYOUT'

    @property
    def type(self) -> str:
        return self.ui_layout_type if self.is_ui_layout_type else self.select_structure_type
