# Import dialog shows preset options
import json
import os
import time
from datetime import datetime

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..gesture import GestureKeymap
from ..ui.ui_list import ImportPresetUIList
from ..utils.property import __set_prop__
from ..utils.backups import (
    blender_close_backup_filename,
    close_backup_filename,
    log_backup,
    PREFERENCES_EXPORT_EXTENSION,
    PREFERENCES_LEGACY_EXTENSION,
    resolve_backups_folder,
)
from ..utils.public import (
    PublicOperator,
    PublicProperty,
    get_pref,
    debug_print,
    poll_addon_preferences,
)
from ..utils.pref_access import PrefAccess
from ..utils.structure_cache_ops import StructureCacheOps
from ..utils.public_cache import cache_update_lock

EXPORT_PROPERTY_EXCLUDE = (
    'selected',
    'relationship',
    'show_child',
    'level',
    'index_element',
    'operator_properties_sync_to_properties',
    'operator_properties_sync_from_temp_properties',
)


EXPORT_ICON_ITEM = ['icon', 'enabled_icon']
EXPORT_PUBLIC_ITEM = ['name', 'element_type', 'enabled', 'description']
EXPORT_PROPERTY_ITEM = {
    'SELECTED_STRUCTURE': [*EXPORT_PUBLIC_ITEM, 'selected_type', 'poll_string'],
    'CHILD_GESTURE': [*EXPORT_PUBLIC_ITEM, *EXPORT_ICON_ITEM, 'direction'],
    'OPERATOR_MODAL': [
        *EXPORT_PUBLIC_ITEM,
        *EXPORT_ICON_ITEM,
        'modal_events',
        'modal_events_index',
        'control_property',
        'number_value_mode',
        'float_incremental_value',
        'float_value',
        'int_incremental_value',
        'int_value',
        'bool_value_mode',
        'enum_value_mode',
        'enum_value_a',
        'enum_value_b',
        'enum_reverse',
        'enum_wrap',
        'event_type',
        'event_ctrl',
        'event_alt',
        'operator_bl_idname',
        'operator_context',
        'operator_properties',
        'event_shift',
        'direction', 'operator_type'],
    'OPERATOR_OPERATOR': [
        *EXPORT_PUBLIC_ITEM,
        *EXPORT_ICON_ITEM,
        'direction', 'operator_bl_idname', 'operator_context', 'operator_properties', ],
    "DIVIDING_LINE": [*EXPORT_PUBLIC_ITEM]
}


def _is_legacy_script_element(element: dict) -> bool:
    return element.get('operator_type') == 'SCRIPT' or bool(element.get('operator_script'))


def _remove_legacy_script_from_tree(elements: dict) -> None:
    remove_keys = []
    for key, element in elements.items():
        nested = element.get('element')
        if nested:
            _remove_legacy_script_from_tree(nested)
        if _is_legacy_script_element(element):
            debug_print(
                f"Gesture Helper: removed legacy SCRIPT element "
                f"'{element.get('name', 'Unknown')}'",
                key='export_import',
            )
            remove_keys.append(key)
    for key in remove_keys:
        del elements[key]


def _migrate_legacy_operator_ids_in_tree(elements: dict) -> None:
    from ..element.element_operator import migrate_legacy_operator_bl_idname

    for element in elements.values():
        nested = element.get('element')
        if nested:
            _migrate_legacy_operator_ids_in_tree(nested)
        old_id = element.get('operator_bl_idname')
        if not old_id:
            continue
        new_id = migrate_legacy_operator_bl_idname(old_id)
        if new_id != old_id:
            element['operator_bl_idname'] = new_id
            debug_print(
                f"Gesture Helper: migrated operator_bl_idname "
                f"'{old_id}' -> '{new_id}'",
                key='export_import',
            )


def sanitize_gesture_import_data(gesture_data: dict) -> dict:
    """Remove legacy SCRIPT elements, migrate operator ids, strip radio flags."""
    from ..utils.selection import strip_radio_from_copy_data

    for gesture in gesture_data.values():
        elements = gesture.get('element')
        if elements:
            _remove_legacy_script_from_tree(elements)
            _migrate_legacy_operator_ids_in_tree(elements)
            for child in elements.values():
                strip_radio_from_copy_data(child)
    return gesture_data


