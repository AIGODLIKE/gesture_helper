from __future__ import annotations

import types
import unittest

from utils.selected_property import (
    capture_selected_object_values,
    restore_snapshot_values,
    set_snapshot_values,
)


class FakeOwner:
    def __init__(self, pointer, **values):
        self._pointer = pointer
        properties = {
            name: types.SimpleNamespace(type='BOOLEAN', is_readonly=False)
            for name in values
        }
        self.bl_rna = types.SimpleNamespace(properties=properties)
        for name, value in values.items():
            setattr(self, name, value)

    def as_pointer(self):
        return self._pointer

    def is_property_readonly(self, _name):
        return False

    def path_resolve(self, path):
        value = self
        for part in path.split('.'):
            value = getattr(value, part)
        return value


class SelectedPropertyTests(unittest.TestCase):
    def test_selected_objects_receive_one_value_and_cancel_restores_them(self):
        active = FakeOwner(1, show_wire=False)
        other_a = FakeOwner(2, show_wire=False)
        other_b = FakeOwner(3, show_wire=True)
        context = types.SimpleNamespace(
            selected_editable_objects=[active, other_a, other_b],
        )

        snapshots = capture_selected_object_values(
            context,
            'object.show_wire',
            active,
            active.bl_rna.properties['show_wire'],
        )
        self.assertTrue(set_snapshot_values(snapshots, True))
        self.assertTrue(other_a.show_wire)
        self.assertTrue(other_b.show_wire)

        self.assertTrue(restore_snapshot_values(snapshots))
        self.assertFalse(other_a.show_wire)
        self.assertTrue(other_b.show_wire)

    def test_non_object_context_path_has_no_selection_targets(self):
        active = FakeOwner(1, show_overlays=False)
        context = types.SimpleNamespace(selected_editable_objects=[])
        self.assertEqual(
            capture_selected_object_values(
                context,
                'space_data.overlay.show_overlays',
                active,
                active.bl_rna.properties['show_overlays'],
            ),
            [],
        )


if __name__ == '__main__':
    unittest.main()
