#

def register():
    ...


def unregister():
    ...

    # bpy.utils.unregister_class(UiElementItem)

# class Panel:
#     """所有的面板数据和方法
#
#     Returns:
#         _type_: _description_
#     """
#     _panel_dict = {}  # uuid:dict
#
#     @property
#     def panel_dict(self) -> dict:
#         """反回当前项的面板数据
#         使用类共有的数据来存储数据
#
#         Returns:
#             dict: _description_
#         """
#         if self.uuid not in self._panel_dict:
#             self._panel_dict[self.uuid] = {}
#         return self._panel_dict[self.uuid]
#     # panel
#
#     def _update_panel(self, context) -> None:
#         '''更新面板数据,更改名称或是标题时更新'''
#         self._refresh_panel()
#
#     def _set_space(self, value) -> None:
#         """设置空间类型
#
#         Args:
#             value (_type_): _description_
#         """
#         self['space_type'] = value
#
#     def _get_space(self) -> int:
#         """反回空间类型的枚举项id（int）
#
#         Returns:
#             int: _description_
#         """
#         if ('space_type' not in self) or (not self['space_type']):
#             return 2
#         return self['space_type']
#
#     def _space_items(self, context):
#         """反回空间类型的枚举
#
#         Args:
#             context (_type_): _description_
#
#         Returns:
#             _type_: _description_
#         """
#         items = [
#             # ('EMPTY', 'Empty', '', 'NONE', 0),
#
#             ('VIEW_3D', '3D Viewport',
#              'Manipulate objects in a 3D environment', 'VIEW3D', 1),
#             ('GRAPH_EDITOR', 'Graph Editor',
#              'Edit drivers and keyframe interpolation', 'GRAPH', 2),
#             ('OUTLINER', 'Outliner',
#              'Overview of scene graph and all available data-blocks', 'OUTLINER', 3),
#             ('PROPERTIES', 'Properties',
#              'Edit properties of active object and related data-blocks', 'PROPERTIES', 4),
#             ('FILE_BROWSER', 'File Browser',
#              'Browse for files and assets', 'FILEBROWSER', 5),
#             ('IMAGE_EDITOR', 'UV/Image Editor',
#              'View and edit images and UV Maps', 'IMAGE', 6),
#             ('INFO', 'Info', 'Log of operations, warnings and error messages', 'INFO', 7),
#             ('NODE_EDITOR', 'Node Editor',
#              'Editor for node-based shading and compositing tools', 'NODETREE', 16),
#             ('SEQUENCE_EDITOR', 'Video Sequencer',
#              'Video editing tools', 'SEQUENCE', 8),
#             ('TEXT_EDITOR', 'Text Editor',
#              'Edit scripts and in-file documentation', 'TEXT', 9),
#             ('CLIP_EDITOR', 'Movie Clip Editor',
#              'Motion tracking tools', 'TRACKER', 20),
#             ('DOPESHEET_EDITOR', 'Dope Sheet',
#              'Adjust timing of keyframes', 'ACTION', 12),
#             ('NLA_EDITOR', 'Nonlinear Animation',
#              'Combine and layer Actions', 'NLA', 13),
#             ('CONSOLE', 'Python Console',
#              'Interactive programmatic console for advanced editing and script development', 'CONSOLE', 18),
#             ('PREFERENCES', 'Preferences',
#              'Edit persistent configuration settings', 'PREFERENCES', 19),
#             ('TOPBAR', 'Top Bar',
#              'Global bar at the top of the screen for global per-window settings', 'NONE', 21),
#             ('STATUSBAR', 'Status Bar',
#              'Global bar at the bottom of the screen for general status information', 'NONE', 22),
#             ('SPREADSHEET', 'Spreadsheet',
#              'Explore geometry data in a table', 'SPREADSHEET', 23),
#         ]
#
#         space_items = map(
#             lambda i: i[:-1] + ((1 << i[-1]),), items)
#
#         matching_dict = {
#             'WINDOW': ('STATUSBAR',),
#             'HEADER': (),
#             'UI': ('CONSOLE', 'PREFERENCES', 'TOPBAR',  'INFO', 'OUTLINER', 'PROPERTIES', 'STATUSBAR',),
#             'TOOLS': ('GRAPH_EDITOR', 'OUTLINER', 'PROPERTIES', 'INFO', 'TEXT_EDITOR', 'DOPESHEET_EDITOR', 'NLA_EDITOR', 'CONSOLE', 'PREFERENCES', 'TOPBAR', 'STATUSBAR'),
#             'TOOL_PROPS': (),
#             'PREVIEW': (),
#             'HUD': (),
#             'NAVIGATION_BAR': (),
#             'FOOTER': (),
#             'TOOL_HEADER': (),
#         }
#
#         return [i for i in space_items if i[0] not in matching_dict[self.region_type]]
#
#     space_type: EnumProperty(name='空间类型',
#                              items=_space_items,
#                              update=_update_panel,
#                              get=_get_space,
#                              set=_set_space,
#                              )
#
#     def _get_region(self):
#
#         return self['region_type']
#
#     def _set_region(self, value):
#         self['region_type'] = value
#
#     region_type: EnumProperty(name='区域类型',
#                               items=[  # ('WINDOW', 'Window', '', 'NONE', 0),
#                                   # ('HEADER', 'Header', '', 'NONE', 1),
#                                   #  ('CHANNELS', 'Channels', '', 'NONE', 2),
#                                   #  ('TEMPORARY', 'Temporary', '', 'NONE', 3),
#                                   #  ('EXECUTE', 'Execute Buttons', '', 'NONE', 10),
#                                   ('UI', 'UI', '',),
#                                   ('TOOLS', 'Tools', '',),
#                                   # ('TOOL_PROPS', 'Tool Properties', '', 'NONE', 6),
#                                   # ('PREVIEW', 'Preview', '', 'NONE', 7),
#                                   # ('HUD', 'Floating Region', '', 'NONE', 8),
#                                   # ('NAVIGATION_BAR', 'Navigation Bar', '', 'NONE', 9),
#                                   # ('FOOTER', 'Footer', '', 'NONE', 11),
#                                   # ('TOOL_HEADER', 'Tool Header', '', 'NONE', 12),
#                                   #  ('XR', 'XR', '', 'NONE', 13)
#                               ],
#                               update=_update_panel,
#                               default='UI',
#                               #   get=_get_region,
#                               #   set=_set_region,
#                               )
#
#     bl_category: StringProperty(
#         name='分类', default='Custom Panel Category', update=_update_panel)
#     bl_label: StringProperty(
#         name='标签', default='Custom Panel Label', update=_update_panel)
#
#     bl_options: EnumProperty(items=[('DEFAULT_CLOSED', 'Default Closed',
#                                      'Defines if the panel has to be open or collapsed at the time of its creation.'),
#                                     ('HIDE_HEADER', 'Hide Header',
#                                      'If set to False, the panel shows a header, which contains a clickable arrow to collapse the panel and the label(see bl_label).'),
#                                     ('HEADER_LAYOUT_EXPAND', 'Expand Header Layout',
#                                      'Allow buttons in the header to stretch and shrink to fill the entire layout width.'),
#                                     ],
#                              description='''Options for this panel type
#                             # WARNING 闪退 ('INSTANCED', 'Instanced Panel',
#                             #  'Multiple panels with this type can be used as part of a list depending on data external to the UI. Used to create panels for the modifiers and other stacks.'),
#                             ''',
#                              options={'ENUM_FLAG'},
#                              update=_update_panel,
#                              )
#
#     def __init__(self):
#         """初始化面板
#         """
#         print('Panel __inti__')
#
#     @classmethod
#     def __load__(cls):
#         '''刚进bl里时面板
#         '''
#         Data.injection_attribute(cls)
#         print('Panel __load__')
#         pref = cls.prefs
#         for ui in pref.ui_items_collection_group:
#             ui._init_panel()
#
#     @property
#     def panel_agers(self):
#         """反回面板类需要的参数
#         TODO 面板POll
#
#         Returns:
#             _type_: _description_
#         """
#         return self._panel_agers()
#     region_type_is_ui = property(lambda self: self.region_type == 'UI')
#     region_type_is_tools = property(lambda self: self.region_type == 'TOOLS')
#
#     def _panel_name(self, space: str) -> str:
#         """反回面板的组合名称
#
#         Args:
#             space (str): _description_
#
#         Returns:
#             str: _description_
#         """
#         return 'PANEL_EXAMPLE_PT_CUSTOM_'+self.uuid+'_'+space
#
#     def _panel_agers(self, space=None) -> dict:
#         """反回面板类需要使用到的参数
#
#         Args:
#             space (_type_, optional): _description_. Defaults to None.
#
#         Returns:
#             dict: _description_
#         """
#
#         def _draw_panel(self, context):
#             # 'DrawCustomUiFunc._draw_func'
#             self.ui._draw_func(self.layout, direct_draw=True)
#
#         agers = {
#             'uuid': self.uuid,
#             'bl_label': self.bl_label,
#             'bl_options': self.bl_options,
#             'bl_region_type': self.region_type,
#             'bl_space_type': space,
#             'bl_idname': self._panel_name(space),
#             'space': space,
#             'draw': _draw_panel,
#             'ui': property(lambda self: self.prefs.ui_items_collection_group.get(self.uuid)),
#             # TODO 'poll': _poll,
#         }
#
#         if self.region_type_is_ui:
#             agers['bl_category'] = self.bl_category
#         return agers
#
#     def _init_panel(self) -> None:
#         """初始化面板
#         设置面板类并注册
#
#         for space in self.space_type:
#             print('_init_panel', space)
#             item = type(self._panel_name(space),
#                         (bpy.types.Panel, Data), self._panel_agers(space))
#             self.panel_dict[space] = item
#         """
#         if (not self.is_panel) or (not self.is_enabled):
#             return
#         space = self.space_type
#
#         item = type(self._panel_name(space),
#                     (bpy.types.Panel, Data), self._panel_agers(space))
#         self.panel_dict[space] = item
#         self._reg_panel()
#
#     def _refresh_panel(self):
#         """刷新面板
#         重新注册面板的所有类
#         """
#         self._unreg_panel()
#         self.panel_dict.clear()
#         self._init_panel()
#
#     def _reg_panel(self) -> None:
#         """注删所有数据内的面板
#         """
#         for panel in self.panel_dict.values():
#             print('_reg_panel', panel)
#             bpy.utils.register_class(panel)
#
#     def _unreg_panel(self) -> None:
#         """取消注册所有面板
#         """
#         for panel in self.panel_dict.values():
#             if panel.is_registered:
#                 bpy.utils.unregister_class(panel)
#
#
# class UIItem(Data,
#              PropertyGroup,
#              PollProperty,
#
#              ElementChange,
#              ItemsChange,
#
#              Panel,
#              ):
#     '''
#     要存快捷键的内容,更改时需要看一下有没有重复的,或是有冲突的
#     将这些内容放在自带的快捷键里面弄,只有自带的添加项才弄这个
#     name -> ui_name 将name 设置为按ui_name更新,避免冲突
#     copy ui items
#     '''
#     @property
#     def draw_items(self) -> list['UIElementItem']:
#         """获取需要绘制的主项
#
#         Returns:
#             _type_: _description_
#         """
#         ui = self.ui
#         items = self.items_need_drawn
#         items_listen = list(ui.get(i.uuid)
#                             for i in items if i.uuid in ui and ui.get(i.uuid).is_enabled)
#         return self.__get_element_items__(items_listen)
#
#     @property
#     def need_draw(self) -> 'UIElementItem':
#         """
#         获取self顶级父级在__get_need_drawn_parent__里面的父级
#         用于仅显示所选项避免内容太多混淆
#         """
#         ul = len(self.ui)
#         if not ul:
#             return []
#         act_index = self.active_ui_index
#         _index = -1 if act_index >= ul else act_index
#         need = self.ui[_index]
#         if not need:
#             return self.__get_element_items__([need, ])
#         while True:
#             if need.parent == None:
#                 return self.__get_element_items__([need, ])
#             else:
#                 need = need.parent
#
#     def _draw_func(self, layout: bpy.types.UILayout, preview=False, direct_draw=False) -> None:
#         """
#         通过这个函数将UI项生成绘制方法
#         print('draw \t\tItems', time())
#         print('draw finished\n')
#         print(prefs,)
#         text = f'draw UIItem  draw_items:{draw_items}\nonly_active:{only_active}'
#         print(text)
#         """
#         # print(self, '\t\tdraw_func')
#
#         prefs = Data.custom_ui_prefs()
#         only = prefs.only_show_active_need_drawn
#
#         only_active = only and (not direct_draw)  # 只显示活动项
#
#         draw_items = self.need_draw if only_active else self.draw_items
#
#         for ui in draw_items:
#             ui.draw(self, layout, preview, direct_draw)
#
#     def draw_gestures(self, layout: bpy.types.UILayout, gestures_item) -> None:
#         """绘制手势项
#
#         Args:
#             layout (bpy.types.UILayout): _description_
#             gestures_item (_type_): _description_
#         """
#
#         dire_items = self.__get_gestures_direction_items__(
#             gestures_item)
#         dire_items[2], dire_items[3] = dire_items[3], dire_items[2]  # 上下反转
#
#         print('draw_items \t', [i.uuid if i else i for i in dire_items])
#         self.draw_pie(layout, dire_items[:8])
#
#         if dire_items[8:] != [None, None]:
#             draw_list = [None for _ in range(8)]
#             draw_list[2], draw_list[3] = dire_items[9], dire_items[8]
#             self.draw_pie(layout, draw_list)
#
#     def draw_pie(self, layout: bpy.types.UILayout, items: list['UIElementItem']) -> None:
#         """绘制饼菜单
#
#         Args:
#             layout (bpy.types.UILayout): _description_
#             items (list[&#39;UIElementItem&#39;]): _description_
#         """
#         for item in items:
#             if item and item.is_enabled:
#                 layout = layout.menu_pie() if item.type != 'menu_pie' else layout
#                 item.draw(self,
#                           layout,
#                           direct_draw=True,
#                           is_select=False,
#                           is_gestures_draw=True,
#                           is_draw_child=True,
#                           )
#             else:
#                 pie = layout.menu_pie()
#                 pie.separator()
#
#     @classmethod
#     def __load__(cls) -> None:
#         """
#         加载已添加数据
#         开启插件时使用此方法
#         拿到所有项需要添加的所有快捷键
#
#         将结果添加到    UIItem.keys
#         存为set()
#         """
#         Data.injection_attribute(cls)
#         KeyMap.__load__()
#         Panel.__load__()
#         text = f'{addon_name} UIItem.__load__() finished \n\tKeyMap.kmi_data:{cls.kmi_data} \n'
#         print(text)
#
#     # property
#
#     def _set_name(self, value) -> None:
#         """
#         自动排序添加名称,不允许同名或为空字符串
#
#         会和PropertyGroup的名称冲突出现两个名称,并显get到的是PropertyGroup的名称
#         将name 改为uuid,因为无法监控更改事件,不使用name作为显示名称了,改成ui_name
#
#         prefs = bbpy.get.addon.prefs().custom_ui
#
#         if value == '' or (self['ui_name'] == value):
#             return
#
#         names = prefs.foreach_get_attribute('ui_items_collection_group', 'ui_name')
#         nums_len = UUID_PREFIX_NUMS_LEN
#
#         if value in names:
#             string = value.split('.')[-1]
#             if string.isnumeric() and len(string) == nums_len:
#                 # 如果后三位就是数字则添加
#                 suf_int = str(int(value[-3:])+1)
#                 suffix = ''.join(
#                     ['0' for _ in range(nums_len - len(suf_int))])
#                 self['ui_name'] = value[:-nums_len] + suffix+suf_int
#             else:
#                 num = f".{''.join(['0' for _ in range(nums_len-1)])}1"
#                 self['ui_name'] = value + num
#         else:
#             self['ui_name'] = value
#         """
#         self['ui_name'] = value
#
#     def _get_name(self) -> str:
#         """
#         获取ui_name的数据
#         """
#         return self['ui_name']
#
#     def gen_uuid(self, slice=5) -> None:
#         """
#         生成uuid
#         保险    避免真的有重复的uuid
#         """
#         pref = bbpy.get.addon.prefs().custom_ui
#         uid = self.generate_uuid(slice=slice)
#
#         if uid in pref.ui_items_collection_group:
#             # uid重复,重新生成一次,跳到下一次生成,这一次不用了
#             return self.gen_uuid(slice=7)
#         self.name = self.uuid = uid
#         return uid
#
#     # Update
#     def update_child_ui_element_parent_uuid(self) -> None:
#         """更新所有子级元素的父UIITEM的uuid
#         """
#         for i in self.ui:
#             i.parent_ui_item_uuid = self.uuid
#
#     def update_uuid(self, context) -> None:
#         """
#         将uuid传递到.key下
#         key的uuid将不能更改
#         """
#         self.update_child_ui_element_parent_uuid()
#         self.name = self.uuid
#         self.key.is_update = True
#         self.key.uuid = self.key.name = self.uuid
#         self.key.is_update = False
#         print('update_uuid', self.name)
#
#     def update_enable(self, context) -> None:
#         """每一次更新keymaps 和 is_enable_keymaps 都设置一遍快捷键是否启用,这样可以在外部调用此方法了
#                 当key里面没有值会报错吗?:会自动生成
#
#         if enable use key.is_enable_keymaps
#         else use self.is_enable
#
#         Args:
#             context (_type_): _description_
#         """
#         key = self.key
#         value = key.is_enable_keymaps if self.is_enabled else self.is_enabled
#         key.set_key_enable_state(value)
#         self._refresh_panel()
#
#     def update_active_index(self, context) -> None:
#         r"""
#         更新活动ui_element
#         并设置所选项的select值
#         print('update_active_index\t',
#               self.active_ui_index, ui, self.ui_item, self, '\n')
#
#         """
#         if self.is_update or (not self.ui):
#             return
#
#         self.is_update = True
#
#         event = bbpy.context.event
#         ui = self.ui[self.active_ui_index]
#         if event and (event.shift or event.ctrl):
#             ui.is_select = ui.is_select ^ True
#         else:
#             for i in self.ui:
#                 i.is_select = False
#             ui.is_select = True
#
#         if ui.type == 'operator':
#             r'''
#             设置操作属性到临时kmi里面
#             切换活动项操作符时需要设置一次
#             更新活动操作符属性
#             '''
#             self.tmp_kmi.idname = ''
#             self.tmp_kmi.idname = ui.operator
#             ui.set_operator_property_to_tmp_kmi()
#         self.is_update = False
#
#     tag: StringProperty()
#
#     ui_name: StringProperty(default='The is a name String',
#                             set=_set_name, get=_get_name)
#
#     description: StringProperty(default='这是一个描述')
#
#     uuid: StringProperty(options={'HIDDEN'},
#                          description='''uuid用来注册快捷键时识别项目,以及更改时设置快捷键项''',
#                          update=update_uuid,
#                          )
#
#     type: EnumProperty(items=CUSTOM_UI_TYPE_ITEMS,
#                        )
#
#     is_panel = property(lambda self: self.type == 'panel', doc='是面板')
#     is_menu = property(lambda self: self.type == 'menu', doc='是菜单')
#     is_menu_pie = property(lambda self: self.type == 'menu_pie', doc='是饼菜单')
#     is_layout = property(lambda self: self.type == 'layout', doc='是UILayout')
#
#     ui: CollectionProperty(name='ui元素', type=UIElementItem)
#
#     def __get_gestures_direction_items__(self, item: 'UIElementItem' = None) -> list['UIElementItem']:
#         """获取手势的10个方向
#
#         Returns:
#             _type_: _description_
#         """
#
#         ret_items = [None for _ in range(10)]
#
#         scope = [str(i) for i in range(1, 11)]  # 1-10
#         for_items = item.childs if item else self.draw_items
#
#         for ui in for_items:
#             index_str = ui.gestures_direction
#
#             switch_dire = {'3': '4', '4': '3'}
#             index_str = switch_dire[index_str] if index_str in switch_dire else index_str
#             if index_str in scope and ui.is_enabled:
#                 ret_items[int(index_str)-1] = ui
#
#         return ret_items
#
#     gestures_direction_items = property(__get_gestures_direction_items__,
#                                         doc='获取手势的8个对应项')
#
#     use_gestures: BoolProperty(name='使用手势操作',
#                                description='在使用PIM菜单时使用手势操作方式',
#                                default=False,
#                                )
#     is_use_gestures = property(lambda self: self.type == 'menu_pie' and self.use_gestures,
#                                doc='是使用手势的'
#                                )
#
#     active_ui_index: IntProperty(name='活动ui索引',
#                                  update=update_active_index)
#
#     key: PointerProperty(type=KeyMap)
#     is_update: BoolProperty(name='是更新中的')
#
#     is_extend: BoolProperty(name='是展开的', default=True)
#     is_select: BoolProperty(name='是选中的', default=True)
#     is_enabled: BoolProperty(name='是启用的',
#                              default=True,
#                              update=update_enable)
#
#     # pie menu draw property default is -1 ,if == -1 user CustomUI pie property
#     pie_animation_timeout:  IntProperty(**pie_animation_timeout)
#     pie_initial_timeout: IntProperty(**pie_initial_timeout)
#     pie_menu_confirm: IntProperty(**pie_menu_confirm)
#     pie_menu_radius: IntProperty(**pie_menu_radius)
#     pie_menu_threshold: IntProperty(**pie_menu_threshold)
#     pie_tap_timeout: IntProperty(**pie_tap_timeout)
