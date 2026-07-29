from __future__ import annotations

import unittest

from utils.operator_compat import resolve_operator_properties


class _EnumItem:
    def __init__(self, identifier):
        self.identifier = identifier


class _EnumProperty:
    type = "ENUM"

    def __init__(self, identifiers):
        self.enum_items = [_EnumItem(identifier) for identifier in identifiers]


class _Operator:
    def __init__(self, identifiers):
        mode = _EnumProperty(identifiers)
        self._rna = type("RNA", (), {"properties": {"mode": mode}})()

    def get_rna_type(self):
        return self._rna


class OperatorCompatibilityTests(unittest.TestCase):
    def test_legacy_modes_map_to_blender_43_and_newer(self):
        operator = _Operator({
            "SCULPT_GREASE_PENCIL",
            "PAINT_GREASE_PENCIL",
            "WEIGHT_GREASE_PENCIL",
            "VERTEX_GREASE_PENCIL",
        })
        resolved = resolve_operator_properties(
            "object.mode_set",
            {"mode": "PAINT_GPENCIL"},
            operator,
        )
        self.assertEqual(resolved, {"mode": "PAINT_GREASE_PENCIL"})

    def test_valid_unknown_and_unrelated_values_are_not_hidden(self):
        operator = _Operator({"OBJECT", "EDIT", "PAINT_GPENCIL"})
        self.assertEqual(
            resolve_operator_properties(
                "object.mode_set", {"mode": "OBJECT"}, operator,
            ),
            {"mode": "OBJECT"},
        )
        self.assertEqual(
            resolve_operator_properties(
                "object.mode_set", {"mode": "NOT_REAL"}, operator,
            ),
            {"mode": "NOT_REAL"},
        )
        self.assertEqual(
            resolve_operator_properties(
                "other.operator", {"mode": "PAINT_GREASE_PENCIL"}, operator,
            ),
            {"mode": "PAINT_GREASE_PENCIL"},
        )


if __name__ == "__main__":
    unittest.main()
