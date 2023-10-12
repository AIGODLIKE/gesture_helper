import ast
import math
from functools import cache
from os.path import basename, dirname, realpath

import blf
import bmesh
import bpy
import gpu
from bpy.app.translations import contexts as i18n_contexts
from bpy.props import EnumProperty, StringProperty, BoolProperty
from bpy.types import EnumPropertyItem, UILayout, PreferencesView, AddonPreferences, Operator, PropertyGroup
from gpu.shader import from_builtin as get_shader
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Euler, Matrix

from .utils import get_rna_data


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


def register_module_factory(module):
    is_debug = False

    def reg():
        for mod in module:
            if is_debug:
                print('register ', mod)
            mod.register()

    def un_reg():
        for mod in reversed(module):
            if is_debug:
                print('unregister ', mod)
            mod.unregister()

    return reg, un_reg


class PublicProperty:
    @staticmethod
    @cache
    def pref_() -> 'AddonPreferences':
        return bpy.context.preferences.addons[PublicData.G_ADDON_NAME].preferences

    @property
    def pref(self) -> 'AddonPreferences':
        return PublicProperty.pref_()

    @property
    def systems(self):
        return self.pref.systems

    @property
    def active_system(self):
        try:
            return self.systems[self.pref.active_index]
        except IndexError:
            ...

    @property
    def active_ui_element(self):
        """
        :return: UiElementItem
        """
        if self.active_system:
            try:
                return self.active_system.selected_children_element[-1]
            except IndexError:
                ...

    @property
    def ui_prop(self):
        return self.pref.ui_property


class PublicMethod:
    exclude_items = {'rna_type', 'bl_idname', 'srna'}  # 排除项

    @staticmethod
    def collection_data(prop, exclude=(), reversal=False) -> dict:
        """获取输入集合属性的内容

        Args:
            prop (_type_): _description_

        Returns:
            :param prop:
            :param reversal:
            :param exclude:
        """
        data = {}
        for index, value in enumerate(prop):
            if value not in PublicMethod.exclude_items:
                data[index] = PublicMethod.props_data(value, exclude, reversal)
        return data

    @staticmethod
    def props_data(prop, exclude=(), reversal=False) -> dict:
        """获取输入的属性内容
        可多选枚举(ENUM FLAG)将转换为列表 list(用于json写入,json 没有 set类型)
        集合信息将转换为字典 index当索引保存  dict

        Args:
            prop (bl_property): 输入blender的属性内容
            exclude (tuple): 排除内容
            reversal (bool): 反转排除内容,如果为True,则只搜索exclude
        Returns:
            dict: 反回字典式数据,
        """
        data = {}

        for i in prop.bl_rna.properties:
            try:
                id_name = i.identifier
                is_ok = (id_name in exclude) if reversal else (
                        id_name not in exclude)

                is_exclude = id_name not in PublicMethod.exclude_items

                if is_exclude and is_ok:
                    typ = i.type

                    pro = getattr(prop, id_name, None)
                    if not pro:
                        continue

                    if typ == 'POINTER':
                        pro = PublicMethod.props_data(pro, exclude, reversal)
                    elif typ == 'COLLECTION':
                        pro = PublicMethod.collection_data(pro, exclude, reversal)
                    elif typ == 'ENUM' and i.is_enum_flag:
                        # 可多选枚举
                        pro = list(pro)
                    data[id_name] = pro
            except Exception as e:
                print(e.args)
                import traceback
                traceback.print_exc()
        return data

    @staticmethod
    def set_prop(prop, path, value):
        pr = getattr(prop, path, None)
        if pr is not None:
            pro = prop.bl_rna.properties[path]
            typ = pro.type
            try:
                if typ == 'POINTER':
                    PublicMethod.set_property_data(prop, value)
                elif typ == 'COLLECTION':
                    PublicMethod.set_collection_data(pr, value)
                elif typ == 'ENUM' and pro.is_enum_flag:
                    # 可多选枚举
                    setattr(prop, path, set(value))
                else:
                    setattr(prop, path, value)
            except Exception as e:
                print(typ, pro, value, e)

    @staticmethod
    def set_property_data(prop, data: dict):
        """_summary_

        Args:
            prop (_type_): _description_
            data (_type_): _description_
        """
        for key, item in data.items():
            pr = getattr(prop, key, None)
            if pr is not None:
                PublicMethod.set_prop(prop, key, item)

        # for i in prop.bl_rna.properties:
        #     id_name = i.identifier
        #     if id_name in data:
        #         set_prop(prop, id_name, data[id_name])

    @staticmethod
    def set_collection_data(prop, data):
        """_summary_

        Args:
            prop (_type_): _description_
            data (_type_): _description_
        """
        for i in data:
            pro = prop.add()
            PublicMethod.set_property_data(pro, data[i])

    @staticmethod
    def calculate_point_on_circle(circle_point: Vector, radius: float, angle: float) -> Vector:
        """计算圆上的任意一点"""
        degree = math.radians(angle)
        x = circle_point[0] + radius * math.cos(degree)
        y = circle_point[1] + radius * math.sin(degree)
        return Vector((x, y))


