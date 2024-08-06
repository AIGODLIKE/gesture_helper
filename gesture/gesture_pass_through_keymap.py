import bpy


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

    area_map = {
        "IMAGE_EDITOR": "Image Paint",
        "NODE_EDITOR": "Node Editor",
        "DOPESHEET_EDITOR": "Dopesheet",
        "GRAPH_EDITOR": "Graph Editor",

        "NLA_EDITOR": "NLA Editor",
        # NLA Generic
        # NLA Tracks

        "SPREADSHEET": "Spreadsheet Generic",
        "TEXT_EDITOR": "Text",  # 文本编辑器
        "CONSOLE": "Console",
        "INFO": "Info",
        "OUTLINER": "Outliner",
        "PROPERTIES": "Property Editor",
        "FILE_BROWSER": "File Browser",
    }

    sequence_map = {
        "SEQUENCER": "Sequencer",
        "PREVIEW": "SequencerPreview",
    }

    # "SEQUENCER_PREVIEW": "SequencerCommon",
    sequencer_preview_map = {
        "PREVIEW": "SequencerPreview",
        "WINDOW": "Sequencer",
    }

    tracking_map = {
        # "CLIP_EDITOR": "Clip",
        # Clip Time Scrub
        "CLIP": "Clip Editor",
        "GRAPH": "Clip Graph Editor",
        "DOPESHEET": "Clip Dopesheet Editor",
    }

    pass_through_idname = (
        # 菜单
        'wm.call_menu',
        'wm.call_panel',
        'wm.call_menu_pie',
        'buttons.context_menu',  # 属性菜单

        'object.delete',  # 删除
        'outliner.operation',  # 大纲
        'object.move_to_collection',  # 合并

        'nla.tracks_add',
        'nla.actionclip_add',

        # 选择
        'object.select_all',
        'mesh.select_all',
        'outliner.select_all',
        'info.select_all',
        'text.select_all',
        'gpencil.select_all',
        'grease_pencil.select_all',
        'paint.face_select_all',
        'paint.vert_select_all',
        'paintcurve.select',
        'pose.select_all',
        'curve.select_all',
        'curves.select_all',
        'armature.select_all',
        'mball.select_all',
        'particle.select_all',
        'font.select_all',
        'console.select_all',
        'anim.channels_select_all',
        'uv.select_all',
        'mask.select_all',
        'marker.select_all',
        'graph.select_all',
        'node.select_all',
        'file.select_all',
        'action.select_all',
        'nla.select_all',
        'sequencer.select_all',
        'clip.select_all',
        'clip.graph_select_all_markers'
    )

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """尝试透传按键事件
        :param context:bpy.types.Ccontext
        :param event:bpy.types.Event
        :return:None
        NODE_EDITOR
        IMAGE_EDITOR
        """
        area_type = context.area.type
        region_type = context.region.type
        keymaps = context.window_manager.keyconfigs.active.keymaps

        view_type = getattr(context.space_data, "view_type", None)
        mode = getattr(context.space_data, "mode", None)
        view = getattr(context.space_data, "view", None)

        mk = self.area_map.get(area_type)

        key = None
        if area_type == "VIEW_3D":
            key = self.object_mode_map.get(context.mode)
        elif area_type == "SEQUENCE_EDITOR":
            sequence = self.sequence_map.get(view_type)
            if sequence is not None:
                key = sequence
            if view_type == "SEQUENCER_PREVIEW":
                key = self.sequencer_preview_map.get(region_type)
        elif area_type == "CLIP_EDITOR":
            if mode == "TRACKING":
                t = self.tracking_map.get(view)
                if t is not None:
                    key = t
            elif mode == "MASK":
                key = "Clip Editor"
        elif mk is not None:
            key = mk
        else:
            for k in keymaps.keys():
                if k.lower() == context.mode.lower():
                    key = k

        if key in keymaps.keys():
            from ..ops.gesture import GestureOperator
            k = keymaps[key]
            match_gesture_key = []
            match_origin_key = []
            for item in k.keymap_items:
                et = item.type == event.type
                if item.idname == GestureOperator.bl_idname and et:
                    match_gesture_key.append(item)
                elif item.idname in self.pass_through_idname and et:
                    match_origin_key.append(item)
            print(f"Try pass through keymap\t{GestureOperator.bl_idname}")
            print(f"\tMatch Key\t{match_gesture_key}")
            print(f"\tOrigin Key\t{[i.idname for i in match_origin_key]}")

            ml = len(match_origin_key)
            if ml == 1:
                try_operator_pass_through_right(match_origin_key[0])
            elif key == "Object Mode":
                if ml > 1 and match_origin_key[0].idname == "object.delete":
                    # 3D视图有两个删除事件
                    try_operator_pass_through_right(match_origin_key[0])
            elif key == "Outliner":  # 为大纲视图单独处理事件
                for m in match_origin_key:
                    ok = try_operator_pass_through_right(m)
                    if ok:
                        return

    @staticmethod
    def try_pass_annotations_eraser(context: bpy.types.Context, event: bpy.types.Event) -> set:
        """尝试跳过注释橡皮擦事件
        GESTURE_OT_operator     modal   PRESS   D       prev RIGHTMOUSE PRESS   get_key:
        GESTURE_OT_operator     modal   NOTHING MOUSEMOVE       prev D PRESS    get_key:
        GESTURE_OT_operator     modal   PRESS   D       prev D PRESS    get_key:
        """
        if context.space_data.type in ("VIEW_3D", "NODE_EDITOR") and context.active_annotation_layer:
            if (event.type, event.type_prev) in [
                ('D', 'RIGHTMOUSE'),
                ('RIGHTMOUSE', 'D'),
                ('MOUSEMOVE', 'D'),
                ('D', 'D')
            ]:
                return {'FINISHED', 'PASS_THROUGH'}


def try_operator_pass_through_right(kmi) -> bool:
    from ..utils.public_key import get_kmi_operator_properties
    try:
        sp = kmi.idname.split('.')
        prefix, suffix = sp
        func = getattr(getattr(bpy.ops, prefix), suffix)
        prop = get_kmi_operator_properties(kmi)
        if not func.poll():
            return False

        op_re = func('INVOKE_DEFAULT', True, **prop)
        print(f"\tcall {kmi.idname}\t{prop}\t{op_re}")
        return "FINISHED" in op_re or "CANCELLED" in op_re or "INTERFACE" in op_re
    except Exception as e:
        print(f"try_operator_pass_through_right Error\t{e.args}")
        return False
