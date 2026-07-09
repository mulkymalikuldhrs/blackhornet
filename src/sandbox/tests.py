"""Tests for FASE 7: Sandbox Self-Modification.

Run: python3 src/sandbox/tests.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestSandboxManager(unittest.TestCase):
    """7.1 SandboxManager — isolated sandbox environments."""

    def setUp(self):
        from src.sandbox.sandbox_manager import SandboxManager
        self.temp = tempfile.mkdtemp()
        self.sm = SandboxManager(base_dir=self.temp)

    def tearDown(self):
        self.sm.destroy_all()
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_create_and_get(self):
        sb = self.sm.create("test_sb")
        self.assertEqual(sb.id, "test_sb")
        got = self.sm.get("test_sb")
        self.assertIsNotNone(got)

    def test_write_and_read_file(self):
        sb = self.sm.create("rw_test")
        self.sm.write_file("rw_test", "hello.txt", "world")
        content = self.sm.read_file("rw_test", "hello.txt")
        self.assertEqual(content, "world")

    def test_list_files(self):
        sb = self.sm.create("list_test")
        self.sm.write_file("list_test", "a.txt", "a")
        self.sm.write_file("list_test", "b.txt", "b")
        files = self.sm.list_files("list_test")
        self.assertEqual(len(files), 2)

    def test_destroy(self):
        sb = self.sm.create("destroy_me")
        self.assertTrue(self.sm.destroy("destroy_me"))
        self.assertIsNone(self.sm.get("destroy_me"))

    def test_stats(self):
        self.sm.create("sb1")
        self.sm.create("sb2")
        stats = self.sm.stats()
        self.assertEqual(stats["active_sandboxes"], 2)


class TestCodeExecutor(unittest.TestCase):
    """7.2 CodeExecutor — execute code safely."""

    def setUp(self):
        from src.sandbox.code_executor import CodeExecutor
        self.ce = CodeExecutor(timeout=10)

    def test_execute_code_success(self):
        result = self.ce.execute_code("print('hello')")
        self.assertTrue(result.success)
        self.assertIn("hello", result.stdout)

    def test_execute_code_error(self):
        result = self.ce.execute_code("raise ValueError('test')")
        self.assertFalse(result.success)

    def test_execute_file_not_found(self):
        result = self.ce.execute_file("/nonexistent/test.py")
        self.assertFalse(result.success)

    def test_execute_module(self):
        result = self.ce.execute_module("this_module_does_not_exist_xyz")
        self.assertFalse(result.success)


class TestSelfModifier(unittest.TestCase):
    """7.3 SelfModifier — modify own source code."""

    def setUp(self):
        from src.sandbox.sandbox_manager import SandboxManager
        from src.sandbox.code_executor import CodeExecutor
        from src.sandbox.self_modifier import SelfModifier
        self.temp = tempfile.mkdtemp()
        self.sm = SandboxManager(base_dir=self.temp)
        self.ce = CodeExecutor(timeout=10)
        self.mod = SelfModifier(sandbox_manager=self.sm, code_executor=self.ce)

    def tearDown(self):
        import shutil
        self.sm.destroy_all()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_apply_patch(self):
        sb = self.sm.create("patch_test")
        self.sm.write_file("patch_test", "test.py", "print('old')\nprint('unchanged')")
        result = self.mod.apply_patch("patch_test", "test.py", "print('old')", "print('new')")
        self.assertTrue(result)
        content = self.sm.read_file("patch_test", "test.py")
        self.assertIn("print('new')", content)
        self.assertIn("print('unchanged')", content)

    def test_modify_and_test(self):
        import os as _os
        src_dir = _os.path.join(self.temp, "src")
        _os.makedirs(src_dir)
        src_file = _os.path.join(src_dir, "module.py")
        with open(src_file, "w") as f:
            f.write("def greet():\n    return 'hello'\n")
        test_file = _os.path.join(src_dir, "test_module.py")
        with open(test_file, "w") as f:
            f.write("""
import unittest
import sys
sys.path.insert(0, '.')
from module import greet
class TestGreet(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet(), 'hello')
if __name__ == '__main__':
    unittest.main()
""")
        result = self.mod.modify_and_test(
            [src_file],
            "'hello'",
            "'hi'",
            f"cd '{src_dir}' && python3 test_module.py",
        )
        self.assertFalse(result.success)  # Test should fail after change


class TestTestRunner(unittest.TestCase):
    """7.4 TestRunner — run tests and measure pass rate."""

    def setUp(self):
        from src.sandbox.test_runner import TestRunner
        self.tr = TestRunner(timeout=10)

    def test_run_single_file_passing(self):
        import tempfile, os
        tmp = tempfile.mkdtemp()
        fpath = os.path.join(tmp, "test_pass.py")
        with open(fpath, "w") as f:
            f.write("""
import unittest
class TestPass(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)
    def test_two(self):
        self.assertTrue(True)
if __name__ == '__main__':
    unittest.main()
""")
        summary = self.tr.run_single_file(fpath)
        self.assertEqual(summary.total, 2)
        self.assertGreater(summary.pass_rate, 0.5)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    def test_threshold_check(self):
        from src.sandbox.test_runner import TestSummary
        ts = TestSummary(total=10, passed=9, failed=1)
        ts.pass_rate = self.tr._compute_rate(ts)
        self.assertTrue(self.tr.is_pass_rate_above_threshold(ts, 0.8))
        self.assertFalse(self.tr.is_pass_rate_above_threshold(ts, 0.95))


class TestAutoMerger(unittest.TestCase):
    """7.5 AutoMerger — auto-merge with test validation."""

    def setUp(self):
        from src.sandbox.sandbox_manager import SandboxManager
        from src.sandbox.code_executor import CodeExecutor
        from src.sandbox.self_modifier import SelfModifier
        from src.sandbox.test_runner import TestRunner
        from src.sandbox.auto_merger import AutoMerger
        self.temp = tempfile.mkdtemp()
        self.sbox = SandboxManager(base_dir=self.temp)
        self.exec = CodeExecutor(timeout=10)
        self.mod = SelfModifier(sandbox_manager=self.sbox, code_executor=self.exec)
        self.tr = TestRunner(timeout=10)
        self.merger = AutoMerger(
            sandbox_manager=self.sbox,
            self_modifier=self.mod,
            test_runner=self.tr,
            pass_threshold=0.5,
        )

    def tearDown(self):
        import shutil
        self.sbox.destroy_all()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_merge_fails_gracefully(self):
        report = self.merger.merge(
            ["/nonexistent/source.py"],
            "old", "new",
            "python3 -c 'print(1)'",
            description="test merge",
        )
        self.assertFalse(report.success)

    def test_stats(self):
        stats = self.merger.stats()
        self.assertIn("pass_threshold", stats)


if __name__ == "__main__":
    unittest.main()
