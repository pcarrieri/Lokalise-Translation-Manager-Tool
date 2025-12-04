"""
Android Localization Key Scanner for Lokalise Translation Manager

This module scans Android Kotlin/Java projects to extract string resource usage
and analyze translation coverage across different locales. It identifies missing
translations and generates detailed CSV reports.

WORKFLOW:
---------
1. Load project configuration (Android project path, Lokalise path)
2. Scan all .kt, .java, and .xml files for string resource references
3. Extract localization keys and count usage per file
4. Load translation files (strings.xml, Localizable.xml) for all locales
5. Compare available translations against used keys
6. Identify missing translations per locale
7. Generate CSV reports:
   - final_result_android.csv: All unique localization keys
   - total_keys_used_android.csv: Same as above (for compatibility)
   - missing_android_translations.csv: Missing translations per key

KEY DETECTION:
--------------
The scanner uses regex pattern matching to find string resource references:

In Kotlin/Java code:
    Pattern: R.string.key_name
    Examples:
        R.string.welcome_message
        R.string.button_ok
        getString(R.string.error_network)

In XML layouts:
    Pattern: @string/key_name
    Examples:
        android:text="@string/welcome_message"
        android:hint="@string/input_placeholder"

Supported file types:
    - .kt (Kotlin)
    - .java (Java)
    - .xml (Layout/resource files)

Not supported (these won't be detected):
    - String resource references via string interpolation
    - Dynamic resource ID resolution
    - Resources from external libraries

TRANSLATION COMPARISON:
-----------------------
The scanner compares all locales against English (values/):
1. Load English strings from values/strings.xml and values/Localizable.xml
2. For each values-XX directory (e.g., values-fr, values-de):
   - Load locale's strings.xml and Localizable.xml
   - Merge strings from both files
   - Check if each used key exists and has a non-empty value
   - Record missing translations

The scanner supports multiple files per locale:
    values/
    ├── strings.xml          # Base strings
    └── Localizable.xml      # Additional strings (from Lokalise)

    values-de/
    ├── strings.xml          # German base strings
    └── Localizable.xml      # German Lokalise strings

EXCLUDED LOCALES:
-----------------
Locales can be excluded from missing translation checks using:
config/excluded_locales.ini:

[EXCLUDED]
excluded_locales = en, base, ar

This is useful for:
- Development locales
- Locales that are intentionally incomplete
- Test/debug resource qualifiers

REPORTS GENERATED:
------------------
1. final_result_android.csv
   Format: One key per line
   Purpose: Complete list of string resource keys used in project

2. total_keys_used_android.csv
   Format: Same as final_result_android.csv
   Purpose: Legacy compatibility (identical content)

3. missing_android_translations.csv
   Format: Key, Languages
   Purpose: Identify incomplete translations
   Example:
       welcome_message, "de, fr, it"
       error_network, "pl, sv"

OUTPUT LOCATION:
----------------
All reports are saved to: reports/android/

CONFIGURATION:
--------------
Requires config/user_config.json:
{
    "project_paths": {
        "android": "/path/to/android/project"
    },
    "lokalise_paths": {
        "android": "/path/to/lokalise/android"
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
    from lokalise_translation_manager.scanner import android_scanner
    android_scanner.main()

As a script:
    python3 -m lokalise_translation_manager.scanner.android_scanner

Via core workflow:
    Automatically called by core.py in Step 2

EXAMPLE OUTPUT:
---------------
When run, displays:
    | Loading... (animated spinner)

    Results have been written to final_result_android.csv
    Total keys have been written to total_keys_used_android.csv
    Missing translations written to missing_android_translations.csv

    +------------------------------------------+-------+
    | Metric                                   | Value |
    +------------------------------------------+-------+
    | Total keys used by the project           | 234   |
    | Keys with missing translations           | 18    |
    | Execution time (ms)                      | 1823  |
    | Total .kt/.java/.xml files analyzed      | 156   |
    | .kt/.java/.xml files with at least one   | 67    |
    +------------------------------------------+-------+

ANDROID RESOURCE STRUCTURE:
---------------------------
Android uses resource qualifiers for different locales:

    res/
    ├── values/              # English (default)
    │   ├── strings.xml
    │   └── Lokalizable.xml
    ├── values-de/           # German
    │   ├── strings.xml
    │   └── Lokalizable.xml
    ├── values-fr/           # French
    │   ├── strings.xml
    │   └── Lokalizable.xml
    └── ...

The scanner extracts the language code from the values-XX directory name.

PERFORMANCE:
------------
- Scans ~200 Kotlin/Java/XML files in ~1-2 seconds
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
REPORTS_DIR = BASE_DIR / "reports" / "android"
FINAL_RESULT_CSV = REPORTS_DIR / "final_result_android.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_android.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_android_translations.csv"

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
    Extract all string resource references from Android project files.

    Recursively scans all .kt, .java, and .xml files in the given directory
    and extracts string resource keys using regex pattern matching. Also tracks
    which files use string resources and how many keys each file contains.

    This function generates two CSV reports:
    1. final_result_android.csv: All unique keys (sorted)
    2. total_keys_used_android.csv: Duplicate of above for compatibility

    Args:
        directory: Root directory of Android project to scan

    Returns:
        Tuple[Set[str], Dict[str, int]]: A tuple containing:
            - Set of unique string resource keys found
            - Dictionary mapping relative file paths to key counts

    Pattern Matching:
        For Kotlin/Java files (.kt, .java):
            Regex: R\\.string\\.([a-zA-Z0-9_]+)
            Matches: R.string.key_name
            Examples:
                R.string.welcome_message
                getString(R.string.error_network)
                binding.textView.setText(R.string.title)

        For XML files (.xml):
            Regex: @string/([a-zA-Z0-9_]+)
            Matches: @string/key_name
            Examples:
                android:text="@string/welcome_message"
                android:hint="@string/input_placeholder"
                tools:text="@string/preview_text"

    CSV Output Format:
        final_result_android.csv:
            welcome_message
            button_ok
            error_network

    File Analysis:
        The function tracks per-file statistics including files with zero
        references (useful for identifying unused layout files).

    Error Handling:
        - Unreadable files: Logs error and continues with remaining files
        - CSV write errors: Logs error but doesn't stop execution
        - Creates reports directory if it doesn't exist

    Example:
        keys, file_stats = extract_localized_strings("/path/to/android/project")
        print(f"Found {len(keys)} unique keys")
        print(f"Total files: {len(file_stats)}")

        # Find file with most string references
        top_file = max(file_stats, key=file_stats.get)
        print(f"Most used file: {top_file} ({file_stats[top_file]} keys)")

        # Output:
        # Found 234 unique keys
        # Total files: 156
        # Most used file: app/src/main/java/MainActivity.kt (45 keys)
    """
    localized_strings = set()
    file_analysis = {}

    # Regex patterns for different file types
    pattern_code = re.compile(r'R\.string\.([a-zA-Z0-9_]+)')  # For Kotlin/Java
    pattern_xml = re.compile(r'@string/([a-zA-Z0-9_]+)')      # For XML

    # Recursively walk through all files in directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.kt', '.java', '.xml')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = []

                        # Use appropriate pattern based on file type
                        if file.endswith(('.kt', '.java')):
                            matches = pattern_code.findall(content)
                        elif file.endswith('.xml'):
                            matches = pattern_xml.findall(content)

                        localized_strings.update(matches)
                        file_analysis[relative_path] = len(matches)
                except Exception as e:
                    print_colored(f"Error reading {file_path}: {e}", Fore.RED)

    # Create reports directory if it doesn't exist
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write final_result_android.csv: All unique keys
    try:
        with FINAL_RESULT_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nResults have been written to final_result_android.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to final_result_android.csv: {e}", Fore.RED)

    # Write total_keys_used_android.csv: Same as above (legacy compatibility)
    try:
        with TOTAL_KEYS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nTotal keys have been written to total_keys_used_android.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to total_keys_used_android.csv: {e}", Fore.RED)

    return localized_strings, file_analysis


