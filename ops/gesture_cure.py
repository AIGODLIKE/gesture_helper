import json

import bpy
from bpy.app.translations import pgettext
from bpy.props import BoolProperty, EnumProperty

from ..gesture import GestureKeymap
from ..gesture.gesture_property import GESTURE_TYPE_ITEMS
from ..utils.public import (
    PublicOperator,
    poll_addon_preferences,
    poll_message_active_gesture,
)
from ..utils.pref_access import PrefAccess
from ..utils.active_selection import ActiveSelection
from ..utils.structure_cache_ops import StructureCacheOps


def _get_preset_sort_keys(filepath: str, is_example: bool) -> list[tuple[bool, bool]]:
    """Return source-group/type sort keys in the JSON import order."""
    with open(filepath, encoding='utf-8') as file:
        gesture_data = json.load(file).get('gesture', {})
    if not isinstance(gesture_data, dict):
        return []
    return [
        (not is_example, gesture.get('gesture_type') == 'MENU')
        for gesture in gesture_data.values()
        if isinstance(gesture, dict)
    ]


def _sort_imported_presets(gestures, start_index: int, sort_keys) -> bool:
    """Stably group new presets by source (example/normal) then runtime type."""
    sort_keys = list(sort_keys)
    if len(gestures) - start_index != len(sort_keys):
        return False

    did_move = False
    for target, sort_key in enumerate(sorted(sort_keys)):
        source = sort_keys.index(sort_key, target)
        if source != target:
            gestures.move(start_index + source, start_index + target)
            sort_keys.insert(target, sort_keys.pop(source))
            did_move = True
    return did_move


def add_all_preset():
    from ..utils.preset import (
        DEBUG_ONLY_PRESET_NAMES,
        get_preset_gesture_list,
    )
    from ..utils.gesture_store import get_gestures

    gestures = get_gestures()
    start_index = len(gestures) if gestures is not None else 0
    sort_keys = []
    count = 0
    for name, filepath in get_preset_gesture_list(
        include_debug_only=True,
    ).items():
        result = bpy.ops.wm.gesture_import(
            filepath=filepath,
            run_execute=True,
        )
        if 'FINISHED' in result:
            count += 1
            sort_keys.extend(
                _get_preset_sort_keys(
                    filepath,
                    name in DEBUG_ONLY_PRESET_NAMES,
                )
            )
    if gestures is not None and _sort_imported_presets(
        gestures,
        start_index,
        sort_keys,
    ):
        from ..utils.gesture_persistence import schedule_save_gestures_to_disk

        schedule_save_gestures_to_disk(description='after_bulk_preset_import')
    return count


class GestureCURE:
    """CRUD operations for gestures."""

    class GesturePoll(PublicOperator, PrefAccess, ActiveSelection, StructureCacheOps):

        @classmethod
        def poll(cls, _):
            return poll_message_active_gesture(cls)

    class ADD(PublicOperator, PrefAccess, ActiveSelection, StructureCacheOps):
        bl_idname = 'wm.gesture_add'
        bl_label = 'Add gesture'
        bl_description = (
            'Add a new gesture. '
            'Hold Ctrl+Alt+Shift while clicking to import every bundled preset, '
            'including examples'
        )
        bl_options = {'REGISTER'}

        gesture_type: EnumProperty(
            name='Type',
            description='Choose the runtime type for this new item',
            items=GESTURE_TYPE_ITEMS,
            default='RADIAL',
            options={'SKIP_SAVE'},
        )

        @classmethod
        def poll(cls, context):
            return poll_addon_preferences(cls)

        def invoke(self, context, event):
            if event.ctrl and event.alt and event.shift:
                count = add_all_preset()
                self.report({'INFO'}, pgettext("Imported %d presets") % count)
                return {'FINISHED'}
            return context.window_manager.invoke_props_dialog(self, width=260)

        def draw(self, _context):
            column = self.layout.column(align=True)
            column.label(text='Choose the type for the new item')
            column.prop(self, 'gesture_type', expand=True)
            column.separator()

            gesture_info = column.box()
            gesture_info.label(text='Gesture: drag in a direction to choose an action.')
            menu_info = column.box()
            menu_info.label(text='Menu: open a persistent menu at the cursor and click an item.')
            column.label(text='The type is fixed after creation.', icon='INFO')

        def execute(self, _):
            from ..utils.gesture_store import get_gesture_store, get_gestures
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None:
                return {'CANCELLED'}
            add = gestures.add()
            add.name = 'Menu' if self.gesture_type == 'MENU' else 'Gesture'
            add.gesture_type = self.gesture_type
            store.index_gesture = len(gestures) - 1
            GestureKeymap.key_restart()
            self.structure_changed(add)
            self.tag_redraw()
            return {'FINISHED'}

    class REMOVE(GesturePoll):
        bl_idname = 'wm.gesture_remove'
        bl_label = 'Remove gesture'
        bl_description = (
            'Remove the active gesture. '
            'Hold Ctrl+Alt+Shift while clicking to remove all gestures '
            '(confirmation required; cannot be undone)'
        )
        bl_options = {'REGISTER'}

        bulk_remove: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

        def invoke(self, context, event):
            from ..utils.adapter import operator_invoke_confirm
            if event.ctrl and event.alt and event.shift:
                self.bulk_remove = True
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Remove all gestures?",
                    message="This removes every gesture. This cannot be undone.",
                )
            self.bulk_remove = False
            if self.pref.draw_property.gesture_remove_tips:
                return operator_invoke_confirm(
                    self,
                    event,
                    context,
                    title="Delete this gesture?",
                    message=f"{self.active_gesture.name}",
                )
            return self.execute(context)

        def execute(self, _):
            from ..utils.gesture_store import get_gesture_store, get_gestures
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None:
                return {'CANCELLED'}
            if self.bulk_remove:
                gestures.clear()
                store.index_gesture = 0
                self.cache_clear()
                GestureKeymap.key_restart()
                self.bulk_remove = False
                return {'FINISHED'}
            pref = self.pref
            act = pref.active_gesture
            act.remove()
            act = pref.active_gesture
            if act:
                act.to_temp_kmi()
            self.cache_clear()
            GestureKeymap.key_restart()
            return {'FINISHED'}

    class SORT(GesturePoll):
        bl_idname = 'wm.gesture_sort'
        bl_label = 'Sort gesture'
        bl_description = 'Move the active gesture up or down in the list'
        bl_options = {'REGISTER'}

        is_next: BoolProperty()

        def execute(self, _):
            gesture = self.pref.active_gesture
            self.pref.active_gesture.sort(self.is_next)
            self.structure_changed(gesture)
            return {'FINISHED'}

    class COPY(GesturePoll):
        bl_idname = 'wm.gesture_copy'
        bl_label = 'Copy gesture'
        bl_description = 'Duplicate the active gesture and its elements'
        bl_options = {'REGISTER'}

        def execute(self, _):
            from ..utils.gesture_store import get_gesture_store, get_gestures
            source = self.active_gesture
            source_index = source.index_element if source and len(source.element) else 0
            source.copy()
            gestures = get_gestures()
            store = get_gesture_store()
            if gestures is None or store is None or not len(gestures):
                return {'CANCELLED'}
            new_gesture = gestures[-1]
            store.index_gesture = len(gestures) - 1
            self.structure_changed(new_gesture)
            new_gesture.__fix_duplicate_name__()
            if len(new_gesture.element):
                from ..utils.selection import enforce_single_selection

                idx = min(source_index, len(new_gesture.element) - 1)
                enforce_single_selection(new_gesture.element[idx])
            return {'FINISHED'}
