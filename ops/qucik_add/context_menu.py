import bpy


class ContextMenu():

    def context_menu(self, context):
        layout = self.layout
        layout.label(text="sefsef")

    @staticmethod
    def register(self):
        bpy.types.WM_MT_button_context.append()

    @staticmethod
    def unregister():
        bpy.types.WM_MT_button_context.remove()
