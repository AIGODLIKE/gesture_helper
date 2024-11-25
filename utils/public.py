from functools import cache
from os.path import dirname, realpath, join, abspath

import bpy
from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator

from .public_cache import PublicCacheFunc, cache_update_lock

ADDON_FOLDER = dirname(dirname(realpath(__file__)))
BACKUPS_FOLDER = abspath(join(ADDON_FOLDER, 'backups'))
PROPERTY_FOLDER = abspath(join(ADDON_FOLDER, 'src', 'preset'))

TRANSLATE_ID = "gesture"
TRANSLATE_KEY = TRANSLATE_ID + "_keymap"


@cache
def get_pref():
    from .. import __package__ as base_package
    return bpy.context.preferences.addons[base_package].preferences


def tag_redraw():
    """redraw interface"""
    for area in bpy.context.window.screen.areas:
        area.tag_redraw()


def get_debug(key=None) -> bool:
    """by key get debug"""
    prop = get_pref().debug_property
    if prop.debug_mode and key:
        kl = key.lower()
        if kl == 'key':
            return prop.debug_key
        elif kl == 'export_import':
            return prop.debug_export_import
        elif kl == "poll":
            return prop.debug_poll
        elif kl == "operator":
            return prop.debug_operator
    return prop.debug_mode


def by_path_set_value(point, data_path: list[str], value) -> None:
    """
    by_path_set_value(bpy, data_path: ['context','scene','render','resolution_x'], 10)

    eq

    bpy.context.scene.render.resolution_x = 10
    """
    if len(data_path) == 0 or point is None:
        print("by_path_set_value set value Error", point, data_path, value)
    elif len(data_path) == 1:
        setattr(point, data_path[0], value)
    else:
        by_path_set_value(getattr(point, data_path[0]), data_path[1:], value)


@cache
def get_gesture_direction_items(iteration):
    direction = {}
    last_selected_structure = None  # 如果不是连续的选择结构
    for item in iteration:
        if item.is_selected_structure:  # 是选择结构
            if item.__selected_structure_is_validity__:  # 是可用的选择结构
                # 是True
                poll = (item.is_selected_else or item.poll_bool)
                if poll and (not last_selected_structure or item.is_selected_if):
                    child = get_gesture_direction_items(item.element)
                    direction.update(child)
                    last_selected_structure = item
            continue  # 不运行后面的
        elif item.is_child_gesture or item.is_operator:  # 是子项或者是操作符
            direction[item.direction] = item
        if item.enabled:  # 如果不是选择结构并
            last_selected_structure = None
    return direction


def update(func):
    def w(*args, **kwargs):
        self = args[0]
        name = func.__name__
        before = getattr(self, f'{name}_before', None)
        after = getattr(self, f'{name}_after', None)

        if before:
            before()
        res = func(*args, **kwargs)
        if after:
            after()

        return res

    return w


class PublicProperty(PublicCacheFunc):

    @staticmethod
    def _pref():
        return get_pref()

    @property
    def pref(self):
        return self._pref()

    @property
    def draw_property(self):
        return self._pref().draw_property

    @property
    def debug_property(self):
        return self._pref().debug_property

    @property
    def backups_property(self):
        return self._pref().backups_property

    @property
    def other_property(self):
        return self._pref().other_property

    @property
    def gesture_property(self):
        return self._pref().gesture_property

    @property
    def active_gesture(self):
        """反回活动的手势"""
        try:
            index = getattr(self.pref, "index_gesture", None)
            if index is not None:
                return self.pref.gesture[index]
        except IndexError:
            ...

    @property
    def active_element(self):
        """反回活动的元素"""
        act_ges = self.active_gesture
        if act_ges and len(act_ges.element):
            for element in act_ges.element_iteration:
                if element.radio:
                    return element

    @classmethod
    def update_state(cls):
        """更新临时快捷键的状态
        操作符"""
        pref = get_pref()
        ag = pref.active_gesture
        ae = pref.active_element
        try:
            if ag:
                ag.to_temp_kmi()
                ag.__check_duplicate_name__()
            if ae:
                if ae.element_type == "OPERATOR" and ae.operator_type == "OPERATOR":
                    ae.to_operator_tmp_kmi()
        except Exception as e:
            print('update_state Error', e.args)
            import traceback
            traceback.print_stack()
            traceback.print_exc()

    @staticmethod
    def __tn__(text):
        """翻译名称"""
        from ..src.translate import __name_translate__
        return __name_translate__(text)

    @staticmethod
    def __tp__(text):
        """翻译预设"""
        from ..src.translate import __preset_translate__
        return __preset_translate__(text)

    @property
    def is_debug(self) -> bool:
        return get_debug()

    @property
    def __is_move_element__(self) -> bool:
        """反回是在移动元素模式的布尔值"""
        return self.__element_move_item__ is not None

    @property
    def __element_move_item__(self) -> "Element":
        """反回移动的element项"""
        from ..element.element_cure import ElementCURE
        return ElementCURE.MOVE.move_item

    @property
    def __is_cut_element__(self) -> bool:
        """反回是在剪切元素模式的布尔值"""
        return self.__element_cut_item__ is not None

    @property
    def __element_cut_item__(self) -> "Element":
        """反回剪切的element项"""
        from ..element.element_cure import ElementCURE
        return ElementCURE.CUT.__cut_data__

    @staticmethod
    def __get_icon__(key) -> int:
        """获取icon"""
        from .icons import Icons
        return Icons.get(key).icon_id

    @property
    def ___dict_data___(self) -> dict:
        """反回当前项的数据"""
        from . import PropertyGetUtils
        return PropertyGetUtils.props_data(self)


