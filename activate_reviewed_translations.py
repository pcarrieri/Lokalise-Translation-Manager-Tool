#!/usr/bin/env python3
"""
Utility script to activate the inject_updated_translations plugin.
Renames a reviewed CSV file to payment_terms_translations_UPDATED.csv
"""

import sys
from pathlib import Path

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


def list_csv_files(reports_dir):
    """List all CSV files in the reports directory"""
    csv_files = [f for f in reports_dir.glob('*.csv') if f.is_file()]
    return sorted(csv_files, key=lambda x: x.name)


def main():
    BASE_DIR = Path(__file__).resolve().parent
    REPORTS_DIR = BASE_DIR / "reports"
    TARGET_NAME = "payment_terms_translations_UPDATED.csv"
    TARGET_FILE = REPORTS_DIR / TARGET_NAME

    print_colored("\n" + "=" * 70, Fore.CYAN)
    print_colored("Activate Reviewed Translations Plugin", Fore.CYAN)
    print_colored("=" * 70, Fore.CYAN)

    # Check if target file already exists
    if TARGET_FILE.exists():
        print_colored(f"\n⚠️  File '{TARGET_NAME}' already exists!", Fore.YELLOW)
        response = input("\nDo you want to replace it? (y/n): ").strip().lower()
        if response not in ['y', 'yes', 's', 'si']:
            print_colored("\nOperation cancelled.", Fore.YELLOW)
            return 0
        # Delete the existing file
        TARGET_FILE.unlink()
        print_colored(f"✅ Deleted existing '{TARGET_NAME}'", Fore.GREEN)

    # List available CSV files
    csv_files = list_csv_files(REPORTS_DIR)

    if not csv_files:
        print_colored("\n❌ No CSV files found in /reports/", Fore.RED)
        return 1

    print_colored("\n📂 Available CSV files in /reports/:", Fore.CYAN)
    print()
    for idx, file in enumerate(csv_files, start=1):
        size_kb = file.stat().st_size / 1024
        print(f"  {idx}. {file.name:<45} ({size_kb:>7.1f} KB)")

    print()
    print_colored("Enter the number of the file to use (or 'q' to quit):", Fore.YELLOW)

    try:
        choice = input("\nYour choice: ").strip()

        if choice.lower() == 'q':
            print_colored("\nOperation cancelled.", Fore.YELLOW)
            return 0

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(csv_files):
            print_colored(f"\n❌ Invalid choice. Please enter a number between 1 and {len(csv_files)}", Fore.RED)
            return 1

        selected_file = csv_files[choice_num - 1]

        # Copy the file
        import shutil
        shutil.copy(selected_file, TARGET_FILE)

        print_colored(f"\n✅ Successfully created '{TARGET_NAME}'", Fore.GREEN)
        print_colored(f"   Source: {selected_file.name}", Fore.CYAN)

        # Validate the structure
        print_colored("\n📋 Validating CSV structure...", Fore.CYAN)

        sys.path.insert(0, str(BASE_DIR))
        from lokalise_translation_manager.plugins import inject_updated_translations

        is_valid, message, delimiter, rows = inject_updated_translations.validate_csv_structure(TARGET_FILE)

        if is_valid:
            print_colored(f"✅ {message}", Fore.GREEN)
            print_colored(f"   Detected delimiter: '{delimiter}'", Fore.CYAN)
            print_colored("\n🎉 Ready to use! Run the tool with:", Fore.GREEN)
            print_colored("   python3 run.py", Fore.CYAN)
        else:
            print_colored(f"\n❌ Validation failed: {message}", Fore.RED)
            print_colored("\nThe file structure is not compatible. Required columns:", Fore.YELLOW)
            for col in inject_updated_translations.REQUIRED_COLUMNS:
                print_colored(f"  - {col}", Fore.YELLOW)
            TARGET_FILE.unlink()
            print_colored(f"\nDeleted invalid file '{TARGET_NAME}'", Fore.YELLOW)
            return 1

    except ValueError:
        print_colored("\n❌ Invalid input. Please enter a number.", Fore.RED)
        return 1
    except KeyboardInterrupt:
        print_colored("\n\nOperation cancelled by user.", Fore.YELLOW)
        return 0
    except Exception as e:
        print_colored(f"\n❌ Error: {e}", Fore.RED)
        import traceback
        traceback.print_exc()
        return 1

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
