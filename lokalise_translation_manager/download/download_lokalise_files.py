# lokalise_translation_manager/download/download_lokalise_files.py

import os
import time
import json
import requests
import zipfile
import itertools
from pathlib import Path

def download_file(download_url, save_path):
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_zip(file_path, extract_to, socketio):
    socketio.emit('detailed_log', {'message': f'Estrazione di {file_path.name}...'})
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(file_path)
    socketio.emit('detailed_log', {'message': 'Estrazione completata.'})

def fetch_lokalise_file(project_id, api_key, platform, format, save_dir, socketio):
    url = f"https://api.lokalise.com/api2/projects/{project_id}/files/async-download"
    payload = {"format": format, "all_platforms": True}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Token": api_key
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    process_id = response.json().get("process_id")

    max_attempts = 30
    wait_seconds = 5.0
    
    for attempt in range(1, max_attempts + 1):
        status_url = f"https://api.lokalise.com/api2/projects/{project_id}/processes/{process_id}"
        response = requests.get(status_url, headers=headers)
        if response.status_code == 200:
            process_info = response.json().get("process", {})
            status = process_info.get("status")
            
            socketio.emit('detailed_log', {'message': f"Recupero file per {platform}... Tentativo {attempt} - Stato: {status}"})

            if status == "finished":
                download_url = process_info.get("details", {}).get("download_url")
                if download_url:
                    Path(save_dir).mkdir(parents=True, exist_ok=True)
                    save_path = Path(save_dir) / f"{platform}_strings.zip"
                    download_file(download_url, save_path)
                    socketio.emit('detailed_log', {'message': f'File per {platform} scaricato.'})
                    extract_zip(save_path, save_dir, socketio)
                    return os.path.abspath(save_dir)
        else:
            socketio.emit('detailed_log', {'message': f"ERRORE: Tentativo {attempt} ha restituito un codice di stato inatteso {response.status_code}"})
        
        time.sleep(wait_seconds)

    raise TimeoutError(f"Download del file per {platform} fallito dopo {attempt} tentativi.")


def main(config, socketio): # <-- MODIFICA CHIAVE: Accetta socketio
    """
    Usa la configurazione passata, scarica i file e restituisce la configurazione aggiornata.
    """
    project_id = config["lokalise"]["project_id"]
    api_key = config["lokalise"]["api_key"]

    ios_path = Path("lokalise_translation_manager/lokalise_files/ios")
    android_path = Path("lokalise_translation_manager/lokalise_files/android")

    # Passa socketio alle sotto-funzioni
    ios_dir = fetch_lokalise_file(project_id, api_key, "iOS", "strings", str(ios_path), socketio)
    android_dir = fetch_lokalise_file(project_id, api_key, "Android", "xml", str(android_path), socketio)

    config["lokalise_paths"] = {
        "ios": ios_dir,
        "android": android_dir
    }

    socketio.emit('detailed_log', {'message': 'Percorsi dei file di Lokalise aggiornati in memoria.'})
    
    return config


if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data['message']}")

    config_path_test = Path(__file__).resolve().parent.parent.parent / "config" / "user_config.json"
    if config_path_test.exists():
        with open(config_path_test) as f:
            test_config = json.load(f)
        main(test_config, MockSocket())
    else:
        print("config/user_config.json non trovato. Impossibile eseguire il test.")