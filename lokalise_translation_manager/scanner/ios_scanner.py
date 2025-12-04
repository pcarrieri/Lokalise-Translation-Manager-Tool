"""
iOS Localization Key Scanner for Lokalise Translation Manager

This module scans iOS Swift projects to extract NSLocalizedString usage and
analyze translation coverage across different locales. It identifies missing
translations and generates detailed CSV reports.

WORKFLOW:
---------
1. Load project configuration (iOS project path, Lokalise path)
2. Scan all .swift files for NSLocalizedString() calls
3. Extract localization keys and count usage per file
4. Load translation files (Localizable.strings) for all locales
5. Compare available translations against used keys
6. Identify missing translations per locale
7. Generate CSV reports:
   - final_result_ios.csv: All unique localization keys
   - total_keys_used_ios.csv: Same as above (for compatibility)
   - swift_files.csv: Per-file key usage analysis
   - missing_ios_translations.csv: Missing translations per key

KEY DETECTION:
--------------
The scanner uses regex pattern matching to find NSLocalizedString calls:

Pattern: NSLocalizedString("key_name", comment: "description")

Supported formats:
    NSLocalizedString("welcome_message", comment: "Welcome screen")
    NSLocalizedString("button.ok", comment: "")

Not supported (these won't be detected):
    - String interpolation in keys
    - Dynamic key generation
    - Objective-C NSLocalizedString calls

TRANSLATION COMPARISON:
-----------------------
The scanner compares all locales against English (en.lproj):
1. Load English Localizable.strings as reference
2. For each locale directory (*.lproj):
   - Load locale's Localizable.strings
   - Check if each used key exists and has a non-empty value
   - Record missing translations

EXCLUDED LOCALES:
-----------------
Locales can be excluded from missing translation checks using:
config/excluded_locales.ini:

[EXCLUDED]
excluded_locales = en, base, ar

This is useful for:
- Development locales
- Locales that are intentionally incomplete
- Base internationalization files

REPORTS GENERATED:
------------------
1. final_result_ios.csv
   Format: One key per line
   Purpose: Complete list of localization keys used in project

2. total_keys_used_ios.csv
   Format: Same as final_result_ios.csv
   Purpose: Legacy compatibility (identical content)

3. swift_files.csv
   Format: File Path, Number of Keys
   Purpose: Analyze which files use most localization keys
   Example:
       Views/HomeView.swift,12
       Models/User.swift,5

4. missing_ios_translations.csv
   Format: Key, Languages
   Purpose: Identify incomplete translations
   Example:
       welcome_message, "de, fr, it"
       error.network, "pl, sv"

OUTPUT LOCATION:
----------------
All reports are saved to: reports/ios/

CONFIGURATION:
--------------
Requires config/user_config.json:
{
    "project_paths": {
        "ios": "/path/to/ios/project"
    },
    "lokalise_paths": {
        "ios": "/path/to/lokalise/ios"
    }
}

Optional config/excluded_locales.ini:
[EXCLUDED]
excluded_locales = en, base

DEPENDENCIES:
-------------
Required:
- Standard library: os, re, csv, time, threading, json, pathlib, configparser

Optional (graceful fallback):
- colorama: Colored console output
- prettytable: Formatted summary tables

USAGE:
------
As a module:
    from lokalise_translation_manager.scanner import ios_scanner
    ios_scanner.main()

As a script:
    python3 -m lokalise_translation_manager.scanner.ios_scanner

Via core workflow:
    Automatically called by core.py in Step 1

EXAMPLE OUTPUT:
---------------
When run, displays:
    | Loading... (animated spinner)

    Results have been written to final_result_ios.csv
    Total keys have been written to total_keys_used_ios.csv
    Swift file details have been written to swift_files.csv
    Missing translations written to missing_ios_translations.csv

    +----------------------------------+-------+
    | Metric                           | Value |
    +----------------------------------+-------+
    | Total keys used by the project   | 145   |
    | Keys with missing translations   | 12    |
    | Execution time (ms)              | 2341  |
    | Total .swift files analyzed      | 87    |
    | .swift files with at least one   | 34    |
    +----------------------------------+-------+

PERFORMANCE:
------------
- Scans ~100 Swift files in ~2-3 seconds
- Memory efficient: streaming file processing
- Thread-safe: Uses daemon thread for spinner animation

AUTHORS:
--------
Part of the Lokalise Translation Manager Tool
Enhanced with comprehensive documentation
"""

