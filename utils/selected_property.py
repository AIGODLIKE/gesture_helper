"""Copy a context property value to matching selected objects."""

from __future__ import annotations


def _rna_identity(value) -> int:
    try:
        return int(value.as_pointer())
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return id(value)


def resolve_context_property(context, data_path: str):
    """Return ``(owner, RNA property)`` for a dotted context data path."""
    path = data_path.strip()
    if path.startswith('bpy.context.'):
        path = path[len('bpy.context.'):]
    elif path.startswith('context.'):
        path = path[len('context.'):]
    if not path or '.' not in path:
        return None
    owner_path, prop_id = path.rsplit('.', 1)
    try:
        owner = context.path_resolve(owner_path)
        rna = getattr(owner, 'bl_rna', None)
        prop = rna.properties.get(prop_id) if rna is not None else None
    except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
        return None
    return (owner, prop) if owner is not None and prop is not None else None


def capture_selected_object_values(context, data_path: str, source_owner, source_prop):
    """Snapshot matching property values on the other selected objects.

    Blender's generic Alt editing supports many editor-specific selections.
    Gesture Helper's context paths currently expose object properties, so this
    helper implements the corresponding object/data branch and ignores paths
    such as ``scene`` and ``space_data`` that have no object selection meaning.
    """
    path = data_path.strip()
    if path.startswith('bpy.context.'):
        path = path[len('bpy.context.'):]
    elif path.startswith('context.'):
        path = path[len('context.'):]
    parts = path.split('.')
    if len(parts) < 2 or parts[0] not in {'object', 'active_object'}:
        return []

    relative_owner_path = '.'.join(parts[1:-1])
    prop_id = parts[-1]
    source_type = getattr(source_prop, 'type', None)
    source_key = _rna_identity(source_owner)
    seen = {source_key}
    snapshots = []
    try:
        selected = context.selected_editable_objects
    except (AttributeError, ReferenceError, RuntimeError, TypeError):
        return snapshots

    for obj in selected:
        try:
            owner = (
                obj.path_resolve(relative_owner_path)
                if relative_owner_path
                else obj
            )
            key = _rna_identity(owner)
            if key in seen:
                continue
            seen.add(key)
            rna = getattr(owner, 'bl_rna', None)
            prop = rna.properties.get(prop_id) if rna is not None else None
            if prop is None or getattr(prop, 'type', None) != source_type:
                continue
            if getattr(prop, 'is_readonly', False):
                continue
            try:
                if owner.is_property_readonly(prop_id):
                    continue
            except (AttributeError, ReferenceError, RuntimeError, TypeError):
                pass
            snapshots.append((owner, prop_id, getattr(owner, prop_id)))
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            continue
    return snapshots


def set_snapshot_values(snapshots, value) -> bool:
    """Assign one value to captured targets and report any real change."""
    changed = False
    for owner, prop_id, _original in snapshots or ():
        try:
            current = getattr(owner, prop_id)
            if current == value:
                continue
            setattr(owner, prop_id, value)
            changed = getattr(owner, prop_id) != current or changed
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            continue
    return changed


def restore_snapshot_values(snapshots) -> bool:
    """Restore values captured before a cancellable Alt edit."""
    changed = False
    for owner, prop_id, original in snapshots or ():
        try:
            current = getattr(owner, prop_id)
            if current == original:
                continue
            setattr(owner, prop_id, original)
            changed = getattr(owner, prop_id) != current or changed
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError):
            continue
    return changed