class CacheHandler(PublicProperty,
                   PublicMethod):
    @classmethod
    def cache_clear(cls):
        cls.pref_.cache_clear()

    @staticmethod
    def tag_redraw(context):
        if context.area:
            context.area.tag_redraw()


class TempKey:
    @property
    def keyconfig(self):
        return bpy.context.window_manager.keyconfigs.active

    @property
    def temp_keymaps(self):
        if 'TEMP' not in self.keyconfig.keymaps:
            self.keyconfig.keymaps.new('TEMP')
        return self.keyconfig.keymaps['TEMP']

    def get_temp_kmi(self, id_name):
        key = id_name
        keymap_items = self.temp_keymaps.keymap_items
        if key not in keymap_items:
            return keymap_items.new(key, 'NONE', 'PRESS')
        return keymap_items[key]

    @staticmethod
    def _get_operator_property(string: str) -> dict:

        """将输入的字符串操作符属性转成字典
        用于传入操作符执行操作符用

        Args:
            string (str): _description_
        Returns:
            dict: _description_
        """
        property_dict = {}
        for prop in string[1:-1].split(', '):  # ['animation=True', ' use_viewport=True']
            try:
                par, value = prop.split('=')
                property_dict[par] = ast.literal_eval(value)
            except ValueError as v:
                print(v.args)
        return property_dict

    @staticmethod
    def from_kmi_get_operator_properties(kmi: 'bpy.types.KeyMapItem') -> str:
        """获取临时kmi操作符的属性
        """
        properties = kmi.properties
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

    @staticmethod
    def _for_set_prop(prop, pro, pr):
        for index, j in enumerate(pr):
            try:
                getattr(prop, pro)[index] = j
            except Exception as e:
                print(e.args)

    def set_operator_property_to(self, property_str, properties: 'bpy.types.KeyMapItem.properties') -> None:
        """注入operator property
        在绘制项时需要使用此方法
        set operator property
        self.operator_property:

        Args:
            properties (bpy.types.KeyMapItem.properties): _description_
            :param properties:
            :param property_str:
        """
        props = ast.literal_eval(property_str)
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

    def from_operator_info_get_property(self, string):
        ...


