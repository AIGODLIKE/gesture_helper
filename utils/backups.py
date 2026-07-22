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
# Names written by releases before the preference backup was moved to the
# extension-specific filename.  Keep them read-only migration candidates.
PREFERENCES_OLD_JSON_FILENAME = "preferences.json"
PREFERENCES_OLD_FILENAME = "preferences"
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


def _prepare_user_folder(path, *, create: bool) -> str:
    """Validate and optionally create a Blender-provided user data path."""
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise OSError("Blender returned an invalid Gesture Helper user folder") from exc
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    if not path:
        # ``bpy.utils.user_resource(..., create=True)`` can swallow a
        # PermissionError and return ``""``.  Never pass that to os.makedirs:
        # it produces an opaque FileNotFoundError for the caller.
        raise OSError("Blender did not provide a Gesture Helper user folder")
    if create:
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as exc:
            raise OSError(
                f"Cannot create Gesture Helper user folder: {path}"
            ) from exc
    elif os.path.exists(path) and not os.path.isdir(path):
        raise OSError(f"Gesture Helper user path is not a directory: {path}")
    return path


def get_extension_user_folder(*, create: bool = True) -> str:
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
    except (TypeError, RuntimeError, ValueError):
        # Legacy add-on only: package is e.g. "gesture_helper", not "bl_ext....".
        path = bpy.utils.user_resource(
            'DATAFILES', path="gesture_helper", create=create
        )
    return _prepare_user_folder(path, create=create)


def get_default_backups_folder(*, create: bool = True) -> str:
    """Default backup root under extension / legacy user data."""
    path = abspath(join(
        get_extension_user_folder(create=create), BACKUP_DIR_NAME
    ))
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def _normalize_dir(path: str) -> str:
    return abspath(bpy.path.abspath(path.strip()))


def _resolve_custom_backups_folder(*, create: bool) -> str | None:
    """Return the enabled custom folder without touching the default root."""
    try:
        from .public import get_pref

        prop = get_pref().backups_property
        if not prop.enabled_backups_to_specified_path:
            return None
        custom = prop.backups_path.strip()
        if not custom:
            return None

        custom = _normalize_dir(custom)
        if os.path.isfile(custom):
            return None
        if create:
            os.makedirs(custom, exist_ok=True)
        elif os.path.exists(custom) and not os.path.isdir(custom):
            return None
        return custom
    except (AttributeError, OSError, TypeError, ValueError, RuntimeError):
        return None


def resolve_backups_folder(
    *,
    allow_custom: bool = True,
    create: bool = True,
) -> str:
    """
    Return the folder used for gesture JSON backups.

    Custom path is optional; invalid custom paths fall back to the default folder.
    """
    if allow_custom:
        custom = _resolve_custom_backups_folder(create=create)
        if custom is not None:
            return custom
    return get_default_backups_folder(create=create)


