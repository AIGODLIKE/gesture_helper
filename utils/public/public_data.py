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


class PublicPoll:
    POLL_ACTIVE_OBJECT_TYPE = {
        'prefix': 'C.object.type == ',
        'suffix': '',
        'name': '活动项物体类型',
        'items': [
            {'name': 'Mesh', 'item': 'MESH', },
            {'name': 'Curve', 'item': 'CURVE', },
            {'name': 'Surface', 'item': 'SURFACE', },
            {'name': 'Metaball', 'item': 'META', },
            {'name': 'Text', 'item': 'FONT', },
            {'name': 'Hair Curves', 'item': 'CURVES', },
            {'name': 'Point Cloud', 'item': 'POINTCLOUD', },
            {'name': 'Volume', 'item': 'VOLUME', },
            {'name': 'Grease Pencil', 'item': 'GPENCIL', },
            {'name': 'Armature', 'item': 'ARMATURE', },
            {'name': 'Lattice', 'item': 'LATTICE', },
            {'name': 'Empty', 'item': 'EMPTY', },
            {'name': 'Light', 'item': 'LIGHT', },
            {'name': 'Light Probe', 'item': 'LIGHT_PROBE', },
            {'name': 'Camera', 'item': 'CAMERA', },
            {'name': 'Speaker', 'item': 'SPEAKER', }, ],
    }

    POLL_MODE_TYPE = {
        'prefix': 'C.mode == ',
        'suffix': '',
        'name': '物体模式',
        'items': [
            {'name': 'Mesh Edit', 'item': 'EDIT_MESH'},
            {'name': 'Curve Edit', 'item': 'EDIT_CURVE'},
            {'name': 'Curves Edit', 'item': 'EDIT_CURVES'},
            {'name': 'Surface Edit', 'item': 'EDIT_SURFACE'},
            {'name': 'Text Edit', 'item': 'EDIT_TEXT'},
            {'name': 'Armature Edit', 'item': 'EDIT_ARMATURE'},
            {'name': 'Metaball Edit', 'item': 'EDIT_METABALL'},
            {'name': 'Lattice Edit', 'item': 'EDIT_LATTICE'},
            None,

            {'name': 'Pose', 'item': 'POSE'},
            {'name': 'Sculpt', 'item': 'SCULPT'},
            {'name': 'Weight Paint', 'item': 'PAINT_WEIGHT'},
            {'name': 'Vertex Paint', 'item': 'PAINT_VERTEX'},
            {'name': 'Texture Paint', 'item': 'PAINT_TEXTURE'},
            {'name': 'Particle', 'item': 'PARTICLE'},
            {'name': 'Object', 'item': 'OBJECT'},
            None,

            {'name': 'Grease Pencil Paint',
             'item': 'PAINT_GPENCIL'},
            {'name': 'Grease Pencil Edit', 'item': 'EDIT_GPENCIL'},
            {'name': 'Grease Pencil Sculpt',
             'item': 'SCULPT_GPENCIL'},
            {'name': 'Grease Pencil Weight Paint',
             'item': 'WEIGHT_GPENCIL'},
            {'name': 'Grease Pencil Vertex Paint',
             'item': 'VERTEX_GPENCIL'},
            {'name': 'Curves Sculpt', 'item': 'SCULPT_CURVES'},
        ],
    }

    POLL_MESH_SELECT_MODE = {
        'prefix': 'tool.mesh_select_mode[:] == ',
        'suffix': '',
        'name': '网格选择模式',
        'items': [

            {'prefix': '', 'suffix': '',
             'item': 'is_select_vert', 'name': '选中了顶点', },
            None,

            {'prefix': 'tool.mesh_select_mode[0] == ',
             'item': True, 'name': '顶点', },
            {'prefix': 'tool.mesh_select_mode[1] == ',
             'item': True, 'name': '边', },
            {'prefix': 'tool.mesh_select_mode[2] == ',
             'item': True, 'name': '面', },
            None,
            {'item': [True, False, False], 'name': '仅顶点', },
            {'item': [False, True, False], 'name': '仅边', },
            {'item': [False, False, True], 'name': '仅面', },
            None,
            {'item': [True, False, True], 'name': '仅 顶点&面', },
            {'item': [False, True, True], 'name': '仅 边&面', },
            {'item': [True, True, False], 'name': '仅 顶点&边', },
            {'item': [True, True, True], 'name': '顶点&边&面', },
        ],
    }
    POLL_REGIONS_TYPE = {
        'prefix': 'C.region.type == ',
        'suffix': '',
        'name': '区域类型',
        'items': [
            {'item': 'WINDOW', 'name': 'Window', },
            {'item': 'HEADER', 'name': 'Header', },
            {'item': 'CHANNELS', 'name': 'Channels', },
            {'item': 'TEMPORARY', 'name': 'Temporary', },
            {'item': 'EXECUTE', 'name': 'Execute Buttons', },
            {'item': 'UI', 'name': 'UI', },
            {'item': 'TOOLS', 'name': 'Tools', },
            {'item': 'TOOL_PROPS', 'name': 'Tool Properties', },
            {'item': 'PREVIEW', 'name': 'Preview', },
            {'item': 'HUD', 'name': 'Floating Region', },
            {'item': 'NAVIGATION_BAR', 'name': 'Navigation Bar', },
            {'item': 'FOOTER', 'name': 'Footer', },
            {'item': 'TOOL_HEADER', 'name': 'Tool Header', },
            {'item': 'XR', 'name': 'XR', },
        ],
    }
    POLL_SPACE_TYPE = {
        'prefix': 'C.space_data.type == ',
        'suffix': '',
        'name': '空间类型',
        'items': [
            {'name': 'Empty', 'item': 'EMPTY', },
            {'name': '3D Viewport', 'item': 'VIEW_3D', },
            {'name': 'UV/Image Editor', 'item': 'IMAGE_EDITOR', },
            {'name': 'Node Editor', 'item': 'NODE_EDITOR', },
            {'name': 'Video Sequencer', 'item': 'SEQUENCE_EDITOR', },
            {'name': 'Movie Clip Editor', 'item': 'CLIP_EDITOR', },
            {'name': 'Dope Sheet', 'item': 'DOPESHEET_EDITOR', },
            {'name': 'Graph Editor', 'item': 'GRAPH_EDITOR', },
            {'name': 'Nonlinear Animation', 'item': 'NLA_EDITOR', },
            {'name': 'Text Editor', 'item': 'TEXT_EDITOR', },
            {'name': 'Python Console', 'item': 'CONSOLE', },
            {'name': 'Info', 'item': 'INFO', },
            {'name': 'Top Bar', 'item': 'TOPBAR', },
            {'name': 'Status Bar', 'item': 'STATUSBAR', },
            {'name': 'Outliner', 'item': 'OUTLINER', },
            {'name': 'Properties', 'item': 'PROPERTIES', },
            {'name': 'File Browser', 'item': 'FILE_BROWSER', },
            {'name': 'Spreadsheet', 'item': 'SPREADSHEET', },
            {'name': 'Preferences', 'item': 'PREFERENCES', },
        ],
    }
    POLL_OTHER = {
        'prefix': '',
        'suffix': '',
        'name': '其它',
        'items': [
            {'item': ' and ',
             'name': 'and',
             'parentheses': False,
             'not_str': True},
            {'item': ' or ',
             'name': 'or',
             'parentheses': False,
             'not_str': True},
            {'item': ' not ',
             'name': 'not',
             'parentheses': False,
             'not_str': True},
            # None,
        ],
    }

    POLL_ALL_LIST = [POLL_MODE_TYPE,
                     POLL_ACTIVE_OBJECT_TYPE,
                     POLL_MESH_SELECT_MODE,
                     None,
                     POLL_SPACE_TYPE,
                     POLL_REGIONS_TYPE,
                     POLL_OTHER
                     ]