class PublicClass(
    CacheHandler,
):
    layout: UILayout


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
    ENUM_ADDON_SHOW_TYPE = [
        ('EDITOR', 'Editor', 'Editor Gesture'),
        ('SETTING', 'Setting', 'Addon Settings'),
        ('About', 'About', 'Addon About'),
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

    G_ADDON_NAME = basename(dirname(realpath(__file__)))  # addon folder path name


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


class PublicBmesh:

    @classmethod
    def get_bmesh(cls, obj: bpy.types.Object) -> 'bmesh':
        if (not obj) or (obj.type != 'MESH'):
            return

        if obj.mode == 'EDIT':
            return bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            return bm


if bpy.app.version >= (4, 0, 0):
    SHADER_2D_UNIFORM_COLOR = get_shader('UNIFORM_COLOR')
    SHADER_2D_IMAGE = get_shader('IMAGE_COLOR')
else:
    SHADER_2D_IMAGE = get_shader('2D_IMAGE')
    SHADER_2D_UNIFORM_COLOR = get_shader('2D_UNIFORM_COLOR')


class PublicGpu:
    _image_data = []

    @staticmethod
    def draw_2d_line(pos, color, line_width):
        shader = SHADER_2D_UNIFORM_COLOR
        size = line_width if line_width else 1
        gpu.state.line_width_set(size)
        gpu.state.point_size_set(size)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": pos})
        shader.bind()
        shader.uniform_float("color", color if color else (1.0, 1.0, 1.0, 1))
        batch.draw(shader)
        gpu.state.line_width_set(1.0)

    @staticmethod
    def draw_2d_points(points, point_size=10, color=(1, 1, 1, 1)):
        gpu.state.point_size_size(point_size)
        shader = SHADER_2D_UNIFORM_COLOR
        batch = batch_for_shader(shader, 'POINTS', {"pos": points})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.point_size_size(1)

    @staticmethod
    def draw_2d_rectangle(x: int, y: int, x2: int, y2: int, color=(0, 0, 0, 1.0)):
        """左下角为初始坐标
        ┌────────────────────────────┐
        │                       x2y2 │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │                            │
        │ xy                         │
        └────────────────────────────┘


        Args:
            :param y2:
            :param x2:
            :param y:
            :param x:
            :param color:
            """
        vertices = ((x, y), (x2, y), (x, y2), (x2, y2))
        indices = ((0, 1, 2), (2, 1, 3))

        shader = SHADER_2D_UNIFORM_COLOR
        batch = batch_for_shader(
            shader,
            'TRIS',
            {"pos": vertices},
            indices=indices
        )
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)

    @staticmethod
    def draw_2d_text(text="Hello Word",
                     size=10,
                     x: int = 100,
                     y: int = 100,
                     color=(0.5, 0.5, 0.5, 1),
                     font_id: int = 0,
                     dpi=72,
                     column=0,
                     ):
        blf.position(font_id, x, y - (size * (column + 1)), 0)
        blf.size(fontid=font_id, size=size, dpi=dpi)
        blf.color(font_id, *color)
        blf.draw(font_id, text)

    @staticmethod
    def draw_2d_image(image_path, x, y, width, height):
        key = f'-{image_path}'
        x2 = x + width
        y2 = y + height
        gpu.state.blend_set('ALPHA')

        if key not in PublicGpu._image_data:
            image = bpy.data.images.load(image_path)
            texture = gpu.texture.from_image(image)
            bpy.data.images.remove(image)
        else:
            texture = PublicGpu._image_data
        from gpu_extras.batch import batch_for_shader

        shader = SHADER_2D_IMAGE
        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": ((x, y), (x2, y), (x2, y2), (x, y2)),
                "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
            },
        )
        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)


