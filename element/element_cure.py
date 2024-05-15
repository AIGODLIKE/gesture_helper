import bpy
from bpy.props import BoolProperty

from .element_property import ElementDirectionProperty
from ..utils.public import PublicProperty, PublicOperator
from ..utils.public_cache import cache_update_lock, PublicCacheFunc


class ElementCURE:

    @cache_update_lock
    def copy(self):
        from ..utils import PropertyGetUtils, PropertySetUtils
        copy_data = PropertyGetUtils.props_data(self.active_element)

        parent = self.parent
        PropertySetUtils.set_prop(parent, 'element', {'0': copy_data})

    @property
    def is_movable(self) -> bool:
        pe = self.parent_element
        if pe:
            if not pe.is_movable:
                return False
        move_from = ElementCURE.MOVE.move_item

        is_ok = move_from and (self not in list(move_from.element))
        move_element = is_ok and move_from != self and self != self.parent_element
        movable = (self.is_child_gesture or self.is_selected_structure) and move_element
        return bool(movable)

    class ElementPoll(PublicProperty, PublicOperator, PublicCacheFunc):

        @classmethod
        def poll(cls, context):
            return cls._pref().active_element is not None

    class ADD(PublicOperator, PublicProperty, ElementDirectionProperty):
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

    class MOVE(ElementPoll):
        bl_idname = 'gesture.element_move'
        bl_label = '移动手势项'
        move_item = None

        cancel: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def move(self):
            from ..utils import PropertyGetUtils, PropertySetUtils
            move_to = getattr(bpy.context, 'move_element', None)
            move_from = ElementCURE.MOVE.move_item

            if move_from:
                move_data = PropertyGetUtils.props_data(move_from)
                if move_to:
                    PropertySetUtils.set_prop(move_to, 'element', {'0': move_data})
                else:
                    PropertySetUtils.set_prop(move_from.parent_gesture, 'element', {'0': move_data})
                self.other.is_move_element = False
                move_from.remove()
            self.cache_clear()

        @property
        def other(self):
            return self.pref.other_property

        def execute(self, context):
            other = self.other
            move_from = ElementCURE.MOVE.move_item

            if self.cancel:

                self.cache_clear()
                other.is_move_element = False
                ElementCURE.MOVE.move_item = None
                return {"FINISHED"}
            elif move_from:
                self.move()
                ae = self.active_element
                self.cache_clear()
                if ae:
                    ae.radio = True
                    ae.__check_duplicate_name__()

                self.cache_clear()
                other.is_move_element = False
                ElementCURE.MOVE.move_item = None
                return {"FINISHED"}

            ElementCURE.MOVE.move_item = self.active_element
            other.is_move_element = True
            self.cache_clear()
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
            self.active_element.copy()
            self.cache_clear()

            ae = self.active_element
            if ae:
                ae.radio = True
                ae.collection[-1].__check_duplicate_name__()

            self.cache_clear()
            return {"FINISHED"}
