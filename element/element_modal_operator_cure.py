import bpy

from bpy.props import BoolProperty

from ..utils.cache_state import CacheState
from ..utils.pref import poll_addon_preferences
from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.structure_cache_ops import StructureCacheOps
from ..utils.public_cache import PublicCache


class ElementModalOperatorEventCRUE:
    class ModalPoll(bpy.types.Operator, PrefAccess, ActiveSelection, StructureCacheOps, PublicCache):
        @classmethod
        def modal_element(cls, context):
            """Element whose modal UI is drawn, else the active element.

            Create-modal popup draws ``ElementCURE.ADD.last_element`` which may
            differ from preferences selection; layout sets ``gesture_modal_element``.
            """
            el = getattr(context, "gesture_modal_element", None)
            if el is not None:
                return el
            return cls._pref().active_element

        @classmethod
        def poll(cls, context):
            if not poll_addon_preferences(cls):
                return False
            ae = cls.modal_element(context)
            if ae is None:
                cls.poll_message_set("No active element")
                return False
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
        bl_description = (
            'Add a modal event for the active element. '
            'Hold Ctrl+Alt+Shift while clicking to add events for every operator property'
        )
        bl_options = {'REGISTER'}
        control_property: bpy.props.StringProperty(name="Control Property")

        def invoke(self, context, event):
            wm = context.window_manager
            if event.ctrl and event.alt and event.shift:
                element = self.modal_element(context)
                if element:
                    try:
                        for i in element.operator_func.get_rna_type().properties:
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
            element = self.modal_element(context)
            if element:
                layout.context_pointer_set('gesture_modal_element', element)
                try:
                    for i in element.operator_func.get_rna_type().properties:
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
            element = self.modal_element(context)
            if element is None:
                return {'CANCELLED'}
            gesture = element.parent_gesture
            new = element.modal_events.add()
            new.control_property = self.control_property
            new.__init_modal__()
            self.cache_clear(gesture=gesture)
            return {"FINISHED"}

    class COPY(ModalPoll):
        bl_label = 'Copy modal event item'
        bl_idname = 'wm.gesture_element_modal_copy'
        bl_description = 'Duplicate the active modal event on this element'
        bl_options = {'REGISTER'}

        @classmethod
        def poll(cls, context):
            ae = cls.modal_element(context)
            return super().poll(context) and ae is not None and ae.active_event is not None

        def execute(self, context):
            element = self.modal_element(context)
            if element is None or element.active_event is None:
                return {'CANCELLED'}
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
        bl_label = 'Remove modal event item'
        bl_idname = 'wm.gesture_element_modal_remove'
        bl_description = (
            'Remove the active modal event. '
            'Hold Ctrl+Alt+Shift while clicking to remove all modal events '
            '(confirmation required; cannot be undone)'
        )
        bl_options = {'REGISTER'}

        bulk_remove: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

        @classmethod
        def poll(cls, context):
            ae = cls.modal_element(context)
            return super().poll(context) and ae is not None and ae.active_event is not None

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            element = self.modal_element(context)
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
                active = element.active_event if element else None
                name = getattr(active, 'control_property', None) or getattr(active, 'event_type', '')
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Delete this modal event?",
                    message=f"{name}",
                )
            return self.execute(context)

        def execute(self, context):
            element = self.modal_element(context)
            if element is None:
                return {'CANCELLED'}
            gesture = element.parent_gesture
            if self.bulk_remove:
                element.modal_events.clear()
                self.cache_clear(gesture=gesture)
                self.bulk_remove = False
                return {'FINISHED'}
            active = element.active_event
            if active is None:
                return {'CANCELLED'}
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
            element = self.modal_element(context)
            if element:
                layout.context_pointer_set('gesture_modal_element', element)
                try:
                    for i in element.operator_func.get_rna_type().properties:
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
            element = self.modal_element(context)
            if element and element.operator_func:
                try:
                    prop = element.operator_func.get_rna_type().properties.get(self.control_property)
                    if prop and prop.type == 'ENUM' and getattr(prop, 'is_enum_flag', False):
                        self.report({'ERROR'}, "Multi-select enum (set) is not supported")
                        return {'CANCELLED'}
                except KeyError:
                    ...
            active_event = element.active_event if element else None
            if active_event is None:
                return {'CANCELLED'}
            active_event.control_property = self.control_property
            return {"FINISHED"}
