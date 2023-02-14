import ast
import re
from functools import wraps, cache
from math import pi
from time import time
from os.path import join, dirname
from os import walk

import bbpy
import bgl
import bpy
import gpu
from bbpy.types import PropertyGroup
from bpy.app.translations import contexts as i18n_contexts
from bpy.app.translations import pgettext
from bpy.props import (IntProperty,
                       BoolProperty,
                       EnumProperty,
                       FloatProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       )
from bpy.types import (EnumPropertyItem,
                       KeyMapItem,
                       PreferencesView,
                       Region,
                       Space,
                       UILayout)
from bpy_extras.io_utils import ExportHelper, ImportHelper
from colorama import Fore
from gpu_extras.batch import batch_for_shader
from mathutils import Euler, Vector, Matrix

from ui import restore_ui, uilist
from ui import get_icon, long_label
draw_extend_ui = bbpy.ui.draw_extend_ui
'''
TODO 面板组
TODO 添加面板到指定面板
TODO UIlayout
'''
# property
addon_name = bbpy.get.addon.name()
get_prop = bbpy.get.property
rna_data = get_prop.from_bl_rna_get_bl_property_data
debug_print = bbpy.debug.debug_print


CTEXT_ENUM_ITEMS = set_ctext_enum()


UUID_PREFIX_NUMS_LEN = 3
# preset property



class CustomUI(PropertyGroup, Data):
    """
    prefs.custom_ui
    """

# Custom Operator
class_tuples = (
    KeyMap,
    KeyMap.SetKeymaps,
    KeyMap.ShowKeymaps,


    Child,
    UIElementItem,
    UIElementItem.SelectMenu,
    UIElementItem.SelectIcon,
    UIElementItem.ApplyOperatorProperty,

    UIItem,

    UIItem.SetPollExpression,

    UIItem.Add,
    UIItem.Del,
    UIItem.Move,
    UIItem.Duplicate,

    UIItem.ElementAdd,
    UIItem.ElementDel,
    UIItem.ElementDuplicate,
    UIItem.ElementMove,

    CustomUI,
    CustomUI.Import,
    CustomUI.Export,
    CustomUI.Preset,

    PopupMenu,
    ExecuteOperator,

    DrawCustomUiFunc.UIElementMenu,
)

register_class, unregister_class = bpy.utils.register_classes_factory(
    class_tuples)


def register():
    register_class()


def unregister():
    unregister_class()
