import bpy

from bpy.types import PropertyGroup
from bpy.props import PointerProperty


class ElementItem(PropertyGroup):
    ...


class UiElementItems(PropertyGroup):
    element_items: PointerProperty(type=ElementItem)


class_tuple = (
    ElementItem,
    UiElementItems,
)

register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()


def unregister():
    unregister_class()

# class Data:
#
#     @classmethod
#     def refresh_poll(cls) -> None:
#         PollProperty._is_select_vert.cache_clear()
#
#     @classmethod
#     def refresh_uilist(cls) -> None:
#         from ...ui.uilist import UI_UL_CustomUILayout
#         UI_UL_CustomUILayout._get_new_order.cache_clear()
#
#     @classmethod
#     def configs_keymaps(cls) -> bpy.types.KeyMaps:
#         """获取使用的快捷键映射
#         k.default == k.active
#         addon里面存的是 插件添加项
#         使用configs.addon添加快捷键
#         user #用户修改过或是用户添加的快捷键都在这里面
#         """
#         keyconfigs = bpy.context.window_manager.keyconfigs
#         return keyconfigs.addon.keymaps
#
#     @classmethod
#     def get_kmi_value(cls, value) -> str:
#         """获取快捷键项需要的值
#         添加了两种新的类型所以需要在这里获取
#         """
#         value = 'PRESS' if value in ('LONG_PRESS', 'DOUBLE_KEY') else value
#         return value
#
#     @classmethod
#     def generate_uuid(cls, slice=5) -> str:
#         """通过内置的uuid模块生成uuid
#         Args:
#             slice (int, optional): 设置生成uuid的位数. Defaults to 5.
#
#         Returns:
#             str: 反回uuid的字符串
#         """
#         import uuid
#         uid = str(uuid.uuid1())
#         return str(uuid.uuid5(uuid.NAMESPACE_DNS, uid))[:slice]
#     # property
#
#     def execute(self, context) -> set:
#         """
#         占位操作符执行函数
#         如果不添加将会弹出错误
#         """
#         text = f'{self.bl_idname}, execute {self}'
#         print(text)
#         return {'FINISHED'}
#
#     @classmethod
#     def is_draw_type(cls, draw_type: str) -> bool:
#         """反回是否绘制类型的布尔值
#         Args:
#             draw_type (str): 反回此类型是否可是绘制项
#
#         Returns:
#             bool: 是在排除项里面的布尔值
#         """
#         return draw_type not in ('operator',)
#
#     @classmethod
#     def injection_attribute(cls, self) -> None:
#         """
#         注入属性
#         向输入的self注入属性
#         如果数据无法写入将会报错
#         """
#
#         pr = 'prefs'
#         kmi = 'tmp_kmi'
#         it = 'act_ui_item'
#         el = 'act_ui_element'
#         getattr(self, pr, setattr(self, pr, Data.prefs.fget(self)))
#         getattr(self, kmi, setattr(self, kmi, Data.tmp_kmi.fget(self)))
#         getattr(self, el, setattr(self, el, Data.act_ui_element.fget(self)))
#         getattr(self, it, setattr(self, it, Data.act_ui_item.fget(self)))
#
#     @classmethod
#     def custom_ui_prefs(cls) -> 'CustomUI':
#         """反回插件的偏好设置
#         Returns:
#             CustomUI: _description_
#         """
#         from .. import addon_folder_name
#         return bbpy.get.addon.prefs(addon_folder_name).custom_ui
#
#     @property
#     def prefs(self=None) -> 'CustomUI':
#         """反回Custom_ui的偏好设置
#         新建文件时闪退 不能使用在绘制方法内
#
#         Args:
#             self (_type_, optional): _description_. Defaults to None.
#
#         Returns:
#             CustomUI: _description_
#         """
#         return Data.custom_ui_prefs()
#
#     @property
#     def act_ui_item(self=None) -> 'UIItem':
#         """获取活动项ui item
#         Args:
#             self (_type_, optional): _description_. Defaults to None.
#         Returns:
#             UIItem: _description_
#         """
#         prefs = bbpy.get.addon.prefs().custom_ui
#         ui_items = prefs.ui_items
#         ul = len(ui_items)
#         if not ul:
#             return None
#         index = -1 if prefs.active_index >= ul else prefs.active_index
#         ui_item = ui_items[index]
#         return ui_item
#
#     @property
#     def act_ui_element(self=None) -> 'UIElementItem':
#         """获取活动项UI元素
#
#         Args:
#             self (_type_, optional): _description_. Defaults to None.
#
#         Returns:
#             UIElementItem: _description_
#         """
#         ui_item = getattr(self, 'ui_item', Data.act_ui_item.fget())
#         if not ui_item or not len(ui_item.ui):
#             # 如果没有ui_item或长度为0
#             return None
#         ul = len(ui_item.ui)
#         index = ui_item.active_ui_index
#         if (index >= ul) or (index < -1):
#             # 保险避免超出范围
#             index = -1
#         return ui_item.ui[index]
#
#     @property
#     def double_keys(self) -> dict:
#         """获取双键信息,用来存有那些双键,在提示的时候有用
#
#         Returns:
#             dict: {key{}}
#         """
#         double_dict = {}
#         for item in self.prefs.ui_items:
#             key = item.key
#             if key.is_use_keymaps and key.is_enable_keymaps and key.value == 'DOUBLE_KEY':
#                 if key.key_combination not in double_dict:
#                     double_dict[key.key_combination] = {'keys': set()}
#                 double_dict[key.key_combination]['keys'].add(key.double_key)
#                 # 用于多个相同的双键区分用,如果有多个项都用一个那么只会保留最后一个使用使用字典因为是
#                 double_dict[key.key_combination][key.double_key] = item.uuid
#         return double_dict
#
#     @property
#     def key_register_data(self) -> dict:
#         """获取所有需要被注册的所有快捷键
#         在load的时候注册使用
#         记录每一个keymaps里面应有的快捷键
#
#
#         Returns:
#             dict: {'3D View':{UIItem,UIItem}} {keymaps_name:{'UIItem','UIItem'...使用集合来存.}}
#         """
#         ui_items = bbpy.get.addon.prefs().custom_ui.ui_items
#
#         data = {}
#
#         def set_key_data(ui_item):
#             """
#             将需要添加快捷键的UIItems 添加到对应的keymaps里面
#
#             """
#             key = ui_item.key
#             keymaps = key.get_use_keymaps_set()
#             for keymap in keymaps:
#                 if keymap not in data:
#                     data[keymap] = set()
#                 data[keymap].add(ui_item)
#
#         for ui in ui_items:
#             if ui.key.is_use_keymaps:
#                 set_key_data(ui)
#         return data
#
#     @classmethod
#     def _get_key_dict(cls) -> dict:
#         """# 初始化,先把应该有的内容填充一下
#                 for ui in ui_items:
#             if ui.key.is_use_keymaps:
#                 key_dict =
#                 data[ui.uuid] = key_dict
#                 获取初始时需要使用的快捷键字典
#         Returns:
#             dict: _description_
#         """
#         ui_items = bbpy.get.addon.prefs().custom_ui.ui_items
#         return {ui.uuid:
#                 {key: None for key in ui.key.get_use_keymaps_set()}
#                 for ui in ui_items
#                 if ui.key.is_use_keymaps}
#
#     def __get_kmi_data__(self=None, del_all_key=False) -> dict:
#         """记录每一个uuid的key和对应的keymaps 的kmi
#
#         删除快捷键也使用此函数
#
#         Args:
#             self (_type_, optional): _description_. Defaults to None.
#             del_all_key (bool, optional): 如果True则删除快捷键. Defaults to False.
#         Returns:
#             dict: {uuid:{keymaps_name:kmi,...}}
#         """
#         data = Data._get_key_dict()
#         idname = ExecuteOperator.bl_idname
#         keymaps = Data.configs_keymaps()
#
#         for keymap in keymaps:  # 先清理一遍
#             for kmi in keymap.keymap_items:
#                 if kmi.idname == idname:  # 是ui的操作符
#                     uuid = kmi.properties.uuid
#                     is_add = len(uuid) and (uuid in data)
#                     if is_add and (not del_all_key):  # 如果有并且id在ui数据里面 uuid则记录
#                         data[uuid][keymap.name] = kmi
#                     else:  # 没有uuid或是uuid没有在表里面 就把这一个快捷键删掉
#                         print(
#                             f'{addon_name} {keymap.name}.keymap_items.remove({kmi})')
#                         keymap.keymap_items.remove(kmi)
#         return data
#
#     kmi_data = property(__get_kmi_data__)
#
#     # tmp kmi 用于临时显示名称
#     _tmp_kmi_data = None
#
#     @classmethod
#     def generate_tmp_kmi(cls) -> None:
#         """生成临时kmi项,作为显示设置快捷键和设置参数用
#         """
#         keymaps = Data.configs_keymaps()
#         maps = 'Window'
#
#         ui_item = cls.act_ui_item.fget(None)
#         ui = cls.act_ui_element.fget(None)
#
#         if ui_item:
#             ui_item.update_active_index(bpy.context)
#
#         bl_idname = ui.operator if ui and ui.operator else ''
#
#         keymap = keymaps.get(
#             maps, keymaps.from_other_keymaps_new('default', maps, 'addon'))
#         kmi = keymap.keymap_items.new(bl_idname, 'NONE', 'PRESS')
#         cls._tmp_kmi_data = kmi
#
#     def __get_tmp_kmi_data(self=None) -> 'bpy.types.KeyMapItem':
#         """获取临时kmi项,用于显示operator的操作符设置
#         生成一个或者拿一个新的
#
#         Args:
#             self (_type_, optional): _description_. Defaults to None.
#
#         Returns:
#             bpy.types.KeyMapItem: _description_
#         """
#         if Data._tmp_kmi_data is None:
#             Data.generate_tmp_kmi()
#         return Data._tmp_kmi_data
#     tmp_kmi = property(__get_tmp_kmi_data, doc='获取临时kmi项,用于显示operator的操作符设置')
#
#     @classmethod
#     def _select_structure(cls, ui: 'UIElementItem', select_structure: list[bool], items: list) -> bool:
#         """测试选择结构
#
#         Args:
#             ui (UIElementItem): _description_
#             select_structure (list[bool]): 记录上一次选择结构是啥
#             items (list): _description_
#
#         Returns:
#             bool: 反回选择结构是否为True的布尔值
#         """
#         typ = ui.type
#         sel = select_structure
#         poll = ui.poll_bool
#
#         is_if = (typ == 'if')
#         is_elif = (typ == 'elif')
#         is_else = (typ == 'else')
#
#         se = sel[0]
#
#         is_false = (se == False)
#         select_error = se in (None, 'ELSE')
#
#         if is_if:
#             sel[0] = poll
#             if sel[0]:
#                 # 如果True
#                 items.extend(ui.childs)
#         elif is_elif:
#             if is_false and poll:
#                 sel[0] = poll
#                 items.extend(ui.childs)
#             elif select_error:
#                 # 前面没有设置值,也就是只有elif这个
#                 ui.is_available = False
#             else:
#                 return False
#         elif is_else:
#             if is_false:
#                 sel[0] = 'ELSE'
#                 items.extend(ui.childs)
#             elif select_error:
#                 # 前面没有设置值,也就是只有else这个
#                 ui.is_available = False
#             else:
#                 return False
#         else:
#             return False
#         return poll
#
#     @classmethod
#     # FROZEN
#     def __get_element_items__(cls, iteration: list['UIElementItem']) -> list:
#         """获取元素项
#
#         Args:
#             iteration ('iter'['UIElementItem']): 可迭代元素项
#
#         Returns:
#             list: _description_
#         """
#         items = []
#         select_structure = [None, ]  # if elif else   None表示之前没有选择结构
#
#         for it in iteration:
#             if it.is_select_structure:
#                 if it.is_enabled:
#                     result = cls._select_structure(it, select_structure, items)
#                     if result != it.poll_bool_result:
#                         it.poll_bool_result = result
#             else:
#                 if select_structure[0] != None:
#                     # uilayout项重置
#                     select_structure[0] = None
#                 items.append(it)
#
#         return items
#
#     # get data
#     @property
#     def _child_data(self) -> list:
#         """反回子元素的数据
#         Returns:
#             list: _description_
#         """
#         data = []
#         parent_item = self._get_parent_ui_item()
#
#         if 'childs' not in self:
#             self['childs'] = []
#
#         for i in self['childs']:
#             da = parent_item.ui.get(i).self_data
#             data.append(da)
#         return data
#
#     @property
#     def self_data(self) -> dict:
#         """反回self的数据
#         如果self内被更改了并且是blender数据的话将会添加到反回的数据内
#         用于导出和复制项
#
#         Returns:
#             dict: _description_
#         """
#         data = {}
#         for i in dir(self):
#             pro = getattr(self, i)
#
#             is_prop = i in self.bl_rna.properties
#             exclude = i not in (  # 不读uuid和name
#                 '__doc__',
#                 '__module__',
#
#                 'uuid',
#                 'name',
#                 'parent_uuid',
#                 'parent_ui_item_uuid',
#                 'is_update',
#
#                 'active_ui_index',
#                 'poll_bool_result',
#
#                 'is_user_modifier',
#                 'is_select',
#                 'is_extend',
#                 'level',
#
#                 'element_type',
#
#                 'key_combination',
#             )
#
#             is_data = isinstance(pro, (int, float, str, bool)
#                                  ) and exclude and is_prop
#             is_chang = is_data and self.is_property_set(i)
#             if is_chang:
#                 data[i] = pro
#
#         if isinstance(self, UIElementItem):
#             if 'childs' not in data:
#                 data['childs'] = []
#             data['childs'].extend(self._child_data)
#         return data
#
#     def _move_collection_index(self, prop_items_len: int, index: int, next_: bool) -> int:
#         """反回需要移动到的索引
#         用于移动blender 集合
#         此函数只能用于非边界移动
#
#         Args:
#             prop_items_len (int): 集合的总长度
#             index (int): 当前需要移动的长度
#             next_ (bool): _description_
#
#         Returns:
#             int: 需要移动到的索引
#         """
#         if next_:
#             if prop_items_len - 1 <= index:
#                 return 0
#             else:
#                 return index+1
#         else:
#             if 0 >= index:
#                 return prop_items_len-1
#             else:
#                 return index-1
#
#     def __move_collection__(self, col: 'bpy.props.CollectionProperty', uuid: str, down: bool):
#         """用于移动集合的元素
#
#         Args:
#             col (bpy.props.CollectionProperty): _description_
#             uuid (str): _description_
#             down (bool): _description_
#         """
#
#         prop_len = len(col)
#         index = col.keys().index(uuid)
#         if (index != None) and col:
#             move_index = self._move_collection_index(prop_len, index, down)
#             col.move(index, move_index)
#
#     @property
#     def is_ui_element(self) -> bool:
#         return isinstance(self, UIElementItem)
#
#
# class Child(PropertyGroup):
#
#     """子级类,用于设置元素的子级或父级项
#     这个用来存所有的子元素id
#     只需要name就行了
#     TODO 不重要,后续直接写进self里面
#
#     Args:
#         PropertyGroup (_type_): _description_
#     """
#     is_update: BoolProperty()
#
#     def update_uuid(self, context):
#         if self.is_update:
#             return
#         self.name = self.uuid
#
#     uuid: StringProperty(update=update_uuid)
#
#
# class ElementDraw:
#     """绘制uiElement项
#     所有绘制方法都写在此类里面
#
#     Returns:
#         _type_: _description_
#     """
#
#     is_popup_gestures = False  # 是弹出手势,子手势弹出
#
#     def _draw_edit_add_item(self, after=True) -> None:
#         """绘制编辑添加项
#         在预览时显示的添加到前面或后面的按钮由此函数绘制
#
#         Args:
#             after (bool, optional): _description_. Defaults to True.
#         """
#         is_layout = isinstance(self.layout, bpy.types.UILayout)
#         if self.is_edit_add_item and is_layout:
#             op = self.layout.operator(ElementChange.ElementAdd.bl_idname,
#                                       text=f'添加新项到 "{self.ui_element_name}" {"前" if after else "后"}面',
#                                       icon='ADD',
#                                       )
#             op.is_prepend = after
#             op.uuid = self.uuid
#
#     def _parameter(func):
#         """装饰器,用来在绘制前和绘制后注入参数和设置高级属性
#         设置高级参数
#         在之前还是之后设置
#         Args:
#             func (_type_): _description_
#
#         Returns:
#             _type_: _description_
#         """
#         @wraps(func)
#         def decorated(*args, **kwargs):
#             self = args[0]
#             self._draw_edit_add_item(True)
#             ret = func(*args, **kwargs)
#             self._draw_edit_add_item(False)
#             self.set_advanced_parameter(ret)
#             return ret
#         return decorated
#     # draw
#
#     def _set_layout_alert(self) -> None:
#         """设置活动layout的alert
#         显示红色
#         """
#         alert = (self.select or self.is_select or (
#             not self.is_available)) and self.is_preview_show_red
#
#         if alert:
#             self.layout.alert = True
#         elif self.layout.alert:
#             self.layout.alert = False
#
#     # @bbpy.debug.time
#     def draw(self,
#              parent_ui_item: 'UIItem',
#              layout: bpy.types.UILayout,
#              preview: bool = False,
#              direct_draw: bool = False,
#              is_select: bool = False,
#              is_gestures_draw: bool = False,
#              is_draw_child: bool = True,
#              debug=False,
#              ) -> None:
#         """
#         自动生成绘制方法
#         预览模式和直接绘制方法
#         绘制当前项和子项
#
#         三种绘制模式():
#             预览(在前面和后面显示添加项按钮)
#             不预览(直接绘应绘制的项)
#             绘制手势项(按子项)
#
#         Args:
#             parent_ui_item (UIItem): 用于UIElement的父子级查找及
#             layout (bpy.types.UILayout): 绘制Layout
#             preview (bool): 预览绘制
#             direct_draw (bool, optional): 直接绘制方法，比如pie_menu将会直接按原方法获取,如果在预览模式需要将这个方法设置成box方便预览. Defaults to False.
#             is_select (bool, optional): 用来绘制红色以提示是有被选中的. Defaults to False.
#             is_gestures_draw (bool, optional): 是使用手势绘制的,为True时将按手势项来绘制UILayout. Defaults to False.
#             is_draw_child (bool,optional): 是绘制子级的,默认需要绘制子级,用于在手势操作时子级作为子级的饼菜单,而不是作为绘制项直接绘制. Defaults to True.
#
#             # print(f'draw {layout} {self.uuid} {self.type}')
#                 # print(f'draw childs {self.uuid} {self.childs}')
#         """
#
#         self.origin_layout = self.layout = layout
#
#         self.preview = preview
#         self.direct_draw = direct_draw
#         self.draw_type = self.type.lower()
#         self.parent_ui_item = parent_ui_item
#         self.is_gestures_draw = is_gestures_draw
#         self.select = is_select
#         self.is_draw_child = is_draw_child  # 是绘制子级
#         self.debug = debug
#         self._set_layout_alert()
#
#         if self.is_enabled:
#             lay = self._draw()  # 绘制项并反回绘制后的UILayout
#             if self.childs and self.is_draw_child and lay:
#                 for kids in self.childs:
#                     kids.draw(parent_ui_item,
#                               lay,
#                               preview,
#                               direct_draw,
#                               self.layout.alert,
#                               self.is_gestures_draw,
#                               self.is_draw_child,
#                               debug=self.debug,
#                               )
#
#     @_parameter
#     def _draw(self) -> None:
#         """实际绘制项
#         绘制时区分预览,编辑及直接绘制
#         预览需要将一些不能显示出来的参数xxx
#         直接绘制是在直接使用时开启,将会直接绘制设置的数据
#         编辑需要显示活动项(红色)
#         仅显示活动项布尔操作
#         """
#
#         try:
#             ret = self.draw_func(**self.kwargs)
#             typ = self.draw_type
#             is_operator = ret and (typ == 'operator')
#             is_menu_pie = ret and (typ == 'menu_pie')
#             is_popup_gestures = ret and (typ == 'popup_gestures')
#             text = f'''draw uuid:{self.uuid}
#             kwargs:{self.kwargs}
#             typ:{typ}
#             is_operator:{is_operator}
#             is_menu_pie:{is_menu_pie}
#             is_popup_gestures:{is_popup_gestures}
#             layout：{self.layout}'''
#
#             bbpy.debug.debug_print(text, self.debug)
#
#             if is_operator:
#                 self.set_operator_property_to(ret)
#             elif is_menu_pie:
#                 # 用column再绘制一次
#                 style = 'box' if self.is_use_box_style_pie or self.child_as_gestures_item else 'column'
#                 self.draw_type = style
#                 self.layout = ret
#                 ret = self._draw()
#             elif is_popup_gestures:
#
#                 ret.uuid = self.parent_ui_item.uuid
#                 ret.direct_draw = True
#                 ret.is_gestures_popup = True
#                 ret.child_gestures_uuid = self.uuid
#
#             if not self.is_available:
#                 # 如果绘制没问题并且不可用时 设置为可用
#                 self.is_available = True
#             return ret
#
#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             text = f'draw_type:{self.draw_type}\tfunc:{self.draw_func}\tkwargs:{self.kwargs}'
#             print(text)
#             self.draw_error_item(e)
#
#     def draw_error_item(self, args: str) -> None:
#         """绘制错误项
#         long_label(
#             self.layout, f'ERROR:  {self.type} '+str(args), 80, 'column')
#         traceback.print_exc()
#
#         Args:
#             args (str): 错误信息
#
#         """
#         column = self.layout.column()
#         column.alert = True
#
#         if self.is_available:
#             self.is_available = False
#         op = column.operator(PopupMenu.bl_idname,
#                              icon='ERROR', text=self.type+" Error")
#         op.popup_type = 'invoke_props_dialog'
#         print('draw_error_item', args)
#
#     def set_advanced_parameter(self, layout: 'UILayout') -> None:
#         """设置uilayout高级参数
#         如果使用高级参数的话就输入一些其它可调整UIlayout
#
#         Args:
#             layout (UILayout): layout
#         """
#         uilayout = UI_LAYOUT_INCOMING_ITEMS['uilayout']  # 参数项
#         is_available = isinstance(layout, bpy.types.UILayout)
#         if self.is_use_advanced_parameter and self.is_draw_type(self.draw_type) and is_available:
#             for item in uilayout:
#                 # 如果项是 emboss_enum转成 emboss　因为有两个emboss属性一个是布尔一个是enum作为区分
#                 item = 'emboss' if item == 'emboss_enum' else item
#                 prop = getattr(self, item, None)
#                 if prop:
#                     setattr(layout, item, prop)
#
#     @property
#     def is_edit_add_item(self) -> bool:
#         """反回是编辑添加项的布尔值
#
#         Returns:
#             bool: _description_
#         """
#         return (not self.direct_draw) and \
#             (not self.preview) and \
#             self.is_allow_child_type and \
#             self.is_select
#
#     @property
#     def is_preview_show_red(self) -> bool:
#         """反回是预览显示红色的布尔值
#
#         Returns:
#             bool: _description_
#         """
#         return ((self.is_select or self.select) and (self.preview and (not self.direct_draw))) and self.prefs.is_red_show_active_item
#
#     # property
#
#     def __get_draw_func__(self) -> bpy.types.UILayout:
#         """反回当前项的绘制方法
#
#         通过self.preview 和self.direct_draw来判断需要反回什么
#         如果是预览需要添加一个添加项新项按钮
#         Returns:
#             bpy.types.UILayout: _description_
#         """
#         layout = self.layout
#         not_direct = not self.direct_draw
#         typ = self.draw_type
#
#         is_menu_pie = (typ == 'menu_pie')
#
#         if self.is_gestures_draw and self.child_as_gestures_item:  # 绘制手势项 如果绘制手势项的话
#             self.is_draw_child = False  # 是子级手势不绘制子级
#             self.draw_type = 'popup_gestures'
#             func = getattr(layout.menu_pie(), 'operator')
#
#         elif not_direct and is_menu_pie:
#             # 如果在预览模式就把menu_pie转成box 绘制在面板上
#             func = getattr(layout, 'column')
#             self.draw_type = 'column'
#
#         elif typ == 'menu' and self.menu_contents:
#             func = getattr(layout, 'menu_contents')
#             self.draw_type = 'menu_contents'
#         else:
#             func = getattr(layout, typ)
#
#         if self.draw_type == 'operator':
#             # 注入操作符上下文
#             layout.operator_context = self.operator_context
#         return func
#
#     draw_func = property(__get_draw_func__, doc='反回应绘制的方法')
#
#     def __get_menu_bl_idname__(self, prop) -> str:
#         """获取菜单idname
#
#         Args:
#             prop (_type_): _description_
#
#         Returns:
#             str: _description_
#         """
#         men = getattr(bpy.types, self.menu,
#                       f'menu {prop} not found')
#         idname = getattr(men, 'bl_idname', men.__name__)
#         return idname if men and men.is_registered and idname else 'UI_MT_CUSTOM_UI_ELEMENT'
#
#     def __get_icon(self, incoming_data):
#         """获取图标,单独获取
#         并设置仅图标的显示
#
#         Args:
#             incoming_data (_type_): _description_
#         """
#
#         available_icon = self.draw_type in (
#             'prop', 'label', 'operator', 'menu',)
#         icon = self.icon
#         custom_icon = self.custom_icon
#         if self.icon_only and available_icon:
#             incoming_data['text'] = ''
#         if icon != 'NONE':
#             incoming_data['icon'] = icon
#         elif custom_icon:
#             incoming_data['icon_value'] = get_icon(custom_icon)
#
#     def __get_incoming__(self, typ: str, item: str, incoming_data: dict):
#         """获取传入的参数
#
#         Args:
#             typ (str): _description_
#             item (str): _description_
#             incoming_data (dict): _description_
#         """
#         ite = getattr(self, item, None)
#         available_ite = ite and ite not in ('NONE', '')
#         available_item = item not in ('icon_only',)  # 'icon', 'icon_value',
#         if available_ite and available_item:
#             menu = (typ == item == 'menu')
#             prop = (typ == 'prop') and (item == 'property')
#             if menu:
#                 # menu 获取菜单
#                 incoming_data[item] = self.__get_menu_bl_idname__(prop)
#             elif prop:
#                 # 获取属性
#                 get_p = bbpy.get.property.from_path
#                 incoming_data['data'] = get_p(self.data)
#                 incoming_data['property'] = self.property_suffix
#             else:
#                 incoming_data[item] = ite
#
#     def __get_incoming_data__(self) -> dict:
#         """
#         通过预设字典获取需要传入的数据
#         根据每一种绘制方法需要传入的内容也不同
#         获取需要传入那些参数
#         operator = typ == item == 'operator'
#                         if operator:
#                             操作符 还有操作符的属性
#                             operator
#                             pass
#         """
#         typ = self.draw_type
#         incoming_data = {}
#
#         if typ == 'popup_gestures':
#             incoming_data['text'] = self.ui_element_name
#             icon = get_icon('Arrow_'+self.gestures_direction)
#             incoming_data['icon_value'] = icon
#             incoming_data['operator'] = 'ui.custom_ui_operator'
#             return incoming_data
#         else:
#             items = UI_LAYOUT_INCOMING_ITEMS[typ]
#             for item in items:
#                 self.__get_incoming__(typ, item, incoming_data)
#         self.__get_icon(incoming_data)
#         return incoming_data
#     kwargs = property(__get_incoming_data__)
#
#
# class ElementOperator:
#     """元素的操作符部分类,所有操作符相关内容都在此类里面
#     mesh.extrude_vertices_move
#     {'MESH_OT_extrude_verts_indiv': <bpy_struct, MESH_OT_extrude_verts_indiv at 0x0000022C002142C8>, 'TRANSFORM_OT_translate': <bpy_struct, TRANSFORM_OT_translate at 0x0000022C00216DE8>}
#     """
#
#     def _operator_update(self, context):
#         """操作符更新
#
#         Args:
#             context (_type_): _description_`
#         """
#         self.tmp_kmi.idname = self.operator
#
#         self._by_operator_set_name()
#         self.set_operator_property_to_tmp_kmi()
#
#     def get_operator_func(self) -> 'bpy.types.Operator':
#         """获取操作符的方法
#
#         Returns:
#             bpy.types.Operator: _description_
#         """
#         sp = self.operator.split('.')
#         if len(sp) == 2:
#             prefix, suffix = sp
#             func = getattr(getattr(bpy.ops, prefix), suffix)
#             return func
#
#     def running_operator(self) -> None:
#         """运行此self的操作符
#         """
#         try:
#             prop = ast.literal_eval(self.operator_property)
#             func = self.get_operator_func()
#             if func:
#                 func(self.operator_context, True, **prop)
#                 print(Fore.BLUE +
#                       f'running_operator Element:{self}\t{self.operator}({self.operator_property[1:-1]})\t{func}\n',
#                       self.operator_property, self.operator_context,
#                       Fore.RESET)
#
#         except Exception as e:
#             print(self.uuid, 'running_operator ERROR', e)
#
#     def _get_operator_property(self, string: str) -> dict:
#         """将输入的字符串操作符属性转成字典
#         用于传入操作符执行操作符用
#
#         Args:
#             string (str): _description_
#
#         Returns:
#             dict: _description_
#         """
#         tmp_index = 0
#         brackets_index = 0
#         property_dict = {}
#         for index, value in enumerate(string):
#
#             is_zero = (brackets_index == 0)
#             if brackets_index < 0:
#                 print(Exception('输入数据错误,无法解析', string))
#             elif value == '(':
#                 brackets_index += 1
#             elif value == ')':
#                 brackets_index -= 1
#             elif is_zero and value == ',':
#                 data = string[tmp_index:index]
#                 print(data)
#                 sp = data.split('=')
#                 if len(sp) == 2:
#                     property_dict[sp[0]] = ast.literal_eval(sp[1])
#             elif is_zero and value == ' ':
#                 tmp_index = index + 1
#             else:
#                 ...
#
#         return property_dict
#
#     def _set_operator(self, value: str) -> None:
#         """规范设置操作符  bpy.ops.mesh.primitive_plane_add() >> mesh.primitive_plane_add
#         掐头去尾
#         bpy.ops.mesh.select_mode(type='VERT')
#         bpy.ops.wm.tool_set_by_id(name="builtin.measure")
#          p  = r'*(*)'
#         prop  =={value:(0.968404, 0.885423, 1.85632), orient_axis_ortho:'X', orient_type:'GLOBAL', orient_matrix:((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type:'GLOBAL', mirror:False, use_proportional_edit:False, proportional_edit_falloff:'SMOOTH', proportional_si
#
#         bpy.ops.transform.translate()
#         value=(-3.41112, 1.25897, 0.817271), orient_axis_ortho='X', orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False
#
#
#         Args:
#             value (str): _description_
#         """
#
#         self['operator'] = value
#
#         if value[:8] == 'bpy.ops.':
#             self['operator'] = value = value[8:]
#         if ('(' in value) and (')' in value):
#             suffix = value[-2:]
#             if suffix == '()':
#                 self['operator'] = value[:-2]
#             else:
#                 self['operator'] = value[:value.index('(')]
#                 r = re.search(r'[(].*[)]', value)  # 操作符参数
#                 prop_dict = ast.literal_eval(self.operator_property)
#                 prop_dict.update(self._get_operator_property(r.group()[1:-1]))
#                 self.operator_property = str(prop_dict)
#                 self._by_operator_set_name()
#
#     def _get_operator_string(self) -> str:
#         """获取操作符的字符串
#
#         Returns:
#             str: _description_
#         """
#         if 'operator' not in self:
#             return 'mesh.primitive_monkey_add'
#         return self['operator']
#
#     def get_tmp_kmi_operator_property(self) -> str:
#         """获取临时kmi操作符的属性
#
#         Returns:
#             str: _description_
#         """
#         properties = self.tmp_kmi.properties
#         prop_keys = dict(properties.items()).keys()
#         dictionary = {i: getattr(properties, i, None) for i in prop_keys}
#         for item in dictionary:
#             prop = getattr(properties, item, None)
#             typ = type(prop)
#             if prop and typ == Vector:
#                 # 属性阵列-浮点数组
#                 dictionary[item] = dictionary[item].to_tuple()
#             elif prop and typ == Euler:
#                 dictionary[item] = dictionary[item][:]
#             elif prop and typ == Matrix:
#                 dictionary[item] = tuple(i[:] for i in dictionary[item])
#         return str(dictionary)
#
#     def from_tmp_kmi_get_operator_property(self) -> None:
#         """从临时kmi里面获取操作符属性
#         """
#         self.operator_property = self.get_tmp_kmi_operator_property()
#
#     def __for_set_prop(self, prop, pro, pr):
#         for index, j in enumerate(pr):
#             try:
#                 getattr(prop, pro)[index] = j
#             except Exception:
#                 ...
#
#     def set_operator_property_to(self, properties: 'bpy.types.KeyMapItem.properties') -> None:
#         """注入operator property
#         在绘制项时需要使用此方法
#         set operator property
#         self.operator_property:
#
#         Args:
#             properties (bpy.types.KeyMapItem.properties): _description_
#         """
#         props = ast.literal_eval(self.operator_property)
#         for pro in props:
#             pr = props[pro]
#             if hasattr(properties, pro):
#                 if type(pr) == tuple:
#                     # 阵列参数
#                     self.__for_set_prop(properties, pro, pr)
#                 else:
#                     try:
#                         setattr(properties, pro, props[pro])
#                     except Exception:
#                         ...
#
#     def set_operator_property_to_tmp_kmi(self) -> None:
#         r'''
#         将ui.operator.property设置到tmp_kmi里面
#         '''
#         self.set_operator_property_to(self.tmp_kmi.properties)
#
#     operator: StringProperty(name='操作符',
#                              description='输入操作符,将会自动格式化 bpy.ops.screen.back_to_previous() >> mesh.primitive_monkey_add',
#                              set=_set_operator,
#                              get=_get_operator_string,
#                              update=_operator_update,
#                              )
#     operator_context: EnumProperty(name='操作符上下文',
#                                    **ui_operator_context)
#
#     operator_property: StringProperty(name='操作符属性', default=r'{}',)
#
#     class ApplyOperatorProperty(Data, bbpy.types.Operator):
#         bl_idname = 'ui.ui_element_apply_operator_property'
#         bl_label = '应用操作符属性'
#         bl_description = '将临时快捷键里面的属性设置到活动项的操作符属性中'
#
#         is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
#
#         def draw(self, context):
#             layout = self.layout
#             layout.operator_context = 'INVOKE_DEFAULT'
#             DrawCustomUiFunc.draw_element_item_props(self, layout)
#
#         def invoke(self, context, event):
#             if self.is_popup_menu:
#                 return context.window_manager.invoke_props_dialog(operator=self, width=500)
#             else:
#                 self.act_ui_element.from_tmp_kmi_get_operator_property()
#             return {'FINISHED'}
#
#
# class ElementUILayoutProperty:
#     """元素的UILayout属性
#     所有UILayout属性都放置在此类里面
#     UILayout.prop需要的数据
#     """
#
#     def set_property(self, value: str) -> None:
#         """设置属性
#
#         Args:
#             value (str): _description_
#         """
#         sp = value.split('.')
#         suf = sp[-1]
#
#         sul = len(suf)
#         if sul > 2:
#             self.data = value[:-(sul+1)]
#             self['property'] = value
#             self.property_suffix = value[-(sul):]
#             get_p = bbpy.get.property.from_path
#             self.is_available = bool(get_p(value))
#
#         self._by_prop_set_name()
#
#     def get_property(self,) -> str:
#         """获取属性
#
#         Returns:
#             str: _description_
#         """
#         if 'property' not in self:
#             return 'bpy.context.object.scale'
#
#         return self['property']
#
#     property: StringProperty(set=set_property,
#                              get=get_property,
#                              default='bpy.context.object.scale',
#                              )
#
#     data: StringProperty(default='bpy.context.object')
#     property_suffix: StringProperty(default='scale', name='属性后缀')
#
#
# class ElementIcon:
#     """图标
#     所有元素内的图标参数都放在这个类里面
#
#     Returns:
#         _type_: _description_
#     """
#     icon_only: BoolProperty(name='仅显示图标',
#                             description='''
#                             prop,
#                             operator,
#                             label,
#                             menu,
#                             icon_value,
#                             template_icon,🚩
#                             operator_menu_hold🚩
#                             ''')  # 只显示图标
#     custom_icon: StringProperty(name='自定义图标', default='')
#     icon: StringProperty(name='图标', default='NONE')
#
#     class SelectIcon(Data, bbpy.types.Operator):
#         r'''
#         选择自定义图标
#         '''
#         bl_idname = 'ui.ui_element_select_icon'
#         bl_label = '选择图标'
#
#         is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
#         icon: StringProperty()
#         search_str: StringProperty()
#         icons = []
#         max_num = 40
#
#         show_brush_icons: BoolProperty(name="Show Brush Icons",
#                                        description="Show brush icons",
#                                        default=True,
#                                        )
#
#         show_event_icons: BoolProperty(name="Show Event Icons",
#                                        description="Show event icons",
#                                        default=True,
#                                        )
#
#         show_colorset_icons: BoolProperty(name="Show Colorset Icons",
#                                           description="Show colorset icons",
#                                           default=True,
#
#                                           )
#         icon_value: BoolProperty()
#
#         def select_icon(self, context):
#             """设置图标的值
#
#             Args:
#                 context (_type_): _description_
#
#             Returns:
#                 _type_: _description_
#             """
#             ui = self.act_ui_element
#             if self.icon_value:
#                 ui.custom_icon = self.icon
#                 ui.property_unset('icon')
#             else:
#                 ui.icon = self.icon
#                 ui.property_unset('custom_icon')
#                 if self.icon not in self.icons:
#                     self.icons.append(self.icon)
#
#             self.tag_redraw()
#             return {'FINISHED'}
#
#         def _draw_custom(self, layout: bpy.types.UILayout):
#             """绘制自定图标部分
#
#             Args:
#                 layout (bpy.types.UILayout): _description_
#             """
#             from..ui import _icon
#             ro = layout.row()
#             ro.label(text=r'自定义图标(可将想要的图标添加到插件文件夹"rsc/icons")')
#             ro.prop(self.act_ui_element, 'icon_only')
#             row = layout.row(align=True)
#             index = 0
#             for name, pre in _icon.icon.items():
#                 index += 1
#                 if not(index % self.max_num):
#                     row = layout.row(align=True)
#
#                 op = row.operator(self.bl_idname,
#                                   icon_value=pre.icon_id,
#                                   text='')
#                 op.is_popup_menu = False
#                 op.icon = name
#                 op.icon_value = True
#
#         def _draw_icon(self, layout: bpy.types.UILayout, id):
#             """绘制单个内置图标
#
#             Args:
#                 layout (bpy.types.UILayout): _description_
#                 id (_type_): _description_
#             """
#             op = layout.operator(self.bl_idname, icon=id, text='')
#             op.is_popup_menu = False
#             op.icon = id
#             op.icon_value = False
#
#         def _draw_select_icons(self, box: 'bpy.types.UILayout', row: 'bpy.types.UILayout'):
#             """绘制所有已选择过的图标
#
#             Args:
#                 box (_type_): _description_
#                 row (_type_): _description_
#             """
#             index = 0
#             for i in self.icons:
#                 if not(index % self.max_num):
#                     index = 0
#                     row = box.row(align=True)
#                 index += 1
#                 self._draw_icon(row, i)
#
#         def _draw_search_icon(self, box, row):
#             """绘制所有内置图标并过滤
#
#             Args:
#                 box (_type_): _description_
#                 row (_type_): _description_
#             """
#             sel = len(self.search_str)
#             index = 0
#             for identifier, *_ in icon_enum['items']:
#                 is_brush = (
#                     'BRUSH_' == identifier[:6] and identifier != 'BRUSH_DATA')
#                 is_event = ('EVENT_' == identifier[:6])
#                 is_colorset = ('COLORSET_' == identifier[:9])
#                 not_tye = (not is_colorset and not is_brush and not is_event)
#
#                 not_is_none = (identifier != 'NONE')
#
#                 brush = is_brush and self.show_brush_icons
#                 event = is_event and self.show_event_icons
#                 colorset = is_colorset and self.show_colorset_icons
#                 search = (not sel) or self.search_str.lower(
#                 ) in identifier.lower()
#                 typ = (brush or event or colorset or not_tye)
#                 is_show = not_is_none and typ and search
#
#                 if not(index % self.max_num):
#                     index = 0
#                     row = box.row(align=True)
#
#                 if is_show:
#                     index += 1
#                     self._draw_icon(row, identifier)
#
#             if not index:
#                 box.label(text=f'未找到 {self.search_str}')
#
#         def _draw_icons(self, layout: bpy.types.UILayout):
#             """绘制图标的
#
#             Args:
#                 layout (bpy.types.UILayout): _description_
#             """
#             self._draw_custom(layout.box())
#             layout.separator()
#             box = layout.column(align=True)
#             # draw icon enums
#             row = box.row(align=True)
#
#             self._draw_select_icons(box, row)
#
#             box.separator()
#
#             self._draw_search_icon(box, row)
#
#         def draw(self, context):
#             """主绘制
#
#             Args:
#                 context (_type_): _description_
#             """
#             layout = self.layout
#             layout.operator_context = 'INVOKE_DEFAULT'
#             column = layout.column(align=True)
#             box = column.box()
#             sp = box.split(factor=0.2, align=True)
#             row = sp.row(align=True)
#             row.prop(self, 'show_brush_icons',
#                      icon_only=True, icon='BRUSH_DATA',)
#             row.prop(self, 'show_colorset_icons',
#                      icon_only=True, icon='GROUP_VCOL',)
#             row.prop(self, 'show_event_icons',
#                      icon_only=True, icon='EVENT_OS',)
#             sp.prop(self, 'search_str', icon_only=True, icon='BORDERMOVE')
#
#             column.separator()
#             self._draw_icons(column)
#
#         def invoke(self, context, event):
#             if self.is_popup_menu:
#                 return context.window_manager.invoke_props_dialog(operator=self, width=800)
#             else:
#                 return self.select_icon(context)
#
#
# class ElementMenu:
#     """所有元素的菜单数据和方法
#
#     Returns:
#         _type_: _description_
#     """
#
#     menu_contents: BoolProperty(name='直接显示菜单内容', description='但是此方法绘制出来的会有间隔')
#     menu: StringProperty(name='菜单', default='WM_MT_splash_about')
#
#     class SelectMenu(Data, bbpy.types.Operator):
#         bl_idname = 'ui.ui_element_select_menu'
#         bl_label = '选择菜单'
#
#         is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
#         menu: StringProperty()
#         search_str: StringProperty()
#
#         def select_menu(self, context):
#             """设置菜单值
#
#             Args:
#                 context (_type_): _description_
#
#             Returns:
#                 _type_: _description_
#             """
#             ui = self.act_ui_element
#             ui.menu = self.menu
#             self.tag_redraw()
#             return {'FINISHED'}
#
#         def draw(self, context):
#             bl_idname = self.bl_idname
#
#             layout = self.layout
#             layout.operator_context = 'INVOKE_DEFAULT'
#             sp = layout.split()
#
#             column = sp.column(align=True)
#             column.prop(self, 'search_str', icon_only=True, icon='BORDERMOVE')
#             for cls in bpy.types.Menu.__subclasses__():
#                 idname = getattr(cls, 'bl_idname', None)
#                 name = idname if idname else cls.__name__
#                 sel = len(self.search_str)
#                 in_text = self.search_str.lower() in name.lower()
#                 search = (sel and in_text) or not sel
#                 if cls.is_registered and search:
#                     op = column.operator(bl_idname, text=name)
#                     op.is_popup_menu = False
#                     op.menu = name
#
#             try:
#                 col = sp.column(align=True)
#                 col.label(text='preview:')
#                 col.menu(self.act_ui_element.menu)
#                 col.separator(factor=5)
#                 box = col.box()
#                 box.menu_contents(self.act_ui_element.menu)
#             except Exception as e:
#                 long_label(col, f'ERROR:'+str(e), 60, 'box')
#
#         def invoke(self, context, event):
#             if self.is_popup_menu:
#                 return context.window_manager.invoke_props_dialog(operator=self, width=600)
#             else:
#                 return self.select_menu(context)
#
#
# class ElementItemProperty(ElementOperator,
#                           ElementUILayoutProperty,
#                           ElementIcon,
#                           ElementMenu
#                           ):
#     """元素项属性总类
#     所有元素内使用的属性都在此类里面
#
#     Args:
#         ElementOperator (_type_): _description_
#         ElementUILayoutProperty (_type_): _description_
#         ElementIcon (_type_): _description_
#         ElementMenu (_type_): _description_
#     """
#     # string
#
#     # UILayout Property
#     default_float = {'min': 0,
#                      'soft_max': 20,
#                      'soft_min': 0.15,
#                      }
#     activate_init: BoolProperty()
#     active: BoolProperty()
#     scale_x: FloatProperty(**default_float)
#     scale_y: FloatProperty(**default_float)
#     ui_units_x: FloatProperty(**default_float)
#     ui_units_y: FloatProperty(**default_float)
#     active_default: BoolProperty()
#
#     alert: BoolProperty()
#     use_property_decorate: BoolProperty()
#     use_property_split: BoolProperty(name='使用属性拆分')
#
#     emboss_enum: EnumProperty(name='emboss enum',
#                               description='有两个emboss 这个用于UILayout的输入枚举项',
#                               **ui_emboss_enum,
#                               default='NORMAL')
#     enabled: BoolProperty(name='启用')
#
#     alignment: EnumProperty('对齐模式', **ui_alignment)
#     direction: EnumProperty(name='方向', **ui_direction)
#     # UILayout property
#
#     def _update_text(self, context):
#         self._by_text_set_name()
#     text: StringProperty(name='文字', default='text', update=_update_text)
#
#     # enum
#     ctext: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
#     text_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
#     heading_ctxt: EnumProperty(items=CTEXT_ENUM_ITEMS, name='翻译类型')
#
#     # int
#     columns: IntProperty()
#
#     row_major: IntProperty()
#
#     toggle: IntProperty(name='切换',
#                         max=1, min=-1, default=1)
#
#     # float
#
#     factor: FloatProperty(name='系数',
#                           min=0.01,
#                           max=100,
#                           soft_max=0.8,
#                           soft_min=0.1,
#                           step=0.01,
#                           default=0.5)
#
#     # bool
#     def _update_heading(self, context):
#         """更新标题文字
#         并自动更新元素名称
#
#         Args:
#             context (_type_): _description_
#         """
#
#         self._by_heading_set_name()
#     align: BoolProperty(name='对齐')
#     heading: StringProperty(name='标题', update=_update_heading)
#     translate: BoolProperty(name='翻译文字')
#     invert_checkbox: BoolProperty(name='反转复选框')
#     emboss: BoolProperty(name='浮雕')
#
#     expand: BoolProperty(name='扩展')
#
#     slider: BoolProperty()
#
#     depress: BoolProperty()
#
#     even_columns: BoolProperty()
#     even_rows: BoolProperty()
#
#
# class ElementParentChild(Data):
#     """元素的父子级关系设置类,
#     所有有关父子级关系的属性都在这里面了
#
#     Args:
#         Data (_type_): _description_
#
#     Returns:
#         _type_: _description_
#     """
#
#     @property
#     def is_cannot_act_as_child(self) -> bool:
#         """是允许作为子级的布尔值
#
#         Returns:
#             bool: _description_
#         """
#         return self.type in CANNOT_ACT_AS_CHILD
#
#     @property
#     def is_allow_child_type(self) -> bool:
#         r"""是允许有子级的布尔值
#         link ui\uilist.py 489
#         Returns:
#             bool: _description_
#         """
#
#         return self.type in ALLOW_CHILD_TYPE
#
#     def _get_parent_ui_item(self, parent: 'UIItem' = None) -> 'UIItem':
#         """反回ui项的父项,如果有设置父项uid直接使用
#         如果输入的是,则使用输入的
#         如果在绘制里面设置了的
#         否则只能使用活动项的
#
#         Args:
#             parent (UIItem, optional): _description_. Defaults to None.
#
#         Returns:
#             UIItem: _description_
#         """
#         pa_uid = self.parent_ui_item_uuid
#         act = getattr(self, 'parent_ui_item', None)
#         if pa_uid:
#             return self.prefs.ui_items.get(pa_uid)
#         elif parent:
#             return parent
#         elif act:
#             return act
#         else:
#             return self.act_ui_item
#
#     def gen_uuid(self, slice=7) -> None:
#         """生成uuid
#         保险避免真的有重复的uuid
#         Args:
#             slice (int, optional): _description_. Defaults to 7.
#
#         Returns:
#             _type_: _description_
#         """
#         uid = self.generate_uuid(slice=slice)
#
#         uuid_list = self.act_ui_item.ui.keys()
#
#         if uid in uuid_list:
#             return self.gen_uuid(slice=slice+1)
#         self['uuid'] = self.name = self.uuid = uid
#         if 'uuid' not in self:
#             return self.gen_uuid()
#
#         return uid
#
#     def __get_parent__(self, parent_ui_item: 'UIItem' = None) -> 'UIElementItem':
#         """获取父级element
#
#         Args:
#             parent_ui_item (UIItem, optional): _description_. Defaults to None.
#
#         Returns:
#             UIElementItem: _description_
#         """
#         ui = parent_ui_item if parent_ui_item else getattr(
#             self, 'parent_ui_item', None)
#         item = ui if ui else self.act_ui_item
#         return item.ui.get(self.parent_uuid, None)
#
#     @property
#     def parent(self) -> 'UIElementItem':
#         """反回父项UIElement 如果没有则反回None
#
#         Returns:
#             UIElementItem: _description_
#         """
#         return self.__get_parent__()
#
#     def __get_child__(self, parent_ui_item=None, all_items=True, select_structure=True) -> list['UIElementItem']:
#         """获取所有子级的element('UIElement')
#
#         Args:
#             parent_ui_item (_type_, optional): _description_. Defaults to None.
#             all_items (bool, optional): 获取所有的子级(包括子级的子级...). Defaults to True.
#             select_structure (bool, optional): 是否使用选择结构 如果使用的话则不会包含选择结构的项. Defaults to True.
#
#         Returns:
#             list: _description_
#         """
#         child_list = []
#
#         parent_item = self._get_parent_ui_item(parent_ui_item)
#         if 'childs' not in self:
#             return child_list
#
#         for item in self._childs:
#             ui = parent_item.ui.get(item)
#             if ui:
#                 ui_items = ui.__get_child__(
#                     parent_ui_item) if all_items else []  # 获取所有子级
#                 child_list += [ui, ] + ui_items
#         if select_structure:
#             return self.__get_element_items__(child_list)
#         return child_list
#
#     @property
#     def childs(self, parent_ui_item=None) -> list['UIElementItem']:
#         '''反回一级子项的列表["UIElement",...]'''
#         return self.__get_child__(parent_ui_item, all_items=False,)
#
#     all_childs = property(
#         __get_child__, doc='反回所有子项的列表,包括子级的子级 ["UIElement",...]')
#
#     childs_items = property(lambda self: self.__get_child__(None, False, False),
#                             doc='反回子项列表,不使用选择结构 ["UIElement",...]')
#
#     def remove_child(self, uuid: 'UIElementItem.uuid'):
#         """按uid删除子级
#
#         Args:
#             uuid (UIElementItem.uuid): _description_
#         """
#         childs = self._childs
#         childs.remove(uuid)
#         self['childs'] = childs
#
#     def from_parent_remove(self, parent_ui_item: 'UIElementItem'):
#         """从当前项的父级删除此项
#         只有在有父项时才能被父项删除子级
#
#         Args:
#             parent_ui_item (UIElementItem): _description_
#         """
#         parent = self.__get_parent__(parent_ui_item)
#         if parent:
#             parent.remove_child(self.uuid)
#
#     def update_uuid(self, context):
#         if self.is_update:
#             return
#         self.name = self.uuid
#
#     parent_uuid: StringProperty()
#     uuid: StringProperty(update=update_uuid)
#     parent_ui_item_uuid: StringProperty(name='父项ui_item 的uuid 用于快速找到父项')
#
#     def child_move_last_to_first(self) -> None:
#         '''移动最后一个到第一个'''
#         print(self, '\tchild_move_last_to_first')
#         childs = self._childs
#         self['childs'] = childs[-1:] + childs[:-1]
#
#     @property
#     def _childs(self) -> list['UIElementItem.uuid']:
#         """反回子级的uuid列表
#         只有第一层子级
#
#         Returns:
#             _type_: _description_
#         """
#         if ('childs' not in self) or (not self['childs']):
#             self['childs'] = []
#             return []
#         import idprop
#         if isinstance(self['childs'], list):
#             return self['childs']
#         elif isinstance(self['childs'], idprop.types.IDPropertyArray):
#             return self['childs'].to_list()
#
#     def add_child(self, uuid: 'UIElementItem.uuid', prepend=False) -> None:
#         """在此项的子级列表内添加此项
#
#         Args:
#             uuid (UIElementItem.uuid): _description_
#             prepend (bool, optional): 如果True则添加到前面. Defaults to False.
#         """
#         if uuid and isinstance(uuid, str):
#             data = [uuid] + self._childs if prepend else self._childs + [uuid]
#
#             self['childs'] = data
#
#     def move_child(self, uuid: 'UIElementItem.uuid', next_=True) -> None:
#         """移动子项
#         用于移动元素的位置
#
#         Args:
#             uuid (_type_): _description_
#             next_ (bool, optional): _description_. Defaults to True.
#         """
#         c_l = self._childs
#         c_len = len(c_l)
#         if c_len <= 1:
#             return
#         u_index = c_l.index(uuid)
#
#         move_index = self._move_collection_index(c_len, u_index, next_)
#         print('move_child\t', self.uuid, c_len,
#               c_l, uuid, next_, u_index, move_index)
#         childs = self['childs']
#
#         if (c_len == u_index+1) and next_:
#             childs = childs[-1:]+childs[:-1]
#         elif (u_index == 0) and (not next_):
#             childs = childs[1:] + childs[:1]
#         else:
#             childs[u_index], childs[move_index] = childs[move_index], childs[u_index]
#
#         print('test', childs)
#         self['childs'] = childs
#
#
# class ElementName(Data):
#     """元素的名称
#     UIlist显示的名称
#
#     Args:
#         Data (_type_): _description_
#     """
#
#     def set_name(self, value) -> None:  # DISCARD 元素名称可以重复出现
#         """
#         自动排序添加名称,不允许同名或为空字符串
#         会和PropertyGroup的名称冲突出现两个名称,并显get到的是PropertyGroup的名称
#         将name 改为uuid,因为无法监控更改事件,不使用name作为显示名称了,改成ui_name
#         """
#         if value == '' or (self['name'] == value):
#             return
#
#         names = self.act_ui_item.foreach_get_attribute('ui', 'ui_element_name')
#
#         prefix_nums = UUID_PREFIX_NUMS_LEN
#
#         if value in names:
#             string = value.split('.')[-1]
#             if string.isnumeric() and len(string) == prefix_nums:
#                 # 如果后三位就是数字则添加
#                 suf_int = str(int(value[-3:])+1)
#                 suffix = ''.join(
#                     ['0' for _ in range(prefix_nums - len(suf_int))])
#                 self.ui_name = value[:-prefix_nums] + suffix+suf_int
#             else:
#                 num = f".{''.join(['0' for _ in range(prefix_nums-1)])}1"
#                 self.ui_name = value + num
#         else:
#             self['name'] = value
#
#     def get_name(self) -> str:  # DISCARD 元素名称可以重复出现
#         """
#         获取ui_name的数据
#         """
#         return self['name']
#
#     ui_element_name: StringProperty(default='The is a name String',
#                                     )
#
#     def _set_name(self, value) -> None:
#         self.ui_element_name = value
#
#     def _by_text_set_name(self) -> None:
#         """更新text时设置名称
#         """
#         p = self.prefs
#         if p.text_sync_update:
#             self._set_name(self.text)
#
#     def _by_heading_set_name(self) -> None:
#         """更新标题时设置名称
#         """
#         p = self.prefs
#         if p.text_sync_update:
#             self._set_name(self.heading)
#
#     def _by_operator_set_name(self) -> None:
#         """更新操作符时更新名称
#         """
#         p = self.prefs
#         op = self.get_operator_func()
#         if op and p.text_sync_update:
#             name = op.get_rna_type().name
#             self.text = name
#             self._set_name(name)
#
#     def _by_prop_set_name(self) -> None:
#         get_p = bbpy.get.property.from_path
#         prop = get_p(self.data)
#         if prop:
#             pro = prop.bl_rna.properties.get(self.property_suffix)
#             if pro:
#                 name = pro.name
#                 self.text = name
#                 self._set_name(name)
#
#
# class UIElementItem(ElementDraw,
#                     ElementItemProperty,
#                     ElementName,
#                     ElementParentChild,
#
#                     PropertyGroup,
#                     PollProperty,
#                     Data
#                     ):
#     """元素项总类
#     确定一个主项
#     然后根据子项添加绘制方法
#     ('popover', 'popover', ''),
#     ('separator_spacer', 'separator_spacer', ''), ✅
#     ('menu_contents', 'menu_contents', ''), ✅
#     ('props_enum', 'props_enum', ''),
#     ('prop_menu_enum', 'prop_menu_enum', ''),
#     ('prop_with_popover', 'prop_with_popover', ''),
#     ('prop_with_menu', 'prop_with_menu', ''),
#     ('prop_tabs_enum', 'prop_tabs_enum', ''),
#     ('prop_enum', 'prop_enum', ''),
#     ('prop_search', 'prop_search', ''),
#     ('prop_decorator', 'prop_decorator', ''),
#     ('operator_menu_hold', 'operator_menu_hold', ''),
#     ('operator_enum', 'operator_enum', ''),
#     ('operator_menu_enum', 'operator_menu_enum', ''),
#     ('column_flow', 'Column Flow', ''),
#     ('grid_flow', 'Grid Flow', ''),
#     按alt 同时更改子元素展开属性
#     menu可以勾选展开子项
#
#
#     Args:
#         ElementDraw (_type_): _description_
#         ElementItemProperty (_type_): _description_
#         ElementName (_type_): _description_
#         ElementParentChild (_type_): _description_
#         PropertyGroup (_type_): _description_
#         PollProperty (_type_): _description_
#         Data (_type_): _description_
#
#     Returns:
#         _type_: _description_
#     """
#
#     # property
#     def _get_element_type(self, context) -> list[tuple[str]]:
#         """获取元素类型的枚举项
#
#         Args:
#             context (_type_): _description_
#
#         Returns:
#             list[tuple[str]]: _description_
#         """
#         if self.is_select_structure:
#             return UI_ELEMENT_SELECT_STRUCTURE_TYPE
#         else:
#             return UI_ELEMENT_TYPE_ENUM_ITEMS
#
#     def _set_element_type(self, typ) -> None:
#         """通过输入项设置element_type的类型
#
#         Args:
#             typ (_type_): _description_
#         """
#
#         is_uilayout = (typ not in SELECT_STRUCTURE)
#         self.element_type = 'uilayout' if is_uilayout else 'select_structure'
#
#     type: EnumProperty(items=_get_element_type,
#                        name='元素类型',
#                        description='类型,根据element_type的不同反回的枚举项也不同',
#                        )
#
#     element_type: EnumProperty(name='ui元素类型',
#                                description='''
#                                ''',
#                                items=[
#                                     ('uilayout',         'UiLayout元素',     '绘制元素'),
#                                     ('select_structure', '选择结构', '(if,elif,else)'),
#                                ],
#                                default='select_structure'
#                                )
#
#     is_uilayout = property(lambda self: self.element_type == 'uilayout',
#                            doc='反回元素类型是否为uilayout的布尔值')
#
#     is_select_structure = property(lambda self: self.element_type == 'select_structure',
#                                    doc='反回元素类型是否为选择结构的布尔值')
#
#     level: IntProperty(name='显示级数', description='用于显示项时缩进,仅在添加项时更新')
#     is_select: BoolProperty(name='是选中的')
#     is_update: BoolProperty(name='是更新中的')
#     is_enabled: BoolProperty(name='是启用的', default=True)
#     is_available: BoolProperty(name='是否可用',
#                                description='如果不可用则为True 此属性只为在UIlayout显示无效项,不作其它作用',
#                                default=True)
#
#     def update_extend(self, context) -> None:
#         """更新元素的展开属性
#
#
#         Args:
#             context (_type_): _description_
#         """
#         item = self.act_ui_item
#         if item.is_update:
#             return
#
#         item.is_update = True
#         ev = bbpy.context.event
#         is_child = ev.ctrl or ev.alt
#
#         if is_child:
#             for i in self.__get_child__(select_structure=False):
#                 i.is_extend = self.is_extend
#         elif ev.shift:
#             for i in self.act_ui_item.ui:
#                 i.is_extend = self.is_extend
#
#         self.refresh_uilist()
#
#         item.is_update = False
#
#     is_extend: BoolProperty(name='是展开的',
#                             default=True,
#                             update=update_extend,
#                             description='''按ctrl or alt 同步子级
#     按shift同步 所有项'''
#                             )
#
#     is_use_advanced_parameter: BoolProperty(name='启用高级属性',
#                                             description='开启后将显示并设置其它UILayout其它可调节参数',
#                                             default=False)
#
#     is_popup: BoolProperty(name='是弹出的',)
#     is_show_title: BoolProperty(name='是显示抬头的',
#                                 default=True)
#
#     gestures_direction: EnumProperty(items=[('1', '左', 'TRIA_LEFT'),
#                                             ('2', '右', 'TRIA_RIGHT'),
#                                             ('4', '上', 'TRIA_UP'),
#                                             ('3', '下', 'TRIA_DOWN'),
#                                             ('5', '左上', ''),
#                                             ('6', '右上', ''),
#                                             ('7', '左下', ''),
#                                             ('8', '右下', ''),
#                                             # 顶 和 底
#                                             ('9', '顶', 'TRIA_UP_BAR'),
#                                             ('10', '底', 'TRIA_DOWN'),
#                                             ('NONE', '无', ''),
#                                             ],
#                                      default='NONE',
#                                      name='手势朝向',
#                                      )
#
#     child_as_gestures_item: BoolProperty(name='子项作为手势项',
#                                          description='开启此项后子项可作为次级手势显示'
#                                          )
#
#     is_available_gestures_child = property(lambda self:
#                                            self.type not in ('label',
#                                                              'separator',
#                                                              'split',
#                                                              'prop',
#                                                              ),
#                                            doc='是可用手势子级项'
#                                            )
#
#     is_use_box_style_pie: BoolProperty(name='Pie菜单样式使用box')
#     # 选择结构
#
#
# class ItemsNeedDrawn:
#     """需要绘制的项
#     用于绘制时的定位主绘制项
#     TODO 后续将直接改成self的数据
#
#     """
#     items_need_drawn: CollectionProperty(
#         name='需要拿出来绘制的项', type=Child)
#
#     def remove_items_need_drawn(self, uuid):
#         """
#         从items_need_drawn中删除输入的uuid
#         """
#         items = self.items_need_drawn.keys()
#         print(f'\tremove {uuid}\t\tfrom items_need_drawn({items}) ')
#         if uuid in items:
#             index = items.index(uuid)
#             self.items_need_drawn.remove(index)
#
#     def add_items_need_drawn(self, uuid):
#         """
#         添加uuid到
#         items_need_drawn
#         """
#         if uuid in self.ui:
#             new = self.items_need_drawn.add()
#             new.name = new.uuid = uuid
#             print(f'add {uuid} to  items_need_drawn')
#
#     def move_items_need_drawn(self, uuid, down=True):
#         col = self.items_need_drawn
#         self.__move_collection__(col, uuid, down)
#
#
# class ElementChange(ItemsNeedDrawn):  #
#     """更改元素项的操作类
#
#     Args:
#         ItemsNeedDrawn (_type_): _description_
#
#     Returns:
#         _type_: _description_
#     """
#     ui: 'list[UIElementItem]'
#
#     @property
#     def select_ui_element_uuid(self) -> list['UIElementItem.uuid']:
#         """获取所有选择项元素的uuid
#
#         Returns:
#             list[str]: _description_
#         """
#         return [i.uuid for i in self.ui if i.is_select]
#
#     def element_index(self, uuid: 'UIElementItem.uuid') -> int:
#         """获取元素在集合中的索引值
#
#         Args:
#             uuid (UIElementItem.uuid): _description_
#
#         Returns:
#             int: _description_
#         """
#         return self.ui.find(uuid)
#
#     def refresh_ui_element_level(self) -> None:
#         """刷新所有ui元素的偏移等级
#         等级是用于显示父子级关系的错位等级
#         只有在UIList里面有使用
#
#         """
#
#         def set_level(ui) -> int:
#             if not len(ui.parent_uuid):
#                 level = 0
#             else:
#                 parent = self.ui.get(ui.parent_uuid)
#                 level = 1 + set_level(parent)
#             ui.level = level
#             return level
#
#         for ui in self.ui:
#             if ui:
#                 set_level(ui)
#
#     def __init_type(self, typ: 'UIItem.type'):
#         """初始化UI元素
#         如果没有输入数据的话会使用此函数
#         使用默认的输入项
#
#         Args:
#             typ (UIItem.type): _description_
#         """
#
#         BOX_UI_LAYOUT = {'type': 'box', 'ui_element_name': '大Box',
#                          'childs': [{'type': 'label', 'text': 'Label 1'}, {'type': 'label', 'text': 'Label 2'}]}
#
#         LABEL_LAYOUT = [{'type': 'label', 'text': 'label 1'},
#                         {'type': 'label', 'text': 'label 2'}]
#
#         PIE_DATA = [{'type': 'menu_pie', 'ui_element_name': i, 'childs': [
#             BOX_UI_LAYOUT, ]} for i in ('左', '右', '上', '下', '左上', '右上', '左下', '右下')]
#
#         UI_ELEMENT_PRESET = {'panel': [{'type': 'box'}, ],
#                              'menu': [{'type': 'row', 'childs': LABEL_LAYOUT}, ],
#                              'menu_pie': PIE_DATA,
#                              'layout': [{'type': 'column', }, ],
#                              }
#
#         self.__init_ui_element__(UI_ELEMENT_PRESET[typ])
#
#     def __init_ui_element__(self, data) -> None:
#         """        初始化ui_element
#         添加项
#         Pie Panel 默认添加6项PiePanel
#
#         如果输入的data是列表则使用列表内的参数初始化而不是使用默认的
#
#
#         Args:
#             data (list | &#39;UIItem.type): _description_
#         """
#         st = time()
#         self.is_update = True
#
#         if isinstance(data, list):
#             for da in data:
#                 self.add_element(
#                     da['type'], data=da,
#                     is_add_preset=True)
#         elif isinstance(data, str):
#             self.__init_type(data)
#
#         self.refresh_ui_element_level()
#         text = f'''__init_ui_element__ uuid:{self.uuid}  time{time() - st}
#         self:{self}
#         type:{self.type}
#         Preset:{data}
#         '''
#         print(text)
#
#     def __get_add_element_type(self, add_type: 'UIElementItem.type', parent_uuid: 'UIElementItem.uuid') -> str:
#         """获取添加元素的类型
#         只对选择结构进行更改
#         如果是添加预设则不进行更改
#
#         Args:
#             add_type (UIElementItem.type): _description_
#             parent_uuid (UIElementItem.uuid): _description_
#
#         Returns:
#             str: _description_
#         """
#         parent = self.ui.get(parent_uuid)
#         if self.is_add_preset:
#             return add_type
#         elif (add_type in SELECT_STRUCTURE) and parent:
#             childs = parent.childs_items
#             available_elif = childs and (childs[-1].type in ('if', 'elif'))
#             if (add_type == 'elif') and available_elif:
#                 # 前面的项是elif 或else
#                 return 'elif'
#             elif (add_type == 'else') and available_elif:
#                 return 'else'
#             return 'if'
#         return add_type
#
#     def __element_add_parent_set(self, add_type: 'UIElementItem.type', parent_uuid: 'UIElementItem.uuid') -> str:
#         """添加项父级设置
#         menu_pie 不允许有父级需要直接放在 ui_item.items_need_drawn   里面
#
#         只有部分内容可以添加子级(box,row,split,column,menu_pie)
#         如果活动项不允许有子级则会添加到无父级也就是根绘制那个里面
#
#         Args:
#             add_type (UIElementItem.type): _description_
#             parent_uuid (UIElementItem.uuid): _description_
#
#         Returns:
#             str: _description_
#         """
#         if self.is_add_preset:
#             return parent_uuid
#
#         parent = self.ui.get(parent_uuid, None)
#
#         cannot_child = (add_type in CANNOT_ACT_AS_CHILD)
#         allow_child = parent and parent.is_allow_child_type
#         # 父级是uilayout并且添加的是menu_pie,这样添加menu_pie就只能在选择结构或是第一层了
#         is_menu_pie = parent and (cannot_child and parent.is_uilayout)
#
#         if ((not allow_child) or is_menu_pie):
#             return ''
#         return parent_uuid
#
#     #   add
#
#     def add_element(self,
#                     add_type: 'UIElementItem.type' = 'row',
#                     parent_uuid: 'UIElementItem.uuid' = '',
#                     data={},
#                     refresh_level=True,
#                     is_prepend=False,
#                     is_add_preset=True,
#                     debug=False
#                     ) -> None:
#         """添加UIElement项
#         添加到同级并且活动项
#
#         Args:
#             add_type (str): 添加类型 可以是UIlayout类型,也可以是选择结构
#             parent_uuid (str, optional): 父级id 如果添加类型可以作为子级并且输入的父级也可以有子级,就会将添加项作为子级添加到输入的父级项. Defaults to ''.
#             data (dict, optional): 输入的其它数据,可以作为预设或是材质. Defaults to {}.
#             refresh_level (bool, optional): 是否刷新显示级数. Defaults to True.
#             is_prepend (bool, optional): 是添加到前面的,默认添加到后面的,如果添加到前面将会重新设置顺序. Defaults to False.
#         添加的项不能作为子级 tip
#         """
#         self.is_add_preset = is_add_preset
#         add_type = self.__get_add_element_type(add_type, parent_uuid)
#         parent = self.__element_add_parent_set(add_type, parent_uuid)
#
#         add = self.ui.add()
#         add.gen_uuid()
#         add._set_element_type(add_type)
#         add.type = add_type
#         add.parent_ui_item_uuid = self.uuid
#
#         add.ui_element_name = add_type.title()  # 先设置一下,如果后面有输入名称的话将会覆盖
#
#         if parent:
#             # 添加项并将uuid添加到父项
#             add.parent_uuid = parent
#             # print(parent, add.parent, '\t\t\tparent')
#             self.ui.get(parent).add_child(add.uuid)
#         else:
#             text = f'''add_element {add} parent:{parent, add.parent}\t
#             self:{self}
#             parent_uuid:{parent_uuid}
#             add_type:{add_type}
#             is_prepend:{is_prepend}
#             is_add_preset:{is_add_preset}
#             data:{data}
#             '''
#             debug_print(text, debug=True)
#             # 不需要添加到子级
#             need = self.items_need_drawn.add()
#             need.name = need.uuid = add.uuid
#         if data:
#             # 设置输入项
#             self.__set_add_element_data(data, add, add.uuid)
#
#         if not is_add_preset:
#             if refresh_level:
#                 self.refresh_ui_element_level()
#             if is_prepend and add.parent:
#                 add.parent.child_move_last_to_first()
#
#     def __set_add_element_data(self, data: list, add: 'UIElementItem', parent_uuid: 'UIElementItem.uuid', debug=False):
#         """设置添加元素的数据,通过输入的数据来填充
#
#         Args:
#             data (list): _description_
#             add (UIElementItem): _description_
#             parent_uuid (UIElementItem.uuid): _description_
#         """
#         text = '__set_add_element_data\t', add, add.element_type
#         debug_print(text, debug=debug)
#         for item in data:
#             text = f'\titem:{item}\tvalue:{data[item]}'
#             debug_print(text, debug=debug)
#
#             if item == 'childs':
#                 # 子级 当场新建
#                 tex = f'''set_childs\t{self}
#
#                 data:{data[item]}
#                 '''
#                 debug_print(tex, debug=debug)
#
#                 kids = data['childs']
#                 for ite in kids:
#                     # 子级为列表,可以存在多个嵌套
#                     text = f'''{add}.add_child
#                     uuid:{add.uuid, add.name}
#                     parent_uuid:{add.uuid}
#                     data:{ite}
#                     '''
#                     debug_print(text, debug=debug)
#
#                     self.add_element(ite['type'],
#                                      parent_uuid,
#                                      ite,
#                                      refresh_level=False,
#                                      is_add_preset=self.is_add_preset,
#                                      )
#             elif item in dir(add):
#                 setattr(add, item, data[item])
#
#     # del
#     def ui_element_remove_by_uuid(self, uuid: 'UIElementItem.uuid') -> None:
#         """按uuid删除ui元素
#
#         Args:
#             uuid (UIElementItem.uuid): _description_
#         """
#         if uuid in self.ui:
#             index = self.element_index(uuid)
#             self.ui.remove(index)
#
#     def ui_element_normal_del(self, element: 'UIElementItem') -> None:
#         """正常删除元素
#
#         Args:
#             element (UIElementItem): _description_
#         """
#         parent = element.parent
#         childs = element.__get_child__(all_items=False,
#                                        select_structure=False)
#         uid = element.uuid
#
#         if parent and len(childs):
#             text = f'''有父级有子级if parent and len(child)
#             parent:{parent}
#             _child:{parent._childs}
#             childs:{childs}
#             remove_uid:{uid}
#             '''
#             print(text)
#
#             parent.remove_child(uid)
#
#             for kid in childs:
#                 kid.parent_uuid = parent.uuid
#                 parent.add_child(kid.uuid)
#
#         elif (not parent) and childs:
#             print(
#                 f'只有子级没有父级\telif (not parent) and len(child) {parent} {childs}')
#             self.remove_items_need_drawn(uid)
#             for kid in childs:
#                 kid.parent_uuid = ''
#                 self.add_items_need_drawn(kid.name)
#         elif parent:
#             print(f'只有父级\telif parent {parent},', childs, uid)
#             parent.remove_child(uid)
#         else:
#             self.remove_items_need_drawn(uid)
#             print(parent, '\t\telse 没有父级没有子级')
#         self.ui_element_remove_by_uuid(uid)
#
#     def _element_del_all_childs(self, element: 'UIElementItem') -> None:
#         """删除所有的子级元素
#
#         Args:
#             element (UIElementItem): _description_
#         """
#         parent = element.parent
#         childs = element.__get_child__(all_items=True,
#                                        select_structure=False)
#         uid = element.uuid
#
#         all_uuid = [i.uuid for i in childs]
#         all_childs = [uid] + all_uuid
#
#         if parent:
#             parent.remove_child(uid)
#         else:
#             self.remove_items_need_drawn(uid)
#
#         print('all_childs', all_childs)
#         for chi in all_childs:
#             print(chi, all_childs)
#             self.ui_element_remove_by_uuid(chi)
#
#     def remove_element(self, uuid='', del_select=False, del_child=False, refresh_ui_level=True) -> None:
#         """删除元素
#
#         同时删除多个项 ,比如删除所有选中项?
#         删除项只有子级? 取消子级父级
#                 删除项有父级? 将父级的子级项删掉
#                 删除项子级父级都有? 将父级的子级项删掉并将被删掉项的子级移到这个父级上面
#                 也没子,直接放在第一层的,当场删掉就好了
#         """
#         element = self.ui.get(uuid, self.act_ui_element)
#
#         text = f'remove_element item_uuid:{self.uuid}\telement_uid:{element.uuid}\tdel_select:{del_select}\tdel_child:{del_child}'
#         print(Fore.RED + text + Fore.RESET)
#
#         if del_select:
#             item = self.select_ui_element_uuid
#             print('del_select', item)
#             for uid in item:
#                 self.remove_element(uid,
#                                     del_child=True,
#                                     refresh_ui_level=False)
#         elif del_child:
#             print('del_child', element)
#             self._element_del_all_childs(element)
#         else:
#             self.ui_element_normal_del(element)
#
#         if refresh_ui_level:
#             self.refresh_ui_element_level()
#
#     class ElementPoll:
#         """元素操作符的Poll属性
#
#
#         Returns:
#             _type_: _description_
#         """
#         bl_options = {'INTERNAL'}
#
#         @classmethod
#         def poll(cls, context):
#             Data.injection_attribute(cls)
#             del_lock = (cls.prefs.modifier_preset_data) or cls.act_ui_element
#
#             ui_item = cls.act_ui_item
#             return ui_item and len(ui_item.ui) and del_lock
#
#     class ElementAdd(Data, bbpy.types.Operator, ElementPoll):
#         bl_idname = 'ui.ui_element_add'
#         bl_label = '添加项'
#         bl_description = '''默认将会添加作为子级\n按住ctrl 添加在同级之下\n按住alt 添加到无父级'''
#
#         @classmethod
#         def poll(cls, context):
#             return True
#
#         element_add_data = {}
#
#         type: StringProperty(name='Layout类型', **SKIP_DEFAULT)
#         uuid: StringProperty(**SKIP_DEFAULT)
#         ui_element_uuid: StringProperty(**SKIP_DEFAULT)
#
#         is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
#         is_add_select_structure_type: BoolProperty(name='添加选择结构',
#                                                    default=False,
#                                                    **SKIP_DEFAULT)
#
#         add_type: EnumProperty(items=[('peer', '添加到同级', ''),
#                                       ('child', '添加到子级', ''),
#                                       ('no_parent', '无父级', ''),
#                                       ],
#                                default='child',
#                                **SKIP_DEFAULT
#                                )
#
#         is_peer = property(lambda self: self.add_type == 'peer')
#         is_child = property(lambda self: self.add_type == 'child')
#         is_no_parent = property(lambda self: self.add_type == 'no_parent')
#
#         is_prepend: BoolProperty(name='添加到前面',
#                                  description='默认为添加到后面,如果添加到前面需要改一下顺序',
#                                  **SKIP_DEFAULT,
#                                  )
#
#         enum_items = property(
#             lambda
#                 self: UI_ELEMENT_SELECT_STRUCTURE_TYPE if self.is_add_select_structure_type else UI_ELEMENT_TYPE_ENUM_ITEMS)
#
#         def get_add_item_parent(self) -> str:
#             """获取添加项的父级
#
#             Returns:
#                 str: _description_
#             """
#             ui = self.act_ui_element
#             if self.is_peer and ui:
#                 return ui.parent_uuid
#             elif self.is_child and ui:
#                 return ui.uuid
#             return ''
#
#         def add_item(self, context):
#             """添加项主函数
#
#             Args:
#                 context (_type_): _description_
#             """
#             parent_uuid = self.get_add_item_parent()
#             text = f'add_item parent_uuid:{parent_uuid} add_type:{self.add_type}, is_prepend:{self.is_prepend}'
#             print(text)
#
#             item = self.act_ui_item
#             item.add_element(self.type,
#                              parent_uuid,
#                              data=self.element_add_data,
#                              is_prepend=self.is_prepend,
#                              is_add_preset=False,
#                              )
#             self.tag_redraw()
#             self.refresh_uilist()
#             self.element_add_data.clear()
#
#         def draw_menu(self, menu, context):
#             """绘制添加项菜单枚举
#             可以添加选择元素或是UILayout
#
#
#             Args:
#                 menu (_type_): _description_
#                 context (_type_): _description_
#             """
#             layout = menu.layout
#             layout.operator_context = 'INVOKE_DEFAULT'
#
#             for identifier, text, *_ in self.enum_items:
#                 if identifier:
#                     op = layout.operator(self.bl_idname, text=text)
#                     op.type = identifier
#                     op.is_popup_menu = False  # 添加项
#                     op.add_type = self.add_type
#                     op.is_prepend = self.is_prepend
#                 else:
#                     layout.separator()
#
#         def invoke(self, context, event):
#             self.set_event_key(event)
#             if self.only_alt:
#                 self.add_type = 'no_parent'
#             elif self.only_ctrl:
#                 self.add_type = 'peer'
#
#             if self.is_popup_menu:
#                 context.window_manager.popup_menu(
#                     self.draw_menu, title='添加UILayout项', icon='ADD')
#             else:
#                 self.add_item(context)
#             return {'FINISHED'}
#
#     class ElementDel(Data, bbpy.types.Operator, ElementPoll):
#         r"""删除UI项
#         按下 ctrl 或 alt 删除当前项+子项
#         按下 shift 删除选中项+子项
#         """
#         bl_idname = 'ui.ui_element_del'
#         bl_label = '删除项'
#
#         uuid: StringProperty(**SKIP_DEFAULT)
#         ui_element_uuid: StringProperty(**SKIP_DEFAULT)
#
#         is_popup_menu: BoolProperty(default=False, **SKIP_DEFAULT)
#         is_del_childs: BoolProperty(default=False, **SKIP_DEFAULT)
#         is_del_select: BoolProperty(default=False, **SKIP_DEFAULT)
#
#         del_childs = property(lambda self: self.event.ctrl or self.event.alt,
#                               doc='是删除子级项')
#
#         del_select = property(lambda self: self.event.shift, doc='是删除所选项')
#
#         def del_item(self, context):
#             ui_item = self.act_ui_item
#             del_child = (self.is_del_childs or self.del_childs)
#             del_select = (self.is_del_select or self.del_select)
#
#             ui_item.remove_element(self.act_ui_element.uuid,
#                                    del_select=del_select,
#                                    del_child=del_child,
#                                    )
#             self.set_active_index(ui_item, 'ui', 'active_ui_index')
#             self.refresh_uilist()
#
#         def draw_menu(self, menu, context):
#             layout = menu.layout
#             op = layout.operator_menu_enum(self.bl_idname, 'type')
#             op.is_popup_menu = False
#
#         def invoke(self, context, event):
#             self.event = event
#             if self.is_popup_menu:
#                 context.window_manager.popup_menu(
#                     self.draw_menu, title='删除UILayout项', icon='ADD')
#             else:
#                 self.del_item(context)
#             return {'FINISHED'}
#
#     class ElementDuplicate(Data, bbpy.types.Operator, ElementPoll):
#         bl_idname = 'ui.ui_element_duplicate'
#         bl_label = '复制项'
#         bl_description = '''复制活动项
#         按ctrl 复制所有选择
#         '''
#
#         def _copy(self, item):
#             data = item.self_data
#             print(self.bl_idname, data)
#             self.act_ui_item.add_element(
#                 item.type, item.parent_uuid, data, is_add_preset=False)
#             self.refresh_uilist()
#
#         def invoke(self, context, event):
#             self.set_event_key(event)
#             if self.only_ctrl:
#                 for i in self.act_ui_item.ui:
#                     if i.is_select:
#                         self._copy(i)
#             else:
#                 act = self.act_ui_element
#                 self._copy(act)
#             return {'FINISHED'}
#
#     class ElementMove(Data, bbpy.types.Operator, ElementPoll):
#         bl_idname = 'ui.ui_element_move'
#         bl_label = '移动项'
#
#         is_moving = [False, '', []]  # 是在移动中的[bool,move_item]
#         move_to_uuid: StringProperty(name='移动到 -> uuid')
#         move_item_uuid: StringProperty()
#
#         exit_move: BoolProperty(**SKIP_DEFAULT, default=False)
#         type: EnumProperty(items=[('UP', '向上', ''),
#                                   ('DOWN', '向下', ''),
#                                   ('MOVE', '移动父子级关系', ''),
#                                   ],
#                            default='MOVE',
#                            **SKIP_DEFAULT,
#                            )
#
#         @property
#         def is_move(self) -> bool:
#             return self.type == 'MOVE'
#
#         @property
#         def is_up(self) -> bool:
#             return self.type == 'UP'
#
#         @property
#         def is_down(self) -> bool:
#             return self.type == 'DOWN'
#
#         @property
#         def move_uuid(self):
#             return self.is_moving[1]
#
#         def _move_item_to(self, move_to_uuid: 'UIElementItem.uuid'):
#             """移动项到指定的了父级
#
#             Args:
#                 move_to_uuid (UIElementItem.uuid): _description_
#             """
#             print('_move_item_to', move_to_uuid, self.move_uuid)
#             act = self.act_ui_item
#             move_to = act.ui.get(move_to_uuid)  # 移动到的项
#             item = act.ui.get(self.move_uuid)  # 被移动项
#             if item:
#                 parent = item.parent
#
#                 print(parent, move_to, move_to_uuid, item)
#
#                 if parent:
#                     item.parent_uuid = ''
#                     parent.remove_child(self.move_uuid)
#                 else:
#                     act.remove_items_need_drawn(self.move_uuid)
#
#                 if move_to:
#                     move_to.add_child(item.uuid)
#                 else:
#                     act.add_items_need_drawn(self.move_uuid)
#                 item.parent_uuid = move_to_uuid
#                 act.refresh_ui_element_level()
#
#         def _exit_move(self) -> None:
#             """退出自定义移动
#             """
#             self.is_moving[0] = False
#             self.is_moving[1] = ''
#             self.is_moving[2] = []
#
#         def parent_move(self) -> None:
#             """父级移动
#             """
#             if self.exit_move:
#                 self._exit_move()
#             elif not self.is_moving[0]:
#                 self.is_moving[0] = True
#                 self.is_moving[1] = self.move_item_uuid
#                 self.is_moving[2] = list(map(lambda a: a.uuid, self.act_ui_element.__get_child__(
#                     select_structure=False)))
#             else:
#                 self._move_item_to(self.move_to_uuid)
#                 self._exit_move()
#             print(list(self.is_moving[2]))
#
#         def up_down_move(self):
#             """上下移动
#             比较简单
#             """
#             act = self.act_ui_element
#             parent = act.parent
#             if parent:
#                 parent.move_child(act.uuid, self.is_down)
#             else:
#                 self.act_ui_item.move_items_need_drawn(act.uuid, self.is_down)
#
#         def execute(self, context):
#             if self.is_move:
#                 self.parent_move()
#             else:
#                 self.up_down_move()
#             self.refresh_uilist()
#             return {'FINISHED'}
#
#     @classmethod
#     def is_moving(cls):
#         return cls.ElementMove.is_moving[0]
#
#
# class ItemsChange:
#     """UIItems更改的所有内容
#
#
#     Returns:
#         _type_: _description_
#     """
#
#     # init and remove
#
#     # ui element property 存放默认添加ui的数据
#
#     def _from_data_load(self, data: dict = None):
#         """从输入的数据加载数据
#         如果没有输入则使用默认初始化
#
#
#         Args:
#             data (dict, optional): _description_. Defaults to None.
#         """
#         if data:
#             self.type = data['type']
#             for i in data:
#                 if i == 'key':
#                     self.key.__init__(data[i])
#                 elif i == 'ui':
#                     self.__init_ui_element__(data[i])
#                 elif i in self.bl_rna.properties:
#                     setattr(self, i, data[i])
#         else:
#             self.key.__init__(self.type)
#             self.__init_ui_element__(self.type)
#
#     def _init(self):
#         """面板初始化
#         不管输入的啥都会使用此函数
#         """
#         if self.is_update:
#             return
#
#         elif self.is_panel:
#             self._init_panel()
#
#     def __init__(self, data=None) -> None:
#         """插件内属性   {uuid:{'ui':UIItem,'key':{keymaps_name:kmi(bpy.types.KeyMapItem),....}}}
#         快捷键项每一个uuid的keymaps_name里面的快捷键应只有一个 {uuid:{}
#         启动时,删除时,添加时更新
#
#         Args:
#             data (None | dict, optional): _description_. Defaults to None.
#         """
#         st = time()
#         print(f'__init__ UIItem  start   {self} {self.uuid} {"_" * 5}')
#         self.gen_uuid()
#         self.ui_name = self.type.title()
#         self.is_update = True
#         self._from_data_load(data)
#         self.is_update = False
#         self._init()
#         text = f'{"==" * 5} init finished  uuid:{self.uuid} time:{time() - st}  {"==" * 5}\n'
#         print(text)
#
#     def _unreg(self) -> None:
#         """删除项前的设置
#         """
#         self.key.__del_key__()
#         self._unreg_panel()
#
#     def remove_item(self, uid: 'UIItem.uuid' = None) -> None:
#         """删除当前项
#         删除时只需要注销快捷键
#         将当前项和keys从ui_items里面删除就行了
#         通过uuid
#
#         Args:
#             uid (UIItem.uuid, optional): _description_. Defaults to None.
#         """
#         uuid = uid if uid else self.uuid
#         print(f'__del_item__ UIItem  start   {self} {uuid} {"__" * 10}')
#         items = self.prefs.ui_items
#         index = items.find(uuid)
#         text = f'{addon_name} remove_item() {self} index:{index} uuid:{uuid}'
#         print(text)
#         self._unreg()
#
#         text = f'{"==" * 5} remove finished  uuid:{uuid}{"==" * 5}\n'
#         items.remove(index)
#         print(text)
#
#     def remove_items(self, items_list: list['UIItem.uuid']):
#         """删除多个项
#
#         Args:
#             items_list (list[&#39;UIItem.uuid&#39;]): _description_
#         """
#         for i in items_list:
#             self.remove_item(i)
#
#     @property
#     def select_items(self) -> list['UIItem.uuid']:
#         """返回所选项的uid列表
#         删除时使用
#
#         Returns:
#             _type_: _description_
#         """
#         return [i.uuid
#                 for i in self.prefs.ui_items
#                 if i.is_select
#                 ]
#
#     class ItemPoll:
#         """Item操作符的Poll
#
#         Returns:
#             _type_: _description_
#         """
#         bl_options = {'INTERNAL'}
#
#         @classmethod
#         def poll(cls, context):
#             Data.injection_attribute(cls)
#
#             uil = len(cls.prefs.ui_items)
#             act = cls.prefs.active_index != -1
#
#             is_ok = uil and act and cls.act_ui_item
#             return is_ok
#
#     class Add(Data, bbpy.types.Operator):
#         bl_idname = 'ui.custom_ui_add'
#         bl_label = '添加项'
#
#         is_popup_menu: BoolProperty(name='弹出菜单',
#                                     description='''是否为弹出菜单,如果为True则弹出菜单,''',
#                                     default=True,
#                                     **SKIP_DEFAULT,
#                                     )
#         type: EnumProperty(items=CUSTOM_UI_TYPE_ITEMS)
#
#         @classmethod
#         def poll(cls, context):
#             return True
#
#         def draw_menu(self, menu, context):
#             layout = menu.layout
#             for identifier, name, _ in CUSTOM_UI_TYPE_ITEMS:
#                 op = layout.operator(self.bl_idname, text=name)
#                 op.type = identifier
#                 op.is_popup_menu = False
#
#         def add_item(self, context):
#             """
#             添加项
#             定义了默认项的属性
#             将一些操作都放到ui_items 的init_item 里面
#             """
#
#             item = self.prefs.ui_items.add()
#             item.type = self.type
#             item.__init__()
#             self.refresh_uilist()
#
#         def execute(self, context):
#             """
#             添加数据到 UI_DATA
#             添加快捷键
#             """
#             if self.is_popup_menu:
#                 context.window_manager.popup_menu(
#                     self.draw_menu, title='添加项')
#             else:
#                 self.add_item(context)
#             self.tag_redraw()
#             return {'FINISHED'}
#
#     class Del(Data, bbpy.types.Operator, ItemPoll):
#         bl_idname = 'ui.custom_ui_del'
#         bl_label = '删除项'
#         bl_description = '''删除项
#         '''
#
#         # 按 ctrl or shift or alt 将会删除所有选中项
#
#         def del_items(self, event):
#             self.set_event_key(event)
#             act = self.act_ui_item
#             act.remove_item()
#
#         def invoke(self, context, event):
#             """
#             从UI_DATA删除数据
#             删除快捷键
#             如果用户手动删掉了快捷键?:将会自动添加回来再删掉
#             添加删除确认? 暂不加
#             删除选中项
#             """
#             prop = bbpy.get.addon.prefs().custom_ui
#             self.set_active_index(prop, 'ui_items', 'active_index')
#             self.del_items(event)
#             self.refresh_uilist()
#
#             return {'FINISHED'}
#
#     class Move(Data, bbpy.types.Operator, ItemPoll):
#         bl_idname = 'ui.custom_ui_move'
#         bl_label = '移动项'
#
#         next: BoolProperty(name='向下移动', default=True)
#
#         def execute(self, context):
#             self.move_collection_element(
#                 self.prefs.ui_items, self.prefs, 'active_index', self.next)
#             self.refresh_uilist()
#             return {'FINISHED'}
#
#     class Duplicate(Data, bbpy.types.Operator, ItemPoll):
#         bl_idname = 'ui.custom_ui_duplicate'
#         bl_label = '复制项'
#
#         def execute(self, context):
#             add = self.prefs.ui_items.add()
#             add.__init__(self.act_ui_item.item_data)
#             add.refresh_ui_element_level()
#             self.refresh_uilist()
#             return {'FINISHED'}
#
#     @property
#     def key_data(self) -> dict:
#         """反回快捷键的数据
#
#         Returns:
#             dict: _description_
#         """
#
#         return {'key': self.key.self_data}
#
#     @property
#     def element_data(self) -> dict:
#         """反回元素的数据字典
#         包含子级信息
#
#         Returns:
#             dict: _description_
#         """
#
#         return {'ui': [self.ui.get(i.uuid).self_data for i in self.items_need_drawn]}
#
#     @property
#     def item_data(self) -> dict:
#         """反回项的所有数据,以字典的型式
#
#         Returns:
#             dict: _description_
#         """
#         data = {'key': {}, 'ui': {}}
#         data.update(self.self_data)
#         data.update(self.key_data)
#         data.update(self.element_data)
#         return data
#