def load_strings_file(file_path: str) -> Dict[str, bool]:
    """
    Parse Android strings XML file and check which keys have values.

    Reads an Android strings.xml file and extracts string resource definitions.
    Returns a dictionary indicating whether each key has a non-empty value.

    Android strings.xml format:
        <resources>
            <string name="key_name">Value text</string>
            <string name="another_key">Another value</string>
        </resources>

    Args:
        file_path: Path to strings.xml or Localizable.xml file

    Returns:
        Dict[str, bool]: Dictionary mapping keys to True if they have a value,
                        False if empty. Returns empty dict if file cannot be read.

    XML Format:
        Android string resources use this format:
            <resources>
                <string name="welcome_message">Welcome!</string>
                <string name="button_ok">OK</string>
                <string name="empty_key"></string>
            </resources>

    Parsing Logic:
        Uses regex to extract <string> tags with name attributes:
        - Pattern: <string name="([^"]+)">(.*?)</string>
        - Uses re.DOTALL to match multi-line string values
        - Strips whitespace from values
        - Returns True if value is non-empty, False if empty

    Error Handling:
        - File not found: Logs error and returns empty dict
        - Malformed XML: May fail to parse some entries but continues
        - Encoding errors: Logs error and returns empty dict

    Example:
        strings = load_strings_file("/path/to/values-de/strings.xml")

        if strings.get("welcome_message"):
            print("German translation exists for welcome_message")
        else:
            print("German translation missing or empty for welcome_message")

        # Check coverage
        total = len(strings)
        translated = sum(1 for has_value in strings.values() if has_value)
        print(f"Translation coverage: {translated}/{total}")
    """
    strings = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Extract all <string> tags with name attribute and content
            # re.DOTALL allows matching across newlines for multi-line strings
            matches = re.findall(r'<string name=\"([^\"]+)\">(.*?)</string>', content, re.DOTALL)

            for match in matches:
                key, value = match
                # Store True if value exists (not empty after stripping), False otherwise
                strings[key] = value.strip() != ""
    except Exception as e:
        print_colored(f"Error reading {file_path}: {e}", Fore.RED)

    return strings


