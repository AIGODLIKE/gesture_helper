def register():
    ...


def unregister():
    ...

# class PollProperty:
#     """用于设置项的Poll
#     TODO 多个项是同一快捷键时
#     使用Poll来设置 运行第一个[for i in items if i.is_enable and i.poll_bool]
#
#     Returns:
#         _type_: _description_
#     """
#     @property
#     def _addons(self):
#         import addon_utils
#         return [
#             (mod, addon_utils.module_bl_info(mod))
#             for mod in addon_utils.modules(refresh=False)]
#
#     @cache
#     def _is_select_vert(self=None) -> bool:
#         '''反回活动网格是否选中了顶点的布尔值'''
#         bm = bbpy.context.object_bmesh
#         if bm:
#             for i in bm.verts:
#                 if i.select:
#                     return True
#         return False
#
#     @property
#     def is_select_vert(self) -> bool:
#         return PollProperty._is_select_vert()
#
#     def _poll_args(self):
#         """反回poll eval的环境
#
#         Returns:
#             _type_: _description_
#         """
#         C = bpy.context
#         D = bpy.data
#         ob = bpy.context.object
#         sel_objs = bpy.context.selected_objects
#         use_sel_obj = ((not ob) and sel_objs)  # 使用选择的obj最后一个
#         O = sel_objs[-1] if use_sel_obj else ob
#         mesh = O.data if O else None
#
#         return {'bpy': bpy,
#                 'C': C,
#                 'D': D,
#                 'O': O,
#                 'mode': C.mode,
#                 'tool': C.tool_settings,
#                 'mesh': mesh,
#                 'is_select_vert': self.is_select_vert,
#                 }
#
#     @property
#     # @bbpy.debug.time
#     def poll_args(self):
#         return self._poll_args()
#
#     def _is_enabled_addon(addon_name):
#         return addon_name in bpy.context.preferences.addons
#
#     __globals = {"__builtins__": None,
#                  'len': len,
#                  'is_enabled_addon': _is_enabled_addon,  # 测试是否启用此插件
#                  #  'max':max,
#                  #  'min':min,
#                  }
#
#     poll_string: StringProperty(
#         name='条件',
#         default='True',
#         description='''poll表达式
#     {'bpy': bpy,
#     'C': bpy.context,
#     'D': bpy.data,
#     'O': bpy.context.object,
#     'mode': bpy.context.mode,
#     'tool': bpy.context.tool_settings,
#     }
#     ''',
#     )
#
#     # @bbpy.debug.time
#     def poll_property(self, poll_string: str) -> bool:
#         """反回输入的poll_string的布尔值
#             s = 'next == None'
#             s = '[(3-2 == 1 ) ,  (100 ** 100 == 101),]'
#             s = 'a'
#             s = r'os.path.split("emm\text")'
#             s = 'import os'
#             c = compile(du, "<string>", "eval")
#
#         Args:
#             poll_string (str): _description_
#
#         Returns:
#             bool | Exception: 反回输入表达式的布尔值或是表达式识别错误
#         """
#
#         dump_data = ast.dump(ast.parse(poll_string), indent=2)
#         shield = {'Del',
#                   #   'Call',
#                   'Import',
#                   'Lambda',
#                   'Return',
#                   'Global',
#                   'Assert',
#                   'ClassDef',
#                   'ImportFrom',
#                   #   'Module',
#                   #   'Expr',
#                   }
#         is_shield = {i for i in shield if i in dump_data}
#         if is_shield:
#             text = Exception(
#                 f'input poll_string is invalid\t{is_shield} of {poll_string}')
#             print(text)
#             return text
#         else:
#             e = eval(poll_string, self.__globals, self.poll_args)
#             return bool(e)
#
#     @property
#     # @bbpy.debug.time
#     def poll_bool(self) -> bool:
#         """反回当前self的poll
#         TODO 选择POLL
#
#         Returns:
#             bool: _description_
#         """
#
#         @bbpy.debug.time
#         def f():
#             self.is_available = False
#             return False
#
#         try:
#             poll = self.poll_property(self.poll_string)
#         except Exception as e:
#             import traceback
#             print(
#                 f'ERROR:\tpoll_bool  {self.poll_string}\t', e, self.poll_args)
#             traceback.print_exc()
#             return f()
#         else:
#             if isinstance(poll, bool):
#                 if not self.is_available:
#                     self.is_available = True
#                 return poll and self.is_enabled
#
#             return f()
#
#     poll_bool_result: BoolProperty()
#
#     class SetPollExpression(bbpy.types.Operator, Data):
#         bl_idname = 'ui.ui_set_poll_expression'
#         bl_label = '设置条件表达式'
#
#         is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
#         width: IntProperty(default=1000)
#
#         is_not: BoolProperty(name='取反', description='可以理解成取反')
#         is_set_item_poll: BoolProperty(name='是设置一个项的poll',
#                                        )
#
#         poll_string: StringProperty(
#             name='条件',
#             default='True',
#         )
#
#         @property
#         def space_type(self):
#             return {
#                 'prefix': 'C.space_data.type == ',
#                 'suffix': '',
#                 'name': '空间类型',
#                 'items': [
#                     {'name': 'Empty',                'item': 'EMPTY', },
#                     {'name': '3D Viewport',          'item': 'VIEW_3D', },
#                     {'name': 'UV/Image Editor',      'item': 'IMAGE_EDITOR', },
#                     {'name': 'Node Editor',          'item': 'NODE_EDITOR', },
#                     {'name': 'Video Sequencer',      'item': 'SEQUENCE_EDITOR', },
#                     {'name': 'Movie Clip Editor',    'item': 'CLIP_EDITOR', },
#                     {'name': 'Dope Sheet',           'item': 'DOPESHEET_EDITOR', },
#                     {'name': 'Graph Editor',         'item': 'GRAPH_EDITOR', },
#                     {'name': 'Nonlinear Animation',  'item': 'NLA_EDITOR', },
#                     {'name': 'Text Editor',          'item': 'TEXT_EDITOR', },
#                     {'name': 'Python Console',       'item': 'CONSOLE', },
#                     {'name': 'Info',                 'item': 'INFO', },
#                     {'name': 'Top Bar',              'item': 'TOPBAR', },
#                     {'name': 'Status Bar',           'item': 'STATUSBAR', },
#                     {'name': 'Outliner',             'item': 'OUTLINER', },
#                     {'name': 'Properties',           'item': 'PROPERTIES', },
#                     {'name': 'File Browser',         'item': 'FILE_BROWSER', },
#                     {'name': 'Spreadsheet',          'item': 'SPREADSHEET', },
#                     {'name': 'Preferences',          'item': 'PREFERENCES', },
#                 ],
#             }
#
#         @property
#         def regions_type(self):
#             return {
#                 'prefix': 'C.region.type == ',
#                 'suffix': '',
#                 'name': '区域类型',
#                 'items': [
#                         {'item': 'WINDOW', 'name': 'Window', },
#                         {'item': 'HEADER', 'name': 'Header', },
#                         {'item': 'CHANNELS', 'name': 'Channels', },
#                         {'item': 'TEMPORARY', 'name': 'Temporary', },
#                         {'item': 'EXECUTE', 'name': 'Execute Buttons', },
#                         {'item': 'UI', 'name': 'UI', },
#                         {'item': 'TOOLS', 'name': 'Tools', },
#                         {'item': 'TOOL_PROPS', 'name': 'Tool Properties', },
#                         {'item': 'PREVIEW', 'name': 'Preview', },
#                         {'item': 'HUD', 'name': 'Floating Region', },
#                         {'item': 'NAVIGATION_BAR', 'name': 'Navigation Bar', },
#                         {'item': 'FOOTER', 'name': 'Footer', },
#                         {'item': 'TOOL_HEADER', 'name': 'Tool Header', },
#                         {'item': 'XR', 'name': 'XR', },
#                 ],
#             }
#
#         @property
#         def active_object_type(self):
#             return {
#                 'prefix': 'C.object.type == ',
#                 'suffix': '',
#                 'name': '活动项物体类型',
#                 'items': [
#                     {'name': 'Mesh',            'item': 'MESH', },
#                     {'name': 'Curve',           'item': 'CURVE', },
#                     {'name': 'Surface',         'item': 'SURFACE', },
#                     {'name': 'Metaball',        'item': 'META', },
#                     {'name': 'Text',            'item': 'FONT', },
#                     {'name': 'Hair Curves',     'item': 'CURVES', },
#                     {'name': 'Point Cloud',     'item': 'POINTCLOUD', },
#                     {'name': 'Volume',          'item': 'VOLUME', },
#                     {'name': 'Grease Pencil',   'item': 'GPENCIL', },
#                     {'name': 'Armature',        'item': 'ARMATURE', },
#                     {'name': 'Lattice',         'item': 'LATTICE', },
#                     {'name': 'Empty',           'item': 'EMPTY', },
#                     {'name': 'Light',           'item': 'LIGHT', },
#                     {'name': 'Light Probe',     'item': 'LIGHT_PROBE', },
#                     {'name': 'Camera',          'item': 'CAMERA', },
#                     {'name': 'Speaker',         'item': 'SPEAKER', }, ],
#             }
#
#         @property
#         def mesh_select_mode(self):
#             return {
#                 'prefix': 'tool.mesh_select_mode[:] == ',
#                 'suffix': '',
#                 'name': '网格选择模式',
#                 'items': [
#
#                     {'prefix': '', 'suffix': '',
#                         'item': 'is_select_vert',        'name': '选中了顶点', },
#                     None,
#
#                     {'prefix': 'tool.mesh_select_mode[0] == ',
#                         'item': True,        'name': '顶点', },
#                     {'prefix': 'tool.mesh_select_mode[1] == ',
#                         'item': True,        'name': '边', },
#                     {'prefix': 'tool.mesh_select_mode[2] == ',
#                         'item': True,        'name': '面', },
#                     None,
#                     {'item': [True, False, False],        'name': '仅顶点', },
#                     {'item': [False, True, False],        'name': '仅边', },
#                     {'item': [False, False, True],        'name': '仅面', },
#                     None,
#                     {'item': [True, False, True],        'name': '仅 顶点&面', },
#                     {'item': [False, True, True],        'name': '仅 边&面', },
#                     {'item': [True, True, False],        'name': '仅 顶点&边', },
#                     {'item': [True, True, True],        'name': '顶点&边&面', },
#                 ],
#             }
#
#         @property
#         def obj_mode(self):
#             return {
#                 'prefix': 'C.mode == ',
#                 'suffix': '',
#                 'name': '物体模式',
#                 'items': [
#                     {'name': 'Mesh Edit',        'item': 'EDIT_MESH'},
#                     {'name': 'Curve Edit',        'item': 'EDIT_CURVE'},
#                     {'name': 'Curves Edit',        'item': 'EDIT_CURVES'},
#                     {'name': 'Surface Edit',        'item': 'EDIT_SURFACE'},
#                     {'name': 'Text Edit',        'item': 'EDIT_TEXT'},
#                     {'name': 'Armature Edit',        'item': 'EDIT_ARMATURE'},
#                     {'name': 'Metaball Edit',        'item': 'EDIT_METABALL'},
#                     {'name': 'Lattice Edit',        'item': 'EDIT_LATTICE'},
#                     None,
#
#                     {'name': 'Pose',        'item': 'POSE'},
#                     {'name': 'Sculpt',        'item': 'SCULPT'},
#                     {'name': 'Weight Paint',        'item': 'PAINT_WEIGHT'},
#                     {'name': 'Vertex Paint',        'item': 'PAINT_VERTEX'},
#                     {'name': 'Texture Paint',        'item': 'PAINT_TEXTURE'},
#                     {'name': 'Particle',        'item': 'PARTICLE'},
#                     {'name': 'Object',        'item': 'OBJECT'},
#                     None,
#
#                     {'name': 'Grease Pencil Paint',
#                         'item': 'PAINT_GPENCIL'},
#                     {'name': 'Grease Pencil Edit',        'item': 'EDIT_GPENCIL'},
#                     {'name': 'Grease Pencil Sculpt',
#                         'item': 'SCULPT_GPENCIL'},
#                     {'name': 'Grease Pencil Weight Paint',
#                         'item': 'WEIGHT_GPENCIL'},
#                     {'name': 'Grease Pencil Vertex Paint',
#                         'item': 'VERTEX_GPENCIL'},
#                     {'name': 'Curves Sculpt',        'item': 'SCULPT_CURVES'},
#                 ],
#             }
#
#         @property
#         def other(self):
#             return{
#                 'prefix': '',
#                 'suffix': '',
#                 'name': '其它',
#                 'items': [
#                     {'item': ' and ',
#                      'name': 'and',
#                      'parentheses': False,
#                      'not_str': True},
#                     {'item': ' or ',
#                      'name': 'or',
#                      'parentheses': False,
#                      'not_str': True},
#                     {'item': ' not ',
#                      'name': 'not',
#                      'parentheses': False,
#                      'not_str': True},
#
#                     None,
#                     {'item': 'POSE',              'name': 'Pose Mode', },
#                     {'item': 'POSE',              'name': 'Pose Mode', },
#                 ],
#             }
#
#         @property
#         def add_list(self) -> list[dict[list[tuple]]]:
#             '''
#             [[(id,name,poll_string)],...]
#             '''
#             return [
#                 self.obj_mode,
#                 self.active_object_type,
#                 self.mesh_select_mode,
#                 None,
#                 self.space_type,
#                 self.regions_type,
#                 self.other,
#             ]
#
#         def draw_logical_operator(self, layout: 'bpy.types.UILayout'):
#
#             is_draw, lay = draw_extend_ui(layout,
#                                           f'draw_logical_operator',
#                                           label='语法解释',
#                                           default_extend=False,
#                                           )
#             if is_draw:
#                 text = '可使用Python逻辑运算符或表达式'
#                 lay.label(text=text)
#                 text = '  and     x and y 布尔"与" - 如果 x 为 False，x and y 返回 x 的值，否则返回 y 的计算值 . '
#                 lay.label(text=text)
#                 text = '  or       x or y 布尔"或" - 如果 x 是 True，它返回 x 的值，否则它返回 y 的计算值 .'
#                 lay.label(text=text)
#                 text = '  not      not x 布尔"非" - 如果 x 为 True，返回 False  .如果 x 为 False，它返回 True .'
#                 lay.label(text=text)
#
#                 lay.separator()
#                 text = '''参数:'''
#                 lay.label(text=text)
#
#                 texts = {'bpy: bpy,': '',
#                          'C: bpy.context,': 'blender 上下文',
#                          'D: bpy.data,': 'blender数据',
#                          'O: bpy.context.object,': '活动物体',
#                          'mode: C.mode,': '模式',
#                          'tool: C.tool_settings,': '工具设置',
#                          'mesh: bpy.context.object.data,': '网格,如果物体不为mesh则为None',
#                          'is_select_vert: bool,': '是否选择了顶点的布尔值', }
#                 for k, v in texts.items():
#                     sp = lay.split(factor=0.2)
#                     sp.label(text='    '+k)
#                     sp.label(text=v)
#
#                 # long_label(lay, text, max_len=500)
#             else:
#
#                 layout.separator()
#
#                 row = layout.row(align=True)
#                 row.prop(self, 'is_not')
#
#                 self.draw_list_items(layout)
#
#         @property
#         def item(self):
#             return self.act_ui_item if self.is_set_item_poll else self.act_ui_element
#
#         def draw(self, context):
#             layout = self.layout
#             col = layout.column()
#             sp = col.split(factor=0.05, align=True)
#             sp.label(text='条件:')
#             sp.prop(self.item, 'poll_string', text='')
#             self.draw_logical_operator(col)
#
#         def draw_list_items(self, layout: 'bpy.types.UILayout'):
#             row = layout.row()
#             for items in self.add_list:
#                 if not items:
#                     row.separator()
#                 else:
#                     col = row.column(align=True)
#                     self.draw_items(col, items)
#
#         def draw_items(self, layout: 'bpy.types.UILayout', data):
#             layout.label(text=data['name'])
#             for item in data['items']:
#                 if not item:
#                     layout.separator()
#                 else:
#                     self.draw_item(layout, item, data)
#
#         def draw_item(self, layout: 'bpy.types.UILayout', item, data):
#             op = layout.operator(self.bl_idname,
#                                  text=item['name']
#                                  )
#             is_parentheses = item.get('parentheses', True)
#
#             prefix = item.get('prefix', data['prefix'])
#             suffix = item.get('suffix', data['suffix'])
#             is_not = 'not ' if self.is_not else ''
#
#             d = item['item']
#             ite = f'"{d}"' if (isinstance(d, str) and (
#                 not item.get('not_str'))) else str(d)
#
#             poll_string = is_not + prefix + ite + suffix
#             if is_parentheses:
#                 poll_string = '(' + poll_string+')'
#
#             op.is_not = self.is_not
#             op.is_popup_menu = False
#             op.poll_string = poll_string
#             op.is_set_item_poll = self.is_set_item_poll
#
#         def invoke(self, context, event):
#             if not self.is_popup_menu:
#                 return self.execute(context)
#
#             data = {'operator': self}
#             if self.width != -1:
#                 data['width'] = self.width
#             return context.window_manager.invoke_props_dialog(**data)
#
#         def execute(self, context):
#             if not self.is_popup_menu:
#                 print(self, 'execute', self.poll_string)
#                 if self.is_set_item_poll:
#                     act = self.act_ui_item
#                 else:
#                     act = self.act_ui_element
#
#                 is_true = act.poll_string == 'True'
#
#                 if is_true:
#                     act.poll_string = self.poll_string
#                 else:
#                     act.poll_string += self.poll_string
#
#             return {'FINISHED'}
#
#
#     class ShowKeymaps(Data, bbpy.types.Operator):
#         bl_idname = 'ui.custom_ui_show_keymaps'
#         bl_label = '显示插件偏好设置'
#
#         def execute(self, context):
#             bpy.ops.screen.userpref_show()
#             context.preferences.active_section = 'KEYMAP'
#             for win in context.window_manager.windows:
#                 for area in win.screen.areas:
#                     if area.type == 'PREFERENCES':
#                         space = area.spaces[0]
#                         space.filter_type = 'KEY'
#                         space.filter_text = self.act_ui_item.key.key_combination
#                         return {'FINISHED'}
#             return {'FINISHED'}
#
