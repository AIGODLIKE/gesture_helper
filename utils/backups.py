"""Backup folder resolution and gesture backup file discovery."""

from __future__ import annotations

import json
import os
from datetime import datetime
from os.path import abspath, join

import bpy

BACKUP_DIR_NAME = "backups"
GESTURES_FILENAME = "gesture_helper_gestures.json"
PREFERENCES_EXPORT_EXTENSION = ".gesture_preference"
PREFERENCES_BACKUP_FILENAME = f"preferences{PREFERENCES_EXPORT_EXTENSION}"
PREFERENCES_IMPORT_MAX_BYTES = 5 * 1024 * 1024
_PREFERENCES_ROOT_KEYS = frozenset({
    "draw_property",
    "debug_property",
    "other_property",
    "backups_property",
    "gesture_property",
    "add_element_property",
    "enabled",
    "show_page",
})

_GESTURE_BACKUP_PREFIX = "Gesture "
_CLOSE_BACKUP_MARKER = "Close Addon Backups"
_BLENDER_CLOSE_MARKER = "Blender Close Backups"


def get_extension_user_folder() -> str:
    """User data folder for backups.

    Extensions use ``extension_path_user``; legacy ``scripts/addons`` installs
    are not extension packages, so fall back to ``user_resource('DATAFILES')``.
    """
    from .. import __package__ as base_package
    try:
        path = bpy.utils.extension_path_user(base_package)
    except ValueError:
        # Legacy add-on: package is e.g. "gesture_helper", not "bl_ext....".
        path = bpy.utils.user_resource('DATAFILES', path="gesture_helper", create=True)
    os.makedirs(path, exist_ok=True)
    return path


def get_default_backups_folder() -> str:
    """Default backup root under extension / legacy user data."""
    path = abspath(join(get_extension_user_folder(), BACKUP_DIR_NAME))
    os.makedirs(path, exist_ok=True)
    return path


def _normalize_dir(path: str) -> str:
    return abspath(bpy.path.abspath(path.strip()))


def resolve_backups_folder(*, allow_custom: bool = True) -> str:
    """
    Return the folder used for gesture JSON backups.

    Custom path is optional; invalid custom paths fall back to the default folder.
    """
    folder = get_default_backups_folder()
    if not allow_custom:
        return folder

    from .public import get_pref

    prop = get_pref().backups_property
    if not prop.enabled_backups_to_specified_path:
        return folder

    custom = prop.backups_path.strip()
    if not custom:
        return folder

    custom = _normalize_dir(custom)
    if os.path.isfile(custom):
        return folder

    os.makedirs(custom, exist_ok=True)
    return custom