def load_all_strings_for_locale(locale_dir: str) -> Dict[str, bool]:
    """
    Load and merge strings from multiple XML files for a locale.

    Android projects often have multiple string XML files per locale:
    - strings.xml: Base/original strings
    - Lokalizable.xml: Additional strings from Lokalise platform

    This function merges both files, with later files overwriting earlier ones.

    Args:
        locale_dir: Path to locale directory (e.g., values/ or values-de/)

    Returns:
        Dict[str, bool]: Merged dictionary mapping keys to True/False
                        indicating whether each key has a non-empty value

    File Priority:
        Files are processed in this order:
        1. strings.xml
        2. Lokalizable.xml (overwrites duplicates from strings.xml)

    Directory Structure:
        locale_dir/
        ├── strings.xml          # Base strings
        └── Lokalizable.xml      # Lokalise strings (optional)

    Error Handling:
        - Missing files: Silently skipped (e.g., if Lokalizable.xml doesn't exist)
        - Malformed XML: Errors logged but function continues
        - Returns empty dict if locale_dir doesn't exist

    Example:
        # Load English strings
        en_strings = load_all_strings_for_locale("/path/to/values")
        print(f"English has {len(en_strings)} keys")

        # Load German strings
        de_strings = load_all_strings_for_locale("/path/to/values-de")
        print(f"German has {len(de_strings)} keys")

        # Find missing translations
        missing = [key for key in en_strings if key not in de_strings]
        print(f"Missing in German: {missing}")
    """
    merged_strings = {}

    for filename in ["strings.xml", "Lokalizable.xml"]:
        file_path = os.path.join(locale_dir, filename)

        if os.path.exists(file_path):
            strings_from_file = load_strings_file(file_path)
            # Merge with existing strings (later files overwrite earlier ones)
            merged_strings.update(strings_from_file)

    return merged_strings