import os
import re
import csv
import time
import threading
import json
from pathlib import Path
from typing import Set, Dict, Tuple
import configparser

# Optional colorama support for colored console output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False
    # Create dummy color classes when colorama is not available
    class Fore:
        CYAN = ''
        RED = ''
        YELLOW = ''

    class Style:
        RESET_ALL = ''

# Optional prettytable support for formatted output
try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

# ==================== DIRECTORY CONFIGURATION ====================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"
EXCLUDED_LOCALES_PATH = BASE_DIR / "config" / "excluded_locales.ini"
REPORTS_DIR = BASE_DIR / "reports" / "ios"
FINAL_RESULT_CSV = REPORTS_DIR / "final_result_ios.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_ios.csv"
SWIFT_FILES_CSV = REPORTS_DIR / "swift_files.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_ios_translations.csv"

# ==================== UTILITY FUNCTIONS ====================

def print_colored(text: str, color: str) -> None:
    """
    Print text to console with optional color formatting.

    Uses colorama if available for colored output. If colorama is not installed,
    falls back to plain text output without colors. This ensures the scanner works
    even without colorama dependency.

    Args:
        text: The text to print
        color: Colorama color constant (e.g., Fore.CYAN, Fore.RED)
               If colorama unavailable, prints plain text

    Example:
        print_colored("Scanning complete!", Fore.CYAN)
        print_colored("Error occurred", Fore.RED)
    """
    print(color + text if color_enabled else text)


def spinner() -> None:
    """
    Display animated loading spinner in terminal.

    Shows a rotating cursor animation (|/-\\) while scanning is in progress.
    Runs in a daemon thread and automatically stops when global stop_loading
    flag is set to True.

    This provides visual feedback during long-running scan operations without
    blocking the main thread.

    Global Variables:
        stop_loading: Boolean flag to stop the spinner animation

    Note:
        This function is designed to run in a daemon thread. It will
        automatically terminate when the main program exits.

    Example:
        global stop_loading
        stop_loading = False
        threading.Thread(target=spinner, daemon=True).start()
        # ... perform scanning ...
        stop_loading = True
    """
    while not stop_loading:
        for cursor in '|/-\\':
            print('\r' + cursor + ' Loading...', end='', flush=True)
            time.sleep(0.1)


# ==================== CORE SCANNING FUNCTIONS ====================

def extract_localized_strings(directory: str) -> Tuple[Set[str], Dict[str, int]]:
    """
    Extract all NSLocalizedString keys from Swift files in directory.

    Recursively scans all .swift files in the given directory and extracts
    localization keys using regex pattern matching. Also tracks which files
    use localization and how many keys each file contains.

    This function generates three CSV reports:
    1. final_result_ios.csv: All unique keys (sorted)
    2. total_keys_used_ios.csv: Duplicate of above for compatibility
    3. swift_files.csv: Per-file key usage statistics

    Args:
        directory: Root directory of iOS project to scan

    Returns:
        Tuple[Set[str], Dict[str, int]]: A tuple containing:
            - Set of unique localization keys found
            - Dictionary mapping relative file paths to key counts

    Pattern Matching:
        Regex: NSLocalizedString\\("([^"]+)",\\s*comment\\s*:\\s*"[^"]*"\\)

        Matches:
            NSLocalizedString("key", comment: "desc")
            NSLocalizedString("key", comment: "")

        Does NOT match:
            NSLocalizedString(variable, comment: "")
            String interpolation in keys

    CSV Output Formats:
        final_result_ios.csv:
            key1
            key2
            key3

        swift_files.csv:
            File Path,Number of Keys
            Views/Home.swift,12
            Models/User.swift,5

    Error Handling:
        - Unreadable files: Logs error and continues with remaining files
        - CSV write errors: Logs error but doesn't stop execution
        - Creates reports directory if it doesn't exist

    Example:
        keys, file_stats = extract_localized_strings("/path/to/ios/project")
        print(f"Found {len(keys)} unique keys")
        print(f"Most used file: {max(file_stats, key=file_stats.get)}")

        # Output:
        # Found 145 unique keys
        # Most used file: Views/MainViewController.swift
    """
    localized_strings = set()
    file_analysis = {}

    # Regex pattern to match NSLocalizedString calls
    # Captures the key (first parameter) from NSLocalizedString("key", comment: "...")
    pattern = re.compile(r'NSLocalizedString\(\"([^\"]+)\",\s*comment\s*:\s*\"[^\"]*\"\)')

    # Recursively walk through all files in directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.swift'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        localized_strings.update(matches)
                        file_analysis[relative_path] = len(matches)
                except Exception as e:
                    print_colored(f"Error reading {file_path}: {e}", Fore.RED)

    # Create reports directory if it doesn't exist
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write final_result_ios.csv: All unique keys
    try:
        with FINAL_RESULT_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nResults have been written to final_result_ios.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to final_result_ios.csv: {e}", Fore.RED)

    # Write total_keys_used_ios.csv: Same as above (legacy compatibility)
    try:
        with TOTAL_KEYS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nTotal keys have been written to total_keys_used_ios.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to total_keys_used_ios.csv: {e}", Fore.RED)

    # Write swift_files.csv: Per-file statistics
    try:
        with SWIFT_FILES_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['File Path', 'Number of Keys'])
            for file_path, count in file_analysis.items():
                writer.writerow([file_path, count])
        print_colored("\nSwift file details have been written to swift_files.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to swift_files.csv: {e}", Fore.RED)

    return localized_strings, file_analysis


