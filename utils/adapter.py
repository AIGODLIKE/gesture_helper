"""
version 0.0.1
Handle API differences across Blender versions.
"""
import bpy


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
