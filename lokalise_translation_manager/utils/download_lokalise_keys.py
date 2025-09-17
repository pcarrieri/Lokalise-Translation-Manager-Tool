# utils/download_lokalise_keys.py

import json
import requests
import csv
import time
from pathlib import Path

# Costanti e percorsi
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
CSV_FILE = REPORTS_DIR / "lokalise_keys.csv"
EN_TRANSLATIONS_FILE = REPORTS_DIR / "en_translations.csv"
MISSING_TRANSLATIONS_FILE = REPORTS_DIR / "missing_translations.csv"
MERGED_RESULT_FILE = REPORTS_DIR / "merged_result.csv"
ALL_TRANSLATION_IDS_FILE = REPORTS_DIR / "all_translation_ids.csv"
REQUESTS_PER_SECOND = 6

def fetch_paginated_data(url, headers, data_key, socketio, resource_name):
    """Funzione generica per scaricare dati paginati da Lokalise."""
    all_items = []
    page = 1
    try:
        while True:
            paginated_url = f"{url}?limit=500&page={page}"
            socketio.emit('detailed_log', {'message': f"Scaricando pagina {page} di {resource_name}..."})
            
            response = requests.get(paginated_url, headers=headers)
            response.raise_for_status()
            
            items = response.json().get(data_key, [])
            if not items:
                break
            
            all_items.extend(items)
            page += 1
            time.sleep(1 / REQUESTS_PER_SECOND)
            
        socketio.emit('detailed_log', {'message': f"Scaricamento di {resource_name} completato. Trovati {len(all_items)} elementi."})
    except requests.exceptions.RequestException as e:
        socketio.emit('detailed_log', {'message': f"ERRORE: Fallito lo scaricamento di {resource_name} - {e}"})
    return all_items

def save_translations(translations, socketio):
    try:
        # Salva solo le traduzioni in inglese
        with EN_TRANSLATIONS_FILE.open('w', newline='', encoding='utf-8') as en_csvfile:
            en_writer = csv.DictWriter(en_csvfile, fieldnames=['key_id', 'translation_id', 'translation'])
            en_writer.writeheader()
            for t in translations:
                if t['language_iso'] == 'en':
                    en_writer.writerow({
                        'key_id': t['key_id'],
                        'translation_id': t['translation_id'],
                        'translation': t['translation']
                    })
        
        # Salva tutti gli ID di traduzione per lingua
        all_translations_map = {}
        for t in translations:
            key_id = t['key_id']
            if key_id not in all_translations_map:
                all_translations_map[key_id] = {}
            all_translations_map[key_id][t['language_iso']] = t['translation_id']

        with ALL_TRANSLATION_IDS_FILE.open('w', newline='', encoding='utf-8') as all_csvfile:
            all_writer = csv.writer(all_csvfile)
            all_writer.writerow(['key_id', 'language_iso', 'translation_id'])
            for key_id, lang_map in all_translations_map.items():
                languages = ','.join(lang_map.keys())
                ids = ','.join(map(str, lang_map.values()))
                all_writer.writerow([key_id, languages, ids])
                
        socketio.emit('detailed_log', {'message': "File delle traduzioni salvati correttamente."})
    except Exception as e:
        socketio.emit('detailed_log', {'message': f"ERRORE: Fallito il salvataggio delle traduzioni - {e}"})

def save_keys_to_csv(keys, socketio):
    try:
        with CSV_FILE.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['key_id', 'key_name'])
            writer.writeheader()
            for key in keys:
                key_id = key['key_id']
                key_name = next(iter(key['key_name'].values()), '') # Prende il nome della chiave per la piattaforma di default
                writer.writerow({'key_id': key_id, 'key_name': key_name})
        socketio.emit('detailed_log', {'message': f"Elenco chiavi salvato in {CSV_FILE.name}."})
    except Exception as e:
        socketio.emit('detailed_log', {'message': f"ERRORE: Fallito il salvataggio delle chiavi in CSV - {e}"})

def merge_keys_with_missing_translations(socketio):
    try:
        if not MISSING_TRANSLATIONS_FILE.exists():
            socketio.emit('detailed_log', {'message': "Nessun file di traduzioni mancanti da unire, salto questo passaggio."})
            # Crea un file vuoto per compatibilità con gli step successivi
            with MERGED_RESULT_FILE.open('w', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['key_name', 'key_id', 'languages'])
            return

        keys_dict = {}
        with CSV_FILE.open('r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                keys_dict[row['key_name']] = row['key_id']

        with MISSING_TRANSLATIONS_FILE.open('r', encoding='utf-8') as infile, MERGED_RESULT_FILE.open('w', newline='', encoding='utf-8') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            writer.writerow(['key_name', 'key_id', 'languages'])
            
            header = next(reader, None) # Salta l'intestazione del file di input
            
            for row in reader:
                if not row: continue
                key_name = row[0]
                key_id = keys_dict.get(key_name, 'NOT_FOUND')
                writer.writerow([key_name, key_id] + row[1:])
        socketio.emit('detailed_log', {'message': f"Risultati uniti salvati in {MERGED_RESULT_FILE.name}."})
    except Exception as e:
        socketio.emit('detailed_log', {'message': f"ERRORE: Fallita l'unione delle chiavi con le traduzioni mancanti - {e}"})

def main(config, socketio):
    project_id = config.get("lokalise", {}).get("project_id")
    api_key = config.get("lokalise", {}).get("api_key")

    if not project_id or not api_key:
        socketio.emit('detailed_log', {"message": "ERRORE: ID Progetto o API Key di Lokalise mancanti."})
        return

    headers = {"accept": "application/json", "X-Api-Token": api_key}
    
    translations_url = f"https://api.lokalise.com/api2/projects/{project_id}/translations"
    translations = fetch_paginated_data(translations_url, headers, 'translations', socketio, "traduzioni")
    if translations:
        save_translations(translations, socketio)

    keys_url = f"https://api.lokalise.com/api2/projects/{project_id}/keys"
    keys = fetch_paginated_data(keys_url, headers, 'keys', socketio, "chiavi")
    if keys:
        save_keys_to_csv(keys, socketio)

    merge_keys_with_missing_translations(socketio)

if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data['message']}")

    config_path_test = BASE_DIR.parent / "config" / "user_config.json"
    if config_path_test.exists():
        with open(config_path_test) as f:
            test_config = json.load(f)
        main(test_config, MockSocket())
    else:
        print("config/user_config.json non trovato. Impossibile eseguire il test.")