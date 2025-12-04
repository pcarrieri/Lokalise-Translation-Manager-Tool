"""
Translation Normalization Module for Lokalise Translation Manager

This module normalizes and prepares translation data for OpenAI processing by:
- Normalizing language codes to Lokalise format
- Merging translation requests with English source translations
- Validating data consistency
- Preparing final CSV for translation engine

Workflow:
    1. Read merged translation requirements (merged_result.csv)
    2. Read English source translations (en_translations.csv)
    3. Match keys requiring translation with their English source
    4. Normalize language codes (e.g., 'tr' → 'tr_TR', 'lt' → 'lt_LT')
    5. Filter out keys without English source
    6. Write normalized output (merged_translations_result.csv)

Language Code Normalization:
    The module maps Lokalise short codes to full locale identifiers:
    - Baltic languages: lt → lt_LT, lv → lv_LV, et → et_EE
    - Turkish: tr → tr_TR
    - Other languages: Remain unchanged (en, de, fr, it, etc.)

Input Files:
    - reports/merged_result.csv: Keys needing translation with language lists
    - reports/en_translations.csv: English source translations from Lokalise

Output File:
    - ready_to_be_translated/merged_translations_result.csv: Normalized data

Usage:
    python3 -m lokalise_translation_manager.utils.normalize_translations

    Or import:
        from lokalise_translation_manager.utils.normalize_translations import process_normalization
        process_normalization()

Example Data Flow:
    Input (merged_result.csv):
        key_name,key_id,languages
        ms_test,123,"tr,lt,de"

    English Source (en_translations.csv):
        key_id,translation_id,translation
        123,456,"Hello"

    Output (merged_translations_result.csv):
        key_name,key_id,languages,translation_id,translation
        ms_test,123,"tr_TR,lt_LT,de",456,"Hello"
"""

import csv
import time
import sys
from pathlib import Path
from .csv_utils import detect_csv_delimiter

try:
    from colorama import init, Fore, Style
    from tabulate import tabulate
    colorama_available = True
    init(autoreset=True)
except ImportError:
    colorama_available = False

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
READY_DIR = BASE_DIR.parent / "ready_to_be_translated"
MERGED_RESULT_FILE = REPORTS_DIR / "merged_result.csv"
EN_TRANSLATIONS_FILE = REPORTS_DIR / "en_translations.csv"
OUTPUT_FILE = READY_DIR / "merged_translations_result.csv"

# Supported language mappings (Lokalise format)
LOKALISE_LANGUAGES = {
    "en": "en", "de": "de", "fr": "fr", "it": "it", "pl": "pl",
    "sv": "sv", "nb": "nb", "da": "da", "fi": "fi",
    "lt": "lt_LT", "lv": "lv_LV", "et": "et_EE",
    "tr": "tr_TR", "ar": "ar", "el": "el"
}

def print_colored(text, color=None):
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def normalize_languages(languages, normalization_count):
    """
    Normalize and clean language codes correctly.

    Args:
        languages: Comma-separated language codes
        normalization_count: Dictionary to track normalization counts

    Returns:
        Normalized comma-separated language codes
    """
    normalized = []
    # CRITICAL FIX APPLIED HERE:
    # 1. Split only by comma
    # 2. Use .strip() to remove invisible whitespace
    for lang in languages.split(','):
        clean_lang = lang.strip()
        if clean_lang in LOKALISE_LANGUAGES:
            normalized_lang = LOKALISE_LANGUAGES[clean_lang]
            normalized.append(normalized_lang)
            normalization_count[normalized_lang] += 1
    return ','.join(normalized)

