import bpy
from bpy.props import BoolProperty

from .element_property import ElementAddProperty
from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
from ..utils.public import PublicProperty, PublicOperator, get_pref
from ..utils.public_cache import cache_update_lock, PublicCacheFunc
from ..utils.translate import translate_lines_text


class ElementCURE:
    """CRUD operations for elements."""

    @cache_update_lock
    def copy(self):
        """Copy element."""
        from ..utils.property import __set_prop__
        __set_prop__(self.parent, 'element', {'0': self.active_element.___dict_data___})

    @property
    def is_movable(self) -> bool:
        """Return whether this item can be moved to."""

        move_from = ElementCURE.MOVE.move_item
        if move_from.parent_element == self:
            # Cannot move to current item parent
            return False
        elif self in move_from.element_child_iteration:
            # Target is a child of the item being moved
            return False

        is_ok = move_from and (self not in list(move_from.element))
        move_element = is_ok and move_from != self and self != self.parent_element
        movable = (self.is_child_gesture or self.is_selected_structure) and move_element
        return bool(movable)

    @property
    def is_can_be_cut(self) -> bool:
        """Return whether this item can be cut."""
        return self.is_child_gesture or self.is_selected_structure

    class ElementPoll(PublicProperty, PublicOperator, PublicCacheFunc):

        @classmethod
        def poll(cls, _):
            return cls._pref().active_element is not None

    class ADD(PublicOperator, PublicProperty, ElementAddProperty):
        bl_label = 'Add element item'
        bl_idname = 'gesture.element_add'
        last_element = None

        @classmethod
        def description(cls, context, properties):
            texts = []

            if properties.element_type == 'SELECTED_STRUCTURE':
                for (i, t, d) in ENUM_SELECTED_TYPE:
                    if i == properties.selected_type:
                        texts.append(d)
            for (i, t, d) in ENUM_ELEMENT_TYPE:
                if i == properties.element_type:
                    texts.append(d)
            return translate_lines_text(*texts)

        @property
        def collection(self):
            relationship = get_pref().add_element_property.relationship
            active = self.active_element
            if relationship == 'SAME' and active:
                # If no sibling level, use root collection
                return active.parent.element
            elif relationship == 'CHILD' and active and active.is_have_add_child:
                return active.element
            return self.active_gesture.element

        @property
        def add_name(self):
            return self.element_type.title() + (" " + self.selected_type.title() if self.is_selected_structure else "")

        def execute(self, _):
            add = self.collection.add()
            self.collection.update()
            add.element_type = self.element_type
            add.selected_type = self.selected_type
            add.__init_element__()
            add.name = self.add_name
            self.cache_clear()

            if self.pref.add_element_property.add_active_radio:
                if self.active_element:
                    self.active_element.show_child = True
                add.update_radio()
            elif self.pref.active_element is None:
                add.update_radio()

            self.__class__.last_element = add
            return {'FINISHED'}

    class REMOVE(ElementPoll):
        bl_label = 'Remove element item'
        bl_idname = 'gesture.element_remove'
        bl_description = 'Ctrl Alt Shift + Click: Remove all element!!!'
        bl_otions = {'REGISTER', 'UNDO'}

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.pref.active_gesture.element.clear()
                self.cache_clear()
                return {'FINISHED'}
            elif self.pref.draw_property.element_remove_tips:
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Confirm To Delete The Element?",
                    message=f"{self.active_element.name}",
                )
            return self.execute(context)

        def execute(self, _):
            ae = self.pref.active_element
            is_last = ae.is_last
            parent = ae.parent
            index = ae.index

            ae.remove()
            self.cache_clear()

            if is_last and index != 0:
                parent.index_element = index - 1
                parent.element[parent.index_element].radio = True
            elif -1 < index < len(parent.element):
                parent.element[index].radio = True

            return {'FINISHED'}

    class MOVE(ElementPoll):
        bl_label = 'Move gesture item'
        bl_idname = 'gesture.element_move'
        move_item = None

        cancel_move: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def move(self):
            from ..utils.property import get_property, __set_prop__
            move_to = getattr(bpy.context, 'move_element', None)
            move_from = ElementCURE.MOVE.move_item

            if move_from:
                move_data = get_property(move_from)
                if move_to:
                    __set_prop__(move_to, 'element', {'0': move_data})
                else:
                    __set_prop__(move_from.parent_gesture, 'element', {'0': move_data})
                move_from.remove()
            self.cache_clear()

        @property
        def other(self):
            return self.pref.other_property

        def execute(self, _):
            move_from = ElementCURE.MOVE.move_item

            if self.cancel_move:
                self.cache_clear()
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}
            elif move_from:
                self.move()
                ae = self.active_element
                if ae:
                    ae.radio = True
                ElementCURE.MOVE.move_item = None
                return {'FINISHED'}

            ElementCURE.MOVE.move_item = self.active_element
            self.cache_clear()
            return {'FINISHED'}

    class SORT(ElementPoll):
        bl_label = 'Sort gesture item'
        bl_idname = 'gesture.element_sort'

        is_next: BoolProperty()

        def execute(self, _):
            self.active_element.sort(self.is_next)
            self.cache_clear()
            return {'FINISHED'}

    class COPY(ElementPoll):
        bl_label = 'Copy gesture item'
        bl_idname = 'gesture.element_copy'

        def execute(self, _):
            self.active_element.copy()
            self.cache_clear()

            ae = self.active_element
            if ae:
                ae.radio = True
                parent = ae.parent
                parent.element.move(len(parent.element) - 1, ae.index + 1)

            self.cache_clear()
            return {'FINISHED'}

    class CUT(ElementPoll):
        bl_label = 'Cut gesture item'
        bl_idname = 'gesture.element_cut'

        __cut_data__ = None  # Cut buffer data

        cancel_cut: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def cut(self):
            from ..utils.property import __set_prop__
            cut = ElementCURE.CUT.__cut_data__

            # During cut/move paste
            cut_to = getattr(bpy.context, 'cut_element', None)
            if cut_to:
                __set_prop__(cut_to, 'element', {'0': cut})
            else:
                __set_prop__(self.active_gesture, 'element', {'0': cut})
            self.cache_clear()

        @classmethod
        def poll(cls, context):
            if cls.__cut_data__ is not None:
                return True
            return super().poll(context)

        def invoke(self, context, event):
            if self.cancel_cut:
                from ..utils.adapter import operator_invoke_confirm
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Confirm To Cancel The Cut?",
                    message="Cut Content Will Be Lost",
                )
            return self.execute(context)

        def execute(self, context):
            cut = ElementCURE.CUT.__cut_data__
            if self.cancel_cut:
                self.cache_clear()
                ElementCURE.CUT.__cut_data__ = None
                return {'FINISHED'}
            elif cut:
                self.cut()
                ae = self.active_element
                if ae:
                    ae.radio = True
                ElementCURE.CUT.__cut_data__ = None
                return {'FINISHED'}

            # Select item to cut
            ae = self.pref.active_element
            ElementCURE.CUT.__cut_data__ = ae.___dict_data___
            is_last = ae.is_last
            parent = ae.parent
            index = ae.index
            ae.remove()
            self.cache_clear()

            if is_last and index != 0:
                parent.index_element = index - 1
                parent.element[parent.index_element].radio = True
            elif -1 < index < len(parent.element):
                parent.element[index].radio = True

            return {'FINISHED'}

    class SwitchShowChild(ElementPoll):
        bl_idname = 'gesture.element_switch_show_child'
        bl_label = 'Switch show child'

        def execute(self, context):
            value = not self.pref.active_element.show_child
            from ..utils.iteration import iter_elements
            for i in iter_elements(self.pref.active_gesture):
                i.show_child = value
            return {"FINISHED"}
