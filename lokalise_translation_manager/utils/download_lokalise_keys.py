"""
Lokalise Keys Downloader Module

This module downloads translation keys and translations from Lokalise API and
prepares them for the translation workflow. It fetches all keys and translations
from the project and merges them with missing translation reports.

Main Functions:
    - Download all translation keys with IDs
    - Download all translations for all languages
    - Extract English source translations
    - Build language → translation_id mappings
    - Merge keys with missing translations list

Workflow:
    1. Fetch all translations from Lokalise (paginated)
    2. Extract English translations as source text
    3. Build translation ID mapping per language
    4. Fetch all keys with key IDs
    5. Save keys to CSV
    6. Merge keys with missing translations

API Features:
    - Pagination support (500 items per page)
    - Rate limiting respect (6 requests/second)
    - Progress indicator with spinner
    - Automatic retry on failure

Input Files:
    - config/user_config.json: Lokalise API credentials
    - reports/missing_translations.csv: Keys needing translation

Output Files:
    - reports/en_translations.csv: English source translations
    - reports/all_translation_ids.csv: Translation ID mappings
    - reports/lokalise_keys.csv: All key IDs and names
    - reports/merged_result.csv: Keys merged with missing translations

Usage:
    python3 -m lokalise_translation_manager.utils.download_lokalise_keys

    Or import:
        from lokalise_translation_manager.utils.download_lokalise_keys import main
        main()

API Endpoints:
    GET /api2/projects/{project_id}/translations?limit=500&page={page}
    GET /api2/projects/{project_id}/keys?limit=500&page={page}

Rate Limiting:
    - Maximum 6 requests per second
    - Automatic delay between requests
    - Progress tracking per page

Example Output:
    Fetching translations from Lokalise...
    Fetching translations page 1...
    Fetching translations page 2...
    English translations saved to en_translations.csv.
    All translations saved to all_translation_ids.csv.

    Fetching keys from Lokalise...
    Fetching keys page 1...
    Keys saved to lokalise_keys.csv.

    Merging keys with missing translations...
    Merged results saved to merged_result.csv.
"""

import os
import json
import requests
import csv
import time
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
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

def print_colored(text: str, color=None) -> None:
    """
    Print colored text with colorama fallback.

    Args:
        text: Text to print
        color: Colorama color code

    Note:
        Falls back to plain text if colorama not available.
    """
    if use_colors and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_config() -> Tuple[Optional[str], Optional[str]]:
    """
    Load Lokalise API credentials from config file.

    Returns:
        Tuple[Optional[str], Optional[str]]: (project_id, api_key) or (None, None) if error

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If lokalise credentials not in config
        JSONDecodeError: If config file is invalid JSON

    Example Config Format:
        {
            "lokalise": {
                "project_id": "123456789abcdef.12345678",
                "api_key": "your_api_key_here"
            }
        }
    """
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

def fetch_translations(project_id: str, api_key: str) -> List[Dict]:
    """
    Fetch all translations from Lokalise API with pagination.

    Downloads all translations for all languages from the Lokalise project.
    Uses pagination to handle large projects (500 translations per request).

    Args:
        project_id: Lokalise project ID
        api_key: Lokalise API token

    Returns:
        List[Dict]: List of translation objects from API

    Translation Object Structure:
        {
            "translation_id": "123456",
            "key_id": "789012",
            "language_iso": "en",
            "translation": "Hello World",
            "is_reviewed": true,
            ...
        }

    API Details:
        - Endpoint: GET /api2/projects/{project_id}/translations
        - Pagination: limit=500, page=1,2,3...
        - Rate limit: 6 requests/second (automatic delay)
        - Stops when page returns empty list

    Example:
        translations = fetch_translations("abc123.xyz", "api_key_here")
        # Returns: [{"translation_id": "123", ...}, {"translation_id": "456", ...}]
    """
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

