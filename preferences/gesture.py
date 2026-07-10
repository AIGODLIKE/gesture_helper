import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty


def _gen_gesture_prop(default, subtype='PIXEL'):
    return {'max': 114514, 'default': default, 'subtype': subtype, 'min': 10}


class GestureProperty(bpy.types.PropertyGroup):
    def update_threshold_confirm(self, _):
        if self.threshold > self.threshold_confirm:
            self['threshold_confirm'] = self.threshold_confirm + 20

    timeout: IntProperty(
        name='Gesture Timeout(ms)',
        description='Idle timeout before the gesture trajectory is finalized',
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
        **{**_gen_gesture_prop(95), "max": 500},
    )
    threshold: IntProperty(
        name='Threshold',
        description='Mouse move distance before the gesture UI starts drawing',
        **_gen_gesture_prop(20),
    )
    threshold_confirm: IntProperty(
        name='Confirm Threshold',
        description='Mouse move distance required to confirm a direction item',
        **_gen_gesture_prop(70),
    )
    return_distance: IntProperty(
        name='Return Previous Gesture Distance',
        description='Distance to move back toward the center to return to the previous gesture level',
        **_gen_gesture_prop(20),
    )

    immediate_implementation: BoolProperty(
        name="Immediate Implementation",
        description="Immediately executes the operator when the mouse exceeds the threshold value",
        default=False,
    )
    show_gesture_keymaps: BoolProperty(
        name='Show Gesture Keymap',
        description='Show the keymap assigned to each gesture in the list',
        default=False,
    )

    pass_through_keymap_type: EnumProperty(
        name="Pass Through Keymap Type",
        description="How to find shortcut keys when setting gestures that require transparent operators",
        items=[
            ("REGION", "Region",
             "It is possible for operator errors to occur when searching for passed operators in the area executed through gesture operations"),
            ("KEYMAPS", "Keymaps", "from gesture set keymaps find key"),
        ],
        default="REGION",
    )

    modal_pass_view_rotation: BoolProperty(
        name='Allow view rotation in modal',
        description="Will occupy the middle key operation",
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
        col.prop(g, 'pass_through_keymap_type')
        col.prop(g, 'modal_pass_view_rotation')
