"""Backup folder resolution and gesture backup file discovery."""

from __future__ import annotations

import os
from datetime import datetime
from os.path import abspath, join

import bpy

BACKUP_DIR_NAME = "backups"
PREFERENCES_BACKUP_FILENAME = "preferences.json"
LEGACY_PREFERENCES_BACKUP_FILENAME = "preferences"

_GESTURE_BACKUP_PREFIX = "Gesture "
_CLOSE_BACKUP_MARKER = "Close Addon Backups"
_BLENDER_CLOSE_MARKER = "Blender Close Backups"
_AUTO_BACKUP_MARKER = "Auto Backups"


def get_extension_user_folder() -> str:
    from .. import __package__ as base_package
    path = bpy.utils.extension_path_user(base_package)
    os.makedirs(path, exist_ok=True)
    return path


def get_default_backups_folder() -> str:
    """Default backup root under extension user data."""
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
    """Return preferences backup file, supporting legacy filename without extension."""
    primary = get_preferences_backup_path()
    if os.path.isfile(primary):
        return primary
    legacy = join(get_default_backups_folder(), LEGACY_PREFERENCES_BACKUP_FILENAME)
    if os.path.isfile(legacy):
        return legacy
    return None


def backup_date_string() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month:02d}-{now.day:02d}"


def backup_datetime_string() -> str:
    """Date and time (H-M-S) safe for filenames on Windows."""
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def close_backup_filename(date: str | None = None) -> str:
    date = date or backup_date_string()
    return f"{_GESTURE_BACKUP_PREFIX}{_CLOSE_BACKUP_MARKER} {date}.json"


def blender_close_backup_filename(mode: str) -> str:
    """Filename when Blender closes (or legacy auto-backup modes)."""
    if mode in ("BLENDER_CLOSE_EVERY", "ADDON_UNREGISTER"):
        stamp = backup_datetime_string()
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER} {stamp}.json"
    if mode in ("BLENDER_CLOSE_DAY", "ADDON_UNREGISTER_DAY"):
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER} {backup_date_string()}.json"
    if mode in ("BLENDER_CLOSE_ONE", "ONLY_ONE"):
        return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER}.json"
    return f"{_GESTURE_BACKUP_PREFIX}{_BLENDER_CLOSE_MARKER}.json"


def auto_backup_filename(mode: str) -> str:
    """Legacy alias; prefer blender_close_backup_filename for quit backups."""
    return blender_close_backup_filename(mode)


def log_backup(message: str) -> None:
    print(f"[Gesture Helper Backup] {message}")


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
    Pick a gesture backup to import on first add-on init.

    Priority:
    1. Today's close-backup (disable add-on)
    2. Newest close-backup
    3. ONLY_ONE auto backup
    4. Newest auto backup
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

    only_one = blender_close_backup_filename("BLENDER_CLOSE_ONE")
    if only_one in files:
        return join(folder, only_one)
    legacy_only = blender_close_backup_filename("ONLY_ONE")
    if legacy_only in files:
        return join(folder, legacy_only)

    blender_files = [name for name in files if _BLENDER_CLOSE_MARKER in name]
    if blender_files:
        return join(folder, blender_files[0])

    auto_files = [name for name in files if _AUTO_BACKUP_MARKER in name]
    if auto_files:
        return join(folder, auto_files[0])

    return join(folder, files[0])