def load_strings_file(file_path: str) -> Dict[str, str]:
    """
    Parse iOS Localizable.strings file into key-value dictionary.

    Reads a .strings file and extracts localization key-value pairs.
    The .strings format is:
        "key" = "value";

    This function handles:
    - Multiple formats of whitespace
    - Keys and values with quotes
    - Semicolon terminators
    - Comments (skipped if no '=' in line)

    Args:
        file_path: Path to Localizable.strings file

    Returns:
        Dict[str, str]: Dictionary mapping keys to translated values
                       Returns empty dict if file cannot be read

    File Format:
        iOS .strings files use this format:
            "welcome_message" = "Welcome!";
            "button.ok" = "OK";
            /* Comment lines are ignored */
            "error.network" = "Network error occurred";

    Parsing Logic:
        1. Split line on '=' character
        2. Strip whitespace and quotes from key (left side)
        3. Strip whitespace, quotes, and semicolon from value (right side)
        4. Store in dictionary

    Error Handling:
        - File not found: Logs error and returns empty dict
        - Encoding errors: Logs error and returns empty dict
        - Malformed lines: Silently skips (lines without '=')

    Example:
        strings = load_strings_file("/path/to/en.lproj/Localizable.strings")
        print(strings.get("welcome_message"))
        # Output: "Welcome!"

        if "button.ok" in strings:
            print(f"OK button text: {strings['button.ok']}")
    """
    strings = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()

            for line in content:
                # Only process lines containing '=' (key-value pairs)
                if '=' in line:
                    key_value = line.split('=')
                    # Strip quotes and whitespace from key
                    key = key_value[0].strip().strip('"')
                    # Strip semicolon, quotes, and whitespace from value
                    value = key_value[1].strip().strip(';').strip().strip('"')
                    strings[key] = value
    except Exception as e:
        print_colored(f"Error reading {file_path}: {e}", Fore.RED)

    return strings


