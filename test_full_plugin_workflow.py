#!/usr/bin/env python3
"""
Test script to verify the full workflow with the inject_updated_translations plugin.
This simulates what happens when translate_with_openai.py is called with the plugin active.
"""

import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

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


def test_full_workflow():
    """Test the full translation workflow with the ACTION plugin"""
    print("=" * 70)
    print("TEST: Full Translation Workflow with ACTION Plugin")
    print("=" * 70)

    REPORTS_DIR = BASE_DIR / "reports"
    UPDATED_FILE = REPORTS_DIR / "payment_terms_translations_UPDATED.csv"
    TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
    READY_TO_TRANSLATIONS = REPORTS_DIR / "ready_to_translations.csv"

    # Check prerequisites
    if not UPDATED_FILE.exists():
        print_colored(f"\n❌ Missing file: {UPDATED_FILE.name}", Fore.RED)
        return False

    print_colored(f"\n✅ Found updated file: {UPDATED_FILE.name}", Fore.GREEN)

    # Backup existing files
    import shutil
    backup_done = None
    if TRANSLATION_DONE_FILE.exists():
        backup_done = REPORTS_DIR / "translation_done.csv.backup"
        shutil.copy(TRANSLATION_DONE_FILE, backup_done)

    try:
        # Import the translation module
        from lokalise_translation_manager.translator import translate_with_openai

        print_colored("\n" + "=" * 70, Fore.CYAN)
        print_colored("SIMULATING: translate_with_openai.main()", Fore.CYAN)
        print_colored("=" * 70, Fore.CYAN)

        # Create a mock input file if it doesn't exist
        if not READY_TO_TRANSLATIONS.exists():
            print_colored("\n⚠️  Creating mock ready_to_translations.csv", Fore.YELLOW)
            with READY_TO_TRANSLATIONS.open('w', encoding='utf-8') as f:
                f.write("key_id,key_name,en,languages,translation_id\n")
                f.write("123,test_key,Test,en,456\n")

        # Run the discover_plugins function
        prompt_plugins, action_plugins, extension_plugins = translate_with_openai.discover_plugins()

        print_colored("\n📋 Plugin Discovery Results:", Fore.CYAN)
        print(f"   - PROMPT plugins: {len(prompt_plugins)}")
        print(f"   - ACTION plugins: {len(action_plugins)}")
        print(f"   - EXTENSION plugins: {len(extension_plugins)}")

        if 'inject_updated_translations.py' not in action_plugins:
            print_colored("\n⚠️  inject_updated_translations.py not found in ACTION plugins", Fore.YELLOW)
            print_colored(f"     Found: {action_plugins}", Fore.YELLOW)
        else:
            print_colored("\n✅ inject_updated_translations.py found in ACTION plugins", Fore.GREEN)

        # Run ACTION plugins
        print_colored("\n" + "-" * 70, Fore.CYAN)
        print_colored("Running ACTION plugins...", Fore.CYAN)
        print_colored("-" * 70, Fore.CYAN)

        should_bypass = translate_with_openai.run_plugins(action_plugins, "ACTION")

        print_colored("\n" + "-" * 70, Fore.CYAN)

        if should_bypass:
            print_colored("\n✅ Bypass signal received from ACTION plugin", Fore.GREEN)
            print_colored("   Translation step would be skipped", Fore.GREEN)

            # Verify translation_done.csv was created
            if TRANSLATION_DONE_FILE.exists():
                print_colored("✅ translation_done.csv was created", Fore.GREEN)

                # Check the content
                import csv
                from lokalise_translation_manager.utils.csv_utils import detect_csv_delimiter

                delimiter = detect_csv_delimiter(TRANSLATION_DONE_FILE)
                with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    rows = list(reader)
                    print_colored(f"✅ File contains {len(rows)} translation rows", Fore.GREEN)
                    print_colored(f"✅ Delimiter: '{delimiter}'", Fore.GREEN)

                print_colored("\n🎉 Full workflow test PASSED!", Fore.GREEN)
                return True
            else:
                print_colored("\n❌ translation_done.csv was not created", Fore.RED)
                return False
        else:
            print_colored("\n❌ No bypass signal received", Fore.RED)
            return False

    except Exception as e:
        print_colored(f"\n❌ Test failed with error: {e}", Fore.RED)
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore backups
        if backup_done and backup_done.exists():
            shutil.copy(backup_done, TRANSLATION_DONE_FILE)
            backup_done.unlink()
            print_colored(f"\n   Restored original translation_done.csv", Fore.CYAN)


def test_workflow_summary():
    """Print a summary of how the workflow works"""
    print("\n" + "=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)
    print("""
When the inject_updated_translations plugin is active:

1. User renames reviewed CSV to: payment_terms_translations_UPDATED.csv

2. User runs: python3 run.py (or ./LokaliseTool.command)

3. The tool runs through the pipeline until Step 7 (Translation)

4. translate_with_openai.py discovers and runs ACTION plugins

5. inject_updated_translations plugin:
   ✓ Detects the _UPDATED.csv file
   ✓ Validates CSV structure (columns, data consistency)
   ✓ Auto-detects delimiter (handles ; or ,)
   ✓ Normalizes delimiter to comma
   ✓ Writes to translation_done.csv
   ✓ Returns True to signal bypass

6. translate_with_openai.py skips OpenAI translation

7. Pipeline continues to Step 8: Upload to Lokalise

8. Translations from the reviewed file are uploaded

Benefits:
- No OpenAI API calls = No cost
- Supports both ; and , delimiters
- Validates data before upload
- Seamlessly integrates with existing workflow
""")
    print("=" * 70)


def main():
    print("\n" + "=" * 70)
    print("TESTING: Full Plugin Workflow")
    print("=" * 70 + "\n")

    success = test_full_workflow()

    test_workflow_summary()

    print("\n" + "=" * 70)
    if success:
        print_colored("FINAL RESULT: ALL TESTS PASSED ✅", Fore.GREEN)
    else:
        print_colored("FINAL RESULT: TESTS FAILED ❌", Fore.RED)
    print("=" * 70 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
