import bpy
from bpy.props import CollectionProperty, BoolProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences, Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .log import log
from .utils import PublicClass, PublicIndex
from ..ui.ui_list import DrawElement, DrawUIElement

from .gesture import ElementGroup
from .property import (
    PieProperty,
    pie_property_items,
    SKIP_DEFAULT,
    ADDON_NAME
)


class AddonOperator:
    class Add(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_add'
        bl_label = 'Add Element'

        def execute(self, context: bpy.types.Context):
            new = self.element_items.add()
            new.name = 'New Element'
            return {'FINISHED'}

    class Del(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_del'
        bl_label = 'Del Element'

        @classmethod
        def poll(cls, context):
            return len(cls.pref_().element_items)

        def execute(self, context: bpy.types.Context):
            try:
                self.active_element.remove()
            except Exception as e:
                log.info(e.args)
            return {'FINISHED'}

    class Copy(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_copy'
        bl_label = 'Copy Element'

        @classmethod
        def poll(cls, context):
            return GestureAddonPreferences.Del.poll(context)

        def execute(self, context: bpy.types.Context):
            self.active_element.copy()
            return {'FINISHED'}

    class Export(Operator, PublicClass, ExportHelper):
        bl_idname = 'gesture_helper.gesture_element_export'
        bl_label = 'Export Element'

        def execute(self, context: bpy.types.Context):
            self.active_element.json_export()
            return {'FINISHED'}

    class Import(Operator, PublicClass, ImportHelper):
        bl_idname = 'gesture_helper.gesture_element_import'
        bl_label = 'Import  Element'

        def execute(self, context: bpy.types.Context):
            self.active_element.json_import()
            return {'FINISHED'}

    class Move(Operator, PublicClass):
        bl_idname = 'gesture_helper.gesture_element_move'
        bl_label = 'Move Element'

        is_next: BoolProperty()

        def execute(self, context: bpy.types.Context):
            self.active_element.move(self.is_next)
            return {'FINISHED'}


class GestureAddonPreferences(AddonPreferences,
                              PublicIndex,
                              PieProperty,
                              PublicClass,
                              AddonOperator):
    bl_idname = ADDON_NAME

    gesture_element_collection_group: CollectionProperty(type=ElementGroup)
    is_debug: BoolProperty()

    @property
    def _items(self):
        return self.gesture_element_collection_group

    @property
    def _index_items(self):
        return self._items

    def register_key(self):
        ...

    def unregister_key(self):
        ...

    @classmethod
    def register(cls):
        ...
        # TODO　key
        # TODO ui

    @classmethod
    def unregister(cls):
        ...

    def draw(self, context):
        from ..ui.draw import DrawPreferences
        DrawPreferences(self.layout)

    def json_export(self, path):
        ...

    def json_import(self, path):
        ...


class_tuple = (
    GestureAddonPreferences,
    GestureAddonPreferences.Add,
    GestureAddonPreferences.Del,
    GestureAddonPreferences.Copy,
    GestureAddonPreferences.Export,
    GestureAddonPreferences.Import,
    GestureAddonPreferences.Move,
)

register_class, unregister_class = bpy.utils.register_classes_factory(class_tuple)


def register():
    register_class()
    GestureAddonPreferences.register()


def unregister():
    unregister_class()
    GestureAddonPreferences.unregister()

    # def update_active_index(self, context):n
    #     #
    #     # prop = bbpy.get.addon.prefs().custom_ui
    #     # event = bbpy.context.event
    #     # if event and (event.shift or event.ctrl):
    #     #     prop.ui_items_collection_group[self.active_index].is_select = prop.ui_items_collection_group[self.active_index].is_select ^ True
    #     # else:
    #     #     for i in prop.ui_items_collection_group:
    #     #         i.is_select = False
    #     #     prop.ui_items_collection_group[self.active_index].is_select = True
    #     ...
    #
    # def update_full_windows(self, context):
    #     """
    #     全屏不过只有主绘制是替换了的
    #     """
    #
    #     # def draw(self, context):
    #     #     DrawCustomUiFunc.draw(self, self.layout, context)
    #     #
    #     # bbpy.ui.menu_item_replace(bpy.types.USERPREF_PT_addons,
    #     #                           draw,
    #     #                           self.is_full_windows,
    #     #                           is_replace_draw_func=True
    #     #                           )
    #
    # def update_enable(self, context):
    #     """
    #     如果禁用的话    需要禁用所有快捷键,不做删除,以免太卡了
    #     """
    #     for ui in self.ui_items_collection_group:
    #         print(ui, 'update_enable')
    #
    #         if ui.key.is_use_keymaps:
    #             ui.update_enable(context) if self.is_enabled else ui.key.set_key_enable_state(
    #                 self.is_enabled)
    #         elif ui.is_panel:
    #             ui._refresh_panel() if self.is_enabled else ui._unreg_panel()
    #
    # # ui property
    # is_enabled: BoolProperty(name='是否启用', default=True, update=update_enable)
    # is_full_windows: BoolProperty(
    #     name='全窗口显示', default=False, update=update_full_windows)
    #
    # ui_items_collection_group: CollectionProperty(type=UIItem)
    # active_index: IntProperty(update=update_active_index)
    #
    # # ui element property
    # edit_ui_item: BoolProperty(default=False, name='编辑UI项')
    # edit_default_property: BoolProperty(default=False, name='编辑默认属性')
    # show_advanced_options: BoolProperty(default=False, name='显示高级选项')
    # show_ui_uuid_data: BoolProperty(default=False, name='显示uuid数据')
    # modifier_preset_data: BoolProperty(default=True, name='修改预设数据')
    # is_red_show_active_item: BoolProperty(default=True,
    #                                       name='高亮显示活动项(红色)',
    #                                       description='''
    #                                       怎么显示不可用项？比如不可用数据或操作 符啥的:红色显示,在绘制里面直接报错
    #                                       ''')  #
    # only_show_active_need_drawn: BoolProperty(name='仅显示活动主绘制项',
    #                                           default=False)
    #
    # # default data
    # default_add_poll_is_expression: BoolProperty(
    #     name='默认添加poll为表达式')  # TODO  默认添加poll为表达式
    # double_key_time: IntProperty(name='双键点击时长(触发方式)',
    #                              description='默认未设置时双键时长',
    #                              default=300,
    #                              subtype='TIME',
    #                              )
    # long_press_time: IntProperty(name='长按时长(触发方式)',
    #                              description='默认未设置时长按时长',
    #                              default=300,
    #                              subtype='TIME',
    #                              )
    # gestures_await_time: IntProperty(name='手势等待时长',
    #                                  description='手势操作在鼠标静止超过此时间后弹出饼菜单',
    #                                  default=150,
    #                                  subtype='TIME',
    #                                  )
    #
    # # pie menu draw property
    # text_sync_update: BoolProperty(name='更改数据时同步更改文字',
    #                                description='同步更改文本,如果开启将会自动更改文本'
    #                                            '在更改label的text'
    #                                            'row'
    #                                            '的heading'
    #                                            'column的heading'
    #                                            '    operator'
    #                                            '    的text'
    #                                            '    prop'
    #                                            '    menu'
    #                                            '    的text',
    #                                )
    #
    #
    # # interactive
    #
    # def draw(self, context, layout: bpy.types.UILayout, mode, text=None, icon=None, force_add=False, debug=False):
    #     layout.operator_context = 'INVOKE_DEFAULT'
    #     row = layout.row()
    #     row.alert = True
    #     row.emboss = 'NORMAL'
    #     data = {
    #         'text': text if text != None else mode,
    #     }
    #     if icon:
    #         data['icon'] = icon
    #
    #     op = row.operator(restore_ui.MenuAddOperator.bl_idname, **data)
    #     cl = self.__class__
    #     op.panel_name = getattr(cl, 'bl_idname', cl.__name__)
    #     op.force_add_draw_func = force_add
    #     op.mode = mode
    #     op.debug = debug
    #
    # def append(self, context):
    #     row = self.layout.row(align=True)
    #     CustomUI.draw(self, context, row, 'append')
    #
    # def prepend(self, context):
    #     """
    #     强制添加需要过滤一些无法重新注册的面板类,不然就会导致面板丢失
    #     """
    #
    #     row = self.layout.row(align=True)
    #     CustomUI.draw(self, context, row, 'prepend')
    #
    #     idname = getattr(self.__class__, 'bl_idname', self.__class__.__name__)
    #
    #     physics = ('PHYSICS' not in idname)
    #     particle = ('PARTICLE' not in idname)
    #     constraint = ('CONSTRAINT' not in idname)
    #     exclude = physics and particle and constraint
    #
    #     not_menu = self.__class__.bl_rna.base.name != 'Menu'
    #     if not_menu and exclude:
    #         CustomUI.draw(self, context, row, 'header_append',
    #                       text='',
    #                       icon='SHADERFX',
    #                       force_add=True,
    #                       debug=False,
    #                       )
    #
    # def header_prepend(self, context):
    #     CustomUI.draw(self, context, self.layout, 'header_prepend')
    #
    # def header_append(self, context):
    #     CustomUI.draw(self, context, self.layout, 'header_append')
    #
    # def header_preset_prepend(self, context):
    #     CustomUI.draw(self, context, self.layout, 'header_preset_prepend')
    #
    # def header_preset_append(self, context):
    #     CustomUI.draw(self, context, self.layout, 'header_preset_append')
    #
    # def interactive(self, context):
    #     from time import time
    #     st = time()
    #     exclude_class = ('PROPERTIES_PT_navigation_bar',
    #                      'USERPREF_PT_navigation_bar',
    #                      )
    #     class_items = [*bpy.types.Panel.__subclasses__(), *
    #     bpy.types.Menu.__subclasses__()]
    #
    #     for clas in class_items:
    #         name = getattr(clas, 'bl_idname', clas.__name__)
    #         pas = (name not in exclude_class)
    #
    #         if self.enable_interactive_mode and clas.is_registered and pas:
    #             clas.prepend(CustomUI.prepend)
    #             clas.append(CustomUI.append)
    #             clas.header_prepend(CustomUI.header_prepend)
    #             clas.header_append(CustomUI.header_append)
    #             clas.header_preset_prepend(CustomUI.header_preset_prepend)
    #             clas.header_preset_append(CustomUI.header_preset_append)
    #         elif clas.is_registered and pas:
    #             clas.remove(CustomUI.prepend)
    #             clas.remove(CustomUI.append)
    #             clas.header_remove(CustomUI.header_prepend)
    #             clas.header_remove(CustomUI.header_append)
    #             clas.header_preset_remove(CustomUI.header_preset_prepend)
    #             clas.header_preset_remove(CustomUI.header_preset_append)
    #
    #     print(
    #         f'custom_ui enable_interactive_mode  {bbpy.get.addon.name()}', time() - st)
    #
    # enable_interactive_mode: BoolProperty(name='启用交互模式',
    #                                       description='在每一个可添加项显示名称',
    #                                       default=False,
    #                                       **SKIP_DEFAULT,
    #                                       update=interactive
    #                                       )
    #
    # class File:
    #     """导入导出文件用的属性类
    #     """
    #     filename_ext = ".json"
    #     filter_glob: StringProperty(
    #         default="*.json",
    #         options={'HIDDEN'},
    #         maxlen=255,  # Max internal buffer length, longer would be clamped.
    #     )
    #
    #     filepath: StringProperty()
    #
    # class Import(bpy.types.Operator, Data, ImportHelper, File):
    #     bl_idname = 'ui.custom_ui_import_property'
    #     bl_label = f'''
    # {bpy.get.addon.name()}
    # 导入预设
    # '''
    #
    #     def import_data(self):
    #         if isinstance(self.data, list):
    #             for item in self.data:
    #                 print(type(item), item)
    #
    #                 if 'type' in item:
    #                     add = self.prefs.ui_items_collection_group.add()
    #                     add.type = item['type']
    #                     add.__init__(item)
    #
    #     def execute(self, context):
    #         import json
    #         try:
    #             with open(self.filepath, 'r', encoding='utf8') as f:
    #                 self.data = json.load(f)
    #             self.import_data()
    #         except Exception as e:
    #             import traceback
    #             print(f'ERROR {self.filepath} 写入属性错误')
    #             print(e)
    #             traceback.print_exc()
    #         self.refresh_uilist()
    #         return {'FINISHED'}
    #
    # class Export(bpy.types.Operator, Data, ExportHelper, File):
    #     bl_idname = 'ui.custom_ui_export_property'
    #     bl_label = f'''
    # {bbpy.get.addon.name()}
    # 导出预设
    # '''
    #
    #     is_popup_menu: BoolProperty(default=True, **SKIP_DEFAULT)
    #
    #     type_enum = [('ALL', '所有项', ''),
    #                  ('SELECT', '选择项', ''),
    #                  #   ('TAG','按标签导出',''),
    #                  ]
    #
    #     type: EnumProperty(items=type_enum)
    #
    #     @property
    #     def is_all(self):
    #         return self.type == 'ALL'
    #
    #     @property
    #     def is_select(self):
    #         return self.type == 'SELECT'
    #
    #     @property
    #     def data(self):
    #         import json
    #         data = []
    #         for i in self.prefs.ui_items_collection_group:
    #             if self.is_select:
    #                 if i.is_select:
    #                     data.append(i.item_data)
    #                 ...
    #             else:
    #                 data.append(i.item_data)
    #
    #         return json.dumps(data,
    #                           separators=(',', ': '),
    #                           indent=1,
    #                           ensure_ascii=True)
    #
    #     def draw_menu(self, menu, context):
    #         layout = menu.layout
    #         layout.operator_context = 'INVOKE_DEFAULT'
    #
    #         for ident, text, _ in self.type_enum:
    #             op = layout.operator(self.bl_idname, text=text)
    #             op.type = ident
    #             op.is_popup_menu = False
    #
    #     def export_data(self):
    #         f = open(self.filepath, 'w', encoding='utf-8')
    #         data = self.data
    #         f.write(data)
    #         f.close()
    #
    #         print('export_data\n', data)
    #
    #     def invoke(self, context, _event):
    #         if self.is_popup_menu:
    #             context.window_manager.popup_menu(
    #                 self.draw_menu, title='导出数据', icon='ADD')
    #             return {'FINISHED'}
    #         else:
    #             import os
    #             if not self.filepath:
    #                 blend_filepath = context.blend_data.filepath
    #                 if not blend_filepath:
    #                     blend_filepath = "untitled"
    #                 else:
    #                     blend_filepath = os.path.splitext(blend_filepath)[0]
    #
    #                 self.filepath = blend_filepath + self.filename_ext
    #             context.window_manager.fileselect_add(self)
    #             return {'RUNNING_MODAL'}
    #
    #     def execute(self, context):
    #         self.export_data()
    #         return {'FINISHED'}
    #
    # class Preset(bbpy.types.Operator, Data, ExportHelper, File):
    #     bl_idname = 'ui.custom_ui_import_preset'
    #     bl_label = f'''
    # {bbpy.get.addon.name()}
    # 导入预设
    # '''
    #
    #     @property
    #     def preset_path(self) -> str:
    #         return join(dirname(dirname(dirname(__file__))), r'rsc\preset\custom_ui')
    #
    #     @property
    #     def preset_items(self) -> list['str']:
    #         paths = walk(self.preset_path)
    #         items = next(paths)[2]
    #
    #         return [i
    #                 for i in items
    #                 if (len(i.split('.')) == 2) and (i.split('.')[1] == 'json')
    #                 ]
    #
    #     def draw_menu(self, menu, context):
    #         layout = menu.layout
    #         layout.operator_context = 'EXEC_DEFAULT'
    #
    #         for item in self.preset_items:
    #             op = layout.operator(CustomUI.Import.bl_idname, text=item[:-5])
    #             op.filepath = join(self.preset_path, item)
    #
    #     def invoke(self, context, event):
    #         context.window_manager.popup_menu(
    #             self.draw_menu, title='导入预设', icon='PRESET')
    #         return {'FINISHED'}