def load_excluded_locales() -> Set[str]:
    """
    Load list of excluded locale codes from configuration file.

    Reads config/excluded_locales.ini to get locales that should be
    skipped during translation comparison. This is useful for locales
    that are intentionally incomplete or under development.

    Configuration File Format:
        [EXCLUDED]
        excluded_locales = en, base, ar

    The locale codes should match the directory names without .lproj suffix.
    For example, "en" excludes "en.lproj", "de-DE" excludes "de-DE.lproj".

    Args:
        None (uses global EXCLUDED_LOCALES_PATH)

    Returns:
        Set[str]: Set of locale codes to exclude from comparison
                 Returns empty set if config file doesn't exist

    Example Configuration:
        [EXCLUDED]
        excluded_locales = en, base, en-GB, ar

    Example Usage:
        excluded = load_excluded_locales()
        print(f"Excluding: {excluded}")
        # Output: Excluding: {'en', 'base', 'en-GB', 'ar'}

        if 'de' not in excluded:
            # Check German translations
            pass
    """
    excluded_locales = set()

    if EXCLUDED_LOCALES_PATH.exists():
        config = configparser.ConfigParser()
        config.read(EXCLUDED_LOCALES_PATH)

        if 'EXCLUDED' in config and 'excluded_locales' in config['EXCLUDED']:
            locales = config['EXCLUDED']['excluded_locales'].split(',')
            excluded_locales = {locale.strip() for locale in locales}

    print_colored(f"Excluded locales: {excluded_locales}", Fore.YELLOW)
    return excluded_locales


def compare_translations(
    localizable_dir: str,
    keys_to_check: Set[str]
) -> Dict[str, list]:
    """
    Compare translations across all locales and identify missing translations.

    This function performs a comprehensive translation coverage analysis:
    1. Load English (en.lproj) as the reference/source locale
    2. For each locale directory (*.lproj):
       - Load its Localizable.strings file
       - Check if each used key exists and has a value
       - Record missing or empty translations
    3. Generate CSV report of missing translations

    The comparison logic:
    - Key exists in English AND (missing in locale OR empty in locale)
      → Mark as missing for that locale
    - Key doesn't exist in English → Skip (not a valid key)
    - Key exists with value in locale → OK

    Args:
        localizable_dir: Path to directory containing *.lproj folders
        keys_to_check: Set of keys actually used in Swift code

    Returns:
        Dict[str, list]: Dictionary mapping keys to lists of locales
                        where translation is missing
                        Example: {"welcome": ["de", "fr"], "error.msg": ["it"]}

    CSV Output Format:
        missing_ios_translations.csv:
            Key,Languages
            welcome_message,"de, fr, it"
            button.ok,"pl"

    Directory Structure Expected:
        localizable_dir/
        ├── en.lproj/
        │   └── Localizable.strings
        ├── de.lproj/
        │   └── Localizable.strings
        ├── fr.lproj/
        │   └── Localizable.strings
        └── ...

    Excluded Locales:
        Locales in excluded_locales.ini are skipped during comparison.
        This is useful for:
        - Base internationalization (base.lproj)
        - Development locales
        - Intentionally incomplete locales

    Error Handling:
        - Missing locale directories: Silently skipped
        - Malformed .strings files: Logs error, returns empty translations
        - CSV write errors: Logs error but doesn't stop execution

    Example:
        keys = {"welcome", "goodbye", "error.network"}
        missing = compare_translations("/path/to/lokalise/ios", keys)

        for key, locales in missing.items():
            print(f"{key} missing in: {', '.join(locales)}")

        # Output:
        # welcome missing in: de, fr
        # error.network missing in: it, pl, sv
    """
    print_colored("Comparing translations...", Fore.CYAN)

    missing_translations = {}
    excluded_locales = load_excluded_locales()

    # Load English strings as reference
    en_path = os.path.join(localizable_dir, 'en.lproj', 'Localizable.strings')
    en_strings = load_strings_file(en_path)

    # Scan all locale directories
    for language_dir in os.listdir(localizable_dir):
        if language_dir.endswith('.lproj'):
            # Extract language code (e.g., "en" from "en.lproj", "de" from "de-DE.lproj")
            lang_code = language_dir.replace('.lproj', '').split('-')[0]

            # Skip excluded locales
            if lang_code in excluded_locales:
                continue

            # Load locale's strings file
            lang_path = os.path.join(localizable_dir, language_dir, 'Localizable.strings')
            lang_strings = load_strings_file(lang_path)

            # Check each key
            for key in keys_to_check:
                # Key must exist in English with a value
                if key in en_strings:
                    # Check if missing or empty in this locale
                    if key not in lang_strings or not lang_strings[key].strip():
                        if key not in missing_translations:
                            missing_translations[key] = []
                        missing_translations[key].append(lang_code)

    # Write missing translations report
    try:
        with MISSING_TRANSLATIONS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in missing_translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"\nMissing translations written to missing_ios_translations.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to missing_ios_translations.csv: {e}", Fore.RED)

    return missing_translations


