import bpy

from .addon_keymap import get_kmi_operator_properties
from ..utils.debug_util import debug_print


_VIEW3D_CONTEXT_MENUS = {
    'OBJECT': 'VIEW3D_MT_object_context_menu',
    'EDIT_MESH': 'VIEW3D_MT_edit_mesh_context_menu',
    'EDIT_CURVE': 'VIEW3D_MT_edit_curve_context_menu',
    'EDIT_SURFACE': 'VIEW3D_MT_edit_curve_context_menu',
    'EDIT_CURVES': 'VIEW3D_MT_edit_curves_context_menu',
    'SCULPT_CURVES': 'VIEW3D_MT_sculpt_curves_context_menu',
    'EDIT_ARMATURE': 'VIEW3D_MT_armature_context_menu',
    'POSE': 'VIEW3D_MT_pose_context_menu',
    'SCULPT': 'VIEW3D_MT_sculpt_context_menu',
    'PAINT_WEIGHT': 'VIEW3D_MT_paint_weight_context_menu',
    'PAINT_VERTEX': 'VIEW3D_MT_paint_vertex_context_menu',
    'PAINT_TEXTURE': 'VIEW3D_MT_paint_texture_context_menu',
    'PARTICLE': 'VIEW3D_MT_particle_context_menu',
    'EDIT_METABALL': 'VIEW3D_MT_edit_metaball_context_menu',
    'EDIT_LATTICE': 'VIEW3D_MT_edit_lattice_context_menu',
    'EDIT_TEXT': 'VIEW3D_MT_edit_font_context_menu',
}


def _kmi_matches_event(event, kmi, ui_idnames) -> bool:
    event_type = event.type
    kmi_type = kmi.type
    if event_type != kmi_type:
        if not (event_type in {'RIGHTMOUSE', 'APP'} and kmi_type in {'RIGHTMOUSE', 'APP'}):
            return False

    if not kmi.any:
        if bool(kmi.shift) != event.shift:
            return False
        if bool(kmi.ctrl) != event.ctrl:
            return False
        if bool(kmi.alt) != event.alt:
            return False
        if bool(getattr(kmi, 'oskey', False)) != bool(getattr(event, 'oskey', False)):
            return False

    if kmi.value not in {'NOTHING', 'ANY'} and event.value != kmi.value:
        if not (
                kmi.idname in ui_idnames
                and event_type in {'RIGHTMOUSE', 'APP'}
                and event.value == 'RELEASE'
                and kmi.value == 'PRESS'
        ):
            return False
    return True


def _match_kmis_in_keymap(km, event, pass_through_idname, ui_idnames):
    active = []
    inactive_ui = []
    for item in km.keymap_items:
        if item.idname not in pass_through_idname:
            continue
        if not _kmi_matches_event(event, item, ui_idnames):
            continue
        if item.active:
            active.append(item)
        elif item.idname in ui_idnames:
            inactive_ui.append(item)
    return active if active else inactive_ui


def _expected_view3d_menu(context) -> str | None:
    area = context.area
    if area is None or area.type != 'VIEW_3D':
        return None
    return _VIEW3D_CONTEXT_MENUS.get(context.mode)


def _filter_view3d_menu_kmis(context, match_kmis):
    """Keep only the context menu that matches the current 3D View mode."""
    expected = _expected_view3d_menu(context)
    if not expected:
        return match_kmis

    call_menus = [kmi for kmi in match_kmis if kmi.idname == 'wm.call_menu']
    if not call_menus:
        return match_kmis

    matched = [
        kmi for kmi in call_menus
        if get_kmi_operator_properties(kmi).get('name') == expected
    ]
    if matched:
        return matched

    # Ignore unrelated wm.call_menu items such as DOPESHEET_MT_channel_context_menu.
    other = [kmi for kmi in match_kmis if kmi.idname != 'wm.call_menu']
    return other


def _apply_user_keymap_overrides(match_kmis, key, user_keymaps):
    if key not in user_keymaps or not match_kmis:
        return match_kmis
    for index, match_kmi in enumerate(match_kmis):
        for kmi in user_keymaps[key].keymap_items:
            props_ok = get_kmi_operator_properties(kmi) == get_kmi_operator_properties(match_kmi)
            if kmi.idname == match_kmi.idname and props_ok and kmi.is_user_modified:
                match_kmis[index] = kmi
    return match_kmis


