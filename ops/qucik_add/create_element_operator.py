import bpy
from mathutils import Euler, Vector, Matrix

from ...element.element_cure import ElementCURE
from ...utils.public import PublicOperator, PublicProperty, get_pref


def __from_rna_get_bl_ops_idname__(bl_rna) -> str | None:
    identifier = bl_rna.identifier
    if "_OT_" in identifier:
        a, b = identifier.split("_OT_")
        return f"{a.lower()}.{b.lower()}"
    return None


class CreateModalOperator:
    def invoke(self, context, event):
        self.button_operator = getattr(context, "button_operator", None)

        self.execute(context)

        last_element = ElementCURE.ADD.last_element
        last_element.operator_type = "MODAL"

        return context.window_manager.invoke_popup(**{'operator': self, 'width': 400})

    def draw(self, context):
        button_operator = self.button_operator

        bl_idname = __from_rna_get_bl_ops_idname__(button_operator.bl_rna)
        description = button_operator.bl_rna.description

        layout = self.layout
        layout.label(text=description)
        layout.label(text=bl_idname)

        last_element = ElementCURE.ADD.last_element
        last_element.draw_operator_modal(layout)

        properties = {}
        for prop in dir(button_operator):
            if prop not in ('__doc__', '__module__', '__slots__', 'bl_rna', 'rna_type', "bl_system_properties_get"):
                value = getattr(button_operator, prop, None)

                if isinstance(value, (Euler, Vector, bpy.types.bpy_prop_array)):
                    value = value[:]
                elif isinstance(value, Matrix):
                    res = ()
                    for i in value:
                        res += (*tuple(i[:]),)
                    value = res
                layout.label(text=prop + " " + str(value))


class CreateElementOperator(PublicOperator, PublicProperty, CreateModalOperator):
    bl_label = 'Create Operator Element'
    bl_idname = 'gesture.create_element_operator'

    @classmethod
    def poll(cls, context):
        button_operator = getattr(context, "button_operator", None)
        return button_operator is not None

    def execute(self, context):
        """
        # ['__doc__', '__module__', '__slots__', 'bl_rna', 'confirm', 'rna_type', 'use_global']

        :param context:
        :return:
        """
        pref = get_pref()
        act = pref.active_element
        with pref.add_element_property.active_radio():
            bpy.ops.gesture.element_add(element_type="OPERATOR")

        button_operator = getattr(context, "button_operator", None)
        bl_idname = __from_rna_get_bl_ops_idname__(button_operator.bl_rna)
        print(f"\n{self.bl_label}\texecute\t", bl_idname)

        properties = {}
        for prop in dir(button_operator):
            if prop not in ('__doc__', '__module__', '__slots__', 'bl_rna', 'rna_type', "bl_system_properties_get"):
                value = getattr(button_operator, prop)

                if isinstance(value, (Euler, Vector, bpy.types.bpy_prop_array)):
                    value = value[:]
                elif isinstance(value, Matrix):
                    res = ()
                    for i in value:
                        res += (*tuple(i[:]),)
                    value = res

                try:
                    p = button_operator.bl_rna.properties[prop]
                    print(prop, p.type, value)
                    if p.type not in ("POINTER", "COLLECTION"):
                        if getattr(p, "is_array", False):
                            default = p.default_array[:]
                        else:
                            if p.type == "ENUM" and p.default == '':
                                default = value
                            else:
                                default = p.default
                        if default != value:
                            print("default != value", default)
                            properties[prop] = value
                except Exception as e:
                    print(e.args)
                    import traceback
                    traceback.print_exc()
                    traceback.print_stack()

        pp = ",".join((f"{k}='{v}'" if type(v) is str else f"{k}={v}" for k, v in properties.items()))
        ae = self.active_element
        if ae:
            ae.operator_bl_idname = f"bpy.ops.{bl_idname}({pp})"
            if on := ae.__operator_original_name__:
                ae.name = on
            print(ae.operator_bl_idname)
        self.cache_clear()
        if act:
            act.radio = True
            self.cache_clear()
        return {"FINISHED"}
