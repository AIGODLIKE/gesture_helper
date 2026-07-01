"""
version 0.0.1
Handle API differences across Blender versions.
"""
import bpy

ALL_ICON = [i.identifier for i in bpy.types.Property.bl_rna.properties['icon'].enum_items_static]  # All icon identifiers


def operator_invoke_confirm(self, event, context, title, message) -> set:
    """Blender 4.1+ requires extra args; new UI shows two buttons."""
    if bpy.app.version >= (4, 1, 0):
        return context.window_manager.invoke_confirm(
            **{
                "operator": self,
                "event": event,
                'title': title,
                'message': message,
            }
        )
    else:
        return context.window_manager.invoke_confirm(
            self, event
        )


def get_adapter_blender_icon(icon=None):
    """Get icon compatible with current Blender version
    """
    version = bpy.app.version[:2]

    if icon not in ALL_ICON:
        icon = "QUESTION"
    elif icon == "INTERNET" and version <= (4, 1):
        icon = "URL"
    elif icon == "FILE_ALIAS" and version <= (4, 2):
        icon = "FOLDER_REDIRECT"
    elif icon == "RNA_ADD" and version <= (5, 0):
        icon = "ADD"
    elif icon is None:
        icon = "NONE"

    return icon
