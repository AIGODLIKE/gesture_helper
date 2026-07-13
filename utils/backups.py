"""Backup folder resolution and gesture backup file discovery."""

from __future__ import annotations

import json
import os
from datetime import datetime
from os.path import abspath, join

import bpy

BACKUP_DIR_NAME = "backups"
GESTURES_FILENAME = "gesture_helper_gestures.json"
PREFERENCES_EXPORT_EXTENSION = ".json"
PREFERENCES_BACKUP_FILENAME = "gesture_helper_preferences.json"
PREFERENCES_LEGACY_EXTENSION = ".gesture_preference"
PREFERENCES_LEGACY_BACKUP_FILENAME = f"preferences{PREFERENCES_LEGACY_EXTENSION}"
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
    """User data folder for backups and persistent gesture files.

    Path boundary (do not mix these roots):
    - Extension install (``bl_ext.*`` package): always
      ``bpy.utils.extension_path_user(__package__)``. Uninstall removes this
      folder with the extension.
    - Legacy ``scripts/addons`` install only: ``extension_path_user`` raises
      ``ValueError`` because the package is not an extension id. Fall back to
      ``bpy.utils.user_resource('DATAFILES', path='gesture_helper')`` so zip /
      manual installs keep working. Never write into the add-on source tree.
    """
    from .. import __package__ as base_package
    try:
        path = bpy.utils.extension_path_user(base_package)
    except ValueError:
        # Legacy add-on only: package is e.g. "gesture_helper", not "bl_ext....".
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
    legacy = join(get_default_backups_folder(), PREFERENCES_LEGACY_BACKUP_FILENAME)
    if os.path.isfile(legacy):
        return legacy
    return None


def is_preferences_import_path(file_path: str) -> bool:
    """Return whether *file_path* looks like a preferences backup file."""
    base = os.path.basename(file_path).lower()
    if base.endswith(PREFERENCES_LEGACY_EXTENSION):
        return True
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
            "Invalid file type: please select a preferences backup (.json)"
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


def get_gestures_extension_path() -> str:
    """Primary gesture JSON under ``extension_path_user`` (or legacy DATAFILES)."""
    path = abspath(join(get_extension_user_folder(), GESTURES_FILENAME))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def get_gestures_config_path() -> str | None:
    """Legacy gesture JSON under Blender CONFIG (read-only migrate path).

    Older builds wrote the main gesture file here. New saves use
    ``get_gestures_extension_path()`` instead. Keep reading CONFIG so existing
    installs still load; do not write new primary data here.
    """
    try:
        root = bpy.utils.user_resource('CONFIG', path='', create=False)
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
    """First load candidate, or None. Prefer ``iter_gestures_load_candidates``."""
    for path in iter_gestures_load_candidates():
        return path
    return None


def iter_gestures_load_candidates() -> list[str]:
    """
    Load candidates in priority order.

    1. Extension user folder fixed file (primary; empty still counts)
    2. Legacy CONFIG fixed file (migrate-only; empty still counts)
    3. Backups-folder fixed file (same empty rule)
    4. Rotating backup — only when none of the fixed files exist

    Callers that hit a corrupt/invalid file should continue to the next candidate.
    A successfully loaded empty ``gesture: {}`` must not fall back to rotating backups.
    """
    paths: list[str] = []

    extension_path = get_gestures_extension_path()
    extension_exists = os.path.isfile(extension_path)
    if extension_exists:
        paths.append(extension_path)

    config_path = get_gestures_config_path()
    config_exists = bool(config_path and os.path.isfile(config_path))
    if config_exists and config_path not in paths:
        paths.append(config_path)

    backup_fixed = get_gestures_backup_fallback_path()
    backup_exists = os.path.isfile(backup_fixed)
    if backup_exists and backup_fixed not in paths:
        paths.append(backup_fixed)

    if not extension_exists and not config_exists and not backup_exists:
        rotating = find_gesture_backup_for_restore()
        if rotating:
            paths.append(rotating)

    return paths


def iter_gestures_load_fallback_after_failure(failed_paths: list[str]) -> list[str]:
    """
    Extra candidates after fixed files failed to parse.

    Rotating backups are included here so a corrupt primary / CONFIG file can
    still recover from Close Addon / Blender Close copies. Empty-but-valid
    fixed files never reach this path (load already succeeded).
    """
    extra: list[str] = []
    seen = set(failed_paths)
    rotating = find_gesture_backup_for_restore()
    if rotating and rotating not in seen:
        extra.append(rotating)
    return extra


def resolve_gestures_save_path() -> str:
    """Prefer extension user folder; fall back to the backups-folder fixed file."""
    try:
        return get_gestures_extension_path()
    except OSError:
        return get_gestures_backup_fallback_path()