class PublicFileOperator(PublicOperator, PrefAccess, StructureCacheOps):
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={'HIDDEN', 'SKIP_SAVE'}, )
    preset_show: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'}, )
    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    run_execute: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}, )

    def __get_all__(self):
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None or not len(gestures):
            return False
        return all((i.selected for i in gestures))

    def __set_all__(self, value):
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None:
            return
        for i in gestures:
            i.selected = value

    selected_all: BoolProperty(name='Select all', get=__get_all__, set=__set_all__)

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def invoke(self, context, _):
        if self.run_execute:
            return self.execute(context)
        elif self.preset_show:
            wm = context.window_manager
            return wm.invoke_props_dialog(**{'operator': self, 'width': 300})
        else:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}


class Import(PublicFileOperator):
    bl_label = 'Import gesture'
    bl_idname = 'wm.gesture_import'
    bl_description = 'Import gesture presets from a JSON file or bundled examples'
    @property
    def preset_items(self):
        from ..utils.preset import get_preset_gesture_list
        return get_preset_gesture_list()

    def execute(self, _):
        if self.preset_show:
            return {'FINISHED'}
        if not self.gesture_import():
            return {'CANCELLED'}
        self.cache_clear()
        from ..utils.public import PublicProperty
        PublicProperty.update_state()
        GestureKeymap.key_restart()
        from ..utils.gesture_persistence import (
            cancel_scheduled_gesture_save,
            save_gestures_to_disk,
        )

        cancel_scheduled_gesture_save()
        path = save_gestures_to_disk(description='after_import')
        if not path:
            from bpy.app.translations import pgettext
            self.report(
                {'WARNING'},
                pgettext("Imported to memory; gesture file write failed"),
            )
        return {'FINISHED'}

    def draw(self, _):
        layout = self.layout
        row = layout.row()

        row.label(text='Import preset')
        column = layout.column(align=True)

        for k, v in self.preset_items.items():
            ops = column.operator(self.bl_idname, text=PublicProperty.__tp__(k))
            ops.filepath = v
            ops.run_execute = True
            ops.preset_show = False

    @cache_update_lock
    def gesture_import(self) -> bool:
        try:
            from ..gesture import gesture_keymap

            from ..utils.selection import suppress_radio_updates

            data = self.read_json()
            if not isinstance(data, dict) or 'gesture' not in data:
                raise ValueError("Invalid gesture file: missing 'gesture' data")
            restore = sanitize_gesture_import_data(data['gesture'])
            if not isinstance(restore, dict):
                raise ValueError("Invalid gesture file: 'gesture' must be an object")
            with suppress_radio_updates():
                from ..utils.gesture_store import get_gesture_store
                store = get_gesture_store()
                if store is None:
                    raise RuntimeError("Gesture store unavailable")
                __set_prop__(store, 'gesture', restore)
            from ..gesture.gesture_relationship import get_gesture_index
            get_gesture_index.cache_clear()
            gesture_keymap.GestureKeymap.key_restart()

            auth = data.get('author', '')
            des = data.get('description', '')
            addon_version = data.get('addon_version', ())
            if isinstance(addon_version, (list, tuple)) and addon_version:
                ver = '.'.join(str(i) for i in addon_version)
            else:
                ver = str(addon_version) if addon_version else '?'

            from bpy.app.translations import pgettext

            text = pgettext(
                r"Imported successfully! Imported %s of data Author:%s Comments:%s Exported data addon version:%s"
            ) % (len(restore), auth, des, ver)
            self.report({'INFO'}, text)
            return True
        except Exception as e:
            from bpy.app.translations import pgettext
            # Translate msgid + detail separately; never report e.args (tuple noise).
            self.report({'ERROR'}, pgettext("Import error: %s") % pgettext(str(e)))
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='export_import')
            debug_traceback(key='export_import')
            return False
    def read_json(self):
        with open(self.filepath, 'r', encoding='utf-8') as file:
            return json.load(file)