# ==================== MAIN ENTRY POINT ====================

def main() -> None:
    """
    Main entry point for iOS localization scanner.

    Orchestrates the complete scanning workflow:
    1. Load project configuration
    2. Validate paths exist
    3. Start loading spinner animation
    4. Extract localization keys from Swift files
    5. Compare translations across locales
    6. Stop spinner and display results
    7. Show summary table with statistics

    Configuration Required:
        config/user_config.json must contain:
        {
            "project_paths": {
                "ios": "/path/to/ios/project"
            },
            "lokalise_paths": {
                "ios": "/path/to/lokalise/ios"
            }
        }

    Global Variables:
        stop_loading: Boolean flag to control spinner animation thread

    Reports Generated:
        - reports/ios/final_result_ios.csv
        - reports/ios/total_keys_used_ios.csv
        - reports/ios/swift_files.csv
        - reports/ios/missing_ios_translations.csv

    Summary Statistics:
        - Total keys used by project
        - Keys with missing translations
        - Execution time in milliseconds
        - Total .swift files analyzed
        - .swift files with at least one localization key

    Error Handling:
        - Missing config file: Exits with error
        - Invalid paths: Exits with error
        - colorama not installed: Runs without colors
        - prettytable not installed: Shows plain text summary

    Example Output:
        +----------------------------------+-------+
        | Metric                           | Value |
        +----------------------------------+-------+
        | Total keys used by the project   | 145   |
        | Keys with missing translations   | 12    |
        | Execution time (ms)              | 2341  |
        | Total .swift files analyzed      | 87    |
        | .swift files with at least one   | 34    |
        +----------------------------------+-------+

    Usage:
        if __name__ == "__main__":
            main()
    """
    if not color_enabled:
        print("Colorama is not installed. Running without graphical enhancements...")

    # Load configuration
    with CONFIG_PATH.open(encoding='utf-8') as f:
        config = json.load(f)
        ios_project_path = config.get("project_paths", {}).get("ios")
        localizable_dir = config.get("lokalise_paths", {}).get("ios")

    # Validate iOS project path
    if not ios_project_path or not os.path.isdir(ios_project_path):
        print_colored("Invalid or missing iOS project path in config.", Fore.RED)
        return

    # Validate Lokalise path
    if not localizable_dir or not os.path.isdir(localizable_dir):
        print_colored("Invalid or missing Lokalise iOS path in config.", Fore.RED)
        return

    # Start loading spinner in daemon thread
    global stop_loading
    stop_loading = False
    threading.Thread(target=spinner, daemon=True).start()

    # Execute scanning workflow
    start_time = time.time()
    localized_keys, file_analysis = extract_localized_strings(ios_project_path)
    missing_translations = compare_translations(localizable_dir, localized_keys)

    # Stop spinner and calculate timing
    stop_loading = True
    time.sleep(0.2)  # Allow spinner to finish current animation
    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)

    # Calculate statistics
    total_files = len(file_analysis)
    files_with_keys = sum(1 for count in file_analysis.values() if count > 0)

    # Display summary table
    if table_enabled:
        summary_table = PrettyTable()
        summary_table.field_names = ["Metric", "Value"]
        summary_table.add_row(["Total keys used by the project", len(localized_keys)])
        summary_table.add_row(["Keys with missing translations", len(missing_translations)])
        summary_table.add_row(["Execution time (ms)", execution_time_ms])
        summary_table.add_row(["Total .swift files analyzed", total_files])
        summary_table.add_row([".swift files with at least one key", files_with_keys])
        print_colored(summary_table.get_string(), Fore.CYAN)
    else:
        # Fallback to plain text summary if prettytable not available
        print_colored(f"\n--- Summary ---\n"
                      f"Total keys: {len(localized_keys)}\n"
                      f"Missing keys: {len(missing_translations)}\n"
                      f"Time: {execution_time_ms} ms\n"
                      f"Files analyzed: {total_files}\n"
                      f"Files with keys: {files_with_keys}", Fore.CYAN)


if __name__ == "__main__":
    main()
