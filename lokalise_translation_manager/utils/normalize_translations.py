# utils/normalize_translations.py - Normalize and prepare translations for OpenAI

import csv
import time
import threading
import sys
import itertools
from pathlib import Path

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

LOKALISE_LANGUAGES = {
    "en": "en", "de": "de", "fr": "fr", "it": "it", "pl": "pl",
    "sv": "sv", "nb": "nb", "da": "da", "fi": "fi",
    "lt": "lt_LT", "lv": "lv_LV", "et": "et_EE"
}

stop_loader = False

def print_colored(text, color=None):
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def loader():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_loader:
            break
        sys.stdout.write(f'\rProcessing {c}')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\rDone!     \n')

def normalize_languages(languages, normalization_count):
    normalized = []
    for lang in languages.split(', '):
        if lang in LOKALISE_LANGUAGES:
            normalized_lang = LOKALISE_LANGUAGES[lang]
            normalized.append(normalized_lang)
            normalization_count[normalized_lang] += 1
    return ', '.join(normalized)

def process_normalization():
    global stop_loader
    normalization_count = {lang: 0 for lang in LOKALISE_LANGUAGES.values()}
    start_time = time.time()

    try:
        READY_DIR.mkdir(parents=True, exist_ok=True)

        # Start loader animation
        loader_thread = threading.Thread(target=loader)
        loader_thread.start()

        with MERGED_RESULT_FILE.open('r') as merged_file:
            merged_reader = csv.DictReader(merged_file)
            merged_data = {row['key_id']: row for row in merged_reader}

        with EN_TRANSLATIONS_FILE.open('r') as en_file:
            en_reader = csv.DictReader(en_file)
            en_data = {row['key_id']: row for row in en_reader}

        output_data = []
        for key_id, merged_row in merged_data.items():
            if key_id in en_data:
                normalized_languages = normalize_languages(merged_row['languages'], normalization_count)
                output_data.append({
                    'key_name': merged_row['key_name'],
                    'key_id': key_id,
                    'languages': normalized_languages,
                    'translation_id': en_data[key_id]['translation_id'],
                    'translation': en_data[key_id]['translation']
                })

        with OUTPUT_FILE.open('w', newline='') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=['key_name', 'key_id', 'languages', 'translation_id', 'translation'])
            writer.writeheader()
            writer.writerows(output_data)

        print_colored(f"\nTranslations processed and saved to {OUTPUT_FILE}.", Fore.GREEN)

    except Exception as e:
        print_colored(f"\nERROR: An error occurred - {e}", Fore.RED)

    finally:
        stop_loader = True
        loader_thread.join()

        elapsed = time.time() - start_time
        print_colored("\nSummary:", Fore.GREEN)
        print(f"Execution time: {elapsed:.2f} seconds")

        table_data = [[lang, count] for lang, count in normalization_count.items()]
        if colorama_available and 'tabulate' in sys.modules:
            print(tabulate(table_data, headers=["Language", "Count"], tablefmt="grid"))
        else:
            print("Language normalization counts:")
            for lang, count in normalization_count.items():
                print(f"  {lang}: {count}")

if __name__ == "__main__":
    process_normalization()
