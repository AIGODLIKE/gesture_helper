from __future__ import annotations

import ast
import tomllib
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).parents[1]


def _bl_info() -> dict:
    tree = ast.parse((REPOSITORY / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("bl_info assignment not found")


class VersionMetadataTests(unittest.TestCase):
    def test_manifest_and_legacy_metadata_stay_in_sync(self):
        with open(REPOSITORY / "blender_manifest.toml", "rb") as handle:
            manifest = tomllib.load(handle)
        bl_info = _bl_info()

        self.assertEqual(
            manifest["version"],
            ".".join(map(str, bl_info["version"])),
        )
        self.assertEqual(
            manifest["blender_version_min"],
            ".".join(map(str, bl_info["blender"])),
        )


if __name__ == "__main__":
    unittest.main()
