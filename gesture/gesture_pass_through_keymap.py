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

    area_map = {
        "VIEW_3D": "3D View",

        "IMAGE_EDITOR": "Image",
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

    image_ui_mode_map = {
        "VIEW": "Image",
        "PAINT": "Image Paint",
        "MASK": "Mask Editing",  # TODO 使用情况需确定
    }
    pass_through_ui_idname = (
        # 菜单
        'wm.call_menu',
        'wm.call_panel',
        'wm.call_menu_pie',
    )
    pass_through_idname = (
        *pass_through_ui_idname,
        'wm.context_toggle',
        'buttons.context_menu',  # 属性菜单

        'object.delete',  # 删除
        'outliner.operation',  # 大纲
        'object.move_to_collection',  # 集合

        'nla.tracks_add',
        'nla.actionclip_add',

        # 选择
        'view3d.localview',
        'view3d.select_circle',
        'view3d.select_box',
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
        'clip.graph_select_all_markers',
        'object.select_hierarchy',

        'wm.tool_set_by_id',  # w切换工具

        'view3d.edit_mesh_extrude_move_normal',
        'mesh.rip_move',
        'mesh.edge_face_add',
        'mesh.separate',
        'mesh.vert_connect_path',
        'mesh.split',
        'mesh.inset',
        'mesh.knife_tool',
        'mesh.select_linked_pick',
        'mesh.hide',

        'anim.keyframe_insert',
        'anim.keyframe_insert_menu',
        'object.hide_view_set',

        'transform.translate',
        'transform.rotate',
        'transform.resize',

        'transform.edge_crease',  # Shift+E
    )

    def from_region_get_keymaps(self, context):

        area_type = context.area.type
        region_type = context.region.type
        keymaps = context.window_manager.keyconfigs.active.keymaps

        view_type = getattr(context.space_data, "view_type", None)
        mode = getattr(context.space_data, "mode", None)
        view = getattr(context.space_data, "view", None)

        mk = self.area_map.get(area_type)

        keys = []
        if area_type == "VIEW_3D":
            keys.append("3D View Generic")
            keys.append(self.object_mode_map.get(context.mode))
        elif area_type == "SEQUENCE_EDITOR":
            sequence = self.sequence_map.get(view_type)
            if sequence is not None:
                keys.append(sequence)
            if view_type == "SEQUENCER_PREVIEW":
                keys.append(self.sequencer_preview_map.get(region_type))
        elif area_type == "CLIP_EDITOR":
            if mode == "TRACKING":
                t = self.tracking_map.get(view)
                if t is not None:
                    keys.append(t)
            elif mode == "MASK":
                keys.append("Clip Editor")
        elif area_type == "IMAGE_EDITOR":
            # 图片或是UV
            ut = context.area.ui_type
            ui_mode = getattr(context.space_data, "ui_mode", None)
            if ut == "UV":
                keys.append("UV Editor")
            elif ut == "IMAGE_EDITOR":
                if ui_mode and ui_mode in self.image_ui_mode_map:
                    keys.append(self.image_ui_mode_map.get(ui_mode))
            keys.append("Image Generic")
            print(ut, ui_mode)
        if mk is not None:
            keys.append(mk)
        else:
            for k in keymaps.keys():
                if k.lower() == context.mode.lower():
                    keys.append(k)

        keys.append("Window")
        return keys

    def get_keymaps(self, context):
        pref = self.pref
        region_keys = self.from_region_get_keymaps(context)
        if pref.gesture_property.pass_through_keymap_type == "REGION":
            return region_keys
        return [key for key in self.operator_gesture.keymaps if key in region_keys]

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        """尝试透传按键事件
        :param context:bpy.types.Ccontext
        :param event:bpy.types.Event
        :return:None
        NODE_EDITOR
        IMAGE_EDITOR
        """
        keys = self.get_keymaps(context)

        kc = context.window_manager.keyconfigs
        keymaps = kc.active.keymaps

        print("try_pass_through_keymap keys", keys)
        user_keymaps = kc.user.keymaps
        # print(f"event\t{keys}\t", event.type, event.shift, event.ctrl, event.alt, self.event_count)
        for key in keys:
            if key in keymaps.keys():
                km = keymaps[key]

                match_kmis = []  # 匹配到的快捷键列表
                for item in km.keymap_items:
                    et = item.type == event.type
                    if item.idname in self.pass_through_idname and et and item.active:
                        if (
                                bool(item.shift) == event.shift and
                                bool(item.ctrl) == event.ctrl and
                                bool(item.alt) == event.alt
                        ):
                            match_kmis.append(item)
                ml = len(match_kmis)

                # 搜索查看用户是否自已改了快捷键,如果改了快捷键将会出现在keymaps.user
                if key in user_keymaps:
                    for index, match_kmi in enumerate(match_kmis):
                        for kmi in user_keymaps[key].keymap_items:
                            props_ok = get_kmi_operator_properties(kmi) == get_kmi_operator_properties(match_kmi)
                            if kmi.idname == match_kmi.idname and props_ok:
                                if kmi.is_user_modified:
                                    # print("找到一个被用户改了的快捷键来替换", kmi)
                                    match_kmis[index] = kmi

                if ml == 1:  # 只匹配到一个键
                    kmi = match_kmis[0]
                    if kmi.active:  # 只有当快捷键启用时才处理
                        if self.try_pass_set_cursor3d_location(context, event, kmi):
                            # print("shift右键鼠标单击 设置游标处理")
                            return
                        ok = try_operator_pass_through_right(kmi)
                        if ok:
                            # print(f"Try pass through keymap\t{GestureOperator.bl_idname}")
                            # print(f"Origin Key\t{key}\t{kmi.idname}", ok)
                            return
                elif key in (
                        "Object Mode",
                        "Mesh",
                        "Outliner",  # 为大纲视图单独处理事件
                ):
                    # 以下都是有多个操作符的
                    #         "object.delete",
                    #         "object.select_all",
                    #         "mesh.select_all",
                    for kmi in match_kmis:
                        if kmi.active:
                            ok = try_operator_pass_through_right(kmi)
                            if ok:
                                # print(f"Try pass through keymap\t{GestureOperator.bl_idname}")
                                # print(f"Origin Key\t{key}\t{kmi.idname}", ok)
                                return
                else:
                    print(f"else\t{key}\t{[i.idname for i in match_kmis]}")

    @staticmethod
    def try_pass_annotations_eraser(context: bpy.types.Context, event: bpy.types.Event) -> set | None:
        """尝试跳过注释橡皮擦事件
        GESTURE_OT_operator     modal   PRESS   D       prev RIGHTMOUSE PRESS   get_key:
        GESTURE_OT_operator     modal   NOTHING MOUSEMOVE       prev D PRESS    get_key:
        GESTURE_OT_operator     modal   PRESS   D       prev D PRESS    get_key:
        """
        if context.space_data and context.space_data.type in ("VIEW_3D", "NODE_EDITOR"):
            if context.active_annotation_layer:
                if (event.type, event.type_prev) in [
                    ('D', 'RIGHTMOUSE'),
                    ('RIGHTMOUSE', 'D'),
                    ('MOUSEMOVE', 'D'),
                    ('D', 'D')
                ]:
                    return {'FINISHED', 'PASS_THROUGH'}
        return None

    @staticmethod
    def try_pass_paint_texture_stencil(context: bpy.types.Context, event: bpy.types.Event) -> set | None:
        """尝试跳过纹理绘制镂板事件
        GESTURE_OT_operator     modal   PRESS   D       prev RIGHTMOUSE PRESS   get_key:
        GESTURE_OT_operator     modal   NOTHING MOUSEMOVE       prev D PRESS    get_key:
        GESTURE_OT_operator     modal   PRESS   D       prev D PRESS    get_key:
        """
        from bl_ui.properties_paint_common import UnifiedPaintPanel

        settings = UnifiedPaintPanel.paint_settings(context)
        brush = getattr(settings, "brush", None)
        if context.space_data and context.space_data.type == "VIEW_3D":
            if context.mode == "PAINT_TEXTURE" and brush:
                ts = getattr(brush, "texture_slot", None)
                if ts and getattr(ts, "map_mode", None) == "STENCIL":
                    if event.type == "RIGHTMOUSE":
                        return {'FINISHED', 'PASS_THROUGH'}
        return None

    def try_pass_set_cursor3d_location(self, context: bpy.types.Context, event: bpy.types.Event,
                                       kmi: bpy.types.KeyMapItem) -> bool:
        """尝试透传设置3D视图的鼠标位置"""
        if (
                event.shift and
                not event.ctrl and
                not event.alt and
                event.type_prev == "RIGHTMOUSE" and
                self.move_count <= 2 and
                kmi.idname == "transform.translate"
        ):
            if get_kmi_operator_properties(kmi) == {'release_confirm': True, 'cursor_transform': True}:
                # shift右键鼠标单击
                if context.area.type == "VIEW_3D":
                    bpy.ops.view3d.cursor3d('INVOKE_DEFAULT', True)
                    return True


def check_kmi_pass_through(kmi: bpy.types.KeyMapItem) -> bool:
    # idname = kmi.idname
    # if idname in GesturePassThroughKeymap.pass_through_ui_idname:
    #     prop = get_kmi_operator_properties(kmi)
    #     if "name" in prop:
    #         name = prop["name"]
    #         draw_cls = getattr(bpy.types, name, None)
    #         # 如果能找到则说明这个是系统的绘制方法
    #         if draw_cls is None:
    #             return False
    #         return draw_cls.poll()
    #     else:
    #         return False
    # getattr(bpy.types, "VIEW3D_MT_edit_mesh_delete", None)
    # TODO("删除键如果在物体模式下没有这个键位，那么在物体模式下会显示编辑模式的菜单,这个是由MP7引发的问题,MP7有替换删除快捷键")

    prefix, suffix = kmi.idname.split('.')
    func = getattr(getattr(bpy.ops, prefix), suffix)
    if not func.poll():
        return False
    return True


def try_operator_pass_through_right(kmi: bpy.types.KeyMapItem, operator_context='INVOKE_DEFAULT') -> bool:
    """尝试穿透操作符,如果穿透了反回Ture"""
    try:
        if not check_kmi_pass_through(kmi):
            return False

        sp = kmi.idname.split('.')
        prefix, suffix = sp
        func = getattr(getattr(bpy.ops, prefix), suffix)

        prop = get_kmi_operator_properties(kmi)
        op_re = func(operator_context, True, **prop)
        print(f"\tcall {kmi.idname}\t{prop}\t{op_re}")
        # import traceback
        # traceback.print_stack()
        return "FINISHED" in op_re or "CANCELLED" in op_re or "INTERFACE" in op_re
    except Exception as e:
        print(f"try_operator_pass_through_right Error\t{e.args}")
        import traceback
        traceback.print_exc()
        traceback.print_stack()
        return False
