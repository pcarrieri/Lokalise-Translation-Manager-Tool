# lokalise_translation_manager/utils/cleanup_unused_keys.py

import csv
import json
import requests
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
IOS_KEYS_FILE = REPORTS_DIR / "ios" / "total_keys_used_ios.csv"
ANDROID_KEYS_FILE = REPORTS_DIR / "android" / "total_keys_used_android.csv"
LOKALISE_KEYS_FILE = REPORTS_DIR / "lokalise_keys.csv"
TOTAL_KEYS_FILE = REPORTS_DIR / "total_keys_used_by_both.csv"
READY_TO_BE_DELETED_FILE = REPORTS_DIR / "ready_to_be_deleted.csv"


def load_keys(file_path):
    """Carica le chiavi da un file CSV (prima colonna)."""
    keys = set()
    if file_path.exists():
        with file_path.open('r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader, None)
            for row in reader:
                if row:
                    keys.add(row[0].strip())
    return keys

def merge_keys(socketio):
    """Unisce le chiavi usate da iOS e Android in un unico file."""
    ios_keys = load_keys(IOS_KEYS_FILE)
    android_keys = load_keys(ANDROID_KEYS_FILE)
    
    socketio.emit('detailed_log', {'message': f'Trovate {len(ios_keys)} chiavi in uso su iOS e {len(android_keys)} su Android.'})

    if not ios_keys and not android_keys:
        socketio.emit('detailed_log', {'message': 'ERRORE: Nessuna chiave trovata nei report. Impossibile continuare.'})
        return False

    total_keys = ios_keys.union(android_keys)

    with TOTAL_KEYS_FILE.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['key_name'])
        for key in sorted(total_keys):
            writer.writerow([key])

    socketio.emit('detailed_log', {'message': f'Trovate {len(total_keys)} chiavi totali in uso.'})
    return True

def filter_lokalise_keys(socketio):
    """Filtra le chiavi di Lokalise per trovare quelle non utilizzate."""
    total_keys_in_use = load_keys(TOTAL_KEYS_FILE)
    lokalise_keys = {}

    if not LOKALISE_KEYS_FILE.exists():
        socketio.emit('detailed_log', {'message': f'ERRORE: File {LOKALISE_KEYS_FILE.name} non trovato.'})
        return []

    with LOKALISE_KEYS_FILE.open('r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            lokalise_keys[row['key_name']] = row['key_id']
    
    socketio.emit('detailed_log', {'message': f'Confronto delle {len(total_keys_in_use)} chiavi locali con le {len(lokalise_keys)} chiavi su Lokalise.'})
    
    unused_keys = [
        (key_id, key_name)
        for key_name, key_id in lokalise_keys.items()
        if key_name not in total_keys_in_use
    ]

    with READY_TO_BE_DELETED_FILE.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['key_id', 'key_name'])
        for key_id, key_name in unused_keys:
            writer.writerow([key_id, key_name])

    socketio.emit('detailed_log', {'message': f'Trovate {len(unused_keys)} chiavi non utilizzate. Report salvato in: {READY_TO_BE_DELETED_FILE.name}'})
    return unused_keys

def delete_keys_from_lokalise(keys_to_delete, config, socketio):
    """
    Funzione dedicata alla cancellazione delle chiavi, chiamata solo dopo conferma dell'utente.
    """
    project_id = config.get("lokalise", {}).get("project_id")
    api_key = config.get("lokalise", {}).get("api_key")

    if not project_id or not api_key:
        socketio.emit('detailed_log', {'message': "ERRORE: Credenziali Lokalise mancanti in user_config.json"})
        return

    socketio.emit('detailed_log', {'message': f"Invio richiesta di cancellazione per {len(keys_to_delete)} chiavi a Lokalise..."})
    
    url = f"https://api.lokalise.com/api2/projects/{project_id}/keys"
    headers = {"accept": "application/json", "content-type": "application/json", "X-Api-Token": api_key}
    
    key_ids = [key_info['key_id'] for key_info in keys_to_delete]
    payload = {"keys": key_ids}

    try:
        response = requests.delete(url, json=payload, headers=headers)
        response.raise_for_status() # Lancia un'eccezione per status code 4xx/5xx
        socketio.emit('detailed_log', {'message': "✅ Chiavi cancellate con successo da Lokalise."})
    except requests.exceptions.RequestException as e:
        socketio.emit('detailed_log', {'message': f"ERRORE: Fallita la cancellazione delle chiavi. Dettagli: {e.response.text if e.response else e}"})


def main(config, socketio):
    """
    Funzione di analisi: trova le chiavi inutilizzate e le restituisce.
    Non esegue la cancellazione.
    """
    if not merge_keys(socketio):
        return []

    keys_to_delete = filter_lokalise_keys(socketio)

    if not keys_to_delete:
        socketio.emit('detailed_log', {'message': '🎉 Nessuna chiave inutilizzata trovata.'})
        return []
    
    # Converte la lista di tuple in una lista di dizionari per inviarla al frontend
    keys_as_dicts = [{'key_id': kid, 'key_name': kname} for kid, kname in keys_to_delete]
    
    return keys_as_dicts

if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data}")

    config_path_test = BASE_DIR / "config" / "user_config.json"
    if config_path_test.exists():
        with open(config_path_test) as f:
            test_config = json.load(f)
        
        # Test della funzione di analisi
        found_keys = main(test_config, MockSocket())
        print(f"\nFunzione di analisi ha trovato {len(found_keys)} chiavi da cancellare.")
        
        # Test della funzione di cancellazione (da usare con cautela)
        # if found_keys and input("Vuoi testare la cancellazione? (y/n): ") == 'y':
        #    delete_keys_from_lokalise(found_keys, test_config, MockSocket())
    else:
        print("config/user_config.json non trovato. Impossibile eseguire il test.")