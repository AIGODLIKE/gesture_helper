from ...utils.public import PublicOperator, PublicProperty


class CreateElementOperator(PublicOperator, PublicProperty):
    bl_label = '创建操作元素'
    bl_idname = 'gesture.create_element_operator'

    @classmethod
    def poll(cls, context):
        button_operator = getattr(context, "button_operator", None)
        return button_operator is not None

    def invoke(self, context, event):
        return {"FINISHED"}
