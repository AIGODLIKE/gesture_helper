from __future__ import annotations

import json
from pathlib import Path
import unittest


TRANSLATION_PATH = (
    Path(__file__).parents[1] / "src" / "translate" / "zh_CN" / "text.json"
)


class TranslationCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.translations = json.loads(TRANSLATION_PATH.read_text(encoding="utf-8"))

    def test_custom_theme_storage_note_is_translated(self):
        self.assertEqual(
            self.translations["Custom colors are stored with preferences"],
            "自定义颜色会随偏好设置保存",
        )

    def test_obsolete_layout_description_is_removed(self):
        self.assertNotIn(
            "Switch the active layout between Row, Column and Box",
            self.translations,
        )
        self.assertIn(
            "Switch the active layout between Row, Column, Box and Split",
            self.translations,
        )

    def test_backups_preferences_page_is_translated(self):
        self.assertEqual(self.translations["Backups"], "备份")
        self.assertEqual(
            self.translations["Backup and restore settings"],
            "备份与恢复设置",
        )
        self.assertEqual(
            self.translations["Preferences Backup"],
            "偏好设置备份",
        )

    def test_long_gesture_action_tooltips_break_before_modifier_help(self):
        self.assertEqual(
            self.translations[
                "Add a new gesture. Hold Ctrl+Alt+Shift while clicking to "
                "import every bundled preset, including examples"
            ],
            "添加新手势\n"
            "按住 Ctrl+Alt+Shift 点击可导入全部内置预设（包括示例）",
        )
        self.assertEqual(
            self.translations[
                "Remove the active gesture. Hold Ctrl+Alt+Shift while "
                "clicking to remove all gestures (confirmation required; "
                "cannot be undone)"
            ],
            "删除当前手势\n"
            "按住 Ctrl+Alt+Shift 点击可删除全部手势（需确认；不可撤销）",
        )


if __name__ == "__main__":
    unittest.main()
