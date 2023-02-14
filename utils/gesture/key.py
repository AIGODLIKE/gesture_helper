def register():
    # bpy.utils.register_class(UiElementItem)
    ...


def unregister():
    # bpy.utils.unregister_class(UiElementItem)
    ...

#
# class KeyMap(PropertyGroup, Data):
#     """存快捷键信息
#     设置快捷键数据
#
#     显示 快捷键属性 ctrl alt shift 的状态那些
#
#
#     Args:
#         PropertyGroup (_type_): Blender属性组
#         Data (_type_): 自定义数据类
#
#     Returns:
#         _type_: _description_
#     """
#     # load
#
#     @classmethod
#     def __load__(cls) -> None:
#         """
#         初始化时
#         也就是开启blender时,初始化一次
#         加载快捷键
#         清理无效快捷键并添加未注册快捷键
#
#         一次性设置所有快捷键的
#         """
#         # print('__init__ keymap', cls)
#         cls.injection_attribute(cls)
#         kmi_data = cls.kmi_data.fget(cls)
#         key_reg_data = cls.key_register_data.fget(cls)
#
#         for keymap in key_reg_data:
#             for ui in key_reg_data[keymap]:
#                 uid = ui.uuid
#                 kmi = kmi_data[uid][keymap]
#                 if not kmi:
#                     item = ui.key
#                     item.is_update = True
#                     item.add_key(keymap)
#                     item.is_update = False
#
#     # type property init
#
#     def _incoming_parameters(self, data):
#         """传入参数
#         并设置到self内,用于初始化或加载数据
#
#         Args:
#             data (str | dict): _description_
#         """
#         def set_pr():
#             for key, value in data.items():
#                 if hasattr(self, key):
#                     print(f'setattr({self}, {key}, {value})')
#                     setattr(self, key, value)
#
#         if isinstance(data, dict):
#             set_pr()
#         elif isinstance(data, str) and (data in ('panel',
#                                                  'layout',
#                                                  )):
#             self.is_use_keymaps = self.is_enable_keymaps = False
#
#     def __init__(self, preset_data = None):
#         """初始化快捷键
#
#         Args:
#             preset_data (str | dict, optional): 如果输入字符串则加载默认的输入类型快捷键,如果输入字典则加载字典内的数据. Defaults to None.
#         """
#         text = f'KeyMap.__init__(type:{type}) uuid:{self.uuid} \n\tPreset data:{preset_data}'
#         print(text)
#         self.is_update = True
#
#         self._incoming_parameters(preset_data)
#
#         if self.is_use_keymaps:
#             # 如果需要使用快捷键的话添加快捷键到blender
#             for keymap in self.keymaps_set:
#                 self.add_key(keymap)
#         print(self.__dict__)
#
#         self.update_key_data(bpy.context)
#
#         self.is_update = False
#
#     def __del_key__(self) -> None:
#         """删除所有快捷键
#         删除上级项时使用
#         """
#
#         keymaps = self.configs_keymaps()
#         keymaps_set = self.get_use_keymaps_set()
#         if self.is_use_keymaps:
#             for keymaps_name in keymaps_set:
#                 keymaps_items = keymaps.get(keymaps_name).keymap_items
#                 self.__re_key(keymaps_items)
#
#     def __re_key(self, keymaps_items):
#         """删除快捷键
#
#         Args:
#             keymaps_items (_type_): _description_
#         """
#         bl_idname = ExecuteOperator.bl_idname
#         if keymaps_items:
#             for kmi in keymaps_items:
#                 if kmi.idname == bl_idname and kmi.properties.uuid == self.uuid:
#                     keymaps_items.remove(kmi)
#
#     def key_unable_update(self) -> bool:
#         """
#         反回是否需要更新的布尔值
#         只有不是在更新中 或 不需要使用快捷键时 反回False
#
#         用于确定是否需要更新
#         """
#         return self.is_update or (self.is_use_keymaps == False)
#
#     def get_type_enum(self, context):
#         """获取快捷键type枚举
#         通过map_type获取需要的枚举
#
#         Args:
#             context (_type_): _description_
#
#         Returns:
#             _type_: _description_
#         """
#         ret = []
#         map_type = self.map_type
#         for id, name, des, icon, value in kmi_type['items']:
#             if id in kmi_type_classify[map_type]:
#                 ret.append((id, name, des, icon, value))
#         return ret
#
#     def set_type(self, value) -> None:
#         """
#         通过多个数据存每一个map_type应是那个数据
#         """
#
#         def get_dict_key(dic: dict, value):
#             """通过值 获取字典的键
#             Args:
#                 dic (_type_): _description_
#                 value (_type_): _description_
#
#             Returns:
#                 _type_: _description_
#
#             # keys = list(dic.keys())
#             # values = list(dic.values())
#             # idx = values.index(value)
#             # key = keys[idx]
#             # return key
#
#             """
#             for k, v in dic.items():
#                 if v == value:
#                     return k
#
#         def _get_map_type(_id):
#             """通过输入的type id获取map_type应为啥
#
#             Args:
#                 id (_type_): _description_
#
#             Returns:
#                 _type_: _description_
#             """
#             values = kmi_type_classify.values()
#             for i in values:
#                 if _id in i:
#                     return get_dict_key(kmi_type_classify, i)
#
#         for item in kmi_value_enum:
#             if item.value == value:
#                 value = item.identifier
#                 self.map_type = _get_map_type(value)
#                 self[self._map_type_key] = value
#                 return
#
#     @property
#     def ui(self) -> 'UIElementItem':
#         """反回当前项的父项元素
#         Returns:
#             UIElementItem: _description_
#         """
#         return self.prefs.ui_items.get(self.uuid)
#
#     @property
#     def _map_type_key(self) -> str:
#         """反回type的临时类型
#
#         Returns:
#             _type_: _description_
#         """
#         return "tmp_type_"+self.map_type.lower()
#
#     def __set_type(self) -> None:
#         """设置type为默认
#         """
#         default = {
#             'tmp_type_timer': 'TIMER',
#             'tmp_type_mouse': 'LEFTMOUSE',
#             'tmp_type_ndof': 'NDOF_MOTION',
#             'tmp_type_keyboard': 'NONE',
#         }
#         for key, value in default.items():
#             if key not in self:
#                 self[key] = value
#
#     def get_type(self) -> str:
#         """
#         获取时就直接拿每一个类对应的数据
#         """
#         self.__set_type()
#         map_type = self.map_type
#         if map_type in ('KEYBOARD',
#                         'MOUSE',
#                         'NDOF',
#                         # 'TEXTINPUT','TIMER',
#                         ):
#             return kmi_value_enum.get(self[self._map_type_key]).value
#
#         return kmi_value_enum.get('NONE').value
#
#     # key set update
#
#     def get_kmi_active_value(self) -> bool:
#         """获取快捷键是否需要激活的布尔值
#         需要所有选项都开启了才会激活快捷键
#
#         Returns:
#             bool: _description_
#         """
#         is_active = all((self.ui.is_enabled, self.is_use_keymaps,
#                          self.is_enable_keymaps, self.prefs.is_enabled))
#
#         return is_active
#
#     def set_to_kmi_properties(self, kmi: 'bpy.types.KeyMapItem') -> None:
#         """将当前self内的数据set to input kmi in
#
#         Args:
#             kmi (bpy.types.KeyMapItem): _description_
#         """
#
#         prop = kmi.properties
#
#         items = {
#             'type': self.ui.type,
#             'uuid': self.uuid,
#             'value': self.value,
#             'double_key': self.double_key,
#             'long_press_time': self.long_press_time,
#             'double_key_time': self.double_key_time,
#
#             'popup_title': self.popup_title,
#             'popup_icon': self.popup_icon,
#             'show_popup_title': self.show_popup_title,
#         }
#
#         for item in items:
#             if item in dir(prop):
#                 setattr(prop, item, items[item])
#
#     def set_data_to_kmi(self, kmi: 'bpy.types.KeyMapItem'):
#         """为输入的kmi设置值为当前self内的值
#
#         Args:
#             kmi (bpy.types.KeyMapItem): _description_
#         """
#         version = bpy.app.version_string
#         items = ('type',
#                  'value',
#                  'repeat',
#                  'map_type',
#                  'key_modifier',
#                  )
#
#         ct = ('alt', 'ctrl', 'shift', 'oskey', )
#         items += (('any', ) if self.any else ct)
#
#         if (version <= '3.1.0') and (self.value == 'CLICK_DRAG'):
#             # 旧版本api项在value里面,新版改到direction里面了
#             items += ('direction',)
#
#         kmi.active = self.get_kmi_active_value()
#
#         for item in items:
#             value = getattr(self, item)
#             if item == 'value':
#                 value = self.get_kmi_value(value)
#             try:
#                 setattr(kmi, item, value)
#             except Exception as e:
#                 print('ERROR\tset_kmi_data\t', kmi, item, value, '\n', e, '\n')
#
#         self.set_to_kmi_properties(kmi)
#
#         # 再将设置好的值 从Kmi反回来,避免不一样
#         self.map_type = kmi.map_type
#         self.key_modifier = kmi.key_modifier
#         self.type = kmi.type
#
#     def set_user_manual_modifier_key_kmi(self, keymap_name: str) -> None:
#         """循环在用户更改的快捷键里面,如果是用户改了的,就把用户改了的直接删掉
#
#         Args:
#             keymap_name (str): _description_
#         """
#         idname = ExecuteOperator.bl_idname
#
#         keyconfigs = bpy.context.window_manager.keyconfigs
#         keymap = keyconfigs.user.keymaps.get(keymap_name)
#         keymap_items = keymap.keymap_items
#
#         for kmi in keymap_items:
#             if kmi.idname == idname:
#                 uuid = kmi.properties.uuid
#                 if uuid == self.uuid:
#                     self.set_data_to_kmi(kmi)
#
#     def for_set_keymaps_data(self) -> None:
#         """
#         从store里面的数据设置快捷键
#         如果用户在快捷键里面更改了键会怎么样?:会存在user里面,再追加一个更改user
#         """
#         if not self.is_use_keymaps:
#             return
#
#         kmi_data = self.kmi_data[self.uuid]
#
#         if not kmi_data:
#             UIItem.__load__()
#
#         for keymap_name in kmi_data:
#             kmi = kmi_data[keymap_name]
#             if kmi:
#                 self.set_data_to_kmi(kmi)
#             self.set_user_manual_modifier_key_kmi(keymap_name)
#
#     def update_any(self, context: 'bpy.context') -> None:
#         """更新any的键, 几个控制键需要同步设置成any的布尔值
#         Args:
#             context (_type_): _description_
#         """
#         if self.key_unable_update():
#             return
#
#         self.is_update = True
#
#         self.ctrl = self.alt = self.shift = self.oskey = self.any
#
#         self.is_update = False
#
#         self.update_key_data(context)
#
#     def update_key_data(self, context: 'bpy.context'):
#         """更新uuid项的所有快捷键,将所有的设置赋予到对应快捷键上面
#         循环在所有快捷键里面,如果idname和uuid匹配将会把所有的数据进行设置(需要操作的数据很多,但不是很卡)
#
#         Args:
#             context (_type_): _description_
#         """
#
#         if self.key_unable_update():
#             return
#
#         self.is_update = True
#         print(f'{addon_name} update_key_data id:{self.uuid}')
#
#         if self.any and (not all((self.ctrl, self.alt, self.shift, self.oskey, self.any))):
#             self.any = False
#
#         self.for_set_keymaps_data()
#         self.is_update = False
#
#     uuid: StringProperty(options={'HIDDEN'}, update=update_key_data)
#
#     type: EnumProperty(name='事件类型',
#                        items=get_type_enum,
#                        update=update_key_data,
#                        set=set_type, get=get_type)
#
#     @classmethod
#     def _key_combination(cls, self):
#         text = ''
#         data = {
#             'any': 'Any',
#             'shift': 'Shift',
#             'ctrl': 'Ctrl',
#             'alt': 'Alt',
#             'oskey': 'Cmd',
#             'key_modifier': pgettext(self.key_modifier, msgctxt=ui_events_keymaps),
#             'type': pgettext(self.type, msgctxt=ui_events_keymaps),
#         }
#
#         for i in data:
#             value = getattr(self, i, None)
#
#             if i == 'key_modifier':
#                 if value != 'NONE':
#                     text += ' '+data[i]
#             elif value:
#                 text += ' '+data[i]
#         return text
#
#     @property
#     def key_combination(self) -> str:
#         """键组合名称
#
#         Returns:
#             str: _description_
#
#         key_combination: StringProperty(name='键组合名称', get=get_key_combination)
#         """
#         return self._key_combination(self)
#
#     alt: BoolProperty(name='Alt', update=update_key_data)
#     any: BoolProperty(name='Any', update=update_any)
#     ctrl: BoolProperty(name='Ctrl', update=update_key_data)
#     shift: BoolProperty(name='Shift', update=update_key_data)
#     oskey: BoolProperty(name='Cmd', update=update_key_data)
#     repeat: BoolProperty(update=update_key_data)
#
#     value: EnumProperty(name='触发方式', **kmi_value,
#                         default='PRESS', update=update_key_data)
#
#     map_type: EnumProperty(**kmi_map_type, update=update_key_data)
#
#     def direction_items(self, context) -> list[tuple[str]]:
#         """反回方向的枚举项
#         因为3.1后的版本更改了快捷键里面的部分内容,所以旧的版本有问题
#
#         Args:
#             context (_type_): _description_
#
#         Returns:
#             list[tuple[str]]: _description_
#         """
#
#         version = bpy.app.version_string
#
#         # 旧版不用这个属性？
#         if version <= '3.1.0':
#             # 旧版本api项在value里面,新版改到direction里面了
#
#             return rna_data(
#                 KeyMapItem, 'value')['items']
#         return rna_data(KeyMapItem, 'direction')['items']
#
#     direction: EnumProperty(items=direction_items,
#                             default=-1, update=update_key_data)
#
#     key_modifier: EnumProperty(**kmi_key_modifier,
#                                default='NONE', update=update_key_data)
#
#     double_key: EnumProperty(name='双键', **kmi_type,
#                              update=update_key_data,
#                              default='A',
#                              description='''第二个键''')
#     double_key_time: IntProperty(
#         name='双键点击时长 ms', default=-1, update=update_key_data,)
#     long_press_time: IntProperty(
#         name='长按时长 ms', default=-1, update=update_key_data,)
#
#     show_popup_title: BoolProperty(name='是否显示弹出窗口抬头', update=update_key_data)
#     popup_title: StringProperty(update=update_key_data)
#     popup_icon: StringProperty(default='NONE', update=update_key_data)
#
#     # keymaps update
#
#     def get_use_keymaps_set(self) -> set:
#         """获取当前UI项 快捷键所在的所有keymaps
#         *set 没有顺序,但可以用来作布尔运算
#
#         Returns:
#             set: _description_
#         """
#
#         is_set = (self.keymaps == 'set()')
#         empty = (self.keymaps == '')
#
#         eval_error = (('{' not in self.keymaps) or ('}' not in self.keymaps))
#         init_keymaps = is_set or empty or eval_error
#
#         if init_keymaps:  # 确保至少有一个快捷键的空间,并确保eval不报错
#             self.keymaps = str(DEFAULT_KEYMAPS)
#         try:
#             items = ast.literal_eval(self.keymaps)
#         except Exception:
#             self.keymaps = str(DEFAULT_KEYMAPS)
#             items = DEFAULT_KEYMAPS
#         return items
#
#     def add_key(self, keymap_name: str) -> bpy.types.KeyMapItem:
#         """添加快捷键到输入的keymaps里面
#
#         Args:
#             keymap_name (str): _description_
#
#         Returns:
#             bpy.types.KeyMapItem: _description_
#         """
#         bl_idname = ExecuteOperator.bl_idname
#
#         uuid = self.uuid
#         keymaps = self.configs_keymaps()
#         value = self.get_kmi_value(self.value)
#
#         keymap = keymaps.get(keymap_name, keymaps.from_other_keymaps_new(
#             'default', keymap_name, 'addon'))
#
#         kmi = keymap.keymap_items.new(bl_idname, self.type, value)
#         self.set_data_to_kmi(kmi)
#
#         text = f'''{addon_name} id:{uuid} \t '{keymap_name}'\t\t.keymap_items.new(\t'{self.type}',\t {value})'''
#         debug_print(text,                    debug=True)
#         return kmi
#
#     def _get_keymaps(self) -> str:
#         """获取keymaps
#
#         Returns:
#             _type_: _description_
#         """
#
#         if 'keymaps' not in self:
#             return str(DEFAULT_KEYMAPS)
#         return self['keymaps']
#
#     def _set_keymaps(self, value) -> None:
#         """设置keymaps
#
#         Args:
#             value (_type_): _description_
#         """
#         self.__set_keymaps(*map(ast.literal_eval, (value, self.keymaps)))
#         self['keymaps'] = value
#
#     def __set_keymaps(self, new_keymaps: set, old_keymaps: set) -> None:
#         """输入一个新的keymaps和旧keymap
#         将两个set差集再使用差异来判断是否需要添加或删除快捷键
#
#
#         只有更新keymaps 时才会有添加 or 删除快捷键操作
#         更新快捷键项,用此函数添加或注册快捷键
#         如果self.is_enable_keymaps == False 需要将所有的快捷键设置为禁用
#
#         只有设置了快捷键的才会设置这个参数
#
#         设置并更新快捷键项
#         只设置项添加或删除快捷键
#         不对快捷键里面的内容进行操作
#
#         Args:
#             new_keymaps (set, optional): _description_.
#             old_keymaps (set, optional): _description_.
#         """
#         if self.key_unable_update():
#             return
#
#         self.is_update = True
#
#         kmi_data = self.kmi_data[self.uuid]
#
#         difference = old_keymaps.symmetric_difference(new_keymaps)
#         text = f'''keymaps_update id:{self.uuid}
#         old_keymaps:{old_keymaps}
#         new_keymaps:{new_keymaps}
#         difference:{difference}
#
#
#         kmi_data:{self.kmi_data}
#
#         '''
#         print(text)
#
#         active_keymaps = self.configs_keymaps()
#
#         for keymap_name in difference:
#             if keymap_name in new_keymaps:
#                 # 还没添加快捷键的
#                 kmi = self.add_key(keymap_name)
#                 self.set_data_to_kmi(kmi)
#
#             else:
#                 # 这个是要被删掉的
#                 kmi = kmi_data[keymap_name]
#                 active_keymaps[keymap_name].keymap_items.remove(kmi)
#                 kmi_data.pop(keymap_name)
#
#         debug_print(f'id:{self.uuid} key difference {difference}',
#                     debug=True)
#
#         self.is_update = False
#
#     @property
#     def keymaps_set(self) -> set:
#         return ast.literal_eval(self.keymaps)
#
#     keymaps: StringProperty(name='keymaps',
#                             default="{'3D View'}",
#                             description='当前项需要添加的快捷键空间',
#                             get=_get_keymaps,
#                             set=_set_keymaps
#                             )
#     # keymaps update
#
#     def update_key_enable_state(self, context) -> None:
#         """更新快捷键是否需要启用
#
#         Args:
#             context (_type_): _description_
#         """
#         if self.key_unable_update():
#             return
#         self.set_key_enable_state(self.is_enable_keymaps)
#
#     def set_key_enable_state(self, value: bool) -> None:
#         """设置快捷键是否需要启用
#         每一次更新keymaps 和 is_enable_keymaps 都设置一遍快捷键是否启用,这样可以在外部调用此方法了
#
#         Args:
#             value (bool): _description_
#         """
#
#         if self.uuid in self.kmi_data:
#             keymaps = self.kmi_data[self.uuid]
#             for keymap in keymaps:
#                 kmi = keymaps[keymap]
#                 kmi.active = value
#
#     is_enable_keymaps: BoolProperty(name='快捷键是启用的',
#                                     default=True,
#                                     update=update_key_enable_state)
#
#     is_update: BoolProperty(default=False, name='是在更新中',
#                             description='常False,更新时为True,避免循环更新,如果开启会阻断keymaps和kmi的更新')
#
#     is_use_keymaps: BoolProperty(name='ui项是否需要使用快捷键',
#                                  default=True,
#                                  options={'HIDDEN', 'PROPORTIONAL'},
#                                  description='只有需要使用快捷键的才开启,如果开启会阻断keymaps和kmi的更新'
#                                  )
#
#     def get_is_user_modifier(self) -> bool:
#         """
#         性能问题？ 一直在刷新 :只有显示快捷键时才会显示
#         # for item in DEFAULT_KEY_DATA:
#         #     prop = getattr(self, item, None)
#         #     if DEFAULT_KEY_DATA[item] != prop:
#         #         return True
#         # return False
#         """
#         return True
#
#     def set_key_to_default(self, _) -> None:
#         """将self快捷键设置为默认值
#         也就是重置快捷键
#
#         Args:
#             _ (_type_): _description_
#         """
#
#         self.is_update = True
#         for key, item in self.bl_rna.properties.items():
#             if(key not in ('is_enable_keymaps',
#                            'is_user_modifier',
#                            'uuid',
#                            'key_combination')) and \
#                     (item.type not in ('POINTER',
#                                        'COLLECT')):
#                 print('property_unset', key)
#                 self.property_unset(key)
#         self.type = 'NONE'
#
#         self.update_key_data(bpy.context)
#
#         self.is_update = False
#
#     is_user_modifier: BoolProperty(
#         name='用户是否修改过快捷键', get=get_is_user_modifier, set=set_key_to_default)
#
#     def update_extend(self, context):
#         ...
#
#     is_extend: BoolProperty(name='是展开的',
#                             default=True,
#                             update=update_extend,
#                             description='''按ctrl or alt 同步子级
#     按shift同步 所有项'''
#                             )
#
#     class SetKeymaps(Data, bbpy.types.Operator):
#         bl_idname = 'ui.custom_ui_set_keymaps'
#         bl_label = '设置keymaps'
#         bl_description = '设置keymaps..'
#
#         uuid: StringProperty(**SKIP_DEFAULT,
#                              description='''uuid用来注册快捷键时识别项目,以及更改时设置快捷键项
#        ''')
#         width: IntProperty(default=-1)
#
#         is_set_value: BoolProperty(default=False, **SKIP_DEFAULT)
#         region_type: StringProperty()
#         space_type: StringProperty()
#         value: StringProperty(**SKIP_DEFAULT)
#
#         def draw_ops(self, layout: 'bpy.types.UILayout', uuid: str, idname: str) -> None:
#             """绘制设置keymaps操作符(直接设置值)
#
#             Args:
#                 layout (bpy.types.UILayout): _description_
#                 uuid (str): _description_
#                 idname (str): _description_
#             """
#
#             set_data = ast.literal_eval(self.act_ui_item.key.keymaps)
#
#             op = layout.operator(self.bl_idname, text=idname,
#                                  depress=idname in set_data,
#                                  emboss=True,
#                                  text_ctxt=i18n_contexts.id_windowmanager,
#                                  )
#             op.uuid = uuid
#             op.is_set_value = True
#             op.value = idname
#
#         def draw_entry(self, entry, layout: bpy.types.UILayout, level=0) -> None:
#             """绘制子项,如果有子项则绘制一个展开
#
#             Args:
#                 entry (_type_): _description_
#                 layout (bpy.types.UILayout): _description_
#                 level (int, optional): _description_. Defaults to 0.
#             """
#             def draw_func(layout: bpy.types.UILayout, idname, uuid):
#                 self.draw_ops(layout, uuid, idname)
#
#             keyconfigs = bpy.context.window_manager.keyconfigs
#
#             idname, space_id, region_id, children = entry
#
#             keymaps_items = {j.name for key in (
#                 keyconfigs.user.keymaps, keyconfigs.addon.keymaps, keyconfigs.default.keymaps) for j in key if not j.is_modal}
#
#             if idname not in keymaps_items:
#                 return
#
#             col = layout
#             col.alignment = 'LEFT'
#             if children:
#                 is_draw, lay = draw_extend_ui(
#                     col, f'draw_keymaps_{idname}_{space_id}_{region_id}', '%s' % idname,
#                     draw_func=draw_func,
#                     draw_func_data={'uuid': self.uuid, 'idname': idname},
#                     align=False,
#                     alignment='EXPAND',
#                 )
#
#                 if is_draw:
#                     for entry in children:
#                         self.draw_entry(entry, lay, level + 1)
#
#             else:
#                 self.draw_ops(layout, self.uuid, idname)
#
#         def draw(self, context) -> None:
#             """绘制弹出面板用于选择keymaps
#
#             Args:
#                 context (_type_): _description_
#             """
#             layout = self.layout
#             row = layout.row()
#
#             col = row.column()
#             for entry in self.keymap_hierarchy:
#                 self.draw_entry(entry, col)
#
#             col = row.column(align=True)
#             is_draw, lay = draw_extend_ui(
#                 col, 'draw_keymaps_is_add_items', label='已添加快捷键项')
#             if is_draw:
#                 set_data = self.act_ui_item.key.get_use_keymaps_set()
#                 for i in set_data:
#                     self.draw_ops(lay, self.uuid, i)
#             col.separator(factor=2)
#
#         def set_keymaps_value(self) -> set:
#             """设置值函数
#
#             Returns:
#                 _type_: _description_
#             """
#
#             set_data = self.act_ui_item.key.get_use_keymaps_set()
#
#             if self.value in set_data:
#                 set_data.remove(self.value)
#             else:
#                 set_data.add(self.value)
#             self.act_ui_item.key.keymaps = str(set_data)
#             return {'FINISHED'}
#
#         def invoke(self, context, event) -> set:
#             """如果展开面板则绘制面板否者直接绘制项
#             Args:
#                 context (_type_): _description_
#                 event (_type_): _description_
#
#             Returns:
#                 set: _description_
#             """
#             from bl_keymap_utils import keymap_hierarchy
#             self.keymap_hierarchy = keymap_hierarchy.generate()
#             ui_items = self.prefs.ui_items
#
#             if self.uuid not in ui_items:
#                 self.report({'ERROR': f'{self.uuid} not in data items'})
#                 return {'CANCELLED'}
#
#             if self.is_set_value:
#                 return self.set_keymaps_value()
#
#             data = {'operator': self}
#             if self.width != -1:
#                 data['width'] = self.width
#
#             return context.window_manager.invoke_props_dialog(**data)
