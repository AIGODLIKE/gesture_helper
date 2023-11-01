from bpy.props import StringProperty
from bpy.types import PropertyGroup


# TODO 子元素的删除需要单独处理,是子级的子级,不能直接拿到
class Element(PropertyGroup):
    emm: StringProperty()