class Export(PublicFileOperator):
    bl_label = 'Export gesture'
    bl_idname = 'wm.gesture_export'
    bl_description = 'Export selected gestures to a JSON preset file'

    description: StringProperty(name='Description', default='This is a description')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_invoke = False

    @property
    def file_path(self):
        folder_path = self.filepath

        if self.is_invoke and folder_path.endswith('.json'):
            return os.path.abspath(folder_path)

        if not folder_path:
            folder_path = resolve_backups_folder()

        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)

        if os.path.isfile(folder_path):
            return os.path.abspath(folder_path)

        return os.path.abspath(
            os.path.join(folder_path, f'Gesture {datetime.now()}.json'.replace(':', ' '))
        )

    @property
    def export_data(self):
        return self._build_export_data(
            self.pref,
            all_gestures=False,
            description=self.description,
        )

    def draw(self, _):
        layout = self.layout

        layout.prop(self.pref.draw_property, 'author', emboss=True)
        layout.prop(self, 'description', emboss=True)
        layout.separator()

        row = layout.row()
        row.label(text='Export')
        row.prop(self, 'selected_all', emboss=True)

        column = layout.column()
        from ..utils.gesture_store import get_gesture_store
        store = get_gesture_store()
        if store is None:
            column.label(text="Gesture store unavailable")
            return
        column.template_list(
            ImportPresetUIList.bl_idname,
            ImportPresetUIList.bl_idname,
            store,
            'gesture',
            store,
            'index_gesture',
        )

    def invoke(self, context, event):
        self.is_invoke = True
        if not self.run_execute and not self.preset_show and not (self.filepath or "").strip():
            self.filepath = self.file_path
        return super().invoke(context, event)

    def execute(self, _):
        from bpy.app.translations import pgettext
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None or len(gestures) == 0:
            return {'CANCELLED'}

        gesture_data = self.export_data['gesture']
        if not len(gesture_data):
            self.report({'INFO'}, pgettext("Export Item Not Selected"))
            return {'CANCELLED'}

        path = self.file_path
        self.write_json_file()
        self.report({'INFO'}, pgettext("Export Finished! %s") % path)
        return {'FINISHED'}

    def write_json_file(self):
        path = self.file_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(self.export_data, file, ensure_ascii=True, indent=2)

    @staticmethod
    def _build_export_data(pref, *, all_gestures: bool, description: str = 'auto_backups') -> dict:
        from .. import ADDON_VERSION
        return {
            'time': time.time(),
            'blender_version': bpy.app.version,
            'addon_version': ADDON_VERSION,
            'author': pref.draw_property.author,
            'description': description,
            'gesture': pref.get_gesture_data(all_gestures),
        }

    @staticmethod
    def _automatic_backup_path(is_blender_close: bool) -> str:
        folder_path = resolve_backups_folder()
        if is_blender_close:
            pref = get_pref()
            mode = pref.backups_property.backups_file_mode
            return os.path.abspath(os.path.join(
                folder_path, blender_close_backup_filename(mode)))
        return os.path.abspath(os.path.join(folder_path, close_backup_filename()))

    @classmethod
    def run_automatic_backup(cls, is_blender_close: bool = False) -> str | None:
        pref = get_pref()
        prop = pref.backups_property
        folder = resolve_backups_folder()
        log_backup(
            f"start blender_close={is_blender_close} "
            f"on_close={prop.backup_on_blender_close} "
            f"on_disable={prop.backup_on_disable_addon} folder={folder}"
        )
        if is_blender_close:
            if not prop.backup_on_blender_close:
                log_backup("skipped: backup_on_blender_close is disabled")
                return None
        elif not prop.backup_on_disable_addon:
            log_backup("skipped: backup_on_disable_addon is disabled")
            return None
        from ..utils.gesture_store import get_gestures
        gestures = get_gestures()
        if gestures is None or not len(gestures):
            log_backup("skipped: no gestures")
            return None

        export_data = cls._build_export_data(
            pref,
            all_gestures=True,
            description='auto_backups',
        )
        gesture_data = export_data.get('gesture', {})
        if not gesture_data:
            log_backup("skipped: export data empty")
            return None

        path = cls._automatic_backup_path(is_blender_close)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, ensure_ascii=True, indent=2)
        log_backup(f"ok: {len(gesture_data)} gesture(s) -> {path}")
        return path

    @staticmethod
    def backups(is_blender_close: bool = False):
        """Export gesture backup when the add-on is disabled or Blender closes."""
        try:
            Export.run_automatic_backup(is_blender_close)
        except Exception as e:
            log_backup(f"failed: {e}")
            import traceback
            traceback.print_exc()


