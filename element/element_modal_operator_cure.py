import bpy

from bpy.props import BoolProperty

from ..utils.cache_state import CacheState
from ..utils.public import poll_message_active_element
from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.structure_cache_ops import StructureCacheOps
from ..utils.public_cache import PublicCache


class ElementModalOperatorEventCRUE:
    class ModalPoll(bpy.types.Operator, PrefAccess, ActiveSelection, StructureCacheOps, PublicCache):
        @classmethod
        def poll(cls, context):
            if not poll_message_active_element(cls):
                return False
            ae = cls._pref().active_element
            if not ae.is_operator:
                cls.poll_message_set("Active element is not an operator")
                return False
            if not ae.operator_is_modal:
                cls.poll_message_set("Active element is not a modal operator")
                return False
            return True

    class ADD(ModalPoll):
        bl_label = 'Add modal event item'
        bl_idname = 'wm.gesture_element_modal_add'
        bl_description = 'Hold Ctrl+Alt+Shift while clicking to add modal events for every operator property'
        bl_options = {'REGISTER'}
        control_property: bpy.props.StringProperty(name="Control Property")

        def invoke(self, context, event):
            wm = context.window_manager
            if event.ctrl and event.alt and event.shift:
                if self.active_element:
                    try:
                        for i in self.active_element.operator_func.get_rna_type().properties:
                            if i.identifier not in ["rna_type", ]:
                                self.control_property = i.identifier
                                self.execute(context)
                    except KeyError:  # KeyError: 'get_rna_type("MESH_OT_fill_gridr") not found'
                        ...
                return {'FINISHED'}
            return wm.invoke_props_dialog(**{'operator': self, 'width': 500})

        def draw(self, context):
            layout = self.layout
            layout.operator_context = "EXEC_DEFAULT"
            if self.active_element:
                try:
                    for i in self.active_element.operator_func.get_rna_type().properties:
                        if i.identifier not in ["rna_type", ]:
                            row = layout.row(align=True)
                            row.label(text=i.type, translate=False)
                            row.label(text=i.name, translate=False)
                            row.label(text=i.name)
                            ops = row.operator(self.bl_idname, text=i.identifier)
                            ops.control_property = i.identifier
                except KeyError:  # KeyError: 'get_rna_type("MESH_OT_fill_gridr") not found'
                    ...

        def execute(self, context):
            if self.control_property == "":
                return {'FINISHED'}
            element = self.active_element
            gesture = element.parent_gesture
            new = element.modal_events.add()
            new.control_property = self.control_property
            new.__init_modal__()
            self.cache_clear(gesture=gesture)
            return {"FINISHED"}

    class COPY(ModalPoll):
        bl_label = 'Copy element modal item'
        bl_idname = 'wm.gesture_element_modal_copy'
        bl_description = 'Duplicate the active modal event on this element'
        bl_options = {'REGISTER'}

        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return super().poll(context) and ae.active_event is not None

        def execute(self, context):
            element = self.pref.active_element
            gesture = element.parent_gesture
            with CacheState.batch():
                element.active_event.copy()
                self.cache_clear(gesture=gesture)
                ae = element.active_event
                if ae:
                    parent = ae.parent_element
                    parent.modal_events.move(len(parent.modal_events) - 1, ae.index + 1)
            return {"FINISHED"}

    class REMOVE(ModalPoll):
        bl_label = 'Remove element modal item'
        bl_idname = 'wm.gesture_element_modal_remove'
        bl_description = (
            'Hold Ctrl+Alt+Shift while clicking to remove all modal events. '
            'You will be asked to confirm. This cannot be undone.'
        )
        bl_options = {'REGISTER'}

        bulk_remove: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return super().poll(context) and ae.active_event is not None

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.bulk_remove = True
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Remove all modal events?",
                    message="This removes every modal event on the active element. This cannot be undone.",
                )
            self.bulk_remove = False
            if self.pref.draw_property.element_remove_tips:
                active = self.pref.active_element.active_event
                name = getattr(active, 'control_property', None) or getattr(active, 'event_type', '')
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Delete this element?",
                    message=f"{name}",
                )
            return self.execute(context)

        def execute(self, context):
            if self.bulk_remove:
                element = self.pref.active_element
                gesture = element.parent_gesture
                element.modal_events.clear()
                self.cache_clear(gesture=gesture)
                self.bulk_remove = False
                return {'FINISHED'}
            element = self.pref.active_element
            gesture = element.parent_gesture
            active = element.active_event
            active.remove()
            self.cache_clear(gesture=gesture)
            return {"FINISHED"}

    class SelectControlProperty(ModalPoll):
        bl_label = 'Select Control Property'
        bl_idname = 'wm.gesture_select_control_property'
        bl_description = 'Choose which operator property this modal event controls'
        bl_options = {'REGISTER'}
        control_property: bpy.props.StringProperty(name="Control Property")

        def invoke(self, context, event):
            wm = context.window_manager
            return wm.invoke_popup(self)

        def draw(self, context):
            layout = self.layout
            layout.operator_context = "EXEC_DEFAULT"
            if self.active_element:
                try:
                    for i in self.active_element.operator_func.get_rna_type().properties:
                        if i.identifier not in ["rna_type", ]:
                            row = layout.row(align=True)
                            is_flag = i.type == 'ENUM' and getattr(i, 'is_enum_flag', False)
                            row.alert = is_flag
                            row.enabled = not is_flag
                            row.label(text=i.type, translate=False)
                            row.label(text=i.name, translate=False)
                            row.label(text=i.name)
                            if is_flag:
                                row.label(text="Multi-select enum (set) is not supported")
                            else:
                                ops = row.operator(self.bl_idname, text=i.identifier)
                                ops.control_property = i.identifier
                except KeyError:  # KeyError: 'get_rna_type("MESH_OT_fill_gridr") not found'
                    ...

        def execute(self, context):
            element = self.active_element
            if element and element.operator_func:
                try:
                    prop = element.operator_func.get_rna_type().properties.get(self.control_property)
                    if prop and prop.type == 'ENUM' and getattr(prop, 'is_enum_flag', False):
                        self.report({'ERROR'}, "Multi-select enum (set) is not supported")
                        return {'CANCELLED'}
                except KeyError:
                    ...
            self.active_event.control_property = self.control_property
            return {"FINISHED"}
