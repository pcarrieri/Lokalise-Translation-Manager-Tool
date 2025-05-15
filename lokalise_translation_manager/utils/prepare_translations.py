# utils/prepare_translations.py - Prepare final file for OpenAI translation engine

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
READY_DIR = BASE_DIR.parent / "ready_to_be_translated"
MERGED_TRANSLATIONS_FILE = READY_DIR / "merged_translations_result.csv"
ALL_TRANSLATION_IDS_FILE = REPORTS_DIR / "all_translation_ids.csv"
OUTPUT_FILE = REPORTS_DIR / "ready_to_translations.csv"

def load_all_translation_ids():
    """
    Load all translation IDs from the CSV file into a dictionary.
    """
    all_translations = {}
    with ALL_TRANSLATION_IDS_FILE.open('r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key_id = row['key_id']
            languages = row['language_iso'].split(',')
            translation_ids = row['translation_id'].split(',')
            all_translations[key_id] = dict(zip(languages, translation_ids))
    return all_translations

def filter_and_save_translations(all_translations):
    """
    Filter translations by key_id and save the result to a new CSV file.
    """
    with MERGED_TRANSLATIONS_FILE.open('r', encoding='utf-8') as infile, \
         OUTPUT_FILE.open('w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = ['key_name', 'key_id', 'languages', 'translation_id', 'translation']
        writer = csv.writer(outfile)
        writer.writerow(fieldnames)

        for row in reader:
            key_id = row['key_id']
            if key_id in all_translations:
                languages = row['languages'].split(', ')
                filtered_languages = []
                filtered_translation_ids = []

                for lang in languages:
                    if lang in all_translations[key_id]:
                        filtered_languages.append(lang)
                        filtered_translation_ids.append(all_translations[key_id][lang])

                if filtered_languages:
                    writer.writerow([
                        row['key_name'],
                        key_id,
                        ','.join(filtered_languages),
                        ','.join(filtered_translation_ids),
                        row['translation']
                    ])

def main():
    all_translations = load_all_translation_ids()
    filter_and_save_translations(all_translations)
    print(f"Filtered translations saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
