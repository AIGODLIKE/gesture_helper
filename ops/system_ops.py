import bpy
from bpy.props import StringProperty

from ..preferences.system import UiElementItem
from ..utils.public.public_operator import PublicOperator


class OpsProp(PublicOperator,
              ):
    system: StringProperty()

    @property
    def current_system(self):
        return self.pref.systems.get(self.system)

    @property
    def system_type(self):
        return self.current_system.system_type

    @property
    def is_exit(self):
        return self.event.value == 'RELEASE'


class GestureOps(OpsProp):

    def invoke_gesture(self, context, event):
        context.window_manager.modal_handler_add(self)
        self.current_system.register_draw_gesture()
        return {'RUNNING_MODAL'}

    def modal_gesture(self, context, event):
        if self.is_exit:
            self.exit()
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def exit_gesture(self):
        self.current_system.unregister_draw_gesture()


class SystemOps(GestureOps,
                ):
    bl_idname = PublicOperator.ops_id_name('gesture_ops')
    bl_label = 'Gesture Ui Operator'

    def invoke(self, context, event):
        self.init_invoke(context, event)
        self.tag_redraw(context)
        if not self.current_system:
            self.report({'WARNING': f'Not Find System {self.system}'})
        else:
            return getattr(self, f'invoke_{self.system_type.lower()}')(context, event)

    def modal(self, context, event):
        self.init_modal(context, event)
        return getattr(self, f'modal_{self.system_type.lower()}')(context, event)

    def exit(self):
        getattr(self, f'exit_{self.system_type.lower()}')()
        self.tag_redraw(bpy.context)


classes_tuple = (
    SystemOps,
)

register_class, unregister_class = bpy.utils.register_classes_factory(classes_tuple)


def register():
    register_class()


def unregister():
    unregister_class()
