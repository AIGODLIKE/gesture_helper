from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from ...utils.public import PublicData


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

    def _update_text(self, context):
        self._by_text_set_name()

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
    ...


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
        items = [
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

        space_items = map(
            lambda i: i[:-1] + ((1 << i[-1]),), items)

        matching_dict = {
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

        return [i for i in space_items if i[0] not in matching_dict[self.region_type]]

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
                              items=[
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
                              ],
                              update=_update_panel,
                              default='UI',
                              #   get=_get_region,
                              #   set=_set_region,
                              )

    bl_category: StringProperty(
        name='分类', default='Custom Panel Category', update=_update_panel)
    bl_label: StringProperty(
        name='标签', default='Custom Panel Label', update=_update_panel)

    bl_options: EnumProperty(items=[('DEFAULT_CLOSED', 'Default Closed',
                                     'Defines if the panel has to be open or collapsed at the time of its creation.'),
                                    ('HIDE_HEADER', 'Hide Header',
                                     'If set to False, the panel shows a header, which contains a clickable arrow to collapse the panel and the label(see bl_label).'),
                                    ('HEADER_LAYOUT_EXPAND', 'Expand Header Layout',
                                     'Allow buttons in the header to stretch and shrink to fill the entire layout width.'),
                                    ],
                             description='''Options for this panel type
                            # WARNING 闪退 ('INSTANCED', 'Instanced Panel',
                            #  'Multiple panels with this type can be used as part of a list depending on data external to the UI. Used to create panels for the modifiers and other stacks.'),
                            ''',
                             options={'ENUM_FLAG'},
                             update=_update_panel,
                             )


class OperatorProp:
    operator: StringProperty(name='操作符',
                             description='输入操作符,将会自动格式化 bpy.ops.screen.back_to_previous() >> mesh.primitive_monkey_add',
                             # set=_set_operator,
                             # get=_get_operator_string,
                             # update=_operator_update,
                             )
    operator_context: EnumProperty(name='操作符上下文',
                                   **PublicData.PROP_OPERATOR_CONTEXT,
                                   )

    operator_property: StringProperty(name='操作符属性', default=r'{}', )


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
