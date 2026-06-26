"""Tests for DeerFlow skill extension system."""
from __future__ import annotations

import unittest
from unittest import mock

from src.colony.orchestration.skill_ext import (
    SkillExecutionMode,
    SkillExtension,
    SkillExtensionSystem,
)


class TestSkillExtensionDataclass(unittest.TestCase):
    def test_default_mode_sync(self):
        ext = SkillExtension(
            name="test", module_path="math", function_name="sqrt",
        )
        self.assertEqual(ext.mode, SkillExecutionMode.SYNC)

    def test_default_enabled(self):
        ext = SkillExtension(
            name="test", module_path="math", function_name="sqrt",
        )
        self.assertTrue(ext.enabled)

    def test_custom_mode(self):
        ext = SkillExtension(
            name="test", module_path="math", function_name="sqrt",
            mode=SkillExecutionMode.DEFERRED,
        )
        self.assertEqual(ext.mode, SkillExecutionMode.DEFERRED)


class TestSkillExtensionSystem(unittest.TestCase):
    def setUp(self):
        self.system = SkillExtensionSystem()

    def test_register_extension_adds(self):
        ext = SkillExtension(
            name="sqrt", module_path="math", function_name="sqrt",
        )
        self.system.register_extension(ext)
        self.assertIn("sqrt", self.system.extensions)

    def test_load_extension_returns_function(self):
        ext = SkillExtension(
            name="sqrt", module_path="math", function_name="sqrt",
        )
        self.system.register_extension(ext)
        func = self.system.load_extension("sqrt")
        self.assertIsNotNone(func)
        self.assertEqual(func(9), 3.0)

    def test_load_extension_nonexistent_returns_none(self):
        result = self.system.load_extension("nonexistent")
        self.assertIsNone(result)

    def test_load_extension_bad_module_returns_none(self):
        ext = SkillExtension(
            name="bad", module_path="does.not.exist",
            function_name="nothing",
        )
        self.system.register_extension(ext)
        result = self.system.load_extension("bad")
        self.assertIsNone(result)

    def test_load_extension_bad_function_returns_none(self):
        ext = SkillExtension(
            name="bad", module_path="math",
            function_name="does_not_exist",
        )
        self.system.register_extension(ext)
        result = self.system.load_extension("bad")
        self.assertIsNone(result)

    def test_execute_loads_and_runs(self):
        ext = SkillExtension(
            name="floor", module_path="math", function_name="floor",
        )
        self.system.register_extension(ext)
        result = self.system.execute("floor", 3.9)
        self.assertEqual(result, 3)

    def test_execute_already_loaded_does_not_reload(self):
        ext = SkillExtension(
            name="ceil", module_path="math", function_name="ceil",
        )
        self.system.register_extension(ext)
        self.system.execute("ceil", 1.1)
        self.system.execute("ceil", 2.2)
        self.assertEqual(self.system.list_loaded(), ["ceil"])

    def test_execute_nonexistent_raises(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.system.execute("ghost")
        self.assertIn("ghost", str(ctx.exception))

    def test_list_loaded_empty_initially(self):
        self.assertEqual(self.system.list_loaded(), [])

    def test_list_loaded_after_loading(self):
        ext = SkillExtension(
            name="abs", module_path="math", function_name="fabs",
        )
        self.system.register_extension(ext)
        self.system.execute("abs", -5.0)
        self.assertIn("abs", self.system.list_loaded())

    def test_list_registered_returns_all(self):
        ext1 = SkillExtension(
            name="a", module_path="math", function_name="sqrt",
        )
        ext2 = SkillExtension(
            name="b", module_path="math", function_name="floor",
        )
        self.system.register_extension(ext1)
        self.system.register_extension(ext2)
        self.assertEqual(len(self.system.list_registered()), 2)

    def test_register_multiple_same_name_overwrites(self):
        ext1 = SkillExtension(
            name="dup", module_path="math", function_name="sqrt",
        )
        ext2 = SkillExtension(
            name="dup", module_path="math", function_name="floor",
        )
        self.system.register_extension(ext1)
        self.system.register_extension(ext2)
        self.assertEqual(self.system.extensions["dup"].function_name, "floor")

    def test_execute_with_multiple_args(self):
        ext = SkillExtension(
            name="pow", module_path="math", function_name="pow",
        )
        self.system.register_extension(ext)
        result = self.system.execute("pow", 2.0, 3.0)
        self.assertEqual(result, 8.0)

    @mock.patch("src.colony.orchestration.skill_ext.logger")
    def test_load_logs_info_on_success(self, mock_logger):
        ext = SkillExtension(
            name="sqrt", module_path="math", function_name="sqrt",
        )
        self.system.register_extension(ext)
        self.system.load_extension("sqrt")
        mock_logger.info.assert_called()

    @mock.patch("src.colony.orchestration.skill_ext.logger")
    def test_load_logs_warning_on_missing(self, mock_logger):
        self.system.load_extension("nope")
        mock_logger.warning.assert_called()

    @mock.patch("src.colony.orchestration.skill_ext.logger")
    def test_load_logs_error_on_failure(self, mock_logger):
        ext = SkillExtension(
            name="bad", module_path="nonexistent_module",
            function_name="nonexistent",
        )
        self.system.register_extension(ext)
        self.system.load_extension("bad")
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
