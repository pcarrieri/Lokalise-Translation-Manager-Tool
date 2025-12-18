"""
Translation Preparation Module for Lokalise Translation Manager

This module prepares the final file for the OpenAI translation engine by:
- Enriching translation data with correct translation IDs
- Mapping language codes to their respective translation IDs
- Handling language code discrepancies (e.g., tr_TR → tr lookup)
- Creating the final input file for the translator

Workflow:
    1. Load translation ID lookup table (all_translation_ids.csv)
    2. Read normalized translation data (merged_translations_result.csv)
    3. For each key and language, find the corresponding translation ID
    4. Handle special cases (Turkish: tr_TR → tr mapping)
    5. Write enriched data to ready_to_translations.csv

Translation ID Lookup:
    The module builds a mapping: {key_id: {language_iso: translation_id}}
    This allows quick lookup of translation IDs for each key-language pair.

Turkish Language Hotfix:
    Lokalise stores Turkish translations with code 'tr', but the normalized
    data uses 'tr_TR'. This module automatically converts tr_TR → tr for
    lookup purposes while preserving tr_TR in the output.

Input Files:
    - reports/all_translation_ids.csv: Complete translation ID mappings
    - ready_to_be_translated/merged_translations_result.csv: Normalized data

Output File:
    - reports/ready_to_translations.csv: Final file for translation engine

Usage:
    python3 -m lokalise_translation_manager.utils.prepare_translations

    Or import:
        from lokalise_translation_manager.utils.prepare_translations import main
        main()

Example Data Flow:
    Input (merged_translations_result.csv):
        key_name,key_id,languages,translation_id,translation
        ms_test,123,"tr_TR,de",456,"Hello"

    Translation ID Lookup (all_translation_ids.csv):
        key_id,language_iso,translation_id
        123,"tr,de","789,790"

    Output (ready_to_translations.csv):
        key_name,key_id,languages,translation_id,translation
        ms_test,123,"tr_TR,de","789,790","Hello"
"""

import csv
from pathlib import Path
from .csv_utils import detect_csv_delimiter

try:
    from colorama import init, Fore, Style
    colorama_available = True
    init(autoreset=True)
except ImportError:
    colorama_available = False

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
READY_DIR = BASE_DIR.parent / "ready_to_be_translated"
MERGED_TRANSLATIONS_FILE = READY_DIR / "merged_translations_result.csv"
ALL_TRANSLATION_IDS_FILE = REPORTS_DIR / "all_translation_ids.csv"
OUTPUT_FILE = REPORTS_DIR / "ready_to_translations.csv"

def print_colored(text, color=None):
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_translation_id_lookup():
    """
    Load all translation IDs into a lookup dictionary.

    Creates a nested dictionary structure: {key_id: {lang_iso: translation_id}}
    This allows O(1) lookup of translation IDs for any key-language combination.

    Returns:
        Dict[str, Dict[str, str]]: Nested dictionary mapping key IDs to language-translation ID pairs

    Raises:
        FileNotFoundError: If all_translation_ids.csv doesn't exist
    """
    print_colored(f"-> Loading translation ID lookup from '{ALL_TRANSLATION_IDS_FILE.name}'...", Fore.BLUE)
    if not ALL_TRANSLATION_IDS_FILE.exists():
        raise FileNotFoundError(f"File not found: {ALL_TRANSLATION_IDS_FILE}")

    id_lookup = {}
    delimiter = detect_csv_delimiter(ALL_TRANSLATION_IDS_FILE)
    with ALL_TRANSLATION_IDS_FILE.open('r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for row in reader:
            key_id = row['key_id']
            if key_id not in id_lookup:
                id_lookup[key_id] = {}
            
            languages = [lang.strip() for lang in row.get('language_iso', '').split(',') if lang.strip()]
            translation_ids = [tid.strip() for tid in row.get('translation_id', '').split(',') if tid.strip()]

            # Create language → ID mapping for this key
            id_lookup[key_id] = dict(zip(languages, translation_ids))
                
    print_colored(f"   Created lookup table for {len(id_lookup)} keys.", Fore.BLUE)
    return id_lookup

def enrich_and_save_translations(id_lookup):
    """
    Enrich translation data with correct translation IDs.

    Handles language code discrepancies, particularly for Turkish (tr_TR → tr).
    For each key and required language, looks up the corresponding translation ID
    from the lookup table and adds it to the output.

    Args:
        id_lookup: Dictionary mapping {key_id: {lang_iso: translation_id}}

    Raises:
        FileNotFoundError: If merged_translations_result.csv doesn't exist

    Note:
        Turkish Hotfix: When the language is 'tr_TR', the function automatically
        looks it up as 'tr' in the lookup table, as Lokalise stores Turkish with
        the short code 'tr' but normalization uses 'tr_TR'.
    """
    print_colored(f"\n-> Reading normalized data from '{MERGED_TRANSLATIONS_FILE.name}'...", Fore.BLUE)
    if not MERGED_TRANSLATIONS_FILE.exists():
         raise FileNotFoundError(f"Normalized file not found: {MERGED_TRANSLATIONS_FILE}")

    delimiter = detect_csv_delimiter(MERGED_TRANSLATIONS_FILE)
    with MERGED_TRANSLATIONS_FILE.open('r', encoding='utf-8') as infile:
        rows_to_process = list(csv.DictReader(infile, delimiter=delimiter))
    
    print_colored(f"   Found {len(rows_to_process)} keys to prepare.", Fore.BLUE)
    print_colored("\n-> Enriching records with translation IDs...", Fore.CYAN)
    
    output_rows = []
    
    for row in rows_to_process:
        key_id = row['key_id']
        key_name = row.get('key_name', 'N/A')
        
        languages_needed = [lang.strip() for lang in row['languages'].split(',') if lang.strip()]
        final_translation_ids = []
        
        for lang in languages_needed:
            # DEFINITIVE HOTFIX: Fix language code BEFORE lookup
            # If language is 'tr_TR', look it up in the table as 'tr'
            lookup_lang = 'tr' if lang == 'tr_TR' else lang

            if key_id in id_lookup and lookup_lang in id_lookup[key_id]:
                trans_id = id_lookup[key_id][lookup_lang]
                final_translation_ids.append(trans_id)
            else:
                # This case shouldn't happen for Turkish anymore, but kept as safety net
                print_colored(f"   - WARNING: No translation_id found for key '{key_name}' in language '{lang}'. Appending empty ID.", Fore.YELLOW)
                final_translation_ids.append('')

        # Prepare final output row
        output_rows.append({
            'key_name': key_name,
            'key_id': key_id,
            'languages': ','.join(languages_needed),
            'translation_id': ','.join(final_translation_ids),
            'translation': row['translation']
        })

    print_colored(f"\n-> Enrichment complete. Writing {len(output_rows)} keys to '{OUTPUT_FILE.name}'...", Fore.CYAN)
    with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['key_name', 'key_id', 'languages', 'translation_id', 'translation']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

def main():
    try:
        print_colored("\nPreparing final file for translation engine...", Fore.CYAN)
        id_lookup_table = load_translation_id_lookup()
        enrich_and_save_translations(id_lookup_table)
        print_colored(f"\n✅ Final translation file saved to {OUTPUT_FILE}.", Fore.GREEN)
    except (FileNotFoundError, KeyError) as e:
        print_colored(f"\n❌ ERROR: {e}", Fore.RED)
    except Exception as e:
        print_colored(f"\n❌ An unexpected error in prepare_translations.py: {e}", Fore.RED)

if __name__ == "__main__":
    main()

