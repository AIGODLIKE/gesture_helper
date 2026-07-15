import bpy

from ...element.element_cure import ElementCURE
from ...utils.property import collect_operator_property_overrides
from ...utils.public import PublicOperator, get_pref, debug_print
from ...utils.structure_cache_ops import StructureCacheOps
from ...utils.public_cache import PublicCache


def __from_rna_get_bl_ops_idname__(bl_rna) -> str | None:
    identifier = bl_rna.identifier
    if "_OT_" in identifier:
        a, b = identifier.split("_OT_")
        return f"{a.lower()}.{b.lower()}"
    return None


class CreateModalOperator:
    def invoke(self, context, event):
        self.button_operator = getattr(context, "button_operator", None)
        PublicCache._suppress_operator_tmp_kmi = True
        try:
            self.execute(context)
            last_element = ElementCURE.ADD.last_element
            if last_element:
                last_element.operator_type = "MODAL"
        finally:
            PublicCache._suppress_operator_tmp_kmi = False

        return context.window_manager.invoke_popup(**{'operator': self, 'width': 400})

    def draw(self, context):
        button_operator = self.button_operator

        bl_idname = __from_rna_get_bl_ops_idname__(button_operator.bl_rna)
        description = button_operator.bl_rna.description

        layout = self.layout
        layout.label(text=description)
        layout.label(text=bl_idname)

        last_element = ElementCURE.ADD.last_element
        if last_element:
            last_element.draw_operator_modal(layout)

        for prop in button_operator.bl_rna.properties:
            identifier = prop.identifier
            if identifier in ('rna_type', 'bl_idname'):
                continue
            try:
                value = getattr(button_operator, identifier)
            except (AttributeError, TypeError):
                continue
            layout.label(text=f"{identifier} {value}")


class CreateElementOperator(PublicOperator, StructureCacheOps, CreateModalOperator):
    bl_label = 'Create Operator Element'
    bl_idname = 'wm.gesture_create_element_operator'
    bl_description = 'Add a gesture element from a right-clicked operator button'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        button_operator = getattr(context, "button_operator", None)
        if button_operator is None:
            cls.poll_message_set("Right-click an operator button in the UI")
            return False
        return True

    def execute(self, context):
        """
        # ['__doc__', '__module__', '__slots__', 'bl_rna', 'confirm', 'rna_type', 'use_global']

        :param context:
        :return:
        """
        pref = get_pref()
        with pref.add_element_property.active_radio():
            bpy.ops.wm.gesture_element_add(element_type="OPERATOR")

        # return {"FINISHED"}
        button_operator = getattr(context, "button_operator", None)
        bl_idname = __from_rna_get_bl_ops_idname__(button_operator.bl_rna)
        debug_print(f"\n{self.bl_label}\texecute\t", bl_idname, key='operator')
        properties = collect_operator_property_overrides(button_operator)
        last_element = ElementCURE.ADD.last_element
        if last_element:
            suppress = PublicCache._suppress_operator_tmp_kmi
            PublicCache._suppress_operator_tmp_kmi = True
            try:
                last_element['operator_bl_idname'] = bl_idname
                last_element['operator_properties'] = str(properties)
            finally:
                PublicCache._suppress_operator_tmp_kmi = suppress
            if on := last_element.__operator_original_name__:
                last_element.name = on
            debug_print(last_element.operator_bl_idname, last_element.operator_properties, key='operator')
        self.cache_clear()
        return {"FINISHED"}
