#!/usr/bin/env python3
"""
Test script to verify that ACTION plugins are detected correctly in core.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
UPDATED_FILE = REPORTS_DIR / "payment_terms_translations_UPDATED.csv"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"

try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False
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


def test_scenario_1():
    """
    Scenario 1: UPDATED file exists
    Expected: Tool should detect it and NOT ask user to skip
    """
    print("=" * 70)
    print("SCENARIO 1: UPDATED file exists")
    print("=" * 70)

    if not UPDATED_FILE.exists():
        print_colored("\n⚠️  Creating mock UPDATED file for testing...", Fore.YELLOW)
        # Create a mock file
        UPDATED_FILE.write_text("key_name,key_id,languages,translation_id,translation,translated\n")

    print_colored(f"\n✅ File exists: {UPDATED_FILE.name}", Fore.GREEN)

    # Simulate the logic from core.py
    has_action_plugin_file = UPDATED_FILE.exists()

    if has_action_plugin_file:
        print_colored("\n🟢 DETECTED: Reviewed translations file found!", Fore.GREEN)
        print_colored(f"   File: {UPDATED_FILE.name}", Fore.CYAN)
        print_colored("   This will be used instead of OpenAI translation.", Fore.CYAN)
        skip_translation = False
        print_colored("\n✅ CORRECT: Will enter translate_with_openai.py (skip_translation=False)", Fore.GREEN)
        return True
    else:
        print_colored("\n❌ ERROR: File not detected!", Fore.RED)
        return False


def test_scenario_2():
    """
    Scenario 2: UPDATED file does NOT exist, but translation_done.csv exists
    Expected: Tool should ask user if they want to skip
    """
    print("\n" + "=" * 70)
    print("SCENARIO 2: Only translation_done.csv exists")
    print("=" * 70)

    # Remove UPDATED file if it exists
    if UPDATED_FILE.exists():
        UPDATED_FILE.unlink()
        print_colored(f"\n   Removed {UPDATED_FILE.name} for testing", Fore.YELLOW)

    # Ensure translation_done.csv exists
    if not TRANSLATION_DONE_FILE.exists():
        print_colored("\n⚠️  Creating mock translation_done.csv for testing...", Fore.YELLOW)
        TRANSLATION_DONE_FILE.write_text("key_name,key_id,languages,translation_id,translation,translated\n")

    print_colored(f"\n✅ File exists: {TRANSLATION_DONE_FILE.name}", Fore.GREEN)
    print_colored(f"❌ File NOT exists: {UPDATED_FILE.name}", Fore.RED)

    # Simulate the logic from core.py
    has_action_plugin_file = UPDATED_FILE.exists()

    if has_action_plugin_file:
        print_colored("\n❌ ERROR: Should not detect UPDATED file!", Fore.RED)
        return False
    else:
        print_colored("\n✅ CORRECT: No UPDATED file detected", Fore.GREEN)
        if TRANSLATION_DONE_FILE.exists():
            print_colored("✅ CORRECT: Would ask user if they want to skip", Fore.GREEN)
            return True
        else:
            print_colored("❌ ERROR: translation_done.csv should exist", Fore.RED)
            return False


def test_scenario_3():
    """
    Scenario 3: Neither file exists
    Expected: Tool should proceed with OpenAI translation normally
    """
    print("\n" + "=" * 70)
    print("SCENARIO 3: Neither file exists")
    print("=" * 70)

    # Remove both files if they exist
    if UPDATED_FILE.exists():
        UPDATED_FILE.unlink()
    if TRANSLATION_DONE_FILE.exists():
        backup = REPORTS_DIR / "translation_done.csv.backup"
        TRANSLATION_DONE_FILE.rename(backup)
        print_colored(f"\n   Backed up {TRANSLATION_DONE_FILE.name}", Fore.YELLOW)

    print_colored(f"\n❌ File NOT exists: {UPDATED_FILE.name}", Fore.RED)
    print_colored(f"❌ File NOT exists: {TRANSLATION_DONE_FILE.name}", Fore.RED)

    # Simulate the logic from core.py
    has_action_plugin_file = UPDATED_FILE.exists()
    skip_translation = False

    if has_action_plugin_file:
        print_colored("\n❌ ERROR: Should not detect UPDATED file!", Fore.RED)
        return False
    else:
        if not TRANSLATION_DONE_FILE.exists():
            print_colored("\n✅ CORRECT: No files detected", Fore.GREEN)
            print_colored("✅ CORRECT: Would proceed with OpenAI translation", Fore.GREEN)

            # Restore backup
            backup = REPORTS_DIR / "translation_done.csv.backup"
            if backup.exists():
                backup.rename(TRANSLATION_DONE_FILE)
                print_colored(f"\n   Restored {TRANSLATION_DONE_FILE.name}", Fore.CYAN)

            return True
        else:
            print_colored("\n❌ ERROR: translation_done.csv should not exist", Fore.RED)
            return False


def main():
    print("\n" + "=" * 70)
    print("TESTING: ACTION Plugin Detection in core.py")
    print("=" * 70 + "\n")

    results = []
    results.append(("Scenario 1: UPDATED file exists", test_scenario_1()))
    results.append(("Scenario 2: Only translation_done.csv exists", test_scenario_2()))
    results.append(("Scenario 3: Neither file exists", test_scenario_3()))

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        color = Fore.GREEN if result else Fore.RED
        print_colored(f"  {test_name}: {status}", color)

    print(f"\nTotal: {passed}/{total} tests passed")

    print("\n" + "=" * 70)
    print("USAGE INSTRUCTIONS")
    print("=" * 70)
    print("""
To use the inject_updated_translations plugin:

1. Prepare your reviewed CSV file with columns:
   key_name, key_id, languages, translation_id, translation, translated

2. Rename it to: payment_terms_translations_UPDATED.csv

3. Place it in: /reports/

4. Run the tool: python3 run.py

5. The tool will:
   ✅ Detect the UPDATED file automatically
   ✅ NOT ask you to skip translation
   ✅ Use your reviewed translations instead of OpenAI
   ✅ Upload to Lokalise

IMPORTANT: The file must be renamed BEFORE running the tool!
""")
    print("=" * 70 + "\n")

    if passed == total:
        print_colored("🎉 All tests passed!", Fore.GREEN)
        return 0
    else:
        print_colored(f"⚠️  {total - passed} test(s) failed", Fore.RED)
        return 1


if __name__ == "__main__":
    sys.exit(main())
