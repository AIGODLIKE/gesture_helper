from mathutils import Euler, Vector, Matrix

from ...utils.public import PublicOperator, PublicProperty


class CreateElementOperator(PublicOperator, PublicProperty):
    bl_label = '创建操作元素'
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
        button_operator = getattr(context, "button_operator", None)
        print(f"\n{self.bl_idname}\tinvoke")

        properties = {}
        for prop in dir(button_operator):
            if prop not in ('__doc__', '__module__', '__slots__', 'bl_rna', 'rna_type'):
                value = getattr(button_operator, prop)
                from bpy.types import bpy_prop_array

                if isinstance(value, (Euler, Vector, bpy_prop_array)):
                    value = value[:]
                elif isinstance(value, Matrix):
                    value = tuple((i[:] for i in value))

                p = button_operator.bl_rna.properties[prop]
                if getattr(p, "is_array", False):
                    # print(value, "\t", default, "\t", dir(button_operator.bl_rna.properties[prop]))
                    default = p.default_array
                else:
                    default = p.default
                print(type(default), type(value), default, value)
                if default != value:
                    properties[prop] = value

        print(properties)
        # print(button_operator)
        # print(button_operator.bl_rna.properties.keys())
        # print(dir(button_operator))
        return {"FINISHED"}