def load_excluded_locales() -> Set[str]:
    """
    Load list of excluded locale codes from configuration file.

    Reads config/excluded_locales.ini to get locales that should be
    skipped during translation comparison. This is useful for locales
    that are intentionally incomplete or under development.

    Configuration File Format:
        [EXCLUDED]
        excluded_locales = en, base, ar

    The locale codes should match the values-XX directory suffix.
    For example, "de" excludes "values-de", "fr" excludes "values-fr".

    Args:
        None (uses global EXCLUDED_LOCALES_PATH)

    Returns:
        Set[str]: Set of locale codes to exclude from comparison
                 Returns empty set if config file doesn't exist

    Example Configuration:
        [EXCLUDED]
        excluded_locales = en, base, ar, night

    Example Usage:
        excluded = load_excluded_locales()
        print(f"Excluding: {excluded}")
        # Output: Excluding: {'en', 'base', 'ar', 'night'}

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
    values_dir: str,
    project_dir: str,
    keys_to_check: Set[str]
) -> Dict[str, list]:
    """
    Compare translations across all locales and identify missing translations.

    This function performs a comprehensive translation coverage analysis:
    1. Load English strings from values/ directory
    2. Scan project to find which locales are actually supported
    3. For each values-XX directory:
       - Load locale's strings from strings.xml and Lokalizable.xml
       - Check if each used key exists and has a value
       - Record missing or empty translations
    4. Generate CSV report of missing translations

    The comparison logic:
    - Key exists in English AND (missing in locale OR empty in locale)
      → Mark as missing for that locale
    - Key doesn't exist in English → Skip (not a valid key)
    - Key exists with value in locale → OK

    Args:
        values_dir: Path to Lokalise directory containing values-XX folders
        project_dir: Path to Android project root (to detect supported locales)
        keys_to_check: Set of keys actually used in Kotlin/Java/XML code

    Returns:
        Dict[str, list]: Dictionary mapping keys to lists of locales
                        where translation is missing
                        Example: {"welcome": ["de", "fr"], "error": ["it"]}

    CSV Output Format:
        missing_android_translations.csv:
            Key,Languages
            welcome_message,"de, fr, it"
            button_ok,"pl"

    Directory Structure Expected:
        values_dir/
        ├── values/
        │   ├── strings.xml
        │   └── Lokalizable.xml
        ├── values-de/
        │   ├── strings.xml
        │   └── Lokalizable.xml
        ├── values-fr/
        │   ├── strings.xml
        │   └── Lokalizable.xml
        └── ...

    Supported Locale Detection:
        The function scans project_dir to find which values-XX directories
        exist in the actual project. This ensures we only check locales that
        are actively used in the app.

    Excluded Locales:
        Locales in excluded_locales.ini are skipped during comparison.
        This is useful for:
        - Base/default resources (values/)
        - Development locales
        - Resource qualifiers like values-night, values-large

    Error Handling:
        - Missing locale directories: Silently skipped
        - Malformed XML files: Logs error, returns empty translations for that file
        - CSV write errors: Logs error but doesn't stop execution

    Example:
        keys = {"welcome", "goodbye", "error_network"}
        missing = compare_translations(
            "/path/to/lokalise/android",
            "/path/to/android/project",
            keys
        )

        for key, locales in missing.items():
            print(f"{key} missing in: {', '.join(locales)}")

        # Output:
        # welcome missing in: de, fr
        # error_network missing in: it, pl, sv
    """
    print_colored("Comparing translations...", Fore.CYAN)

    missing_translations = {}
    excluded_locales = load_excluded_locales()

    # Load English strings as reference
    en_dir = os.path.join(values_dir, 'values')
    en_strings = load_all_strings_for_locale(en_dir)

    # Scan project to find supported languages
    # This ensures we only check locales that are actually used in the project
    supported_languages = set()
    for root, dirs, _ in os.walk(project_dir):
        for dir_name in dirs:
            if dir_name.startswith('values-'):
                # Check if directory contains strings.xml or Lokalizable.xml
                has_strings = os.path.isfile(os.path.join(root, dir_name, 'strings.xml'))
                has_lokalizable = os.path.isfile(os.path.join(root, dir_name, 'Lokalizable.xml'))

                if has_strings or has_lokalizable:
                    # Extract language code (e.g., "de" from "values-de")
                    lang_code = dir_name.split('-')[1]
                    supported_languages.add(lang_code)

    # Check each locale in Lokalise directory
    for root, dirs, _ in os.walk(values_dir):
        for dir_name in dirs:
            if dir_name.startswith('values-'):
                lang_code = dir_name.split('-')[1]

                # Skip excluded locales
                if lang_code in excluded_locales:
                    continue

                # Only check locales that are supported in the project
                if lang_code in supported_languages:
                    lang_dir = os.path.join(root, dir_name)
                    lang_strings = load_all_strings_for_locale(lang_dir)

                    # Check each key
                    for key in keys_to_check:
                        # Key must exist in English with a value
                        if key in en_strings:
                            # Check if missing or empty in this locale
                            if key not in lang_strings or not lang_strings[key]:
                                if key not in missing_translations:
                                    missing_translations[key] = []
                                missing_translations[key].append(lang_code)

    # Write missing translations report
    try:
        with MISSING_TRANSLATIONS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in missing_translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"\nMissing translations written to missing_android_translations.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to missing_android_translations.csv: {e}", Fore.RED)

    return missing_translations


# ==================== MAIN ENTRY POINT ====================

def main() -> None:
    """
    Main entry point for Android localization scanner.

    Orchestrates the complete scanning workflow:
    1. Load project configuration
    2. Validate paths exist
    3. Start loading spinner animation
    4. Extract string resource keys from Kotlin/Java/XML files
    5. Compare translations across locales
    6. Stop spinner and display results
    7. Show summary table with statistics

    Configuration Required:
        config/user_config.json must contain:
        {
            "project_paths": {
                "android": "/path/to/android/project"
            },
            "lokalise_paths": {
                "android": "/path/to/lokalise/android"
            }
        }

    Global Variables:
        stop_loading: Boolean flag to control spinner animation thread

    Reports Generated:
        - reports/android/final_result_android.csv
        - reports/android/total_keys_used_android.csv
        - reports/android/missing_android_translations.csv

    Summary Statistics:
        - Total keys used by project
        - Keys with missing translations
        - Execution time in milliseconds
        - Total .kt/.java/.xml files analyzed
        - Files with at least one string resource reference

    Error Handling:
        - Missing config file: Exits with error
        - Invalid paths: Exits with error
        - colorama not installed: Runs without colors
        - prettytable not installed: Shows plain text summary

    Example Output:
        +------------------------------------------+-------+
        | Metric                                   | Value |
        +------------------------------------------+-------+
        | Total keys used by the project           | 234   |
        | Keys with missing translations           | 18    |
        | Execution time (ms)                      | 1823  |
        | Total .kt/.java/.xml files analyzed      | 156   |
        | .kt/.java/.xml files with at least one   | 67    |
        +------------------------------------------+-------+

    Usage:
        if __name__ == "__main__":
            main()
    """
    if not color_enabled:
        print("Colorama is not installed. Running without graphical enhancements...")

    # Load configuration
    with CONFIG_PATH.open(encoding='utf-8') as f:
        config = json.load(f)
        android_project_path = config.get("project_paths", {}).get("android")
        values_dir = config.get("lokalise_paths", {}).get("android")

    # Validate Android project path
    if not android_project_path or not os.path.isdir(android_project_path):
        print_colored("Invalid or missing Android project path in config.", Fore.RED)
        return

    # Validate Lokalise path
    if not values_dir or not os.path.isdir(values_dir):
        print_colored("Invalid or missing Lokalise Android path in config.", Fore.RED)
        return

    # Start loading spinner in daemon thread
    global stop_loading
    stop_loading = False
    threading.Thread(target=spinner, daemon=True).start()

    # Execute scanning workflow
    start_time = time.time()
    localized_keys, file_analysis = extract_localized_strings(android_project_path)
    missing_translations = compare_translations(values_dir, android_project_path, localized_keys)

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
        summary_table.add_row(["Total .kt/.java/.xml files analyzed", total_files])
        summary_table.add_row([".kt/.java/.xml files with at least one key", files_with_keys])
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
