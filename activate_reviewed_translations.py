#!/usr/bin/env python3
"""
Activate Reviewed Translations Plugin - Interactive File Selector

This utility script activates the inject_updated_translations plugin by copying
a reviewed CSV file to the special filename that triggers the plugin:
payment_terms_translations_UPDATED.csv

Purpose:
    The inject_updated_translations plugin automatically detects and processes
    files named payment_terms_translations_UPDATED.csv. This script provides
    an interactive interface to select which reviewed translation file should
    be activated.

Workflow:
    1. Check if target file already exists
    2. Prompt for replacement if needed
    3. List all available CSV files in reports/
    4. Display file sizes for reference
    5. User selects file by number
    6. Copy selected file to target name
    7. Validate CSV structure
    8. Confirm plugin is ready to use

Plugin Integration:
    - Target filename: payment_terms_translations_UPDATED.csv
    - Location: reports/
    - Validation: Uses inject_updated_translations.validate_csv_structure()
    - Required columns: key_id, key_name, language_iso, translation_id,
                       new_translation, modified_at

Features:
    - Interactive file selection with numbering
    - File size display for easy identification
    - Automatic CSV structure validation
    - Colorama support for enhanced output
    - Graceful error handling
    - Confirmation messages

Required CSV Structure:
    key_id,key_name,language_iso,translation_id,new_translation,modified_at
    123,ms_test,it,456,Ciao,2024-01-15T10:30:00Z

Usage:
    python3 activate_reviewed_translations.py

    Then follow the interactive prompts:
    1. Confirm replacement if file exists
    2. Enter number of file to use
    3. Or enter 'q' to quit

Example Session:
    $ python3 activate_reviewed_translations.py

    ======================================================================
    Activate Reviewed Translations Plugin
    ======================================================================

    📂 Available CSV files in /reports/:

      1. final_report.csv                           (    45.2 KB)
      2. translation_done.csv                       (    89.1 KB)
      3. merged_result.csv                          (    12.3 KB)

    Enter the number of the file to use (or 'q' to quit):

    Your choice: 1

    ✅ Successfully created 'payment_terms_translations_UPDATED.csv'
       Source: final_report.csv

    📋 Validating CSV structure...
    ✅ Valid CSV structure with 150 rows
       Detected delimiter: ','

    🎉 Ready to use! Run the tool with:
       python3 run.py

Safety Features:
    - Warns before overwriting existing file
    - Validates CSV structure before confirming
    - Deletes invalid files automatically
    - Shows required columns if validation fails

Exit Codes:
    0: Success
    1: Error (invalid choice, validation failed, etc.)

Error Handling:
    - ValueError: Invalid numeric input
    - KeyboardInterrupt: User cancellation (Ctrl+C)
    - Exception: General errors with traceback
"""

import sys
from pathlib import Path
from typing import List

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


def print_colored(text: str, color: str = '') -> None:
    """
    Print colored text to console with colorama fallback.

    Args:
        text: Text to print
        color: Colorama color code (Fore.RED, Fore.GREEN, etc.)

    Note:
        If colorama is not available, prints plain text without colors.
        The Fore class is stubbed with empty strings when colorama is missing.
    """
    if color_enabled and color:
        print(color + text)
    else:
        print(text)


def list_csv_files(reports_dir: Path) -> List[Path]:
    """
    List all CSV files in the reports directory.

    Args:
        reports_dir: Path to the reports directory

    Returns:
        List[Path]: Sorted list of CSV file paths

    Note:
        - Only includes files (not directories)
        - Filters by .csv extension
        - Sorted alphabetically by filename
        - Returns empty list if directory doesn't exist or has no CSV files
    """
    csv_files = [f for f in reports_dir.glob('*.csv') if f.is_file()]
    return sorted(csv_files, key=lambda x: x.name)


def main() -> int:
    """
    Main function to activate reviewed translations plugin.

    Provides interactive interface for selecting and activating a reviewed
    translation CSV file. The selected file is copied to the special name
    that triggers the inject_updated_translations plugin.

    Returns:
        int: Exit code (0 for success, 1 for error)

    Workflow:
        1. Display banner
        2. Check if target file exists
        3. Prompt for replacement if needed
        4. List available CSV files with sizes
        5. Get user selection
        6. Copy selected file to target name
        7. Validate CSV structure
        8. Display confirmation or error

    User Interactions:
        - "Do you want to replace it? (y/n)": Replace existing file
        - "Enter the number of the file to use (or 'q' to quit)": File selection
        - Valid responses: 1-N (file number), 'q' (quit)

    Validation:
        Uses inject_updated_translations.validate_csv_structure() to verify:
        - Required columns present
        - CSV delimiter detection
        - Row count

    Exit Codes:
        0: Success - file activated and validated
        1: Error - invalid choice, validation failed, file not found, etc.

    Error Handling:
        ValueError: Invalid numeric input → Returns 1
        KeyboardInterrupt: User cancelled (Ctrl+C) → Returns 0
        Exception: General error with traceback → Returns 1

    Example Output (Success):
        ======================================================================
        Activate Reviewed Translations Plugin
        ======================================================================

        📂 Available CSV files in /reports/:

          1. final_report.csv                           (    45.2 KB)
          2. translation_done.csv                       (    89.1 KB)

        Enter the number of the file to use (or 'q' to quit):

        Your choice: 1

        ✅ Successfully created 'payment_terms_translations_UPDATED.csv'
           Source: final_report.csv

        📋 Validating CSV structure...
        ✅ Valid CSV structure with 150 rows
           Detected delimiter: ','

        🎉 Ready to use! Run the tool with:
           python3 run.py

    Example Output (Error):
        ❌ Validation failed: Missing required column 'modified_at'

        The file structure is not compatible. Required columns:
          - key_id
          - key_name
          - language_iso
          - translation_id
          - new_translation
          - modified_at

        Deleted invalid file 'payment_terms_translations_UPDATED.csv'
    """
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
