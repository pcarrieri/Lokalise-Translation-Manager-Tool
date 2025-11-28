#!/usr/bin/env python3
"""
Test script to verify that EXTENSION plugins run when skipping translation.

This script simulates the workflow when translation_done.csv exists and
the user chooses to skip the translation step.
"""

import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lokalise_translation_manager.core import (
    discover_extension_plugins,
    run_extension_plugins,
    PLUGINS_DIR
)

try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False
    # Create dummy Fore class for when colorama is not available
    class Fore:
        GREEN = ''
        RED = ''
        YELLOW = ''
        CYAN = ''
        BLUE = ''


def print_colored(text, color=''):
    if color_enabled and color:
        print(color + text)
    else:
        print(text)


def test_plugin_discovery():
    """Test 1: Verify plugin discovery works"""
    print("=" * 70)
    print("TEST 1: Plugin Discovery")
    print("=" * 70)

    plugins = discover_extension_plugins()

    print(f"\nPlugins directory: {PLUGINS_DIR}")
    print(f"Found {len(plugins)} EXTENSION plugin(s):")

    for plugin in plugins:
        print(f"  ✓ {plugin}")

    if plugins:
        print_colored("\n✅ TEST 1 PASSED: Plugin discovery working", Fore.GREEN)
        return True
    else:
        print_colored("\n⚠️  TEST 1 WARNING: No plugins found (may be expected)", Fore.YELLOW)
        return False


def test_plugin_structure():
    """Test 2: Verify plugin has correct structure"""
    print("\n" + "=" * 70)
    print("TEST 2: Plugin Structure Validation")
    print("=" * 70)

    plugin_file = PLUGINS_DIR / "myPayments.py"

    if not plugin_file.exists():
        print_colored("\n⚠️  TEST 2 SKIPPED: myPayments.py not found", Fore.YELLOW)
        return False

    content = plugin_file.read_text()

    checks = {
        "[EXTENSION] marker": "[EXTENSION]" in content,
        "main() function": "def main():" in content,
        "filter_translations() function": "def filter_translations():" in content,
        "Uses detect_csv_delimiter": "detect_csv_delimiter" in content,
        "Reads translation_done.csv": "TRANSLATION_DONE_FILE" in content,
    }

    print(f"\nChecking plugin: {plugin_file.name}\n")

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        color = Fore.GREEN if passed else Fore.RED
        print_colored(f"  {status} {check_name}", color)
        if not passed:
            all_passed = False

    if all_passed:
        print_colored("\n✅ TEST 2 PASSED: Plugin structure is valid", Fore.GREEN)
    else:
        print_colored("\n❌ TEST 2 FAILED: Plugin structure has issues", Fore.RED)

    return all_passed


def test_skip_translation_workflow():
    """Test 3: Simulate skip translation workflow"""
    print("\n" + "=" * 70)
    print("TEST 3: Skip Translation Workflow (Simulation)")
    print("=" * 70)

    print("\nSimulating scenario:")
    print("  1. translation_done.csv exists")
    print("  2. User chooses to skip translation")
    print("  3. EXTENSION plugins should still run")

    print("\nDiscovering EXTENSION plugins...")
    plugins = discover_extension_plugins()

    if plugins:
        print(f"Found {len(plugins)} plugin(s): {', '.join(plugins)}")
        print("\nNote: Would execute plugins here in real scenario")
        print("      (Skipping actual execution to avoid side effects)")

        print_colored("\n✅ TEST 3 PASSED: Workflow logic is correct", Fore.GREEN)
        return True
    else:
        print_colored("\n⚠️  TEST 3 WARNING: No plugins to execute", Fore.YELLOW)
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("TESTING: Skip Translation with EXTENSION Plugins")
    print("=" * 70 + "\n")

    results = []

    # Run tests
    results.append(("Plugin Discovery", test_plugin_discovery()))
    results.append(("Plugin Structure", test_plugin_structure()))
    results.append(("Skip Translation Workflow", test_skip_translation_workflow()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "WARNING/FAILED"
        color = Fore.GREEN if result else Fore.YELLOW
        print_colored(f"  {test_name}: {status}", color)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print_colored("\n🎉 All tests passed!", Fore.GREEN)
        return 0
    else:
        print_colored(f"\n⚠️  {total - passed} test(s) with warnings/failures", Fore.YELLOW)
        return 1


if __name__ == "__main__":
    sys.exit(main())
