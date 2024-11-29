import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty
from bpy.types import PropertyGroup


class GestureProperty(PropertyGroup):
    @staticmethod
    def gen_gesture_prop(default, subtype='PIXEL'):
        return {'max': 114514, 'default': default, 'subtype': subtype, 'min': 20}

    def update_threshold_confirm(self, _):
        if self.threshold > self.threshold_confirm:
            self['threshold_confirm'] = self.threshold_confirm + 20

    timeout: IntProperty(name='Gesture Timeout(ms)', **gen_gesture_prop(100, 'TIME'))
    radius: IntProperty(name='Gesture Radius', **gen_gesture_prop(100))
    threshold: IntProperty(name='Threshold', **gen_gesture_prop(30))
    threshold_confirm: IntProperty(name='Confirm Threshold', **gen_gesture_prop(80))
    return_distance: IntProperty(name='Return Previous Gesture Distance', **gen_gesture_prop(30))

    immediate_implementation: BoolProperty(name="Immediate Implementation",
                                           description="Immediately executes the operator when the mouse exceeds the threshold value",
                                           default=False)
    show_gesture_keymaps: BoolProperty(name='Show Gesture Keymap')

    pass_through_keymap_type: EnumProperty(name="Pass Through Keymap Type",
                                           items=[
                                               ("REGION", "Region", "from gesture exec region find key"),
                                               ("KEYMAPS", "Keymaps", "from gesture set keymaps find key")
                                           ],
                                           default="REGION"
                                           )

    @staticmethod
    def draw_gesture_property(layout: bpy.types.UILayout):
        from ..utils.public import get_pref
        pref = get_pref()
        col = layout.box().column(align=True)
        g = pref.gesture_property
        col.prop(g, 'timeout')
        col.prop(g, 'radius')
        col.prop(g, 'threshold')
        col.prop(g, 'threshold_confirm')
        col.prop(g, 'immediate_implementation')
        col.prop(g, 'return_distance')
        col.prop(g, 'pass_through_keymap_type')
