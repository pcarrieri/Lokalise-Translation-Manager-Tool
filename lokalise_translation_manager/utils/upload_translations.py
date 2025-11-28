# lokalise_translation_manager/utils/upload_translations.py

import os
import csv
import json
import requests
import time
from pathlib import Path
from .csv_utils import detect_csv_delimiter

try:
    from colorama import init, Fore, Style
    from tabulate import tabulate
    colorama_available = True
    init(autoreset=True)
except ImportError:
    colorama_available = False
    tabulate = None

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
FINAL_REPORT_FILE = REPORTS_DIR / "final_report.csv"
FAILED_UPDATE_FILE = REPORTS_DIR / "failed_update.csv"

RATE_LIMIT = 6  # Lokalise allows ~6 req/sec with free plan

def print_colored(text, color=None):
    if colorama_available:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_lokalise_config():
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            config = json.load(f)
            return config["lokalise"]["project_id"], config["lokalise"]["api_key"]
    raise FileNotFoundError("user_config.json not found or misconfigured.")

def update_translations():
    project_id, api_key = load_lokalise_config()

    report_data = []
    failed_data = []
    request_count = 0
    success_count = 0
    failure_count = 0

    try:
        if not TRANSLATION_DONE_FILE.exists():
            print_colored(f"ERROR: Input file '{TRANSLATION_DONE_FILE.name}' not found. Nothing to upload.", Fore.RED)
            return

        # Rilevamento automatico del delimitatore CSV
        delimiter = detect_csv_delimiter(TRANSLATION_DONE_FILE)
        print_colored(f"INFO: Using detected CSV delimiter: '{delimiter}'", Fore.YELLOW)

        with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as infile:
            reader = list(csv.DictReader(infile, delimiter=delimiter))

        if not reader:
            print_colored(f"INFO: Input file '{TRANSLATION_DONE_FILE.name}' is empty. Nothing to upload.", Fore.YELLOW)
            return
            
        print_colored(f"Found {len(reader)} keys with new translations to upload.", Fore.CYAN)

        for row in reader:
            key_name = row['key_name']
            key_id = row['key_id']
            languages = row['languages'].split(',')
            translation_ids = row['translation_id'].split(',')
            translations = row['translated'].split('|')

            if not (len(languages) == len(translation_ids) == len(translations)):
                print_colored(f"\nFATAL DATA MISMATCH for key '{key_name}' ({key_id}). Skipping this row.", Fore.RED)
                print_colored(f"  - Found: {len(languages)} languages, {len(translation_ids)} IDs, {len(translations)} translations.", Fore.RED)
                failure_count += len(languages)
                continue

            for lang, trans_id, translation in zip(languages, translation_ids, translations):
                lang = lang.strip()
                trans_id = trans_id.strip()
                translation = translation.strip()

                if not trans_id:
                    print_colored(f"Skipping update for '{key_name}' in '{lang}' because its Translation ID is missing.", Fore.YELLOW)
                    failure_count += 1
                    continue

                print_colored(f"Updating '{key_name}' in '{lang}'...", Fore.BLUE)

                url = f"https://api.lokalise.com/api2/projects/{project_id}/translations/{trans_id}"
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "X-Api-Token": api_key
                }
                payload = {"translation": translation}

                response = requests.put(url, headers=headers, json=payload)
                request_count += 1

                if request_count % RATE_LIMIT == 0:
                    time.sleep(1)

                if response.status_code == 200:
                    success_count += 1
                    mod_time = response.json()['translation']['modified_at']
                    report_data.append({
                        'key_id': key_id, 'key_name': key_name, 'language_iso': lang,
                        'translation_id': trans_id, 'new_translation': translation, 'modified_at': mod_time
                    })
                else:
                    failure_count += 1
                    print_colored(f"Failed to update '{key_name}' ({lang}) — Status: {response.status_code}", Fore.RED)
                    failed_data.append({
                        'key_id': key_id, 'key_name': key_name, 'language_iso': lang,
                        'translation_id': trans_id, 'new_translation': translation, 'status_code': response.status_code
                    })

        if report_data:
            with FINAL_REPORT_FILE.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
                writer.writeheader()
                writer.writerows(report_data)
            print_colored(f"\n✅ Uploaded translations. Report saved to: {FINAL_REPORT_FILE}", Fore.GREEN)

        if failed_data:
            with FAILED_UPDATE_FILE.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=failed_data[0].keys())
                writer.writeheader()
                writer.writerows(failed_data)
            print_colored(f"\nSome translations failed. See: {FAILED_UPDATE_FILE}", Fore.RED)

        print_colored("\n===== UPLOAD SUMMARY =====", Fore.MAGENTA)
        summary = [
            ["Total API Requests", request_count],
            ["Successful Updates", success_count],
            ["Failed/Skipped Updates", failure_count],
        ]
        if tabulate:
            print(tabulate(summary, headers=["Metric", "Count"], tablefmt="grid"))
        else:
            for label, count in summary:
                print(f"{label}: {count}")

    except Exception as e:
        print_colored(f"\n❌ An unexpected error occurred: {e}", Fore.RED)

def main():
    print_colored("Uploading translations to Lokalise...", Fore.CYAN)
    update_translations()

if __name__ == "__main__":
    main()
