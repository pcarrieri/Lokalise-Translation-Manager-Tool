# ios_scanner.py - Modular iOS scanning script

import os
import re
import csv
import time
import threading
import configparser
from pathlib import Path

# Optional modules
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

from lokalise_translation_manager.scanner import android_scanner  # Placeholder import

# Define directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "ios"
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"
EXCLUDED_LOCALES_PATH = BASE_DIR / "config" / "excluded_locales.ini"

FINAL_RESULT_CSV = REPORTS_DIR / "final_result_ios.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_ios.csv"
SWIFT_FILES_CSV = REPORTS_DIR / "swift_files.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_ios_translations.csv"


def print_colored(text, color):
    print(color + text if color_enabled else text)

def spinner():
    while not stop_loading:
        for cursor in '|/-\\':
            print('\r' + cursor + ' Loading...', end='', flush=True)
            time.sleep(0.1)

def extract_localized_strings(directory):
    localized_strings = set()
    file_analysis = {}
    pattern = re.compile(r'NSLocalizedString\("([^"]+)",\s*comment\s*:\s*"[^"]*"\)')

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

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with FINAL_RESULT_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        with TOTAL_KEYS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        with SWIFT_FILES_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['File Path', 'Number of Keys'])
            for file_path, count in file_analysis.items():
                writer.writerow([file_path, count])
    except Exception as e:
        print_colored(f"Error writing to CSV: {e}", Fore.RED)

    return sorted(localized_strings), file_analysis

def load_strings_file(file_path):
    strings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
            for line in content:
                if '=' in line:
                    parts = line.split('=')
                    key = parts[0].strip().strip('"')
                    value = parts[1].strip().strip(';').strip().strip('"')
                    strings[key] = value
    except Exception as e:
        print_colored(f"Error reading {file_path}: {e}", Fore.RED)
    return strings

def load_excluded_locales():
    excluded_locales = set()
    if EXCLUDED_LOCALES_PATH.exists():
        config = configparser.ConfigParser()
        config.read(EXCLUDED_LOCALES_PATH)
        if 'EXCLUDED' in config and 'excluded_locales' in config['EXCLUDED']:
            locales = config['EXCLUDED']['excluded_locales'].split(',')
            excluded_locales = {locale.strip() for locale in locales}
    print_colored(f"Excluded locales: {excluded_locales}", Fore.YELLOW)
    return excluded_locales

def compare_translations(localizable_dir, keys_to_check):
    print_colored("Comparing translations...", Fore.CYAN)
    excluded_locales = load_excluded_locales()
    missing_translations = {}

    en_path = os.path.join(localizable_dir, 'en.lproj', 'Localizable.strings')
    en_strings = load_strings_file(en_path)

    for language_dir in os.listdir(localizable_dir):
        if language_dir.endswith('.lproj'):
            lang_code = language_dir.replace('.lproj', '').split('-')[0]
            if lang_code in excluded_locales:
                continue
            lang_path = os.path.join(localizable_dir, language_dir, 'Localizable.strings')
            lang_strings = load_strings_file(lang_path)

            for key in keys_to_check:
                if key in en_strings and (key not in lang_strings or not lang_strings[key].strip()):
                    if key not in missing_translations:
                        missing_translations[key] = []
                    missing_translations[key].append(lang_code)

    try:
        with MISSING_TRANSLATIONS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in missing_translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"Results written to {MISSING_TRANSLATIONS_CSV}", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to CSV: {e}", Fore.RED)

    return missing_translations

def main():
    import json

    if not color_enabled:
        print("Colorama not installed. Running in plain mode.")

    try:
        with CONFIG_PATH.open() as f:
            config = json.load(f)
            project_paths = config.get("project_paths", [])
            ios_path = project_paths[0].strip() if project_paths else None
    except Exception as e:
        print_colored(f"Error reading config: {e}", Fore.RED)
        return

    if not ios_path or not os.path.isdir(ios_path):
        print_colored("Invalid iOS project path.", Fore.RED)
        return

    localizable_dir = ios_path

    global stop_loading
    stop_loading = False
    threading.Thread(target=spinner, daemon=True).start()

    start_time = time.time()
    keys, file_analysis = extract_localized_strings(ios_path)
    missing = compare_translations(localizable_dir, keys)

    stop_loading = True
    time.sleep(0.2)

    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)

    total_files = len(file_analysis)
    files_with_keys = sum(1 for count in file_analysis.values() if count > 0)

    if table_enabled:
        table = PrettyTable()
        table.field_names = ["Metric", "Value"]
        table.add_row(["Total keys used by the project", len(keys)])
        table.add_row(["Keys with missing translations", len(missing)])
        table.add_row(["Execution time (ms)", execution_time_ms])
        table.add_row(["Total .swift files analyzed", total_files])
        table.add_row([".swift files with at least one key", files_with_keys])
        print_colored(table.get_string(), Fore.CYAN)
    else:
        print_colored(f"\n--- Summary ---\n"
                      f"Total keys: {len(keys)}\n"
                      f"Missing keys: {len(missing)}\n"
                      f"Time: {execution_time_ms} ms\n"
                      f"Files analyzed: {total_files}\n"
                      f"Files with keys: {files_with_keys}", Fore.CYAN)

    # Call Android scanner optionally
    android_scanner.main()  # Uncomment if desired

if __name__ == "__main__":
    main()