def process_normalization():
    print_colored("\nStarting normalization and merge process...", Fore.CYAN)
    start_time = time.time()
    
    normalization_count = {lang: 0 for lang in LOKALISE_LANGUAGES.values()}
    merged_keys_count = 0
    skipped_keys_count = 0

    try:
        READY_DIR.mkdir(parents=True, exist_ok=True)

        # DETAILED LOG: FILE READING
        print_colored(f"-> Reading keys needing translation from '{MERGED_RESULT_FILE.name}'...", Fore.BLUE)
        if not MERGED_RESULT_FILE.exists():
            raise FileNotFoundError(f"Input file not found: {MERGED_RESULT_FILE}")

        delimiter_merged = detect_csv_delimiter(MERGED_RESULT_FILE)
        with MERGED_RESULT_FILE.open('r', encoding='utf-8') as merged_file:
            merged_reader = csv.DictReader(merged_file, delimiter=delimiter_merged)
            merged_data = {row['key_id']: row for row in merged_reader}
        print_colored(f"   Found {len(merged_data)} total keys.", Fore.BLUE)

        print_colored(f"-> Reading available English translations from '{EN_TRANSLATIONS_FILE.name}'...", Fore.BLUE)
        if not EN_TRANSLATIONS_FILE.exists():
            raise FileNotFoundError(f"English translations file not found: {EN_TRANSLATIONS_FILE}")

        delimiter_en = detect_csv_delimiter(EN_TRANSLATIONS_FILE)
        with EN_TRANSLATIONS_FILE.open('r', encoding='utf-8') as en_file:
            en_reader = csv.DictReader(en_file, delimiter=delimiter_en)
            en_data = {row['key_id']: row for row in en_reader}
        print_colored(f"   Found {len(en_data)} English translations.", Fore.BLUE)
        
        print_colored("\n-> Starting merge process...", Fore.CYAN)
        output_data = []
        for key_id, merged_row in merged_data.items():
            key_name = merged_row.get('key_name', 'N/A')
            # DETAILED LOG: MERGE PROCESS FOR EACH KEY
            if key_id in en_data:
                print_colored(f"   [OK] Match for key '{key_name}' ({key_id}) found. Preparing for translation.", Fore.GREEN)
                
                normalized_languages = normalize_languages(merged_row['languages'], normalization_count)
                if not normalized_languages:
                    print_colored(f"      - WARNING: Key '{key_name}' has no valid languages after normalization. Skipping.", Fore.YELLOW)
                    skipped_keys_count += 1
                    continue

                output_data.append({
                    'key_name': key_name,
                    'key_id': key_id,
                    'languages': normalized_languages,
                    'translation_id': en_data[key_id]['translation_id'],
                    'translation': en_data[key_id]['translation']
                })
                merged_keys_count += 1
            else:
                print_colored(f"   [SKIP] No English translation for key '{key_name}' ({key_id}). Skipping.", Fore.YELLOW)
                skipped_keys_count += 1
        
        print_colored(f"\n-> Merge complete. Writing {merged_keys_count} keys to '{OUTPUT_FILE.name}'...", Fore.CYAN)
        with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as output_file:
            fieldnames=['key_name', 'key_id', 'languages', 'translation_id', 'translation']
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)
        
        print_colored(f"\n✅ Process finished successfully.", Fore.GREEN)

    except FileNotFoundError as e:
        print_colored(f"\n❌ ERROR: A required file was not found. Please check the path.", Fore.RED)
        print_colored(f"   Details: {e}", Fore.RED)
    except Exception as e:
        print_colored(f"\n❌ An unexpected error occurred: {e}", Fore.RED)

    finally:
        elapsed = time.time() - start_time
        print_colored("\n===== NORMALIZATION SUMMARY =====", Fore.CYAN)
        print(f"Total keys needing translation: {len(merged_data)}")
        print(f"Total English translations available: {len(en_data)}")
        print_colored(f"Keys successfully merged and prepared: {merged_keys_count}", Fore.GREEN)
        print_colored(f"Keys skipped (no EN translation found): {skipped_keys_count}", Fore.YELLOW)
        print(f"Execution time: {elapsed:.2f} seconds")

        table_data = [[lang, count] for lang, count in normalization_count.items()]
        if colorama_available and 'tabulate' in sys.modules:
            print(tabulate(table_data, headers=["Language", "Count"], tablefmt="grid"))
        else:
            print("\nLanguage normalization counts:")
            for lang, count in normalization_count.items():
                print(f"  {lang}: {count}")

if __name__ == "__main__":
    process_normalization()

