# android_scanner.py - Android localization key scanner

import os
import re
import csv
import time
import threading
import json
from pathlib import Path
import configparser

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

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"
EXCLUDED_LOCALES_PATH = BASE_DIR / "config" / "excluded_locales.ini"
REPORTS_DIR = BASE_DIR / "reports" / "android"
FINAL_RESULT_CSV = REPORTS_DIR / "final_result_android.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_android.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_android_translations.csv"


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
    pattern = re.compile(r'R\.string\.([a-zA-Z0-9_]+)')

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.kt') or file.endswith('.java'):
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
        print_colored("\nResults have been written to final_result_android.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to final_result_android.csv: {e}", Fore.RED)

    try:
        with TOTAL_KEYS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nTotal keys have been written to total_keys_used_android.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to total_keys_used_android.csv: {e}", Fore.RED)

    return localized_strings, file_analysis

def load_strings_file(file_path):
    strings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            matches = re.findall(r'<string name=\"([^\"]+)\">(.*?)</string>', content, re.DOTALL)
            for match in matches:
                key, value = match
                strings[key] = value.strip() != ""
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

def compare_translations(values_dir, project_dir, keys_to_check):
    print_colored("Comparing translations...", Fore.CYAN)

    missing_translations = {}
    excluded_locales = load_excluded_locales()
    en_path = os.path.join(values_dir, 'values', 'strings.xml')
    en_strings = load_strings_file(en_path)

    supported_languages = set()
    for root, dirs, _ in os.walk(project_dir):
        for dir_name in dirs:
            if dir_name.startswith('values-') and os.path.isfile(os.path.join(root, dir_name, 'strings.xml')):
                supported_languages.add(dir_name.split('-')[1])

    for root, dirs, _ in os.walk(values_dir):
        for dir_name in dirs:
            if dir_name.startswith('values-'):
                lang_code = dir_name.split('-')[1]
                if lang_code in excluded_locales:
                    continue
                if lang_code in supported_languages:
                    lang_path = os.path.join(root, dir_name, 'strings.xml')
                    lang_strings = load_strings_file(lang_path)

                    for key in keys_to_check:
                        if key in en_strings and (key not in lang_strings or not lang_strings[key]):
                            if key not in missing_translations:
                                missing_translations[key] = []
                            missing_translations[key].append(lang_code)

    try:
        with MISSING_TRANSLATIONS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in missing_translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"\nMissing translations written to missing_android_translations.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to missing_android_translations.csv: {e}", Fore.RED)

    return missing_translations

def main():
    if not color_enabled:
        print("Colorama is not installed. Running without graphical enhancements...")

    with CONFIG_PATH.open() as f:
        config = json.load(f)
        android_project_path = config.get("project_paths", {}).get("android")
        values_dir = config.get("lokalise_paths", {}).get("android")

    if not android_project_path or not os.path.isdir(android_project_path):
        print_colored("Invalid or missing Android project path in config.", Fore.RED)
        return

    if not values_dir or not os.path.isdir(values_dir):
        print_colored("Invalid or missing Lokalise Android path in config.", Fore.RED)
        return

    global stop_loading
    stop_loading = False
    threading.Thread(target=spinner, daemon=True).start()

    start_time = time.time()
    localized_keys, file_analysis = extract_localized_strings(android_project_path)
    missing_translations = compare_translations(values_dir, android_project_path, localized_keys)

    stop_loading = True
    time.sleep(0.2)
    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)

    total_files = len(file_analysis)
    files_with_keys = sum(1 for count in file_analysis.values() if count > 0)

    if table_enabled:
        summary_table = PrettyTable()
        summary_table.field_names = ["Metric", "Value"]
        summary_table.add_row(["Total keys used by the project", len(localized_keys)])
        summary_table.add_row(["Keys with missing translations", len(missing_translations)])
        summary_table.add_row(["Execution time (ms)", execution_time_ms])
        summary_table.add_row(["Total .kt/.java files analyzed", total_files])
        summary_table.add_row([".kt/.java files with at least one key", files_with_keys])
        print_colored(summary_table.get_string(), Fore.CYAN)
    else:
        print_colored(f"\n--- Summary ---\n"
                      f"Total keys: {len(localized_keys)}\n"
                      f"Missing keys: {len(missing_translations)}\n"
                      f"Time: {execution_time_ms} ms\n"
                      f"Files analyzed: {total_files}\n"
                      f"Files with keys: {files_with_keys}", Fore.CYAN)

if __name__ == "__main__":
    main()
