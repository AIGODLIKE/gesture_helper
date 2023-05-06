from bpy.app.translations import contexts as i18n_contexts

from bpy.types import EnumPropertyItem, UILayout

from ..property import get_rna_data


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
                     'alert', 'use_property_decorate', 'use_property_split', 'emboss_enum', 'enabled', 'alignment',
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

    ENUM_TYPE_UI = [
        ('GESTURE', 'Gesture', 'emm'),
        ('MENU', 'Menu', 'menu'),
        ('MENU_PIE', 'Pie Panel', '饼菜单,指定快捷键设置弹出饼菜单,也可设置为手势系统,通过手势来'),
        ('LAYOUT', 'Layout', 'layout'),
    ]
    ENUM_TYPE_UI_LAYOUT = {
        # ('SEPARATOR_SPACER', 'Separator Spacer', ''),  # TODO 用作Separator的附加属性
        ('', 'General', '',),
        ('SEPARATOR', 'Separator', '',),

        ('', 'Layout', '',),
        ('LABEL', 'Label', '',),
        ('ROW', 'Row', '',),
        ('BOX', 'Box', '',),
        ('SPLIT', 'Split', '',),
        ('COLUMN', 'Column', '',),

        ('', 'other', '',),
        ('MENU_PIE', 'Menu Pie', '',),
        ('MENU', 'Menu', '',),
        ('PROP', 'Prop', '',),
        ('OPERATOR', 'Operator', '',),
        # operator_menu_hold
        # operator_enum
        # operator_menu_enum
        # template_operator_search
        # popup_menu_pie
        # ('',            'popup_menu', ''),
    }

    ENUM_TYPE_SELECT_STRUCTURE = from_each_as_enum(PublicTuple.SELECT_STRUCTURE_ELEMENT)

    ENUM_iCON = get_rna_data(EnumPropertyItem, 'icon')

    ENUM_UI_LAYOUT_EMBOSS = get_rna_data(UILayout, 'emboss')
    ENUM_UI_LAYOUT_ALIGNMENT = get_rna_data(UILayout, 'alignment')
    ENUM_UI_LAYOUT_DIRECTION = get_rna_data(UILayout, 'direction')
    ENUM_OPERATOR_CONTEXT = get_rna_data(UILayout, 'operator_context')
    ENUM_CTEXT = get_i18n_enum()


class PublicData(PublicEnum, PublicTuple):
    DEFAULT_KEYMAPS = {'3D View', 'Window'}  # 默认添加keymaps

    PROP_DEFAULT_TIME = {'max': 2000, 'min': -1, 'default': 300}
    PROP_DEFAULT_SKIP = {'options': {'HIDDEN', 'SKIP_SAVE', }}