def get_preferences_backup_path() -> str:
    path = join(get_default_backups_folder(), PREFERENCES_BACKUP_FILENAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def resolve_preferences_backup_path() -> str | None:
    """Return the automatic preferences backup file in the default backup folder."""
    path = get_preferences_backup_path()
    if os.path.isfile(path):
        return path
    return None


def is_preferences_import_path(file_path: str) -> bool:
    """Return whether *file_path* looks like a preferences backup file."""
    base = os.path.basename(file_path).lower()
    return base.endswith(PREFERENCES_EXPORT_EXTENSION)


def load_preferences_backup_file(file_path: str) -> dict:
    """
    Load and validate a preferences backup JSON file.

    Raises ValueError with a user-facing message when the file is invalid.
    """
    if not file_path or not os.path.isfile(file_path):
        raise ValueError("Preferences backup file not found")

    if not is_preferences_import_path(file_path):
        raise ValueError(
            f"Invalid file type: please select a preferences backup ({PREFERENCES_EXPORT_EXTENSION})"
        )

    try:
        size = os.path.getsize(file_path)
    except OSError as e:
        raise ValueError("Cannot read preferences backup file") from e

    if size > PREFERENCES_IMPORT_MAX_BYTES:
        raise ValueError("File is too large to be a preferences backup")

    try:
        with open(file_path, "rb") as file:
            raw = file.read(PREFERENCES_IMPORT_MAX_BYTES + 1)
    except OSError as e:
        raise ValueError("Cannot read preferences backup file") from e

    if len(raw) > PREFERENCES_IMPORT_MAX_BYTES:
        raise ValueError("File is too large to be a preferences backup")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Not a valid UTF-8 preferences backup file") from e

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON in preferences backup file") from e

    if not isinstance(data, dict):
        raise ValueError("Invalid preferences backup: root must be a JSON object")

    if not data.keys() & _PREFERENCES_ROOT_KEYS:
        raise ValueError("Invalid preferences backup: not a Gesture Helper preferences file")

    return data


def backup_date_string() -> str:
    return datetime.now().strftime(r"%Y-%m-%d")


def backup_datetime_string() -> str:
    """Year-month-day-hour-minute-second, safe for filenames on Windows."""
    return datetime.now().strftime(r"%Y-%m-%d-%H-%M-%S")


def close_backup_filename(date: str | None = None) -> str:
    date = date or backup_date_string()
    return f"{_GESTURE_BACKUP_PREFIX}{_CLOSE_BACKUP_MARKER} {date}.json"


def blender_close_backup_filename(mode: str) -> str:
    """Filename when Blender closes."""
    if mode == "BLENDER_CLOSE_EVERY":
        stamp = backup_datetime_string()
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER} {stamp}.json"
    if mode == "BLENDER_CLOSE_DAY":
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER} {backup_date_string()}.json"
    if mode == "BLENDER_CLOSE_ONE":
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER}.json"
    return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER}.json"


def log_backup(message: str) -> None:
    from .debug_util import debug_print
    debug_print(f"[Gesture Helper Backup] {message}", key='export_import')


def _gesture_backup_files(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(
        (
            name for name in os.listdir(folder)
            if name.startswith(_GESTURE_BACKUP_PREFIX) and name.endswith(".json")
        ),
        reverse=True,
    )


def find_gesture_backup_for_restore(folder: str | None = None) -> str | None:
    """
    Pick a gesture backup as a load fallback when CONFIG / fixed files are missing.

    Priority:
    1. Today's disable-add-on backup
    2. Newest disable-add-on backup
    3. Newest Blender-close backup (EVERY mode: newest timestamp wins via reverse name sort)
    """
    folder = folder or resolve_backups_folder()
    files = _gesture_backup_files(folder)
    if not files:
        return None

    today_close = close_backup_filename()
    if today_close in files:
        return join(folder, today_close)

    close_files = [name for name in files if _CLOSE_BACKUP_MARKER in name]
    if close_files:
        return join(folder, close_files[0])

    blender_files = [name for name in files if _BLENDER_CLOSE_MARKER in name]
    if blender_files:
        return join(folder, blender_files[0])

    return None


def get_gestures_config_path() -> str | None:
    """Fixed path under Blender CONFIG; return None when CONFIG is unavailable."""
    try:
        root = bpy.utils.user_resource('CONFIG', path='', create=True)
        if not root:
            return None
        return abspath(join(root, GESTURES_FILENAME))
    except Exception:
        return None


def get_gestures_backup_fallback_path() -> str:
    """Same filename under the gesture backups folder."""
    path = abspath(join(resolve_backups_folder(), GESTURES_FILENAME))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def resolve_gestures_load_path() -> str | None:
    """
    Resolve which gesture JSON to load.

    Priority:
    1. CONFIG fixed file
    2. Backups-folder fixed file
    3. Newest rotating backup via find_gesture_backup_for_restore()
    """
    config_path = get_gestures_config_path()
    if config_path and os.path.isfile(config_path):
        return config_path

    backup_fixed = get_gestures_backup_fallback_path()
    if os.path.isfile(backup_fixed):
        return backup_fixed

    return find_gesture_backup_for_restore()


def resolve_gestures_save_path() -> str:
    """Prefer CONFIG; fall back to the backups-folder fixed file."""
    config_path = get_gestures_config_path()
    if config_path:
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            return config_path
        except OSError:
            ...
    return get_gestures_backup_fallback_path()
