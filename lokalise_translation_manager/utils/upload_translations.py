"""
Translation Upload Module for Lokalise Translation Manager

This module uploads completed translations to Lokalise via the API. It reads
translated content from the OpenAI translation engine output and updates the
corresponding translations in the Lokalise project.

Workflow:
    1. Read translation_done.csv with completed translations
    2. Auto-detect CSV delimiter for compatibility
    3. Parse translation data (key_id, translation_id, languages, translations)
    4. Upload each translation via Lokalise API (PUT request)
    5. Respect rate limiting (6 requests/second)
    6. Generate success report (final_report.csv)
    7. Generate failure report if needed (failed_update.csv)
    8. Display summary statistics

Features:
    - Automatic CSV delimiter detection
    - Rate limiting compliance (6 requests/second)
    - Batch upload with progress tracking
    - Success and failure reports
    - Data validation before upload
    - Colorama/tabulate support for enhanced output

API Details:
    - Endpoint: PUT /api2/projects/{project_id}/translations/{translation_id}
    - Authentication: X-Api-Token header
    - Payload: {"translation": "translated text"}
    - Rate Limit: ~6 requests/second (free plan)
    - Response: 200 OK with modified_at timestamp

Input Files:
    - config/user_config.json: Lokalise API credentials
    - reports/translation_done.csv: Completed translations from OpenAI

Output Files:
    - reports/final_report.csv: Successfully uploaded translations
    - reports/failed_update.csv: Failed uploads (only if errors occur)

CSV Format (translation_done.csv):
    key_name,key_id,languages,translation_id,translated
    ms_test_1,123,"it,de,fr","456,789,012","Ciao|Hallo|Bonjour"

Report Format (final_report.csv):
    key_id,key_name,language_iso,translation_id,new_translation,modified_at
    123,ms_test_1,it,456,Ciao,2024-01-15T10:30:00Z

Usage:
    python3 -m lokalise_translation_manager.utils.upload_translations

    Or import:
        from lokalise_translation_manager.utils.upload_translations import main
        main()

Example Output:
    INFO: Using detected CSV delimiter: ','
    Found 50 keys with new translations to upload.
    Updating 'ms_test_1' in 'it'...
    Updating 'ms_test_1' in 'de'...
    ...
    ✅ Uploaded translations. Report saved to: reports/final_report.csv

    ===== UPLOAD SUMMARY =====
    Total API Requests: 150
    Successful Updates: 148
    Failed/Skipped Updates: 2

Error Handling:
    - Missing input file: Exits with error message
    - Empty input file: Exits with info message
    - Data mismatch: Skips row and logs error
    - Missing translation_id: Skips translation
    - API errors: Logs failure and continues
    - All errors tracked in failed_update.csv
"""

import os
import csv
import json
import requests
import time
from pathlib import Path
from typing import Tuple
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

def print_colored(text: str, color=None) -> None:
    """
    Print colored text to console with colorama fallback.

    Args:
        text: Text to print
        color: Colorama color code (Fore.RED, Fore.GREEN, etc.)

    Note:
        If colorama is not available, prints plain text without colors.
    """
    if colorama_available:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_lokalise_config() -> Tuple[str, str]:
    """
    Load Lokalise API credentials from config file.

    Returns:
        Tuple[str, str]: (project_id, api_key)

    Raises:
        FileNotFoundError: If config file doesn't exist or is misconfigured

    Example Config Format:
        {
            "lokalise": {
                "project_id": "123456789abcdef.12345678",
                "api_key": "your_api_key_here"
            }
        }
    """
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            config = json.load(f)
            return config["lokalise"]["project_id"], config["lokalise"]["api_key"]
    raise FileNotFoundError("user_config.json not found or misconfigured.")

def update_translations() -> None:
    """
    Upload completed translations to Lokalise via API.

    Main workflow function that:
    1. Loads API credentials from config
    2. Reads translation_done.csv with completed translations
    3. Validates data integrity (languages, IDs, translations counts match)
    4. Uploads each translation via PUT request to Lokalise API
    5. Respects rate limiting (6 requests/second)
    6. Tracks successes and failures
    7. Generates final_report.csv (successes) and failed_update.csv (failures)
    8. Displays summary statistics

    Input File Format (translation_done.csv):
        key_name,key_id,languages,translation_id,translated
        ms_test,123,"it,de,fr","456,789,012","Ciao|Hallo|Bonjour"

    Output Files:
        - final_report.csv: Successfully uploaded translations with timestamps
        - failed_update.csv: Failed uploads with status codes (only if errors)

    API Request:
        PUT /api2/projects/{project_id}/translations/{translation_id}
        Headers: X-Api-Token: {api_key}
        Payload: {"translation": "translated text"}

    Rate Limiting:
        - 6 requests per second maximum
        - Automatic sleep(1) after every 6 requests

    Error Handling:
        - Missing file: Exits with error
        - Empty file: Exits with info
        - Data mismatch: Skips row and logs
        - Missing translation_id: Skips and logs
        - API errors: Logs failure and continues

    Example Output:
        Found 50 keys with new translations to upload.
        Updating 'ms_test_1' in 'it'...
        ✅ Uploaded translations. Report saved to: reports/final_report.csv

        ===== UPLOAD SUMMARY =====
        Total API Requests: 150
        Successful Updates: 148
        Failed/Skipped Updates: 2
    """
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

        # Automatic CSV delimiter detection
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

def main() -> None:
    """
    Main entry point for the upload translations module.

    Displays header message and executes the upload workflow.

    Usage:
        python3 -m lokalise_translation_manager.utils.upload_translations

        Or:
        from lokalise_translation_manager.utils.upload_translations import main
        main()
    """
    print_colored("Uploading translations to Lokalise...", Fore.CYAN)
    update_translations()

if __name__ == "__main__":
    main()
