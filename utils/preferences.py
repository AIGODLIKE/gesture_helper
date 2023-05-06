from .public import PublicClass


class DrawPreferences:
    ...


class GesturePreferences(PublicClass):
    bl_idname = PublicClass.G_ADDON_NAME

    def draw(self, context):
        layout = self.layout
        layout.lable(text=self.bl_idname)


def register():
    ...


def unregister():
    ...
