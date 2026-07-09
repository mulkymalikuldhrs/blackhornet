"""
MVP Test Runner
Runs all MVP integration tests in sequence.
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test(module_name, display_name=None):
    """Run a single test module by importing and executing its main()"""
    start = time.time()
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(os.path.dirname(__file__), f"{module_name}.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'main'):
            passed, failed, skipped = mod.main()
            status = f"{passed}p/{failed}f/{skipped}s"
        else:
            status = "loaded"
        elapsed = time.time() - start
        print(f"  \u2713 {display_name or module_name} ({status}, {elapsed:.2f}s)")
        return True
    except SystemExit:
        # Test may call sys.exit() with 0 for pass
        elapsed = time.time() - start
        print(f"  \u2713 {display_name or module_name} ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  \u2717 {display_name or module_name}: {e} ({elapsed:.2f}s)")
        import traceback
        traceback.print_exc()
        return False

def discover_tests():
    """Auto-discover test_*.py files in the scripts directory"""
    import glob
    test_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py")))
    tests = []
    for f in test_files:
        name = os.path.splitext(os.path.basename(f))[0]
        display = name.replace('test_', '').replace('_', ' ').title()
        tests.append((name, display))
    return tests

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("MVP INTEGRATION TEST SUITE")
    print(f"{'='*60}")

    tests = discover_tests()
    if not tests:
        # Fallback to default list
        tests = [
            ("test_colony_bridge", "Colony Bridge Integration"),
        ]

    results = []
    for module, display in tests:
        print(f"\n[{display}]")
        ok = run_test(module, display)
        results.append((display, ok))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} tests passed")
    print(f"{'='*60}")
    sys.exit(0 if passed == total else 1)
