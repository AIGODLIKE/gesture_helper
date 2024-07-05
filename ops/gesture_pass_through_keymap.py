import bpy

from ..utils.public_key import get_kmi_operator_properties


class GesturePassThroughKeymap:
    object_mode_map = {
        "OBJECT": "Object Mode",
        "SCULPT": "Sculpt",
        "PAINT_VERTEX": "Vertex Paint",
        "PAINT_WEIGHT": "Weight Paint",
        "PAINT_TEXTURE": "Image Paint",
        "EDIT_MESH": "Mesh",
        "EDIT_LATTICE": "Lattice",
        "EDIT_ARMATURE": "Armature",
        "EDIT_TEXT": "Font",
        "EDIT_METABALL": "Metaball",
        "EDIT_SURFACE": "Curve",
        "EDIT_CURVE": "Curve",

        "POSE": "Pose",
        "EDIT_GREASE_PENCIL": "Grease Pencil Edit Mode",
        "SCULPT_GREASE_PENCIL": "Grease Pencil Sculpt Mode",
        "PAINT_GREASE_PENCIL": "Grease Pencil Paint Mode",
        "WEIGHT_GREASE_PENCIL": "Grease Pencil Weight Paint",
    }

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """尝试透传按键事件
        :param context:bpy.types.Ccontext
        :param event:bpy.types.Event
        :return:None
        NODE_EDITOR
        IMAGE_EDITOR
        """
        keymaps = bpy.context.window_manager.keyconfigs.active.keymaps
        is3d = context.area.type == "VIEW_3D"
        isImage = context.area.type == "IMAGE_EDITOR"
        key = None
        if is3d:
            key = self.object_mode_map.get(context.mode)
        elif isImage:
            key = "Image Paint"
        else:
            for k in keymaps.keys():
                if k.lower() == context.mode.lower():
                    key = k

        if key in keymaps.keys():
            from .gesture import GestureOperator
            k = keymaps[key]
            match_gesture_key = []
            match_origin_key = []
            for item in k.keymap_items:
                et = item.type == event.type
                if item.idname == GestureOperator.bl_idname and et:
                    match_gesture_key.append(item)
                elif item.idname in ('wm.call_menu', 'wm.call_panel', 'wm.call_menu_pie', 'object.delete') and et:
                    match_origin_key.append(item)
            print(match_gesture_key)
            print(match_origin_key)
            if len(match_origin_key) == 1:
                self.try_operator_pass_through_right(match_origin_key[0])

    def try_operator_pass_through_right(self, kmi):
        try:
            sp = kmi.idname.split('.')
            prefix, suffix = sp
            func = getattr(getattr(bpy.ops, prefix), suffix)
            prop = get_kmi_operator_properties(kmi)

            func('INVOKE_DEFAULT', True, **prop)
        except Exception as e:
            print(f"try_operator_pass_through_right Error\t{e.args}")
            ...
