from bpy.props import BoolProperty

from .element_property import ElementDirectionProperty
from ...public import PublicProperty, PublicOperator
from ...public_cache import cache_update_lock


class ElementCURE:

    @cache_update_lock
    def copy(self):
        from ... import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self.active_element)

        parent = self.parent
        PropertySetUtils.set_prop(parent, 'element', {'0': copy_data})

    class ElementPoll(PublicProperty, PublicOperator):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_element is not None

    class ADD(PublicOperator, ElementDirectionProperty, PublicProperty):
        bl_idname = 'gesture.element_add'
        bl_label = '添加手势项'

        @property
        def collection(self):
            r = self.relationship
            ae = self.active_element
            if r == 'SAME' and ae:
                pe = ae.parent_element
                # 如果没有同级则快进到根
                if pe:
                    return pe.element
            elif r == 'CHILD' and ae:
                return ae.element
            return self.active_gesture.element

        @property
        def add_name(self):
            return self.element_type.title() + (" " + self.selected_type.title() if self.is_selected_structure else "")

        def execute(self, context):
            add = self.collection.add()
            add.cache_clear()

            if self.active_element:
                self.active_element.radio = True  # 还是保持默认选择是当前

            add.element_type = self.element_type
            add.selected_type = self.selected_type
            add.init()
            add.cache_clear()
            add.name = self.add_name
            return {"FINISHED"}

    class REMOVE(ElementPoll):
        bl_idname = 'gesture.element_remove'
        bl_label = '删除手势项'

        def execute(self, context):
            self.pref.active_element.remove()
            self.cache_clear()
            return {"FINISHED"}

    # TODO MOVE COPY
    class MOVE(ElementPoll):
        bl_idname = 'gesture.element_move'
        bl_label = '移动手势项'

        def execute(self, context):
            self.cache_clear()
            other_property = self.pref.other_property
            other_property.is_move_element = True
            return {"FINISHED"}

    class SORT(ElementPoll):
        bl_idname = 'gesture.element_sort'
        bl_label = '排序手势项'

        is_next: BoolProperty()

        def execute(self, _):
            self.active_element.sort(self.is_next)
            self.cache_clear()
            return {"FINISHED"}

    class COPY(ElementPoll):
        bl_idname = 'gesture.element_copy'
        bl_label = '复制手势项'

        def execute(self, _):
            ag = self.active_element.copy()
            self.cache_clear()
            print('active_element.collection', self.active_element.collection)
            self.active_element.radio = True
            self.active_element.collection[-1].__check_duplicate_name__()
            self.cache_clear()
            return {"FINISHED"}