class PublicOperator(CacheHandler, Operator):
    @staticmethod
    def ops_id_name(string):
        return f'gesture.{string}'

    event: bpy.types.Event
    context: bpy.types.Context
    _mouse_x: int
    _mouse_y: int

    @staticmethod
    def get_event_key(event):
        alt = event.alt
        shift = event.shift
        ctrl = event.ctrl

        not_key = ((not ctrl) and (not alt) and (not shift))

        only_ctrl = (ctrl and (not alt) and (not shift))
        only_alt = ((not ctrl) and alt and (not shift))
        only_shift = ((not ctrl) and (not alt) and shift)

        shift_alt = ((not ctrl) and alt and shift)
        ctrl_alt = (ctrl and alt and (not shift))

        ctrl_shift = (ctrl and (not alt) and shift)
        ctrl_shift_alt = (ctrl and alt and shift)
        return not_key, only_ctrl, only_alt, only_shift, shift_alt, ctrl_alt, ctrl_shift, ctrl_shift_alt

    def set_event_key(self):
        (self.not_key,
         self.only_ctrl,
         self.only_alt,
         self.only_shift,
         self.shift_alt,
         self.ctrl_alt,
         self.ctrl_shift,
         self.ctrl_shift_alt) = self.get_event_key(
            self.event)

    def _set_ce(self, context, event):
        self.context = context
        self.event = event
        self.set_event_key()

    def _set_mouse(self, context, event, key):
        setattr(self, f'{key}_mouse_x', min(max(0, event.mouse_region_x), context.region.width))
        setattr(self, f'{key}_mouse_y', min(max(0, event.mouse_region_y), context.region.height))

    def init_invoke(self, context, event) -> None:
        self._set_ce(context, event)
        self._set_mouse(context, event, '_start')

    def init_modal(self, context, event) -> None:
        self._set_ce(context, event)
        self._set_mouse(context, event, '')

    @property
    def mouse_co(self) -> Vector:
        return Vector((self.event.mouse_region_x, self.event.mouse_region_y))

    @property
    def start_mouse_co(self) -> Vector:
        return Vector((self._start_mouse_x, self._start_mouse_y))


class PublicPropertyGroup(PropertyGroup,
                          ):

    def set_active_index(self, index):
        """需要重写,用作移动时设置列表活动索引
        :param index:
        :return:
        """
        ...

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        """需要重写,获取父集合属性

        :return:
        """
        return object

    @cache
    def _parent_collection_property(self) -> 'PropertyGroup':
        """缓存,父级正常情况下不会变
        :return:
        """
        return self.parent_collection_property

    @classmethod
    def cache_clear_parent_collection_property(cls):
        """清理缓存
        :return:
        """
        cls._parent_collection_property.cache_clear()

    @property
    def items(self) -> 'iter':
        """通过设置父级集合属性拿每一个集㕣元素

        :return:
        """
        return self.parent_collection_property.values()

    @property
    def index(self) -> int:
        """反回当前项在集合属性内的索引"""
        if self in self.items:
            return self.items.index(self)

    def remove(self) -> None:
        """通过索引删除自身
        :return:
        """
        self.parent_collection_property.remove(self.index)

    def move(self, is_next=True):
        """移动此元素在集合内的位置,如果在头或尾部会做处理

        :param is_next: bool ,向下移
        :return:
        """
        le = len(self.items)
        index = self.index
        le1 = le - 1
        next_index = (0 if le1 == index else index + 1) if is_next else (le1 if index == 0 else index - 1)
        self.parent_collection_property.move(index, next_index)

        active_index = le1 if next_index == -1 else next_index
        self.set_active_index(active_index)


class PublicRelationship(PropertyGroup):
    items: iter
    _parent_key = 'parent_name'
    parent_collection_property: PropertyGroup

    def update_parent(self, context):
        self.cache_clear_relationship()

    parent_name: StringProperty(update=update_parent)

    # Parent
    @cache
    def _get_parent_relationship(self):
        try:
            parent = self.parent_collection_property[self.parent_name]
            if self != parent:
                return parent
        except KeyError:
            ...

    def _set_parent_relationship(self, value):
        if type(value) == str:
            self[self._parent_key] = value
        else:
            self[self._parent_key] = value.name
        self.cache_clear_relationship()

    def _del_parent_relationship(self):
        del self[self._parent_key]
        self.cache_clear_relationship()

    def change_name(self, old, new):
        """修改名称时调用此方法,同时修改子级的父项"""
        print('change_name', old, new, self.children)
        for child in self.children:
            child.parent = new

    parent = property(fget=_get_parent_relationship, fset=_set_parent_relationship, fdel=_del_parent_relationship)

    # Child
    @cache
    def _get_children(self) -> 'list':
        return [i for i in self.items if i.parent == self]

    @property
    def children(self) -> 'list':
        return self._get_children()

    @property
    def children_recursion(self) -> 'list':
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.children)
        return children

    @classmethod
    def cache_clear_relationship(cls):
        cls._get_children.cache_clear()
        cls._get_parent_relationship.cache_clear()


