import bpy

from ..utils.public import PublicProperty
from ..utils.public_cache import PublicCache


class ElementModalOperatorEventCRUE:
    class ModalPoll(bpy.types.Operator, PublicProperty, PublicCache):
        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return ae is not None and ae.is_operator and ae.operator_is_modal

    class ADD(ModalPoll):
        bl_label = 'Add element modal item'
        bl_idname = 'gesture.element_modal_add'
        control_property: bpy.props.StringProperty(name="Control Property")

        def invoke(self, context, event):
            wm = context.window_manager
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
            new = element.modal_events.add()
            new.control_property = self.control_property
            self.cache_clear()
            return {"FINISHED"}

    class COPY(ModalPoll):
        bl_label = 'Copy element modal item'
        bl_idname = 'gesture.element_modal_copy'

        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return super().poll(context) and ae.active_event is not None

        def execute(self, context):
            element = self.pref.active_element
            element.active_event.copy()

            self.cache_clear()
            ae = element.active_event
            if ae:
                parent = ae.parent
                parent.modal_events.move(len(parent.modal_events) - 1, ae.index + 1)

            self.cache_clear()
            return {"FINISHED"}

    class REMOVE(ModalPoll):
        bl_label = 'Remove element modal item'
        bl_idname = 'gesture.element_modal_remove'

        @classmethod
        def poll(cls, context):
            pref = cls._pref()
            ae = pref.active_element
            return super().poll(context) and ae.active_event is not None

        def execute(self, context):
            element = self.pref.active_element
            active = element.active_event
            print("active", active, active.collection, active.event_type, active.parent_element,
                  element.modal_events_index, active.index)
            self.cache_clear()
            active.remove()
            # element.modal_events.remove(element.modal_events_index)
            self.cache_clear()
            return {"FINISHED"}

    class SelectControlProperty(ModalPoll):
        bl_label = 'Select Control Property'
        bl_idname = 'gesture.select_control_property'
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
                            row.label(text=i.type, translate=False)
                            row.label(text=i.name, translate=False)
                            row.label(text=i.name)
                            ops = row.operator(self.bl_idname, text=i.identifier)
                            ops.control_property = i.identifier
                except KeyError:  # KeyError: 'get_rna_type("MESH_OT_fill_gridr") not found'
                    ...

        def execute(self, context):
            print(self.bl_idname, self.control_property)
            return {"FINISHED"}
