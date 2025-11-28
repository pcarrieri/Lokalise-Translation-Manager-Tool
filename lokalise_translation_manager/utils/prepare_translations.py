# utils/prepare_translations.py - Prepare final file for OpenAI translation engine

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
    Carica tutti gli ID di traduzione in un dizionario di lookup.
    Struttura: {key_id: {lang_iso: translation_id}}
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
            
            # Crea una mappa lingua -> id per questa chiave
            id_lookup[key_id] = dict(zip(languages, translation_ids))
                
    print_colored(f"   Created lookup table for {len(id_lookup)} keys.", Fore.BLUE)
    return id_lookup

def enrich_and_save_translations(id_lookup):
    """
    Arricchisce i dati di traduzione con i corretti translation_id,
    gestendo la discrepanza del codice lingua per il turco.
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
            # --- HOTFIX DEFINITIVO: Corregge il codice lingua PRIMA della ricerca ---
            # Se la lingua è 'tr_TR', la cerchiamo nella tabella di lookup come 'tr'.
            lookup_lang = 'tr' if lang == 'tr_TR' else lang
            # --------------------------------------------------------------------

            if key_id in id_lookup and lookup_lang in id_lookup[key_id]:
                trans_id = id_lookup[key_id][lookup_lang]
                final_translation_ids.append(trans_id)
            else:
                # Questo caso non dovrebbe più accadere per il turco, ma rimane come sicurezza
                print_colored(f"   - WARNING: No translation_id found for key '{key_name}' in language '{lang}'. Appending empty ID.", Fore.YELLOW)
                final_translation_ids.append('')
        
        # Prepara la riga finale per l'output
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

