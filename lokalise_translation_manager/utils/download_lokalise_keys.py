# utils/download_lokalise_keys.py - Download Lokalise keys and merge with missing translations

import os
import json
import requests
import csv
import time
import sys
from pathlib import Path
from .csv_utils import detect_csv_delimiter

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    use_colors = True
except ImportError:
    use_colors = False

# Constants and paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR.parent / "config" / "user_config.json"
REPORTS_DIR = BASE_DIR.parent / "reports"
EN_TRANSLATIONS_FILE = REPORTS_DIR / "en_translations.csv"
CSV_FILE = REPORTS_DIR / "lokalise_keys.csv"
MISSING_TRANSLATIONS_FILE = REPORTS_DIR / "missing_translations.csv"
MERGED_RESULT_FILE = REPORTS_DIR / "merged_result.csv"
REQUESTS_PER_SECOND = 6

def print_colored(text, color=None):
    if use_colors and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_config():
    try:
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open('r') as config_file:
                config_data = json.load(config_file)
                return config_data['lokalise']['project_id'], config_data['lokalise']['api_key']
        else:
            raise FileNotFoundError("No user_config.json found.")
    except Exception as e:
        print_colored(f"ERROR: Failed to load configuration - {e}", Fore.RED)
        return None, None

def fetch_translations(project_id, api_key):
    all_translations = []
    page = 1
    try:
        while True:
            url = f"https://api.lokalise.com/api2/projects/{project_id}/translations?limit=500&page={page}"
            headers = {"accept": "application/json", "X-Api-Token": api_key}
            sys.stdout.write(f"\rFetching translations page {page}...")
            sys.stdout.flush()
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            translations = response.json().get('translations', [])
            if not translations:
                break
            all_translations.extend(translations)
            page += 1
            time.sleep(1 / REQUESTS_PER_SECOND)
        sys.stdout.write("\n")
    except requests.exceptions.RequestException as e:
        print_colored(f"\nERROR: Failed to fetch translations - {e}", Fore.RED)
    return all_translations

def save_translations(translations):
    try:
        with EN_TRANSLATIONS_FILE.open('w', newline='') as en_csvfile:
            en_writer = csv.DictWriter(en_csvfile, fieldnames=['key_id', 'translation_id', 'translation'])
            en_writer.writeheader()
            for t in translations:
                if t['language_iso'] == 'en':
                    en_writer.writerow({
                        'key_id': t['key_id'],
                        'translation_id': t['translation_id'],
                        'translation': t['translation']
                    })
        print_colored(f"English translations saved to {EN_TRANSLATIONS_FILE}.", Fore.GREEN)

        all_translations = {}
        for t in translations:
            key_id = t['key_id']
            if key_id not in all_translations:
                all_translations[key_id] = {'language_iso': [], 'translation_id': []}
            all_translations[key_id]['language_iso'].append(t['language_iso'])
            all_translations[key_id]['translation_id'].append(t['translation_id'])

        with (REPORTS_DIR / 'all_translation_ids.csv').open('w', newline='') as all_csvfile:
            all_writer = csv.writer(all_csvfile)
            all_writer.writerow(['key_id', 'language_iso', 'translation_id'])
            for key_id, data in all_translations.items():
                all_writer.writerow([key_id, ','.join(data['language_iso']), ','.join(map(str, data['translation_id']))])

        print_colored("All translations saved to all_translation_ids.csv.", Fore.GREEN)
    except Exception as e:
        print_colored(f"ERROR: Failed to save translations - {e}", Fore.RED)

def fetch_keys(project_id, api_key):
    all_keys = []
    page = 1
    try:
        while True:
            url = f"https://api.lokalise.com/api2/projects/{project_id}/keys?limit=500&page={page}"
            headers = {"accept": "application/json", "X-Api-Token": api_key}
            sys.stdout.write(f"\rFetching keys page {page}...")
            sys.stdout.flush()
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            keys = response.json().get('keys', [])
            if not keys:
                break
            all_keys.extend(keys)
            page += 1
            time.sleep(1 / REQUESTS_PER_SECOND)
        sys.stdout.write("\n")
    except requests.exceptions.RequestException as e:
        print_colored(f"\nERROR: Failed to fetch keys - {e}", Fore.RED)
    return all_keys

def save_keys_to_csv(keys):
    try:
        with CSV_FILE.open('w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['key_id', 'key_name'])
            writer.writeheader()
            for key in keys:
                key_id = key['key_id']
                key_name = next(iter(key['key_name'].values()), '')
                writer.writerow({'key_id': key_id, 'key_name': key_name})
        print_colored(f"Keys saved to {CSV_FILE}.", Fore.GREEN)
    except Exception as e:
        print_colored(f"ERROR: Failed to save keys to CSV - {e}", Fore.RED)

def merge_keys_with_missing_translations():
    try:
        keys_dict = {}
        delimiter_keys = detect_csv_delimiter(CSV_FILE)
        with CSV_FILE.open('r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter_keys)
            for row in reader:
                keys_dict[row['key_name']] = row['key_id']

        delimiter_missing = detect_csv_delimiter(MISSING_TRANSLATIONS_FILE)
        with MISSING_TRANSLATIONS_FILE.open('r') as infile, MERGED_RESULT_FILE.open('w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['key_name', 'key_id', 'languages'])
            for row in csv.reader(infile, delimiter=delimiter_missing):
                key_name = row[0]
                key_id = keys_dict.get(key_name, '')
                writer.writerow([key_name, key_id] + row[1:])
        print_colored(f"Merged results saved to {MERGED_RESULT_FILE}.", Fore.GREEN)
    except Exception as e:
        print_colored(f"ERROR: Failed to merge keys with missing translations - {e}", Fore.RED)

def main():
    project_id, api_key = load_config()
    if not project_id or not api_key:
        print_colored("Lokalise project ID or API key missing. Please configure them in user_config.json", Fore.RED)
        return

    print_colored("Fetching translations from Lokalise...", Fore.CYAN)
    translations = fetch_translations(project_id, api_key)
    save_translations(translations)

    print_colored("Fetching keys from Lokalise...", Fore.CYAN)
    keys = fetch_keys(project_id, api_key)
    save_keys_to_csv(keys)

    print_colored("Merging keys with missing translations...", Fore.CYAN)
    merge_keys_with_missing_translations()

if __name__ == "__main__":
    main()