#!/usr/bin/env python3
"""
Test script to verify the inject_updated_translations plugin works correctly.
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


def test_plugin_execution():
    """Test that the plugin executes correctly and validates the CSV"""
    print("=" * 70)
    print("TEST: inject_updated_translations Plugin Execution")
    print("=" * 70)

    # Import the plugin
    try:
        from lokalise_translation_manager.plugins import inject_updated_translations
        print_colored("\n✅ Plugin imported successfully", Fore.GREEN)
    except ImportError as e:
        print_colored(f"\n❌ Failed to import plugin: {e}", Fore.RED)
        return False

    # Check if the updated file exists
    REPORTS_DIR = BASE_DIR / "reports"
    UPDATED_FILE = REPORTS_DIR / "payment_terms_translations_UPDATED.csv"
    TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"

    if not UPDATED_FILE.exists():
        print_colored(f"\n⚠️  File not found: {UPDATED_FILE.name}", Fore.YELLOW)
        print_colored("     Please ensure payment_terms_translations_UPDATED.csv exists", Fore.YELLOW)
        return False

    print_colored(f"\n✅ Found updated file: {UPDATED_FILE.name}", Fore.GREEN)

    # Backup the original translation_done.csv if it exists
    backup_file = None
    if TRANSLATION_DONE_FILE.exists():
        backup_file = REPORTS_DIR / "translation_done.csv.backup"
        import shutil
        shutil.copy(TRANSLATION_DONE_FILE, backup_file)
        print_colored(f"   Backed up existing translation_done.csv", Fore.CYAN)

    # Run the plugin
    try:
        print("\n" + "-" * 70)
        result = inject_updated_translations.run()
        print("-" * 70)

        if result is True:
            print_colored("\n✅ Plugin returned True (bypass signal)", Fore.GREEN)
        else:
            print_colored("\n❌ Plugin returned False (should return True)", Fore.RED)
            return False

        # Verify that translation_done.csv was created
        if not TRANSLATION_DONE_FILE.exists():
            print_colored("\n❌ translation_done.csv was not created", Fore.RED)
            return False

        print_colored(f"✅ translation_done.csv was created successfully", Fore.GREEN)

        # Verify the delimiter is comma
        from lokalise_translation_manager.utils.csv_utils import detect_csv_delimiter
        delimiter = detect_csv_delimiter(TRANSLATION_DONE_FILE)

        if delimiter == ',':
            print_colored(f"✅ CSV delimiter normalized to comma", Fore.GREEN)
        else:
            print_colored(f"⚠️  CSV delimiter is '{delimiter}' (expected comma)", Fore.YELLOW)

        # Verify the structure
        import csv
        with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)
            fieldnames = reader.fieldnames

            required_cols = ['key_name', 'key_id', 'languages', 'translation_id', 'translation', 'translated']
            missing_cols = [col for col in required_cols if col not in fieldnames]

            if missing_cols:
                print_colored(f"❌ Missing columns: {', '.join(missing_cols)}", Fore.RED)
                return False

            print_colored(f"✅ All required columns present", Fore.GREEN)
            print_colored(f"✅ File contains {len(rows)} rows", Fore.GREEN)

        print_colored("\n🎉 All checks passed!", Fore.GREEN)
        return True

    except Exception as e:
        print_colored(f"\n❌ Plugin execution failed: {e}", Fore.RED)
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore the backup if it exists
        if backup_file and backup_file.exists():
            import shutil
            shutil.copy(backup_file, TRANSLATION_DONE_FILE)
            backup_file.unlink()
            print_colored(f"\n   Restored original translation_done.csv from backup", Fore.CYAN)


def main():
    print("\n" + "=" * 70)
    print("TESTING: inject_updated_translations Plugin")
    print("=" * 70 + "\n")

    success = test_plugin_execution()

    print("\n" + "=" * 70)
    if success:
        print_colored("TEST RESULT: PASSED ✅", Fore.GREEN)
    else:
        print_colored("TEST RESULT: FAILED ❌", Fore.RED)
    print("=" * 70 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
