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
    'EDIT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'SCULPT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'PAINT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
    'WEIGHT_GREASE_PENCIL': 'VIEW3D_MT_greasepencil_edit_context_menu',
}


def _screen_contains_area(screen, area) -> bool:
    """Check whether *screen* still contains *area* (Blender 5.x safe)."""
    if screen is None or area is None:
        return False
    try:
        area_ptr = area.as_pointer()
    except ReferenceError:
        return False
    for candidate in screen.areas:
        try:
            if candidate.as_pointer() == area_ptr:
                return True
        except ReferenceError:
            continue
    return False


def _find_window_for_area(area):
    """Return the window that contains *area* (works on Blender 4.x and 5.x)."""
    if area is None:
        return None
    wm = getattr(bpy.context, 'window_manager', None)
    if wm is None:
        return getattr(bpy.context, 'window', None)
    for window in wm.windows:
        if _screen_contains_area(window.screen, area):
            return window
    return None


def _area_is_valid(area) -> bool:
    if area is None:
        return False
    try:
        _ = area.type
    except ReferenceError:
        return False

    screen = getattr(area, 'screen', None)
    if screen is not None:
        return _screen_contains_area(screen, area)

    return _find_window_for_area(area) is not None


def _window_region(area):
    for region in area.regions:
        if region.type == 'WINDOW':
            return region
    return None


def _defer_operator_call(
        context,
        area,
        idname: str,
        properties: dict | None = None,
        *,
        operator_context: str = 'INVOKE_DEFAULT',
) -> bool:
    """Schedule operator invocation after the modal handler finishes."""
    window = None
    region = None
    if area is not None and _area_is_valid(area):
        window = _find_window_for_area(area)
        region = _window_region(area)
    if window is None:
        window = getattr(context, 'window', None)
    if region is None and getattr(context, 'region', None) is not None:
        region = context.region
    if window is None:
        return False

    properties = dict(properties or {})
    prefix, suffix = idname.split('.', 1)

    def _invoke(*_args):
        try:
            func = getattr(getattr(bpy.ops, prefix), suffix)
            override = {'window': window}
            if area is not None and _area_is_valid(area):
                override['area'] = area
            if region is not None:
                try:
                    # Region may be invalid after layout changes.
                    _ = region.type
                    override['region'] = region
                except ReferenceError:
                    ...
            with context.temp_override(**override):
                result = func(operator_context, True, **properties)
            debug_print(f"deferred {idname}", properties, result, key='key')
        except Exception as exc:
            debug_print(f"deferred {idname} error", exc.args, key='key')
        return None

    bpy.app.timers.register(_invoke, first_interval=0)
    return True


# Operators that open a window / UI while the gesture modal is still on the stack
# leave the gesture "stuck" until the new window closes. Defer these until after exit.
_DEFER_GESTURE_OPERATOR_IDNAMES = frozenset({
    'screen.userpref_show',
    'wm.call_menu',
    'wm.call_panel',
    'wm.call_menu_pie',
    'wm.call_menu_pie_drag_only',
    'wm.search_menu',
    'wm.search_operator',
    'wm.search_single_menu',
    'preferences.addon_show',
})


def should_defer_gesture_operator(idname: str) -> bool:
    """Return True if *idname* should run after the gesture modal exits."""
    if not idname:
        return False
    if idname in _DEFER_GESTURE_OPERATOR_IDNAMES:
        return True
    # Any call_* UI helper tends to return INTERFACE and nest under the gesture.
    if idname.startswith('wm.call_'):
        return True
    return False


def defer_gesture_element_operator(context, area, element) -> bool:
    """Defer a gesture element operator until after the modal returns FINISHED."""
    from ..element.element_operator import resolve_operator_bl_idname

    idname = resolve_operator_bl_idname(getattr(element, 'operator_bl_idname', '') or '')
    if not idname or '.' not in idname:
        return False
    props = getattr(element, 'properties', None)
    if not isinstance(props, dict):
        props = {}
    op_context = getattr(element, 'operator_context', None) or 'INVOKE_DEFAULT'
    return _defer_operator_call(
        context,
        area,
        idname,
        props,
        operator_context=op_context,
    )


