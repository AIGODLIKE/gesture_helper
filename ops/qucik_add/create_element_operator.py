import bpy
from mathutils import Euler, Vector, Matrix

from ...utils.public import PublicOperator, PublicProperty, get_pref


def __from_rna_get_bl_ops_idname__(bl_rna) -> str:
    identifier = bl_rna.identifier
    if "_OT_" in identifier:
        a, b = identifier.split("_OT_")
        return f"{a.lower()}.{b.lower()}"


class CreateElementOperator(PublicOperator, PublicProperty):
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
        add = pref.add_element_property
        bpy.ops.gesture.element_add(
            add_active_radio=True,
            element_type="OPERATOR",
            relationship=add.relationship,
        )

        button_operator = getattr(context, "button_operator", None)
        bl_idname = __from_rna_get_bl_ops_idname__(button_operator.bl_rna)
        print(f"\n{self.bl_idname}\tinvoke\t", bl_idname)

        properties = {}
        for prop in dir(button_operator):
            if prop not in ('__doc__', '__module__', '__slots__', 'bl_rna', 'rna_type'):
                value = getattr(button_operator, prop)
                from bpy.types import bpy_prop_array

                if isinstance(value, (Euler, Vector, bpy_prop_array)):
                    value = value[:]
                elif isinstance(value, Matrix):
                    res = ()
                    for i in value:
                        res += (*tuple(i[:]),)
                    value = res

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
        pp = ",".join((f"{k}='{v}'" if type(v) is str else f"{k}={v}" for k, v in properties.items()))
        ae = self.active_element
        if ae:
            ae.operator_bl_idname = f"bpy.ops.{bl_idname}({pp})"
            on = ae.__operator_name__
            if on:
                ae.name = on
            print(ae.operator_bl_idname)
        self.cache_clear()
        if act:
            act.radio = True
            self.cache_clear()
        return {"FINISHED"}