class GesturePassThroughKeymap:
    _ESSENTIAL_PASS_THROUGH_KEYMAPS = frozenset({
        "Window",
        "3D View",
        "3D View Generic",
    })
    _MULTI_MATCH_KEYMAPS = frozenset({
        "Window",
        "3D View",
        "3D View Generic",
        "Object Mode",
        "Mesh",
        "Curve",
        "Curves",
        "Sculpt Curves",
        "Armature",
        "Pose",
        "Metaball",
        "Font",
        "Lattice",
        "Outliner",
    })

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
        "EDIT_CURVES": "Curves",
        "SCULPT_CURVES": "Sculpt Curves",
        "POSE": "Pose",
        "PARTICLE": "Particle",

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
        "TEXT_EDITOR": "Text",  # Text editor
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
        "MASK": "Mask Editing",  # TODO: usage needs confirmation
    }
    pass_through_ui_idname = (
        # Menus
        'wm.call_menu',
        'wm.call_panel',
        'wm.call_menu_pie',
        'wm.call_menu_pie_drag_only',
    )
    pass_through_idname = (
        *pass_through_ui_idname,
        'wm.context_toggle',
        'buttons.context_menu',  # Property context menu

        'object.delete',  # Delete
        'outliner.operation',  # Outliner
        'object.move_to_collection',  # Collection

        'nla.tracks_add',
        'nla.actionclip_add',

        # Selection
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

        'wm.tool_set_by_id',  # W key tool switch

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
        # Read-only: inspect active keymaps for pass-through, never modify them.
        keymaps = context.window_manager.keyconfigs.active.keymaps

        view_type = getattr(context.space_data, "view_type", None)
        mode = getattr(context.space_data, "mode", None)
        view = getattr(context.space_data, "view", None)

        mk = self.area_map.get(area_type)

        keys = []
        if area_type == "VIEW_3D":
            keys.append("3D View Generic")
            mode_key = self.object_mode_map.get(context.mode)
            if mode_key:
                keys.append(mode_key)
            else:
                obj = context.object
                if obj and obj.type == "CURVES":
                    keys.append("Curves")
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
            # Image or UV editor
            ut = context.area.ui_type
            ui_mode = getattr(context.space_data, "ui_mode", None)
            if ut == "UV":
                keys.append("UV Editor")
            elif ut == "IMAGE_EDITOR":
                if ui_mode and ui_mode in self.image_ui_mode_map:
                    keys.append(self.image_ui_mode_map.get(ui_mode))
            keys.append("Image Generic")
            debug_print(ut, ui_mode, key='key')
        if mk is not None:
            keys.append(mk)
        else:
            for k in keymaps.keys():
                if k.lower() == context.mode.lower():
                    keys.append(k)

        keys.append("Window")
        return [key for key in keys if key]

    def get_keymaps(self, context, event=None):
        pref = self.pref
        region_keys = self.from_region_get_keymaps(context)
        if pref.gesture_property.pass_through_keymap_type == "REGION":
            return region_keys

        gesture_keys = [key for key in self.operator_gesture.keymaps if key in region_keys]
        # Context menus usually live in Window / 3D View even when the gesture
        # only enables a mode keymap such as Curve or Mesh.
        if event is not None and event.type in {'RIGHTMOUSE', 'APP'}:
            return list(dict.fromkeys(gesture_keys + region_keys))

        essential = [key for key in region_keys if key in self._ESSENTIAL_PASS_THROUGH_KEYMAPS]
        return list(dict.fromkeys(gesture_keys + essential))

    def _try_pass_matched_kmis(self, context, event, match_kmis) -> bool:
        if not match_kmis:
            return False

        match_kmis = _filter_view3d_menu_kmis(context, match_kmis)
        if not match_kmis:
            return False

        ui_kmis = [kmi for kmi in match_kmis if kmi.idname in self.pass_through_ui_idname]
        candidates = ui_kmis if ui_kmis else match_kmis
        for kmi in candidates:
            if not (kmi.active or kmi.idname in self.pass_through_ui_idname):
                continue
            if self.try_pass_set_cursor3d_location(context, event, kmi):
                return True
            if try_operator_pass_through_right(kmi):
                return True
        return False

    def _try_pass_keymap_list(self, context, event, keys, keymaps, user_keymaps) -> bool:
        ui_idnames = self.pass_through_ui_idname
        for key in keys:
            if key not in keymaps.keys():
                continue
            km = keymaps[key]
            match_kmis = _match_kmis_in_keymap(km, event, self.pass_through_idname, ui_idnames)
            match_kmis = _apply_user_keymap_overrides(match_kmis, key, user_keymaps)
            if not match_kmis:
                continue
            debug_print("try_pass_through_keymap match", key, [i.idname for i in match_kmis], key='key')
            if self._try_pass_matched_kmis(context, event, match_kmis):
                return True
            if key not in self._MULTI_MATCH_KEYMAPS:
                debug_print(f"else\t{key}\t{[i.idname for i in match_kmis]}", key='key')
        return False

    @staticmethod
    def _try_view3d_context_menu(context) -> bool:
        area = context.area
        if area is None or area.type != 'VIEW_3D':
            return False
        menu_name = _VIEW3D_CONTEXT_MENUS.get(context.mode)
        if not menu_name:
            return False
        try:
            result = bpy.ops.wm.call_menu('INVOKE_DEFAULT', name=menu_name)
            debug_print("try_view3d_context_menu", menu_name, result, key='key')
            return bool({'FINISHED', 'INTERFACE'} & set(result))
        except Exception as e:
            debug_print("try_view3d_context_menu Error", menu_name, e.args, key='key')
            return False

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> bool:
        """Try to pass through key events."""
        if event.type in {'RIGHTMOUSE', 'APP'} and _expected_view3d_menu(context):
            if self._try_view3d_context_menu(context):
                return True

        keys = self.get_keymaps(context, event)

        kc = context.window_manager.keyconfigs
        keymaps = kc.active.keymaps

        debug_print("try_pass_through_keymap keys", keys, key='key')
        user_keymaps = kc.user.keymaps
        if self._try_pass_keymap_list(context, event, keys, keymaps, user_keymaps):
            return True

        if event.type in {'RIGHTMOUSE', 'APP'} and _expected_view3d_menu(context):
            return self._try_view3d_context_menu(context)
        return False

    @staticmethod
    def try_pass_annotations_eraser(context: bpy.types.Context, event: bpy.types.Event) -> set | None:
        """Try to skip annotation eraser events
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
        """Try to skip texture paint stencil events
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
        """Try to pass through 3D view cursor placement."""
        if (
                event.shift and
                not event.ctrl and
                not event.alt and
                event.type_prev == "RIGHTMOUSE" and
                self.move_count <= 2 and
                kmi.idname == "transform.translate"
        ):
            if get_kmi_operator_properties(kmi) == {'release_confirm': True, 'cursor_transform': True}:
                # Shift+right-click
                if context.area.type == "VIEW_3D":
                    bpy.ops.view3d.cursor3d('INVOKE_DEFAULT', True)
                    return True


def check_kmi_pass_through(kmi: bpy.types.KeyMapItem, *, skip_ui_poll=False) -> bool:
    if skip_ui_poll and kmi.idname in GesturePassThroughKeymap.pass_through_ui_idname:
        return True
    prefix, suffix = kmi.idname.split('.')
    func = getattr(getattr(bpy.ops, prefix), suffix)
    if not func.poll():
        return False
    return True


def try_operator_pass_through_right(
        kmi: bpy.types.KeyMapItem,
        operator_context='INVOKE_DEFAULT',
        ui_idnames=GesturePassThroughKeymap.pass_through_ui_idname,
) -> bool:
    """Try to pass through operator; returns True if pass-through succeeded."""
    try:
        skip_ui_poll = kmi.idname in ui_idnames
        if not check_kmi_pass_through(kmi, skip_ui_poll=skip_ui_poll):
            debug_print("pass_through poll failed", kmi.idname, key='key')
            return False

        sp = kmi.idname.split('.')
        prefix, suffix = sp
        func = getattr(getattr(bpy.ops, prefix), suffix)

        prop = get_kmi_operator_properties(kmi)
        op_re = func(operator_context, True, **prop)
        debug_print(f"\tcall {kmi.idname}\t{prop}\t{op_re}", key='key')
        return "FINISHED" in op_re or "CANCELLED" in op_re or "INTERFACE" in op_re
    except Exception as e:
        debug_print(f"try_operator_pass_through_right Error\t{e.args}", key='key')
        import traceback
        traceback.print_exc()
        traceback.print_stack()
        return False