def get_preferences_backup_path() -> str:
    path = join(get_default_backups_folder(), PREFERENCES_BACKUP_FILENAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def resolve_preferences_backup_path() -> str | None:
    """Return the automatic preferences backup file in the default backup folder."""
    paths = iter_preferences_backup_paths()
    return paths[0] if paths else None


def iter_preferences_backup_paths() -> list[str]:
    """Return existing automatic preference backups, newest format first."""
    try:
        folder = get_default_backups_folder(create=False)
    except Exception:
        # Auto-restore is read-only; an unavailable default folder should not
        # prevent the add-on from starting with its current preferences.
        return []
    paths = (
        join(folder, PREFERENCES_BACKUP_FILENAME),
        join(folder, PREFERENCES_LEGACY_BACKUP_FILENAME),
        join(folder, PREFERENCES_OLD_JSON_FILENAME),
        join(folder, PREFERENCES_OLD_FILENAME),
    )
    existing: list[str] = []
    for path in paths:
        try:
            if os.path.isfile(path):
                existing.append(path)
        except OSError:
            continue
    return existing


def is_preferences_import_path(file_path: str) -> bool:
    """Return whether *file_path* looks like a preferences backup file."""
    base = os.path.basename(file_path).lower()
    if base in {
        PREFERENCES_OLD_FILENAME,
        PREFERENCES_OLD_JSON_FILENAME,
    }:
        return True
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


def _is_rotating_gesture_backup(name: str) -> bool:
    """True for generated Close Addon / Blender Close filenames only.

    User-exported presets also start with ``Gesture ``.  Keep those files out
    of pruning and restore discovery by validating the generated date suffixes
    instead of matching the marker as an arbitrary substring.
    """
    if not (name.startswith(_GESTURE_BACKUP_PREFIX) and name.endswith(".json")):
        return False
    stem = name[len(_GESTURE_BACKUP_PREFIX):-len(".json")]

    def is_date(value: str) -> bool:
        if (
            len(value) != 10
            or value[4] != "-"
            or value[7] != "-"
            or not value.replace("-", "").isdigit()
        ):
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True

    def is_datetime(value: str) -> bool:
        # Releases before the filename cleanup used a space between the date
        # and time.  Accept both forms, plus the numeric collision suffix used
        # by the current EVERY-close mode.
        candidates = [value]
        stem_part, separator, serial = value.rpartition("-")
        if separator and serial.isdigit():
            candidates.append(stem_part)
        for candidate in candidates:
            if len(candidate) != 19:
                continue
            if candidate[10] not in ("-", " "):
                continue
            fmt = "%Y-%m-%d-%H-%M-%S" if candidate[10] == "-" else "%Y-%m-%d %H-%M-%S"
            try:
                datetime.strptime(candidate, fmt)
            except ValueError:
                continue
            return True
        return False

    if stem.startswith(_CLOSE_BACKUP_MARKER + " "):
        return is_date(stem[len(_CLOSE_BACKUP_MARKER) + 1:])
    if stem == _BLENDER_CLOSE_MARKER:
        return True
    if stem.startswith(_BLENDER_CLOSE_MARKER + " "):
        suffix = stem[len(_BLENDER_CLOSE_MARKER) + 1:]
        return is_date(suffix) or is_datetime(suffix)
    return False


def iter_rotating_gesture_backup_paths(folder: str | None = None) -> list[str]:
    """Absolute paths of rotating auto-backups in the active (or given) folder."""
    folder = folder or resolve_backups_folder(create=False)
    if not os.path.isdir(folder):
        return []
    try:
        names = sorted(
            (
                name for name in os.listdir(folder)
                if _is_rotating_gesture_backup(name)
                and os.path.isfile(join(folder, name))
            ),
            reverse=True,
        )
    except OSError:
        return []
    return [abspath(join(folder, name)) for name in names]


def _rotating_backup_paths_by_mtime(folder: str | None = None) -> list[tuple[float, str]]:
    """``(mtime, path)`` for rotating auto-backups, oldest first.

    Preferences single-file backups and ``gesture_helper_gestures.json`` are
    never included — only Close Addon / Blender Close rotating copies.
    """
    items: list[tuple[float, str]] = []
    for path in iter_rotating_gesture_backup_paths(folder):
        try:
            items.append((os.path.getmtime(path), path))
        except OSError:
            continue
    # Compare stems before full paths so an EVERY-mode collision orders the
    # base file before ``-001``, ``-002``, etc. when mtimes are identical.
    items.sort(key=lambda item: (
        item[0], os.path.splitext(item[1])[0], item[1]
    ))
    return items


def get_newest_rotating_backup_path(folder: str | None = None) -> str | None:
    """Newest rotating auto-backup by mtime, or None."""
    items = _rotating_backup_paths_by_mtime(folder)
    if not items:
        return None
    return items[-1][1]


def _gesture_payload_fingerprint(gesture_data) -> str:
    """Stable fingerprint of gesture content only (ignores time / versions)."""
    return json.dumps(gesture_data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def gesture_auto_backup_unchanged(
    export_data: dict,
    folder: str | None = None,
    path: str | None = None,
) -> bool:
    """True when *export_data* ``gesture`` matches a rotating backup.

    When *path* is supplied, compare that target file.  Otherwise preserve the
    original public behavior and compare the newest rotating backup in *folder*.
    Export ``time`` always changes, so only the gesture payload is compared.
    Unreadable / invalid last backup → False (write).
    """
    candidate = path or get_newest_rotating_backup_path(folder)
    if candidate is None or not os.path.isfile(candidate):
        return False
    try:
        with open(candidate, "r", encoding="utf-8") as file:
            previous = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return False
    if not isinstance(previous, dict):
        return False
    current_gesture = export_data.get("gesture") if isinstance(export_data, dict) else None
    previous_gesture = previous.get("gesture")
    if not isinstance(current_gesture, dict) or not isinstance(previous_gesture, dict):
        return False
    return (
        _gesture_payload_fingerprint(current_gesture)
        == _gesture_payload_fingerprint(previous_gesture)
    )


def prune_rotating_gesture_backups(
    max_count: int,
    folder: str | None = None,
) -> tuple[int, int]:
    """
    Delete oldest rotating auto-backups until count ``<= max_count``.

    Returns ``(deleted_count, deleted_bytes)``. Never touches preferences
    backups or the fixed gestures JSON.
    """
    if max_count < 1:
        max_count = 1
    items = _rotating_backup_paths_by_mtime(folder)
    overflow = len(items) - max_count
    if overflow <= 0:
        return 0, 0

    deleted_count = 0
    deleted_bytes = 0
    for _mtime, path in items[:overflow]:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        try:
            os.remove(path)
        except OSError as e:
            log_backup(f"prune skipped ({path}): {e}")
            continue
        deleted_count += 1
        deleted_bytes += size
        log_backup(f"prune deleted oldest: {path}")
    return deleted_count, deleted_bytes


def get_rotating_backup_stats(folder: str | None = None) -> tuple[int, int]:
    """Return ``(count, total_bytes)`` for rotating auto-backups."""
    total = 0
    count = 0
    for path in iter_rotating_gesture_backup_paths(folder):
        try:
            total += os.path.getsize(path)
            count += 1
        except OSError:
            continue
    return count, total


def format_backup_size(nbytes: int) -> str:
    """Human-readable size for backup stats UI."""
    if nbytes < 1024:
        return f"{nbytes} B"
    if nbytes < 1024 * 1024:
        return f"{nbytes / 1024:.1f} KB"
    return f"{nbytes / (1024 * 1024):.1f} MB"


def clear_rotating_gesture_backups(folder: str | None = None) -> tuple[int, int]:
    """
    Delete rotating auto-backups only.

    Never touches preferences backups or ``gesture_helper_gestures.json``.
    Returns ``(deleted_count, deleted_bytes)``.
    """
    deleted_count = 0
    deleted_bytes = 0
    for path in iter_rotating_gesture_backup_paths(folder):
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        try:
            os.remove(path)
        except OSError as e:
            log_backup(f"clear skipped ({path}): {e}")
            continue
        deleted_count += 1
        deleted_bytes += size
        log_backup(f"clear deleted: {path}")
    return deleted_count, deleted_bytes


def find_gesture_backup_for_restore(folder: str | None = None) -> str | None:
    """
    Pick a gesture backup as a load fallback when CONFIG / fixed files are missing.

    Priority:
    1. Today's disable-add-on backup
    2. Newest disable-add-on backup
    3. Newest Blender-close backup (EVERY mode: newest timestamp wins via reverse name sort)
    """
    paths = iter_gesture_backup_restore_paths(folder)
    return paths[0] if paths else None


def iter_gesture_backup_restore_paths(folder: str | None = None) -> list[str]:
    """Return all rotating restore candidates in priority order.

    The first candidate retains the historical priority (today's Close Addon,
    then newest Close Addon, then newest Blender Close).  Returning the full
    list lets callers continue after a corrupt candidate instead of repeatedly
    selecting the same broken file.
    """
    folder = folder or resolve_backups_folder(create=False)
    if not os.path.isdir(folder):
        return []

    try:
        files = [
            name for name in os.listdir(folder)
            if _is_rotating_gesture_backup(name)
            and os.path.isfile(join(folder, name))
        ]
    except OSError:
        return []
    if not files:
        return []

    def newest_first(names):
        def key(name):
            try:
                mtime = os.path.getmtime(join(folder, name))
            except OSError:
                mtime = float("-inf")
            # Filename keeps ordering deterministic when files share an mtime.
            return mtime, os.path.splitext(name)[0], name

        return sorted(names, key=key, reverse=True)

    close_files = newest_first(
        name for name in files if _CLOSE_BACKUP_MARKER in name
    )
    blender_files = newest_first(
        name for name in files if _BLENDER_CLOSE_MARKER in name
    )

    ordered: list[str] = []
    today_close = close_backup_filename()
    if today_close in close_files:
        ordered.append(today_close)
        close_files.remove(today_close)
    ordered.extend(close_files)
    ordered.extend(blender_files)
    return [abspath(join(folder, name)) for name in ordered]


def get_gestures_extension_path(*, create: bool = True) -> str:
    """Primary gesture JSON under ``extension_path_user`` (or legacy DATAFILES)."""
    path = abspath(join(
        get_extension_user_folder(create=create), GESTURES_FILENAME
    ))
    if create:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def get_gestures_legacy_datafiles_path() -> str | None:
    """Stable legacy ZIP-install path, also checked by extension installs."""
    try:
        root = bpy.utils.user_resource(
            'DATAFILES', path="gesture_helper", create=False
        )
        if not root:
            return None
        return abspath(join(root, GESTURES_FILENAME))
    except Exception:
        return None


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


def get_gestures_backup_fallback_path(*, create: bool = True) -> str:
    """Same filename under the gesture backups folder."""
    path = abspath(join(
        resolve_backups_folder(create=create), GESTURES_FILENAME
    ))
    if create:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def iter_gestures_save_paths() -> list[str]:
    """Save candidates in primary then active-backup order."""
    paths: list[str] = []
    for resolver in (
        get_gestures_extension_path,
        get_gestures_backup_fallback_path,
    ):
        try:
            path = resolver()
        except OSError:
            continue
        if path not in paths:
            paths.append(path)
    return paths


def resolve_gestures_load_path() -> str | None:
    """First load candidate, or None. Prefer ``iter_gestures_load_candidates``."""
    for path in iter_gestures_load_candidates():
        return path
    return None


def iter_gestures_load_candidates() -> list[str]:
    """
    Load candidates in priority order.

    Fixed files are tried newest-first; empty files still count as valid.
    Equal mtimes retain this priority: extension, legacy DATAFILES/CONFIG,
    then the backups-folder file.
    4. Rotating backup — only when none of the fixed files exist

    Callers that hit a corrupt/invalid file should continue to the next candidate.
    A successfully loaded empty ``gesture: {}`` must not fall back to rotating backups.
    """
    paths: list[str] = []

    try:
        extension_path = get_gestures_extension_path(create=False)
    except Exception:
        # A read-only extension user directory must not prevent loading the
        # legacy CONFIG or rotating backups.
        extension_path = None
    try:
        extension_exists = bool(extension_path and os.path.isfile(extension_path))
    except OSError:
        extension_exists = False
    if extension_exists:
        paths.append(extension_path)

    datafiles_path = get_gestures_legacy_datafiles_path()
    try:
        datafiles_exists = bool(
            datafiles_path and os.path.isfile(datafiles_path)
        )
    except OSError:
        datafiles_exists = False
    if datafiles_exists and datafiles_path not in paths:
        paths.append(datafiles_path)

    config_path = get_gestures_config_path()
    config_exists = bool(config_path and os.path.isfile(config_path))
    if config_exists and config_path not in paths:
        paths.append(config_path)

    try:
        backup_fixed = get_gestures_backup_fallback_path(create=False)
    except Exception:
        backup_fixed = None
    try:
        backup_exists = bool(backup_fixed and os.path.isfile(backup_fixed))
    except OSError:
        backup_exists = False
    if backup_exists and backup_fixed not in paths:
        paths.append(backup_fixed)

    # A fallback may contain the latest data when the primary file is readable
    # but not writable (common for portable installs under protected folders).
    priority = {path: len(paths) - index for index, path in enumerate(paths)}

    def fixed_candidate_key(path: str):
        try:
            modified = os.path.getmtime(path)
        except OSError:
            modified = float("-inf")
        return modified, priority[path]

    paths.sort(key=fixed_candidate_key, reverse=True)

    if not any((
        extension_exists,
        datafiles_exists,
        config_exists,
        backup_exists,
    )):
        try:
            rotating = find_gesture_backup_for_restore()
        except Exception:
            rotating = None
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
    seen = set(failed_paths)
    try:
        candidates = iter_gesture_backup_restore_paths()
    except Exception:
        candidates = []
    return [path for path in candidates if path not in seen]


def resolve_gestures_save_path() -> str:
    """Prefer extension user folder; fall back to the backups-folder fixed file."""
    paths = iter_gestures_save_paths()
    if not paths:
        raise OSError("No writable Gesture Helper user folder is available")
    return paths[0]
