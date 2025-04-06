# utils/merge_translations.py - Merge iOS and Android missing translations reports

import os
import csv
from pathlib import Path
from collections import defaultdict

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

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
IOS_CSV = REPORTS_DIR / "ios" / "missing_ios_translations.csv"
ANDROID_CSV = REPORTS_DIR / "android" / "missing_android_translations.csv"
FINAL_CSV = REPORTS_DIR / "missing_translations.csv"


def print_colored(text, color):
    print(color + text if color_enabled else text)

def load_missing_translations(file_path):
    translations = defaultdict(list)
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                for row in reader:
                    key = row[0]
                    languages = row[1].split(', ') if len(row) > 1 else []
                    translations[key] = languages
        except Exception as e:
            print_colored(f"Error reading {file_path}: {e}", Fore.RED)
    return translations

def merge_translations(ios_translations, android_translations):
    merged = dict(ios_translations)
    for key, langs in android_translations.items():
        if key not in merged:
            merged[key] = langs
    return merged

def write_final_csv(translations):
    try:
        with FINAL_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in translations.items():
                writer.writerow([key, ", ".join(languages)])
        print_colored(f"Merged results written to {FINAL_CSV}", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to final CSV: {e}", Fore.RED)

def print_summary(ios, android, merged):
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