class PublicCollectionNoRepeatName(PropertyGroup):
    """
    用来避免名称重复的类,将会代理name属性,如果更改了名称将会判断是否重复,如果重复将会在后缀上加上.001
    需要实例化items函数反回的应是此元素的集合属性,用于遍历所有的元素
    """
    items: 'iter'

    @property
    def _name_keys(self):
        return [i.name for i in self.items]

    @staticmethod
    def _get_suffix(string):
        sp = string.split('.')
        try:
            return int(sp[-1])
        except:
            return -1

    @classmethod
    def _suffix_is_number(cls, string: str) -> bool:
        _i = cls._get_suffix(string)
        if _i == -1 or len(string) < 3:
            return False
        return True

    @property
    def _not_update_name(self):
        return 'name' not in self

    def _get_name(self):
        if self._not_update_name:
            return f'not update name {self}'
        elif 'name' not in self:
            self._set_name('New Name')

        return self['name']

    def _get_effective_name(self, value):

        def _get_number(n):
            if n < 999:
                return f'{n}'.rjust(3, '0')
            return f'1'.rjust(3, '0')

        if value in self._name_keys:
            if self._suffix_is_number(value):
                number = _get_number(self._get_suffix(value) + 1)
                sp = value.split('.')
                sp[-1] = number
                value = '.'.join(sp)
            else:
                value += '.001'
            return self._get_effective_name(value)
        return value

    def _set_name(self, value):
        keys = self._name_keys
        not_update = ('name' in self and value == self['name'] and keys.count(value) < 2)
        if not_update or not value:
            return
        new_name = self._get_effective_name(value)

        old_name = self['name'] if 'name' in self else None
        self['name'] = new_name
        if getattr(self, 'change_name', False):
            self.change_name(old_name, new_name)
        if (len(keys) - len(set(keys))) >= 1:  # 有重复的名称
            raise ValueError('发现重复名称 !!', keys)

    def _update_name(self, context):
        ...

    def change_name(self, old, new):
        ...

    name: StringProperty(
        name='name',
        get=_get_name,
        set=_set_name,
        update=_update_name,
    )


