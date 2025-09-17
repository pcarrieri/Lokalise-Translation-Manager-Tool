# utils/merge_translations.py - Merge iOS and Android missing translations reports

import csv
from pathlib import Path
from collections import defaultdict

# I percorsi dei file di input e output
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
IOS_CSV = REPORTS_DIR / "ios" / "missing_ios_translations.csv"
ANDROID_CSV = REPORTS_DIR / "android" / "missing_android_translations.csv"
FINAL_CSV = REPORTS_DIR / "missing_translations.csv"


def load_missing_translations(file_path, platform, socketio):
    """Carica le traduzioni mancanti da un file CSV."""
    translations = defaultdict(list)
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader, None) # Salta l'intestazione
                for row in reader:
                    if not row: continue
                    key = row[0]
                    languages = row[1].split(', ') if len(row) > 1 else []
                    translations[key] = languages
        except Exception as e:
            socketio.emit('detailed_log', {'message': f"Errore durante la lettura di {file_path}: {e}"})
    else:
        socketio.emit('detailed_log', {'message': f"File report per {platform} non trovato, lo salto."})
    return translations

def merge_translations(ios_translations, android_translations):
    """Unisce i dizionari di traduzioni mancanti, senza duplicare le lingue."""
    merged = defaultdict(list, ios_translations)
    for key, langs in android_translations.items():
        existing_langs = set(merged[key])
        for lang in langs:
            if lang not in existing_langs:
                merged[key].append(lang)
    return merged

def write_final_csv(translations, socketio):
    """Scrive il file CSV finale con tutte le traduzioni mancanti unificate."""
    try:
        FINAL_CSV.parent.mkdir(parents=True, exist_ok=True)
        with FINAL_CSV.open('w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['key_name', 'languages']) # Aggiunge un'intestazione
            for key, languages in sorted(translations.items()):
                writer.writerow([key, ", ".join(sorted(languages))])
        socketio.emit('detailed_log', {'message': f"Risultati uniti salvati in {FINAL_CSV.name}"})
    except Exception as e:
        socketio.emit('detailed_log', {'message': f"Errore durante la scrittura del CSV finale: {e}"})

def run_merge(config, socketio):
    """Funzione principale che orchestra il processo di unione."""
    ios = load_missing_translations(IOS_CSV, "iOS", socketio)
    android = load_missing_translations(ANDROID_CSV, "Android", socketio)

    if not ios and not android:
        socketio.emit('detailed_log', {'message': "Nessun file di traduzioni mancanti da unire."})
        write_final_csv({}, socketio)
        return

    merged = merge_translations(ios, android)
    write_final_csv(merged, socketio)
    
    # --- NUOVO: Invia dati strutturati per il grafico ---
    summary_data = {
        'title': 'Riepilogo Unione Traduzioni',
        'type': 'bar',
        'data': {
            'labels': [
                'Mancanti solo su iOS', 
                'Mancanti solo su Android',
                'Mancanti su Entrambi (Comuni)',
                'Totale Chiavi Unificate'
            ],
            'values': [
                len(set(ios.keys()) - set(android.keys())),
                len(set(android.keys()) - set(ios.keys())),
                len(set(ios.keys()) & set(android.keys())),
                len(merged)
            ]
        }
    }
    socketio.emit('summary_data', summary_data)

if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data}")
    
    run_merge({}, MockSocket())