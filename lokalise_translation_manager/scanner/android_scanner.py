# android_scanner.py - Android localization key scanner

import os
import re
import csv
import json
from pathlib import Path
import configparser

try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

# I percorsi sono definiti ma usati principalmente per scrivere i report
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "android"
FINAL_RESULT_CSV = REPORTS_DIR / "final_result_android.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_android.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_android_translations.csv"
EXCLUDED_LOCALES_PATH = BASE_DIR / "config" / "excluded_locales.ini"


def extract_localized_strings(directory, socketio):
    localized_strings = set()
    file_analysis = {}
    pattern = re.compile(r'R\.string\.([a-zA-Z0-9_]+)')

    socketio.emit('detailed_log', {'message': f'Scansione della directory Android: {directory}'})
    
    file_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.kt', '.java')):
                file_count += 1
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        if matches:
                            localized_strings.update(matches)
                except Exception as e:
                    socketio.emit('detailed_log', {'message': f'Errore durante la lettura del file {file_path}: {e}'})

    socketio.emit('detailed_log', {'message': f'Analizzati {file_count} file .kt/.java.'})
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with FINAL_RESULT_CSV.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['key_name'])
        for string in sorted(localized_strings):
            writer.writerow([string])

    with TOTAL_KEYS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['key_name'])
        for string in sorted(localized_strings):
            writer.writerow([string])
    socketio.emit('detailed_log', {'message': f'Trovate {len(localized_strings)} chiavi uniche.'})

    return localized_strings, file_count

def load_strings_file(file_path):
    strings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            matches = re.findall(r'<string name="([^"]+)">(.*?)</string>', content, re.DOTALL)
            for key, value in matches:
                strings[key] = value.strip().replace('<![CDATA[', '').replace(']]>', '').strip() != ""
    except Exception:
        pass
    return strings

def load_excluded_locales():
    excluded_locales = set()
    if EXCLUDED_LOCALES_PATH.exists():
        config = configparser.ConfigParser()
        config.read(EXCLUDED_LOCALES_PATH)
        if 'EXCLUDED' in config and 'excluded_locales' in config['EXCLUDED']:
            locales_str = config['EXCLUDED']['excluded_locales']
            excluded_locales = {locale.strip() for locale in locales_str.split(',') if locale.strip()}
    return excluded_locales

def compare_translations(values_dir, keys_to_check, socketio):
    socketio.emit('detailed_log', {'message': 'Confronto delle traduzioni con i file di Lokalise...'})

    missing_translations = {}
    excluded_locales = load_excluded_locales()
    socketio.emit('detailed_log', {'message': f'Locali esclusi: {", ".join(excluded_locales) if excluded_locales else "Nessuno"}'})
    
    en_path = os.path.join(values_dir, 'values', 'strings.xml')
    en_strings = load_strings_file(en_path)

    if not en_strings:
        socketio.emit('detailed_log', {'message': 'ATTENZIONE: File strings.xml per la lingua inglese (values/strings.xml) non trovato o vuoto.'})

    for dir_name in os.listdir(values_dir):
        if dir_name.startswith('values-'):
            lang_code_parts = dir_name.split('-')
            if len(lang_code_parts) > 1:
                lang_code = lang_code_parts[1]
                if lang_code in excluded_locales or lang_code == 'en':
                    continue

                lang_path = os.path.join(values_dir, dir_name, 'strings.xml')
                if os.path.exists(lang_path):
                    lang_strings = load_strings_file(lang_path)
                    for key in keys_to_check:
                        if key in en_strings and (key not in lang_strings or not lang_strings[key]):
                            if key not in missing_translations:
                                missing_translations[key] = []
                            missing_translations[key].append(lang_code)

    with MISSING_TRANSLATIONS_CSV.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['key_name', 'languages'])
        for key, languages in missing_translations.items():
            writer.writerow([key, ", ".join(languages)])
    socketio.emit('detailed_log', {'message': f'Trovate {len(missing_translations)} chiavi con traduzioni mancanti.'})

    return missing_translations

def main(config, socketio):
    android_project_path = config.get("project_paths", {}).get("android")
    values_dir = config.get("lokalise_paths", {}).get("android")

    if not android_project_path or not os.path.isdir(android_project_path):
        socketio.emit('detailed_log', {'message': 'ERRORE: Percorso del progetto Android non valido o mancante nella configurazione.'})
        return

    if not values_dir or not os.path.isdir(values_dir):
        socketio.emit('detailed_log', {'message': 'ERRORE: Percorso dei file Lokalise per Android non valido o mancante.'})
        return

    localized_keys, files_analyzed = extract_localized_strings(android_project_path, socketio)
    missing_translations = compare_translations(values_dir, localized_keys, socketio)

    # --- NUOVO: Invia dati strutturati per il grafico ---
    summary_data = {
        'title': 'Riepilogo Scanner Android',
        'type': 'bar',
        'data': {
            'labels': [
                'Chiavi Totali Usate', 
                'Chiavi con Trad. Mancanti',
                'File Analizzati (.kt/.java)'
            ],
            'values': [
                len(localized_keys), 
                len(missing_translations),
                files_analyzed
            ]
        }
    }
    socketio.emit('summary_data', summary_data)

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