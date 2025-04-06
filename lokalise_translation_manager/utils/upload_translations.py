# lokalise_translation_manager/utils/upload_translations.py

import os
import csv
import json
import requests
import time
from pathlib import Path
from colorama import init, Fore, Style

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

# Initialize colorama
init(autoreset=True)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
FINAL_REPORT_FILE = REPORTS_DIR / "final_report.csv"
FAILED_UPDATE_FILE = REPORTS_DIR / "failed_update.csv"

RATE_LIMIT = 6  # Lokalise allows ~6 req/sec with free plan


def print_colored(text, color=None):
    print(color + text + Style.RESET_ALL if color else text)


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
        with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                key_name = row['key_name']
                key_id = row['key_id']
                languages = row['languages'].split(',')
                translation_ids = row['translation_id'].split(',')
                translations = row['translated'].split('|')

                for lang, trans_id, translation in zip(languages, translation_ids, translations):
                    print(Fore.CYAN + f"Updating '{key_name}' in '{lang}'...")

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
                        mod_time = response.json()['translation']['modified_at']
                        report_data.append({
                            'key_id': key_id,
                            'key_name': key_name,
                            'language_iso': lang,
                            'translation_id': trans_id,
                            'new_translation': translation,
                            'modified_at': mod_time
                        })
                        success_count += 1
                    else:
                        failure_count += 1
                        failed_data.append({
                            'key_id': key_id,
                            'key_name': key_name,
                            'language_iso': lang,
                            'translation_id': trans_id,
                            'new_translation': translation,
                            'modified_at': 'N/A'
                        })
                        print(Fore.RED + f"Failed to update '{key_name}' ({lang}) — {response.status_code}")

        # Write success report
        with FINAL_REPORT_FILE.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
            writer.writeheader()
            writer.writerows(report_data)

        # Write failures
        if failed_data:
            with FAILED_UPDATE_FILE.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=failed_data[0].keys())
                writer.writeheader()
                writer.writerows(failed_data)
            print(Fore.RED + f"\nSome translations failed. See: {FAILED_UPDATE_FILE}")

        print(Fore.GREEN + f"\n✅ Uploaded translations. Report saved to: {FINAL_REPORT_FILE}")

        # Summary
        print(Fore.MAGENTA + "\nSummary:")
        summary = [
            ["Total Requests", request_count],
            ["Successful Updates", success_count],
            ["Failed Updates", failure_count],
        ]
        if tabulate:
            print(tabulate(summary, headers=["Metric", "Count"], tablefmt="grid"))
        else:
            for label, count in summary:
                print(f"{label}: {count}")

    except Exception as e:
        print(Fore.RED + f"\n❌ ERROR: {e}")


def main():
    update_translations()


if __name__ == "__main__":
    update_translations()
