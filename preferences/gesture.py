import bpy
from bpy.props import BoolProperty, IntProperty


def _gen_gesture_prop(default, subtype='PIXEL'):
    return {'max': 114514, 'default': default, 'subtype': subtype, 'min': 10}


class GestureProperty(bpy.types.PropertyGroup):
    timeout: IntProperty(
        name='Gesture Timeout (ms)',
        description='Idle time before the radial gesture UI appears',
        **_gen_gesture_prop(200, 'TIME'),
    )
    modal_operator_target_fps: IntProperty(
        name='Modal Operator Target FPS',
        description='Report an error when one modal operator step takes longer than one frame at this rate',
        default=10,
        min=1,
        max=240,
    )
    radius: IntProperty(
        name='Gesture Radius',
        description='Radius of the gesture pie / direction ring',
        **{**_gen_gesture_prop(70), "max": 500},
    )
    threshold: IntProperty(
        name='Threshold',
        description='Mouse move distance before a direction item is preview-selected',
        **_gen_gesture_prop(20),
    )
    threshold_confirm: IntProperty(
        name='Confirm Threshold',
        description='Extra mouse travel past the start threshold required to confirm (arm) a direction item',
        **_gen_gesture_prop(20),
    )
    return_distance: IntProperty(
        name='Return Previous Gesture Distance',
        description='Distance to move back toward the center to return to the previous gesture level',
        **_gen_gesture_prop(20),
    )

    immediate_implementation: BoolProperty(
        name="Run Immediately",
        description="Run the selected operator once the mouse passes the confirm threshold (radial UI must be visible)",
        default=False,
    )
    show_gesture_keymaps: BoolProperty(
        name='Show Gesture Keymap',
        description='Show the keymap assigned to each gesture in the list',
        default=False,
    )

    modal_pass_view_rotation: BoolProperty(
        name='Allow view rotation in modal',
        description="Uses the middle mouse button while a modal gesture is active",
        default=True,
    )

    @staticmethod
    def draw_gesture_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        col = layout.box().column(align=True)
        g = pref.gesture_property
        col.prop(g, 'timeout')
        col.prop(g, 'modal_operator_target_fps')
        col.prop(g, 'radius')
        col.prop(g, 'threshold')
        col.prop(g, 'threshold_confirm')
        col.prop(g, 'immediate_implementation')
        col.prop(g, 'return_distance')
        col.prop(g, 'modal_pass_view_rotation')
