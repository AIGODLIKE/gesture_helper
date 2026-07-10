import bpy
from bpy.props import BoolProperty

from .element_property import ElementAddProperty
from ..utils.enum import ENUM_ELEMENT_TYPE, ENUM_SELECTED_TYPE
from ..utils.public import (
    PublicProperty,
    PublicOperator,
    get_pref,
    poll_message_active_element,
    poll_message_active_gesture,
)
from ..utils.public_cache import cache_update_lock, PublicCacheFunc
from ..utils.cache_state import CacheState
from ..utils.translate import translate_lines_text


def _select_sibling_after_remove(element, parent, index, is_last):
    """Restore selection after removing *element* from *parent*."""
    from ..utils.selection import select_element

    if not len(parent.element):
        return
    was_root = element.is_root
    if is_last and index != 0:
        parent.index_element = index - 1
        if not was_root:
            select_element(parent.element[parent.index_element])
    elif -1 < index < len(parent.element):
        sibling = parent.element[index]
        if not sibling.radio:
            select_element(sibling)


class ElementCURE:
    """CRUD operations for elements."""

    @cache_update_lock
    def copy(self):
        """Copy element."""
        from ..utils.property import get_property, __set_prop__
        from ..utils.selection import strip_radio_from_copy_data

        data = strip_radio_from_copy_data(get_property(self))
        __set_prop__(self.parent, 'element', {'0': data})

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
            return poll_message_active_element(cls)

    class ADD(PublicOperator, PublicProperty, ElementAddProperty):
        bl_label = 'Add element item'
        bl_idname = 'wm.gesture_element_add'
        bl_options = {'REGISTER'}
        last_element = None

        @classmethod
        def poll(cls, context):
            return poll_message_active_gesture(cls)

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
            gesture = self.active_gesture
            if gesture and active and active.collection is None:
                PublicCacheFunc.ensure_gesture_structure(gesture)
            if relationship == 'SAME' and active:
                target = active.collection
                if target is not None:
                    return target
                if gesture and active.is_root:
                    return gesture.element
            elif relationship == 'CHILD' and active and active.is_have_add_child:
                return active.element
            if gesture:
                return gesture.element
            return None

        @property
        def add_name(self):
            return self.element_type.title() + (" " + self.selected_type.title() if self.is_selected_structure else "")

        def execute(self, _):
            gesture = self.active_gesture
            if gesture is None:
                return {'CANCELLED'}
            target = self.collection
            if target is None:
                return {'CANCELLED'}
            with CacheState.batch():
                add = target.add()
                target.update()
                PublicCacheFunc.ensure_gesture_structure(gesture)
                add.element_type = self.element_type
                add.selected_type = self.selected_type
                add.__init_element__()
                add.name = self.add_name
                self.cache_clear(gesture=gesture)

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
        bl_idname = 'wm.gesture_element_remove'
        bl_description = (
            'Hold Ctrl+Alt+Shift while clicking to remove all elements in the active gesture. '
            'You will be asked to confirm. Use Ctrl+Z to undo.'
        )
        bl_options = {'REGISTER'}

        bulk_remove: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.bulk_remove = True
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Remove all elements?",
                    message="This removes every element in the active gesture. You can undo with Ctrl+Z.",
                )
            self.bulk_remove = False
            if self.pref.draw_property.element_remove_tips:
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Confirm To Delete The Element?",
                    message=f"{self.active_element.name}",
                )
            return self.execute(context)

        def execute(self, _):
            if self.bulk_remove:
                gesture = self.pref.active_gesture
                gesture.element.clear()
                self.cache_clear(gesture=gesture)
                self.bulk_remove = False
                return {'FINISHED'}
            ae = self.pref.active_element
            gesture = ae.parent_gesture
            is_last = ae.is_last
            parent = ae.parent
            index = ae.index

            ae.remove()
            self.cache_clear(gesture=gesture)
            _select_sibling_after_remove(ae, parent, index, is_last)

            return {'FINISHED'}

    class MOVE(ElementPoll):
        bl_label = 'Move gesture item'
        bl_idname = 'wm.gesture_element_move'
        bl_description = 'Move the active element to another parent or cancel the move'
        bl_options = {'REGISTER'}
        move_item = None

        cancel_move: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def move(self):
            from ..utils.property import get_property, __set_prop__
            from ..utils.selection import strip_radio_from_copy_data, suppress_radio_updates

            move_to = getattr(bpy.context, 'move_element', None)
            move_from = ElementCURE.MOVE.move_item
            gesture = move_from.parent_gesture if move_from else None

            if move_from:
                move_data = strip_radio_from_copy_data(get_property(move_from))
                with suppress_radio_updates():
                    if move_to:
                        __set_prop__(move_to, 'element', {'0': move_data})
                    else:
                        __set_prop__(move_from.parent_gesture, 'element', {'0': move_data})
                move_from.remove()
            self.cache_clear(gesture=gesture)

        @property
        def other(self):
            return self.pref.other_property

        def execute(self, _):
            move_from = ElementCURE.MOVE.move_item
            gesture = self.active_gesture

            if self.cancel_move:
                self.cache_clear(gesture=gesture)
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
            self.cache_clear(gesture=gesture)
            return {'FINISHED'}

    class SORT(ElementPoll):
        bl_label = 'Sort gesture item'
        bl_idname = 'wm.gesture_element_sort'
        bl_description = 'Move the active element up or down within its parent list'
        bl_options = {'REGISTER'}

        is_next: BoolProperty()

        def execute(self, _):
            gesture = self.active_gesture
            with CacheState.batch():
                self.active_element.sort(self.is_next)
                self.cache_clear(gesture=gesture)
            return {'FINISHED'}

    class COPY(ElementPoll):
        bl_label = 'Copy gesture item'
        bl_idname = 'wm.gesture_element_copy'
        bl_description = 'Duplicate the active element within the gesture'
        bl_options = {'REGISTER'}

        def execute(self, _):
            from ..utils.selection import clear_active_element_cache, enforce_single_selection

            gesture = self.active_gesture
            source = self.active_element
            if gesture is None or source is None:
                return {'CANCELLED'}
            parent = source.parent
            index_before = len(parent.element)
            with CacheState.batch():
                source.copy()
                PublicCacheFunc.ensure_gesture_structure(gesture)
                clear_active_element_cache(gesture)
                if index_before < len(parent.element):
                    duplicate = parent.element[index_before]
                    enforce_single_selection(duplicate)
                    parent.element.move(len(parent.element) - 1, duplicate.index)
                self.cache_clear(gesture=gesture)

            return {'FINISHED'}

    class CUT(ElementPoll):
        bl_label = 'Cut gesture item'
        bl_idname = 'wm.gesture_element_cut'
        bl_description = 'Cut the active element and paste it elsewhere, or cancel the cut'
        bl_options = {'REGISTER'}

        __cut_data__ = None  # Cut buffer data

        cancel_cut: BoolProperty(default=False, options={'SKIP_SAVE'})

        @cache_update_lock
        def cut(self):
            from ..utils.property import __set_prop__
            from ..utils.selection import select_element, suppress_radio_updates

            cut = ElementCURE.CUT.__cut_data__
            gesture = self.active_gesture

            # During cut/move paste
            cut_to = getattr(bpy.context, 'cut_element', None)
            target = cut_to if cut_to else self.active_gesture
            with suppress_radio_updates():
                __set_prop__(target, 'element', {'0': cut})
            self.cache_clear(gesture=gesture)
            if len(target.element):
                select_element(target.element[-1])

        @classmethod
        def poll(cls, context):
            if cls.__cut_data__ is not None:
                return True
            return poll_message_active_element(cls)

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
                ElementCURE.CUT.__cut_data__ = None
                return {'FINISHED'}

            # Select item to cut
            ae = self.pref.active_element
            gesture = ae.parent_gesture
            from ..utils.property import get_property
            from ..utils.selection import strip_radio_from_copy_data

            ElementCURE.CUT.__cut_data__ = strip_radio_from_copy_data(get_property(ae))
            is_last = ae.is_last
            parent = ae.parent
            index = ae.index
            ae.remove()
            self.cache_clear(gesture=gesture)
            _select_sibling_after_remove(ae, parent, index, is_last)

            return {'FINISHED'}

    class SwitchShowChild(ElementPoll):
        bl_idname = 'wm.gesture_element_switch_show_child'
        bl_label = 'Switch show child'
        bl_description = 'Show or hide child elements for every item in the active gesture'
        bl_options = {'REGISTER'}

        def execute(self, context):
            value = not self.pref.active_element.show_child
            from ..utils.iteration import iter_elements
            for i in iter_elements(self.pref.active_gesture):
                i.show_child = value
            return {"FINISHED"}