class PublicProp:
    SELECT_STRUCTURE_ELEMENT = ['if', 'elif', 'else']
    GESTURE_UI_TYPE = ['operator', 'child_gestures']
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
        'operator': ['operator', 'text',
                     # 'translate', 'icon', 'emboss', 'depress',
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
    SPACE_MATCHING_REGION_TYPE = {
        'WINDOW': ('STATUSBAR',),
        'HEADER': (),
        'UI': ('CONSOLE', 'PREFERENCES', 'TOPBAR', 'INFO', 'OUTLINER', 'PROPERTIES', 'STATUSBAR',),
        'TOOLS': ('GRAPH_EDITOR', 'OUTLINER', 'PROPERTIES', 'INFO', 'TEXT_EDITOR', 'DOPESHEET_EDITOR', 'NLA_EDITOR',
                  'CONSOLE', 'PREFERENCES', 'TOPBAR', 'STATUSBAR'),
        'TOOL_PROPS': (),
        'PREVIEW': (),
        'HUD': (),
        'NAVIGATION_BAR': (),
        'FOOTER': (),
        'TOOL_HEADER': (),
    }


class PublicEnum:
    @staticmethod
    def from_each_as_enum(enum):
        return [(i.upper(), i, i)
                for i in enum]

    ENUM_SELECT_STRUCTURE_TYPE = from_each_as_enum(PublicProp.SELECT_STRUCTURE_ELEMENT)
    ENUM_GESTURE_UI_TYPE = from_each_as_enum(PublicProp.GESTURE_UI_TYPE)

    ENUM_UI_TYPE = [
        ('UI_LAYOUT', 'UI Layout', ''),
        ('SELECT_STRUCTURE', 'Select Structure', ''),
        ('GESTURE', 'Gesture', ''),
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

    ENUM_CTEXT = get_i18n_enum()

    ENUM_GESTURES_TYPE = [
        ('DIRECTION', '方向', 'DIRECTION'),
        ('UP', '顶', 'TRIA_UP_BAR'),
        ('DOWN', '底', 'TRIA_DOWN'),
        ('NONE', '无', ''),
    ]
    ENUM_GESTURE_DIRECTION = [
        ('1', '左', 'TRIA_LEFT'),
        ('2', '右', 'TRIA_RIGHT'),
        ('4', '上', 'TRIA_UP'),
        ('3', '下', 'TRIA_DOWN'),
        ('5', '左上', ''),
        ('6', '右上', ''),
        ('7', '左下', ''),
        ('8', '右下', ''),
    ]
    ENUM_SPACE_TYPE = [
        # ('EMPTY', 'Empty', '', 'NONE', 0),

        ('VIEW_3D', '3D Viewport',
         'Manipulate objects in a 3D environment', 'VIEW3D', 1),
        ('GRAPH_EDITOR', 'Graph Editor',
         'Edit drivers and keyframe interpolation', 'GRAPH', 2),
        ('OUTLINER', 'Outliner',
         'Overview of scene graph and all available data-blocks', 'OUTLINER', 3),
        ('PROPERTIES', 'Properties',
         'Edit properties of active object and related data-blocks', 'PROPERTIES', 4),
        ('FILE_BROWSER', 'File Browser',
         'Browse for files and assets', 'FILEBROWSER', 5),
        ('IMAGE_EDITOR', 'UV/Image Editor',
         'View and edit images and UV Maps', 'IMAGE', 6),
        ('INFO', 'Info', 'Log of operations, warnings and error messages', 'INFO', 7),
        ('NODE_EDITOR', 'Node Editor',
         'Editor for node-based shading and compositing tools', 'NODETREE', 16),
        ('SEQUENCE_EDITOR', 'Video Sequencer',
         'Video editing tools', 'SEQUENCE', 8),
        ('TEXT_EDITOR', 'Text Editor',
         'Edit scripts and in-file documentation', 'TEXT', 9),
        ('CLIP_EDITOR', 'Movie Clip Editor',
         'Motion tracking tools', 'TRACKER', 20),
        ('DOPESHEET_EDITOR', 'Dope Sheet',
         'Adjust timing of keyframes', 'ACTION', 12),
        ('NLA_EDITOR', 'Nonlinear Animation',
         'Combine and layer Actions', 'NLA', 13),
        ('CONSOLE', 'Python Console',
         'Interactive programmatic console for advanced editing and script development', 'CONSOLE', 18),
        ('PREFERENCES', 'Preferences',
         'Edit persistent configuration settings', 'PREFERENCES', 19),
        ('TOPBAR', 'Top Bar',
         'Global bar at the top of the screen for global per-window settings', 'NONE', 21),
        ('STATUSBAR', 'Status Bar',
         'Global bar at the bottom of the screen for general status information', 'NONE', 22),
        ('SPREADSHEET', 'Spreadsheet',
         'Explore geometry data in a table', 'SPREADSHEET', 23),
    ]

    ENUM_REGION_TYPE = [
        ('UI', 'UI', '',),
        ('TOOLS', 'Tools', '',),
        # ('WINDOW', 'Window', '', 'NONE', 0),
        # ('HEADER', 'Header', '', 'NONE', 1),
        #  ('CHANNELS', 'Channels', '', 'NONE', 2),
        #  ('TEMPORARY', 'Temporary', '', 'NONE', 3),
        #  ('EXECUTE', 'Execute Buttons', '', 'NONE', 10),
        # ('TOOL_PROPS', 'Tool Properties', '', 'NONE', 6),
        # ('PREVIEW', 'Preview', '', 'NONE', 7),
        # ('HUD', 'Floating Region', '', 'NONE', 8),
        # ('NAVIGATION_BAR', 'Navigation Bar', '', 'NONE', 9),
        # ('FOOTER', 'Footer', '', 'NONE', 11),
        # ('TOOL_HEADER', 'Tool Header', '', 'NONE', 12),
        #  ('XR', 'XR', '', 'NONE', 13)
    ]
    ENUM_BL_OPTIONS = [
        ('DEFAULT_CLOSED', 'Default Closed',
         'Defines if the panel has to be open or collapsed at the time of its creation.'),
        ('HIDE_HEADER', 'Hide Header',
         'If set to False, the panel shows a header,'
         ' which contains a clickable arrow to collapse the panel and the label(see bl_label).'),
        ('HEADER_LAYOUT_EXPAND', 'Expand Header Layout',
         'Allow buttons in the header to stretch and shrink to fill the entire layout width.'),
    ]


class PublicData(PublicEnum, PublicProp):
    DEFAULT_KEYMAPS = {'3D View', 'Window'}  # 默认添加keymaps

    PROP_ICON = get_rna_data(EnumPropertyItem, 'icon')
    PROP_UI_LAYOUT_EMBOSS = get_rna_data(UILayout, 'emboss')
    PROP_UI_LAYOUT_ALIGNMENT = get_rna_data(UILayout, 'alignment')
    PROP_UI_LAYOUT_DIRECTION = get_rna_data(UILayout, 'direction')
    PROP_OPERATOR_CONTEXT = get_rna_data(UILayout, 'operator_context')

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

    def update_ui_type(self, context):
        ...

    def update_select_structure_type(self, context):
        ...

    ui_type: EnumProperty(items=PublicData.ENUM_UI_TYPE,
                          update=update_ui_type)

    gesture_type: EnumProperty(items=PublicData.ENUM_GESTURE_UI_TYPE, default='OPERATOR')
    ui_layout_type: EnumProperty(items=PublicData.ENUM_UI_LAYOUT_TYPE, default='LABEL')
    select_structure_type: EnumProperty(items=PublicData.ENUM_SELECT_STRUCTURE_TYPE, default='IF',
                                        update=update_select_structure_type)

    @property
    def is_else_type(self):
        return self.select_structure_type == 'ELSE'

    @property
    def enum_type_data(self):
        if self.is_ui_layout_type:
            return PublicData.ENUM_UI_LAYOUT_TYPE
        elif self.is_select_structure_type:
            return PublicData.ENUM_SELECT_STRUCTURE_TYPE
        elif self.is_gesture_type:
            return PublicData.ENUM_GESTURE_UI_TYPE

    @property
    def is_select_structure_type(self) -> bool:
        """是选择结构类型"""
        return self.ui_type == 'SELECT_STRUCTURE'

    @property
    def is_ui_layout_type(self) -> bool:
        """是UI Layout类型"""
        return self.ui_type == 'UI_LAYOUT'

    @property
    def is_gesture_type(self) -> bool:
        """是手势类型"""
        return self.ui_type == 'GESTURE'

    @property
    def type(self) -> str:
        """Element Type"""
        if self.is_ui_layout_type:
            return self.ui_layout_type
        elif self.is_select_structure_type:
            return self.select_structure_type
        elif self.is_gesture_type:
            return self.gesture_type
