# ios_scanner.py - iOS localization key scanner

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
REPORTS_DIR = BASE_DIR / "reports" / "ios"
FINAL_RESULT_CSV = REPORTS_DIR / "final_result_ios.csv"
TOTAL_KEYS_CSV = REPORTS_DIR / "total_keys_used_ios.csv"
SWIFT_FILES_CSV = REPORTS_DIR / "swift_files.csv"
MISSING_TRANSLATIONS_CSV = REPORTS_DIR / "missing_ios_translations.csv"
EXCLUDED_LOCALES_PATH = BASE_DIR / "config" / "excluded_locales.ini"

def extract_localized_strings(directory, socketio):
    localized_strings = set()
    file_analysis = {}
    pattern = re.compile(r'NSLocalizedString\(\"([^\"]+)\",\s*comment\s*:\s*\"[^\"]*\"\)')

    socketio.emit('detailed_log', {'message': f'Scansione della directory iOS: {directory}'})
    
    file_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.swift'):
                file_count += 1
                file_path = os.path.join(root, file)
                # --- ECCO LA RIGA MANCANTE, REINSERITA ---
                relative_path = os.path.relpath(file_path, directory) 
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        if matches:
                            localized_strings.update(matches)
                            file_analysis[relative_path] = len(matches)
                except Exception as e:
                    socketio.emit('detailed_log', {'message': f'Errore durante la lettura del file {file_path}: {e}'})

    socketio.emit('detailed_log', {'message': f'Analizzati {file_count} file .swift.'})
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

    with SWIFT_FILES_CSV.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['File Path', 'Number of Keys'])
        for path, count in file_analysis.items():
            writer.writerow([path, count])

    return localized_strings, file_analysis

def load_strings_file(file_path):
    strings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
            for line in content:
                if '=' in line:
                    key_value = line.split('=', 1)
                    if len(key_value) == 2:
                        key = key_value[0].strip().strip('"')
                        value = key_value[1].strip().strip(';').strip().strip('"')
                        strings[key] = value
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

def compare_translations(localizable_dir, keys_to_check, socketio):
    socketio.emit('detailed_log', {'message': 'Confronto delle traduzioni con i file di Lokalise...'})

    missing_translations = {}
    excluded_locales = load_excluded_locales()
    socketio.emit('detailed_log', {'message': f'Locali esclusi: {", ".join(excluded_locales) if excluded_locales else "Nessuno"}'})
    
    en_path = os.path.join(localizable_dir, 'en.lproj', 'Localizable.strings')
    en_strings = load_strings_file(en_path)

    if not en_strings:
        socketio.emit('detailed_log', {'message': 'ATTENZIONE: File Localizable.strings per la lingua inglese (en) non trovato o vuoto.'})

    for language_dir in os.listdir(localizable_dir):
        if language_dir.endswith('.lproj'):
            lang_code = language_dir.replace('.lproj', '').split('-')[0]
            if lang_code in excluded_locales or lang_code == 'en':
                continue

            lang_path = os.path.join(localizable_dir, language_dir, 'Localizable.strings')
            lang_strings = load_strings_file(lang_path)

            for key in keys_to_check:
                if key in en_strings and (key not in lang_strings or not lang_strings.get(key, "").strip()):
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
    ios_project_path = config.get("project_paths", {}).get("ios")
    localizable_dir = config.get("lokalise_paths", {}).get("ios")

    if not ios_project_path or not os.path.isdir(ios_project_path):
        socketio.emit('detailed_log', {'message': 'ERRORE: Percorso del progetto iOS non valido o mancante nella configurazione.'})
        return

    if not localizable_dir or not os.path.isdir(localizable_dir):
        socketio.emit('detailed_log', {'message': 'ERRORE: Percorso dei file Lokalise per iOS non valido o mancante.'})
        return

    localized_keys, file_analysis = extract_localized_strings(ios_project_path, socketio)
    missing_translations = compare_translations(localizable_dir, localized_keys, socketio)

    summary_data = {
        'title': 'Riepilogo Scanner iOS',
        'type': 'bar',
        'data': {
            'labels': [
                'Chiavi Totali Usate', 
                'Chiavi con Trad. Mancanti',
                'File Analizzati',
                'File con Chiavi'
            ],
            'values': [
                len(localized_keys), 
                len(missing_translations),
                len(file_analysis),
                sum(1 for count in file_analysis.values() if count > 0)
            ]
        }
    }
    socketio.emit('summary_data', summary_data)

if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data}")

    if (BASE_DIR / "config" / "user_config.json").exists():
        with open(BASE_DIR / "config" / "user_config.json") as f:
            test_config = json.load(f)
        main(test_config, MockSocket())
    else:
        print("config/user_config.json non trovato. Impossibile eseguire il test.")