class PublicOperator(Operator):
    event: 'bpy.types.Event'

    def init_invoke(self, event):
        self.event = event

    def init_module(self, event):
        self.event = event

    @property
    def is_right_mouse(self):
        return self.event.type == 'RIGHTMOUSE'

    @property
    def is_release(self):
        return self.event.value == 'RELEASE'

    @property
    def is_exit(self):
        return self.is_release or self.is_right_mouse

    @staticmethod
    def tag_redraw():
        tag_redraw()


class PublicUniqueNamePropertyGroup:
    """不重复名称"""

    names_iteration: list
    __is_check_duplicate_name__ = True

    @staticmethod
    def __generate_new_name__(names, new_name):
        # 检查新名称是否已存在,TIPS 最大999
        if new_name in names:
            base_name = new_name
            count = 1
            while new_name in names:
                new_name = f"{base_name}.{count:03}"
                count += 1
        return new_name

    @property
    def __names__(self):
        return list(map(lambda s: s.name, self.names_iteration))

    @cache_update_lock
    def __check_duplicate_name__(self):
        names = self.__names__
        if self.__names__.count(self.name) > 1:
            self.name = self.__generate_new_name__(self.__names__, self.name)
        if len(names) != len(set(names)):
            for i in self.names_iteration:
                if self.__names__.count(i.name) > 1:
                    self.cache_clear()
                    i.name = self.__generate_new_name__(self.__names__, i.name)

    @update
    def rename(self):
        if self.__is_check_duplicate_name__:
            self.__check_duplicate_name__()
        update_name = getattr(self, "update_name", None)
        if update_name:
            update_name()

    name: StringProperty(
        name='名称',
        description='不允许名称重复,如果名称重复则编号 e.g .001 .002 .999 支持重命名到999',
        update=lambda self, context: self.rename()
    )


class PublicSortAndRemovePropertyGroup:
    index: int
    collection: CollectionProperty

    def _get_index(self):
        return 0

    def _set_index(self, value):
        ...

    index = property(fget=_get_index, fset=_set_index,
                     doc='通过当前项的index,来设置索引的index值,以及移动项')

    @property
    def is_last(self) -> bool:
        """
        反回此手势 是否为最后一个的布尔值
        用于移动手势位置
        @rtype: object
        """
        return self == self.collection[-1]

    @property
    def is_first(self) -> bool:
        """
        反回此手势 是否为第一个的布尔值
        用于移动手势位置
        @return:
        """
        return self == self.collection[0]

    @update
    def sort(self, is_next):
        col = self.collection
        gl = len(col)
        if is_next:
            if self.is_last:
                col.move(gl - 1, 0)
                self.index = 0
            else:
                col.move(self.index, self.index + 1)
                self.index = self.index + 1
        else:
            if self.is_first:
                col.move(self.index, gl - 1)
                self.index = gl - 1
            else:
                col.move(self.index - 1, self.index)
                self.index = self.index - 1

    @update
    def remove(self):
        self.collection.remove(self.index)