class PublicUi:

    @staticmethod
    def _get_blender_icon(icon_style):
        """反回图标名称

        Args:
            icon_style (类型或直接输入两个已设置的图标, optional): 图标风格,也可以自已设置图标id. Defaults to 'TRIA' | 'ARROW' | 'TRI' | (str, str).
        Returns:
            (str,str): _description_
        """
        icon_data = {
            'TRI': ('DISCLOSURE_TRI_DOWN', 'DISCLOSURE_TRI_RIGHT'),
            'TRIA': ('TRIA_DOWN', 'TRIA_RIGHT'),
            'SORT': ('SORT_ASC', 'SORT_DESC'),
            'ARROW': ('DOWNARROW_HLT', 'RIGHTARROW'),
            'CHECKBOX': ('CHECKBOX_HLT', 'CHECKBOX_DEHLT'),
            'RESTRICT_SELECT': ('RESTRICT_SELECT_OFF', 'RESTRICT_SELECT_ON'),
        }
        if icon_style in icon_data:
            return icon_data[icon_style]
        else:
            return icon_data['TRI']

    @staticmethod
    def icon_two(bool_prop, style='CHECKBOX', custom_icon: tuple[str, str] = None, ) -> str:
        """输入一个布尔值,反回图标类型str
        Args:
            bool_prop (_type_): _description_
            custom_icon (tuple[str, str], optional): 输入两个自定义的图标名称,True反回前者. Defaults to None.
            style (str, optional): 图标的风格. Defaults to 'CHECKBOX'.
        Returns:
            str: 反回图标str
        """
        icon_true, icon_false = custom_icon if custom_icon else PublicUi._get_blender_icon(
            style)
        return icon_true if bool_prop else icon_false

    @staticmethod
    def space_layout(layout: 'bpy.types.UILayout', space: int, level: int) -> 'bpy.types.UILayout':
        """
        设置间隔
        """
        if level == 0:
            return layout.column()
        indent = level * space / bpy.context.region.width

        split = layout.split(factor=indent)
        split.column()
        return split.column()

    @staticmethod
    def draw_default_ui_list_filter(ui_list, layout):
        """绘制UIList默认过滤UI"""
        sub_row = layout.row(align=True)
        sub_row.prop(ui_list, 'filter_name')
        sub_row.prop(ui_list, 'use_filter_invert',
                     icon='ARROW_LEFTRIGHT',
                     toggle=True,
                     icon_only=True,
                     )
        if not (ui_list.use_filter_sort_lock and ui_list.bitflag_filter_item):
            sub = sub_row.row(align=True)
            sub.prop(ui_list, 'use_filter_sort_alpha',
                     toggle=True,
                     icon_only=True,
                     )
            icon = 'SORT_REVERSE' if (
                    ui_list.bitflag_filter_item and ui_list.use_filter_sort_reverse) else 'SORT_ASC'
            sub.prop(ui_list, 'use_filter_sort_reverse',
                     icon=icon,
                     toggle=True,
                     icon_only=True,
                     )

    @staticmethod
    def draw_extend_ui(layout: bpy.types.UILayout, prop_name, label: str = None, align=True, alignment='LEFT',
                       default_extend=False,
                       style='BOX', icon_style='ARROW', draw_func=None, draw_func_data=None):
        """
        使用bpy.context.window_manager来设置并存储属性
        if style == 'COLUMN':
            lay = layout.column()
        # "TRIA,ARROW,TRI""TRIA,ARROW,TRI"
        #: str("BOUND,BOX")
        enum in [‘EXPAND’, ‘LEFT’, ‘CENTER’, ‘RIGHT’], default LEFT

        draw_func(layout,**)
        draw_func_data{}
        """
        from .utils.property import RegUiProp
        extend = RegUiProp.temp_wm_prop()

        extend_prop_name = prop_name + '_extend'
        extend_bool = getattr(extend, extend_prop_name, None)
        if not isinstance(extend_bool, bool):
            # 如果没有则当场新建一个属性
            extend.default_bool_value = default_extend
            extend.add_ui_extend_bool_property = extend_prop_name
            extend_bool = getattr(extend, extend_prop_name)

        icon = PublicUi.icon_two(extend_bool, style=icon_style)

        lay = layout.column()
        if style == 'BOX':
            if extend_bool:
                col = layout.column(align=True)
                lay = col.box()
            else:
                col = layout
        else:
            col = lay = layout

        row = lay.row(align=align)

        row.alignment = alignment
        row.prop(extend, extend_prop_name,
                 icon=icon,
                 text='',
                 toggle=1,
                 icon_only=True,
                 emboss=False
                 )

        if draw_func:
            # 使用传入的绘制方法
            draw_func(layout=row, **draw_func_data)
        else:
            row.prop(extend, extend_prop_name,
                     text=label if label else extend_prop_name,
                     toggle=1,
                     expand=True,
                     emboss=False
                     )

        if style == 'BOX':
            if extend_bool:
                out_lay = col.column(align=True).box()
            else:
                out_lay = lay

        else:
            out_lay = lay

        return extend_bool, out_lay


class PublicPopupMenuOperator(Operator):
    title: str
    bl_label: str
    bl_idname: str
    is_popup_menu: BoolProperty(name='弹出菜单',
                                description='''是否为弹出菜单,如果为True则弹出菜单,''',
                                default=True,
                                **PublicData.PROP_DEFAULT_SKIP,
                                )

    def execute(self, context):
        print(self.bl_label)
        return {'FINISHED'}

    def draw_menu(self, menu, context):
        layout = menu.layout
        layout.label(text=self.bl_label)
        ops = layout.operator(self.bl_idname)
        ops.is_popup_menu = False

    def invoke(self, context, event):
        if self.is_popup_menu:
            context.window_manager.popup_menu(
                self.draw_menu, title=getattr(self, 'title', self.bl_label))
            return {'FINISHED'}
        return self.execute(context)
