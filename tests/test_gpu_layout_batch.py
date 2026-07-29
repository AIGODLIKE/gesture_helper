from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "utils" / "gpu_layout_batch.py"
PACKAGE = "_gpu_layout_batch_test"


class GpuLayoutBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = (
            "gpu",
            "gpu_extras",
            "gpu_extras.batch",
            "mathutils",
            PACKAGE,
            f"{PACKAGE}.utils",
            f"{PACKAGE}.utils.color",
        )
        cls.old_modules = {name: sys.modules.get(name) for name in names}

        gpu = types.ModuleType("gpu")
        gpu_extras = types.ModuleType("gpu_extras")
        gpu_batch = types.ModuleType("gpu_extras.batch")
        gpu_batch.batch_for_shader = lambda *_args, **_kwargs: None
        mathutils = types.ModuleType("mathutils")
        mathutils.Vector = tuple

        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(MODULE_PATH.parents[1])]
        utils = types.ModuleType(f"{PACKAGE}.utils")
        utils.__path__ = [str(MODULE_PATH.parent)]
        color = types.ModuleType(f"{PACKAGE}.utils.color")
        color.color_to_gpu = tuple
        sys.modules.update({
            "gpu": gpu,
            "gpu_extras": gpu_extras,
            "gpu_extras.batch": gpu_batch,
            "mathutils": mathutils,
            PACKAGE: package,
            f"{PACKAGE}.utils": utils,
            color.__name__: color,
        })

        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.utils.gpu_layout_batch",
            MODULE_PATH,
        )
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop(f"{PACKAGE}.utils.gpu_layout_batch", None)
        for name, old in cls.old_modules.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old

    def test_snapshot_retains_commands_and_prepares_fill_batch(self):
        batch = self.module.GpuLayoutBatch()
        batch._fills = ["fill"]
        batch._strokes = ["stroke"]
        batch._content = ["content"]

        with mock.patch.object(
                self.module.GpuLayoutBatch,
                "_prepare_fills",
                return_value="prepared",
        ) as prepare:
            retained = batch.snapshot()

        prepare.assert_called_once_with(["fill"])
        self.assertEqual(retained._prepared_fills, "prepared")
        self.assertEqual(retained._fills, ["fill"])
        self.assertEqual(retained._strokes, ["stroke"])
        self.assertEqual(retained._content, ["content"])
        self.assertIsNot(retained._fills, batch._fills)

    def test_replay_uses_prepared_fill_and_retained_content(self):
        batch = self.module.GpuLayoutBatch()
        batch._fills = ["raw-fill"]
        batch._strokes = ["stroke"]
        batch._content = ["content"]
        batch._prepared_fills = "prepared-fill"

        with (
            mock.patch.object(
                self.module.GpuLayoutBatch,
                "_draw_fills",
            ) as raw_fills,
            mock.patch.object(
                self.module.GpuLayoutBatch,
                "_draw_prepared_fills",
            ) as prepared,
            mock.patch.object(
                self.module.GpuLayoutBatch,
                "_draw_strokes",
            ) as strokes,
            mock.patch.object(
                self.module.GpuLayoutBatch,
                "_draw_content",
            ) as content,
        ):
            batch.replay()

        raw_fills.assert_not_called()
        prepared.assert_called_once_with("prepared-fill")
        strokes.assert_called_once_with(["stroke"])
        content.assert_called_once_with(["content"])

    def test_flush_draws_once_and_releases_frame_commands(self):
        batch = self.module.GpuLayoutBatch()
        batch._fills = ["fill"]
        batch._strokes = ["stroke"]
        batch._content = ["content"]

        with mock.patch.object(
                self.module.GpuLayoutBatch,
                "_draw_commands",
        ) as draw:
            batch.flush()

        draw.assert_called_once_with(["fill"], ["stroke"], ["content"])
        self.assertEqual(batch._fills, [])
        self.assertEqual(batch._strokes, [])
        self.assertEqual(batch._content, [])


if __name__ == "__main__":
    unittest.main()
