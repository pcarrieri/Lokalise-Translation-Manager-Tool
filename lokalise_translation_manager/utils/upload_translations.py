# lokalise_translation_manager/utils/upload_translations.py

import csv
import json
import requests
import time
from pathlib import Path

try:
    from tabulate import tabulate
    tabulate_available = True
except ImportError:
    tabulate_available = False

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
FINAL_REPORT_FILE = REPORTS_DIR / "final_report.csv"
FAILED_UPDATE_FILE = REPORTS_DIR / "failed_update.csv"

RATE_LIMIT = 6  # Richieste al secondo per l'API di Lokalise

def update_translations(project_id, api_key, socketio):
    report_data = []
    failed_data = []
    request_count = 0
    success_count = 0
    
    if not TRANSLATION_DONE_FILE.exists():
        socketio.emit('detailed_log', {'message': 'Nessun file di traduzioni completate (translation_done.csv) trovato. Salto lo step di upload.'})
        return

    translations_to_upload = []
    with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        translations_to_upload = list(reader)

    if not translations_to_upload:
        socketio.emit('detailed_log', {'message': 'Il file delle traduzioni è vuoto. Nessun dato da caricare.'})
        return
        
    total_uploads = sum(len(row['languages'].split(',')) for row in translations_to_upload)
    socketio.emit('detailed_log', {'message': f"Inizio upload di {total_uploads} traduzioni su Lokalise."})
    
    start_time = time.time()
    completed_count = 0
    
    for row in translations_to_upload:
        key_name = row['key_name']
        key_id = row['key_id']
        languages = row['languages'].split(',')
        translation_ids = row['translation_id'].split(',')
        translations = row['translated'].split('|')

        if len(languages) != len(translations):
            socketio.emit('detailed_log', {'message': f"ATTENZIONE: Numero di lingue e traduzioni non corrisponde per la chiave '{key_name}'. Salto questa chiave."})
            continue

        for lang, trans_id, translation in zip(languages, translation_ids, translations):
            socketio.emit('detailed_log', {'message': f"Carico traduzione per '{key_name}' in '{lang}'..."})

            url = f"https://api.lokalise.com/api2/projects/{project_id}/translations/{trans_id}"
            headers = {"accept": "application/json", "content-type": "application/json", "X-Api-Token": api_key}
            payload = {"translation": translation}

            response = requests.put(url, headers=headers, json=payload)
            request_count += 1
            completed_count += 1
            
            # --- MODIFICA CHIAVE: Invia l'aggiornamento per la barra di avanzamento ---
            percent = (completed_count / total_uploads) * 100 if total_uploads > 0 else 0
            socketio.emit('progress_update', {'percentage': percent})
            
            if request_count % RATE_LIMIT == 0:
                time.sleep(1)

            if response.status_code == 200:
                mod_time = response.json().get('translation', {}).get('modified_at', 'N/A')
                report_data.append({
                    'key_id': key_id, 'key_name': key_name, 'language_iso': lang,
                    'translation_id': trans_id, 'new_translation': translation, 'modified_at': mod_time
                })
                success_count += 1
            else:
                failed_data.append({
                    'key_id': key_id, 'key_name': key_name, 'language_iso': lang,
                    'translation_id': trans_id, 'new_translation': translation, 'error': response.text
                })
                socketio.emit('detailed_log', {'message': f"ERRORE: Fallito l'aggiornamento di '{key_name}' ({lang}) — Codice: {response.status_code}"})

    if report_data:
        with FINAL_REPORT_FILE.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
            writer.writeheader()
            writer.writerows(report_data)

    if failed_data:
        with FAILED_UPDATE_FILE.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=failed_data[0].keys())
            writer.writeheader()
            writer.writerows(failed_data)
        socketio.emit('detailed_log', {'message': f"Alcune traduzioni non sono state caricate. Controlla il file: {FAILED_UPDATE_FILE.name}"})

    elapsed = time.time() - start_time
    socketio.emit('detailed_log', {'message': f"Upload completato in {elapsed:.2f} secondi."})

    summary_data = {
        'title': 'Riepilogo Upload su Lokalise',
        'type': 'bar',
        'data': {
            'labels': ['Aggiornamenti Riusciti', 'Aggiornamenti Falliti'],
            'values': [success_count, len(failed_data)]
        }
    }
    socketio.emit('summary_data', summary_data)


def main(config, socketio):
    project_id = config.get("lokalise", {}).get("project_id")
    api_key = config.get("lokalise", {}).get("api_key")

    if not project_id or not api_key:
        socketio.emit('detailed_log', {'message': "ERRORE: Credenziali Lokalise non trovate nella configurazione."})
        raise ValueError("Lokalise credentials not found in config")
        
    update_translations(project_id, api_key, socketio)


if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data}")

    config_path_test = BASE_DIR / "config" / "user_config.json"
    if config_path_test.exists():
        with open(config_path_test) as f:
            test_config = json.load(f)
        main(test_config, MockSocket())
    else:
        print("config/user_config.json non trovato. Impossibile eseguire il test.")