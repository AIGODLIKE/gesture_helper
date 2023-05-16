import bpy.utils
from bpy.props import BoolProperty, CollectionProperty, IntProperty, PointerProperty
from bpy.props import EnumProperty
from bpy.types import PropertyGroup

from . import key
from . import ui_element
from .key import SystemKey
from .ui_element import UiElement
from ...utils.public import PublicClass, register_module_factory
from ...utils.public.public_data import PublicData
from ...utils.public.public_property import PublicCollectionNoRepeatName, PublicPropertyGroup
from ...utils.public.public_ui import PublicUi


class SystemProp(PublicClass,
                 PublicPropertyGroup,
                 PublicCollectionNoRepeatName,
                 PublicUi
                 ):

    def set_active_index(self, index):
        self.pref.active_index = index

    @property
    def parent_collection_property(self) -> 'PropertyGroup':
        return self.pref.systems

    @property
    def children_element_recursion(self):
        """子级元素迭代"""
        rsc = []
        for i in self.ui_element:
            rsc += [i, *i.children_recursion]
        return rsc

    @property
    def selected_children_element(self):
        """反回所有选中的子级UI元素"""
        return [i for i in self.children_element_recursion if i.is_selected]

    ui_element: CollectionProperty(type=UiElement)
    system_type: EnumProperty(items=PublicData.ENUM_UI_SYSTEM_TYPE)
    active_index: IntProperty(name='ui element active index')
    is_selected: BoolProperty(name='Selected Item')
    is_enabled: BoolProperty(name='Use this System', default=True)

    @property
    def is_draw_key(self):
        return True


class SystemDraw(SystemProp):
    def draw(self, layout):
        split = layout.split(factor=self.ui_prop.system_split_factor)
        sp_row = split.row(align=True)
        sp_row.emboss = 'NONE'
        sp_row.prop(self, 'is_enabled', text='', icon=self.icon_two(self.is_enabled, 'CHECKBOX'))
        sp_row.prop(self, 'is_selected', text='', icon=self.icon_two(self.is_selected, 'RESTRICT_SELECT'),
                    event=True,
                    # full_event=True
                    )

        sp_row = split.row(align=True)
        sp_row.prop(self, 'name')
        sp_row.prop(self, 'system_type', text='')


class SystemItem(SystemDraw
                 ):
    """UI System Item
    """
    key: PointerProperty(type=SystemKey)

    def change_name(self, old, new):
        self.key.update()

    @property
    def is_have_key(self):
        return self.system_type not in ('LAYOUT',)

    def register_system(self):
        print('register_system', self.name, self.system_type)
        if self.is_have_key:
            self.key.update()

    def unregister_system(self):
        print('unregister_system', self.name, self.system_type)
        self.key.unregister_key()

    def remove(self):
        self.unregister_system()
        super().remove()

    def copy(self):  # TODO

        cp = self.parent_collection_property.add()
        cp.name = self.name


classes_tuple = (
    SystemItem,
)
modules_tuple = (
    key,
    ui_element,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)
register_mod, unregister_mod = register_module_factory(modules_tuple)


def register():
    register_mod()
    register_class()


def unregister():
    unregister_mod()
    unregister_class()
