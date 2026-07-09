"""
BH Import Chain Smoke Test
Verifies all module imports resolve correctly.
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def check_import(module_path, expected_attr=None):
    """Try to import a module and optionally check an attribute"""
    try:
        mod = __import__(module_path, fromlist=[expected_attr] if expected_attr else [])
        if expected_attr:
            attr = getattr(mod, expected_attr, None)
            assert attr is not None, f"{module_path} has no {expected_attr}"
        print(f"  \u2713 {module_path}" + (f".{expected_attr}" if expected_attr else ""))
        return True
    except Exception as e:
        print(f"  \u2717 {module_path}: {e}")
        return False

if __name__ == "__main__":
    print(f"\n{'='*50}")
    print("BH IMPORT CHAIN SMOKE TEST")
    print(f"{'='*50}\n")

    imports = [
        # Core modules
        ("src.core",),
        ("src.core.base_agent", "BaseAgent"),
        ("src.core.agent_loop", "AgentLoop"),
        ("src.core.llm_provider", "LLMProvider"),
        ("src.core.event_bus", "EventBus"),
        ("src.core.tool_registry", "ToolRegistry"),

        # Agent modules
        ("src.agents",),
        ("src.agents.registry", "AgentRegistry"),

        # Colony modules
        ("src.colony",),

        # Top-level modules
        ("src.colony_bridge", "ColonyBridge"),
        ("src.colony_bridge", "COLONY_CAPABILITIES"),

        # Original files (should still import)
        ("src.hermes_quant", "blackhornet"),
    ]

    results = []
    for imp in imports:
        module_path = imp[0]
        expected_attr = imp[1] if len(imp) > 1 else None
        ok = check_import(module_path, expected_attr)
        results.append(ok)

    passed = sum(1 for r in results if r)
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{len(results)} imports resolved")
    if passed == len(results):
        print("STATUS: ALL PASSED \u2713")
        sys.exit(0)
    else:
        print(f"STATUS: {len(results)-passed} FAILED \u2717")
        sys.exit(1)
    print(f"{'='*50}")