def _defer_context_menu(context, area, menu_name: str) -> bool:
    return _defer_operator_call(context, area, 'wm.call_menu', {'name': menu_name})


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

    sequencer_preview_map = {
        "PREVIEW": "SequencerPreview",
        "WINDOW": "Sequencer",
    }

    tracking_map = {
        "CLIP": "Clip Editor",
        "GRAPH": "Clip Graph Editor",
        "DOPESHEET": "Clip Dopesheet Editor",
    }

    image_ui_mode_map = {
        "VIEW": "Image",
        "PAINT": "Image Paint",
        "MASK": "Mask Editing",
    }
    pass_through_ui_idname = (
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

    def _collect_pass_kmis(self, context, event, keys, keymaps, user_keymaps):
        ui_idnames = self.pass_through_ui_idname
        matched = []
        for key in keys:
            if key not in keymaps:
                continue
            km = keymaps[key]
            match_kmis = _match_kmis_in_keymap(km, event, self.pass_through_idname, ui_idnames)
            match_kmis = _apply_user_keymap_overrides(match_kmis, key, user_keymaps)
            if match_kmis:
                debug_print("try_pass_through_keymap match", key, [i.idname for i in match_kmis], key='key')
                matched.extend(match_kmis)
        return _filter_view3d_menu_kmis(context, matched) if matched else []

    def _defer_pass_matched_kmis(self, context, area, event, match_kmis) -> bool:
        if not match_kmis:
            return False

        ui_kmis = [kmi for kmi in match_kmis if kmi.idname in self.pass_through_ui_idname]
        candidates = ui_kmis if ui_kmis else match_kmis
        for kmi in candidates:
            if not (kmi.active or kmi.idname in self.pass_through_ui_idname):
                continue
            if self.try_pass_set_cursor3d_location(context, event, kmi, area):
                return True
            if defer_kmi_pass_through(context, area, kmi):
                return True
        return False

    def try_pass_through_keymap(self, context: bpy.types.Context, event: bpy.types.Event) -> str | None:
        """Try to pass through key events.

        Returns:
            ``'handled'`` when a deferred menu/operator was scheduled,
            ``'pass_through'`` when the event should be forwarded to Blender,
            ``None`` when nothing should happen.
        """
        gesture_area = getattr(self, 'area', None) or context.area
        is_rmb = event.type in {'RIGHTMOUSE', 'APP'}

        keys = self.get_keymaps(context, event)
        kc = context.window_manager.keyconfigs
        debug_print("try_pass_through_keymap keys", keys, key='key')
        match_kmis = self._collect_pass_kmis(context, event, keys, kc.active.keymaps, kc.user.keymaps)

        if is_rmb:
            if self._defer_pass_matched_kmis(context, gesture_area, event, match_kmis):
                return 'handled'

            menu_name = None
            if _area_is_valid(gesture_area) and gesture_area.type == 'VIEW_3D':
                menu_name = _VIEW3D_CONTEXT_MENUS.get(context.mode)

            if menu_name and _defer_context_menu(context, gesture_area, menu_name):
                debug_print("try_pass_through_keymap deferred menu", menu_name, key='key')
                return 'handled'

            if gesture_area is not None:
                debug_print("try_pass_through_keymap fallback PASS_THROUGH", gesture_area.type, key='key')
                return 'pass_through'
            return None

        if match_kmis and self._defer_pass_matched_kmis(context, gesture_area, event, match_kmis):
            return 'handled'
        return None

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
                                       kmi: bpy.types.KeyMapItem, area=None) -> bool:
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
                target_area = area or context.area
                if target_area and target_area.type == "VIEW_3D":
                    return _defer_operator_call(context, target_area, 'view3d.cursor3d', {})
        return False


def check_kmi_pass_through(kmi: bpy.types.KeyMapItem, *, skip_ui_poll=False) -> bool:
    if skip_ui_poll and kmi.idname in GesturePassThroughKeymap.pass_through_ui_idname:
        return True
    prefix, suffix = kmi.idname.split('.')
    func = getattr(getattr(bpy.ops, prefix), suffix)
    if not func.poll():
        return False
    return True


def defer_kmi_pass_through(
        context,
        area,
        kmi: bpy.types.KeyMapItem,
        ui_idnames=GesturePassThroughKeymap.pass_through_ui_idname,
) -> bool:
    """Schedule pass-through operator after modal ends; returns True if scheduled."""
    skip_ui_poll = kmi.idname in ui_idnames
    if not check_kmi_pass_through(kmi, skip_ui_poll=skip_ui_poll):
        debug_print("pass_through poll failed", kmi.idname, key='key')
        return False
    prop = get_kmi_operator_properties(kmi)
    return _defer_operator_call(context, area, kmi.idname, prop)


def try_operator_pass_through_right(
        kmi: bpy.types.KeyMapItem,
        operator_context='INVOKE_DEFAULT',
        ui_idnames=GesturePassThroughKeymap.pass_through_ui_idname,
) -> bool:
    """Try to pass through operator synchronously (non-modal use only)."""
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