class ExportPreferences(bpy.types.Operator, ExportHelper):
    bl_idname = "wm.gesture_export_preferences"
    bl_label = "Export Preferences"
    bl_description = "Export add-on preferences to a backup file"

    filename_ext = PREFERENCES_EXPORT_EXTENSION

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def invoke(self, context, event):
        from ..utils.backups import (
            PREFERENCES_BACKUP_FILENAME,
            get_default_backups_folder,
        )

        if not (self.filepath or "").strip():
            self.filepath = os.path.join(
                get_default_backups_folder(), PREFERENCES_BACKUP_FILENAME)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from ..utils.public import get_pref
        from ..utils.debug_util import debug_trace_stack, debug_traceback
        from bpy.app.translations import pgettext
        try:
            get_pref().preferences_backups(self.filepath)
        except Exception as e:
            debug_trace_stack(key='export_import')
            debug_traceback(key='export_import')
            debug_print(e.args, key='export_import')
            self.report({'ERROR'}, pgettext("Export error, please check path %s") % self.filepath)
            return {'CANCELLED'}
        return {"FINISHED"}


class SaveGesturesAndUserPref(bpy.types.Operator):
    """Save gesture data to the CONFIG JSON file."""

    bl_idname = "wm.gesture_save_userpref"
    bl_label = "Save Gestures"
    bl_description = "Save gesture data to the config JSON file"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def execute(self, context):
        from ..utils.gesture_persistence import save_gestures_to_disk
        from bpy.app.translations import pgettext

        path = save_gestures_to_disk(description='manual_save')
        if path:
            self.report({'INFO'}, pgettext("Saved gestures"))
            return {'FINISHED'}
        self.report({'WARNING'}, pgettext("Gesture file write failed"))
        return {'CANCELLED'}


class ImportPreferences(bpy.types.Operator, ImportHelper):
    bl_idname = "wm.gesture_import_preferences"
    bl_label = "Import Preferences"
    bl_description = "Import add-on preferences from a backup file"

    filename_ext = PREFERENCES_EXPORT_EXTENSION
    filter_glob: bpy.props.StringProperty(
        default=f"*{PREFERENCES_EXPORT_EXTENSION};*{PREFERENCES_LEGACY_EXTENSION}",
        options={'HIDDEN'},
        maxlen=255,
    )

    @classmethod
    def poll(cls, context):
        return poll_addon_preferences(cls)

    def invoke(self, context, event):
        from ..utils.backups import (
            PREFERENCES_BACKUP_FILENAME,
            get_default_backups_folder,
        )

        self.filepath = os.path.join(get_default_backups_folder(), PREFERENCES_BACKUP_FILENAME)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from bpy.app.translations import pgettext
        from ..utils.public import get_pref

        filepath = (self.filepath or "").strip()
        if not filepath:
            self.report({'ERROR'}, pgettext("Please select a preferences backup file"))
            return {'CANCELLED'}

        try:
            get_pref().preferences_restore(filepath)
        except ValueError as e:
            self.report({'ERROR'}, pgettext(str(e)))
            return {'CANCELLED'}
        except Exception as e:
            from ..utils.debug_util import debug_trace_stack, debug_traceback
            debug_trace_stack(key='export_import')
            debug_traceback(key='export_import')
            debug_print(e.args, key='export_import')
            self.report(
                {'ERROR'},
                pgettext("Import error, please select preference settings file"),
            )
            return {'CANCELLED'}

        self.report({'INFO'}, pgettext("Preferences imported successfully"))
        return {"FINISHED"}
