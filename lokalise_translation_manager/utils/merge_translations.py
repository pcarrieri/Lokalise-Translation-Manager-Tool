"""
Translation Merge Module for Lokalise Translation Manager

This module merges missing translation reports from iOS and Android scanners
into a single unified list. It consolidates translation requirements from both
platforms to avoid duplicate translation requests.

Workflow:
    1. Load missing translations from iOS scanner (missing_ios_translations.csv)
    2. Load missing translations from Android scanner (missing_android_translations.csv)
    3. Merge the two lists (union of keys)
    4. Write unified list to missing_translations.csv
    5. Display summary statistics

Features:
    - Automatic CSV delimiter detection for each input file
    - Deduplication of common keys across platforms
    - Summary statistics (total, common, platform-specific)
    - PrettyTable output when available

Input Files:
    - reports/ios/missing_ios_translations.csv
    - reports/android/missing_android_translations.csv

Output File:
    - reports/missing_translations.csv

Usage:
    python3 -m lokalise_translation_manager.utils.merge_translations

    Or import:
        from lokalise_translation_manager.utils.merge_translations import run_merge
        run_merge()

Example Data Flow:
    iOS Report:
        key_name,languages
        ms_test_1,"it, de, fr"
        ms_common,"el, tr"

    Android Report:
        key_name,languages
        ms_test_2,"pl, sv"
        ms_common,"el, tr"

    Merged Output:
        key_name,languages
        ms_test_1,"it, de, fr"
        ms_test_2,"pl, sv"
        ms_common,"el, tr"

    Summary:
        Total iOS keys: 2
        Total Android keys: 2
        Merged keys: 3
        Common keys: 1
"""

import os
import csv
from pathlib import Path
from collections import defaultdict
from .csv_utils import detect_csv_delimiter

try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Adjusted to go up to root project directory
REPORTS_DIR = BASE_DIR / "reports"
IOS_CSV = REPORTS_DIR / "ios" / "missing_ios_translations.csv"
ANDROID_CSV = REPORTS_DIR / "android" / "missing_android_translations.csv"
FINAL_CSV = REPORTS_DIR / "missing_translations.csv"


def print_colored(text, color):
    print(color + text if color_enabled else text)

def load_missing_translations(file_path):
    """
    Load missing translations from a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        dict: Dictionary mapping key names to lists of missing languages

    Note:
        Uses automatic CSV delimiter detection to handle both comma and
        semicolon delimited files correctly.
    """
    translations = defaultdict(list)
    if file_path.exists():
        try:
            # Detect CSV delimiter automatically
            delimiter = detect_csv_delimiter(file_path)
            with file_path.open('r', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file, delimiter=delimiter)
                for row in reader:
                    key = row[0]
                    languages = row[1].split(', ') if len(row) > 1 else []
                    translations[key] = languages
        except Exception as e:
            print_colored(f"Error reading {file_path}: {e}", Fore.RED)
    return translations

def merge_translations(ios_translations, android_translations):
    """
    Merge iOS and Android translation dictionaries.

    Performs a union merge: keys from both platforms are included,
    but duplicates (common keys) are only included once.

    Args:
        ios_translations: Dictionary from iOS scanner
        android_translations: Dictionary from Android scanner

    Returns:
        dict: Merged dictionary containing all unique keys
    """
    merged = dict(ios_translations)
    for key, langs in android_translations.items():
        if key not in merged:
            merged[key] = langs
    return merged

def write_final_csv(translations):
    """
    Write merged translations to the final CSV file.

    Args:
        translations: Dictionary of merged translations

    Output Format:
        key_name,languages
        ms_test_1,"it, de, fr"
        ms_test_2,"pl, sv"
    """
    try:
        with FINAL_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"Merged results written to {FINAL_CSV}", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to final CSV: {e}", Fore.RED)

def print_summary(ios, android, merged):
    """
    Print summary statistics of the merge operation.

    Args:
        ios: iOS translations dictionary
        android: Android translations dictionary
        merged: Merged translations dictionary

    Displays:
        - Total iOS keys
        - Total Android keys
        - Merged keys (unique)
        - Common keys (overlap)
    """
    total_ios = len(ios)
    total_android = len(android)
    total_merged = len(merged)
    common = len(set(ios.keys()) & set(android.keys()))

    if table_enabled:
        table = PrettyTable()
        table.field_names = ["Metric", "Value"]
        table.add_row(["Total iOS keys", total_ios])
        table.add_row(["Total Android keys", total_android])
        table.add_row(["Merged keys", total_merged])
        table.add_row(["Common keys", common])
        print_colored(table.get_string(), Fore.CYAN)
    else:
        print_colored(f"\n--- Summary ---\n"
                      f"Total iOS keys: {total_ios}\n"
                      f"Total Android keys: {total_android}\n"
                      f"Merged keys: {total_merged}\n"
                      f"Common keys: {common}", Fore.CYAN)

def run_merge():
    """
    Main function to execute the merge process.

    Loads both iOS and Android translation reports, merges them,
    writes the output, and displays summary statistics.
    """
    if not color_enabled:
        print("Colorama not installed. Running without colored output.")

    ios = load_missing_translations(IOS_CSV)
    android = load_missing_translations(ANDROID_CSV)

    if not ios and not android:
        print_colored("No translation files found. Exiting.", Fore.RED)
        return

    merged = ios or android or {}
    if ios and android:
        merged = merge_translations(ios, android)

    write_final_csv(merged)
    print_summary(ios, android, merged)

if __name__ == "__main__":
    run_merge()