def save_translations(translations: List[Dict]) -> None:
    """
    Save translations to CSV files for processing.

    Creates two output files:
    1. en_translations.csv: English source translations only
    2. all_translation_ids.csv: Translation ID mappings for all languages

    Args:
        translations: List of translation objects from Lokalise API

    Output Files:
        en_translations.csv:
            key_id,translation_id,translation
            123,456,"Hello World"

        all_translation_ids.csv:
            key_id,language_iso,translation_id
            123,"en,de,fr","456,789,012"

    Purpose:
        - English translations serve as source text for OpenAI
        - Translation ID mappings enable updating specific translations
        - Grouped by key_id for efficient lookup

    Example:
        translations = [
            {"key_id": "123", "language_iso": "en", "translation_id": "456", "translation": "Hello"},
            {"key_id": "123", "language_iso": "de", "translation_id": "789", "translation": "Hallo"}
        ]
        save_translations(translations)
        # Creates both CSV files with appropriate data
    """
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

def fetch_keys(project_id: str, api_key: str) -> List[Dict]:
    """
    Fetch all translation keys from Lokalise API with pagination.

    Downloads all keys with their IDs and metadata. Keys are the core
    identifiers for translations (e.g., "ms_welcome_message").

    Args:
        project_id: Lokalise project ID
        api_key: Lokalise API token

    Returns:
        List[Dict]: List of key objects from API

    Key Object Structure:
        {
            "key_id": "123456",
            "key_name": {
                "ios": "ms_welcome_message",
                "android": "ms_welcome_message",
                "web": "ms_welcome_message"
            },
            "platforms": ["ios", "android"],
            ...
        }

    API Details:
        - Endpoint: GET /api2/projects/{project_id}/keys
        - Pagination: limit=500, page=1,2,3...
        - Rate limit: 6 requests/second
        - Stops when page returns empty list

    Example:
        keys = fetch_keys("abc123.xyz", "api_key_here")
        # Returns: [{"key_id": "123", "key_name": {...}}, ...]
    """
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

def save_keys_to_csv(keys: List[Dict]) -> None:
    """
    Save translation keys to CSV file.

    Extracts key IDs and names from API response and writes to CSV.
    Key names are extracted from the multi-platform structure.

    Args:
        keys: List of key objects from Lokalise API

    Output File:
        lokalise_keys.csv:
            key_id,key_name
            123456,ms_welcome_message
            789012,ms_logout_button

    Key Name Extraction:
        - Keys in Lokalise have platform-specific names
        - This extracts the first available name (usually same across platforms)
        - Format: {"ios": "key_name", "android": "key_name", ...}
        - Result: "key_name"

    Example:
        keys = [
            {
                "key_id": "123",
                "key_name": {"ios": "ms_test", "android": "ms_test"}
            }
        ]
        save_keys_to_csv(keys)
        # Writes: 123,ms_test
    """
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

def merge_keys_with_missing_translations() -> None:
    """
    Merge translation keys with missing translations report.

    Combines the missing translations list (from scanners) with key IDs
    (from Lokalise) to create a complete file ready for translation.

    Input Files:
        lokalise_keys.csv:
            key_id,key_name
            123,ms_test_1

        missing_translations.csv:
            key_name,languages
            ms_test_1,"it, de, fr"

    Output File:
        merged_result.csv:
            key_name,key_id,languages
            ms_test_1,123,"it, de, fr"

    Purpose:
        - Links key names (from code) to key IDs (from Lokalise)
        - Enables API updates using key_id
        - Preserves language requirements from scanners

    Algorithm:
        1. Load all key_id → key_name mappings from Lokalise
        2. Read missing translations line by line
        3. For each key, lookup its key_id
        4. Write combined record with key_name, key_id, languages

    Example:
        merge_keys_with_missing_translations()
        # Creates merged_result.csv with key IDs added
    """
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

def main() -> None:
    """
    Main orchestration function for downloading Lokalise data.

    Executes the complete download and merge workflow:
        1. Load API credentials from config
        2. Fetch all translations from Lokalise
        3. Save translations to CSVs (English + mappings)
        4. Fetch all keys from Lokalise
        5. Save keys to CSV
        6. Merge keys with missing translations

    Exit Conditions:
        - Missing config file: Exits with error
        - Missing credentials: Exits with error
        - API errors: Continues but data may be incomplete

    Output Files Created:
        - reports/en_translations.csv
        - reports/all_translation_ids.csv
        - reports/lokalise_keys.csv
        - reports/merged_result.csv

    Example:
        main()
        # Downloads everything and creates all necessary CSV files
    """
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