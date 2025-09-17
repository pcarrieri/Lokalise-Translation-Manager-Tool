# utils/prepare_translations.py - Prepare final file for OpenAI translation engine

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
READY_DIR = BASE_DIR.parent / "ready_to_be_translated"
MERGED_TRANSLATIONS_FILE = READY_DIR / "merged_translations_result.csv"
ALL_TRANSLATION_IDS_FILE = REPORTS_DIR / "all_translation_ids.csv"
OUTPUT_FILE = REPORTS_DIR / "ready_to_translations.csv"

def load_all_translation_ids(socketio):
    """
    Carica tutti gli ID di traduzione dal file CSV in un dizionario.
    """
    all_translations = {}
    if not ALL_TRANSLATION_IDS_FILE.exists():
        socketio.emit('detailed_log', {'message': f'ERRORE: File {ALL_TRANSLATION_IDS_FILE.name} non trovato.'})
        return all_translations

    with ALL_TRANSLATION_IDS_FILE.open('r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key_id = row['key_id']
            languages = row['language_iso'].split(',')
            translation_ids = row['translation_id'].split(',')
            all_translations[key_id] = dict(zip(languages, translation_ids))
    
    socketio.emit('detailed_log', {'message': f'Caricati {len(all_translations)} record di ID di traduzione.'})
    return all_translations

def filter_and_save_translations(all_translations, socketio):
    """
    Filtra le traduzioni per key_id e salva il risultato in un nuovo file CSV.
    """
    if not MERGED_TRANSLATIONS_FILE.exists():
        socketio.emit('detailed_log', {'message': f'ERRORE: File {MERGED_TRANSLATIONS_FILE.name} non trovato.'})
        # Crea un file di output vuoto per non interrompere il flusso
        with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as outfile:
             writer = csv.writer(outfile)
             writer.writerow(['key_name', 'key_id', 'languages', 'translation_id', 'translation'])
        return

    translations_to_process = []
    with MERGED_TRANSLATIONS_FILE.open('r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        translations_to_process = list(reader)
    
    socketio.emit('detailed_log', {'message': f'Trovate {len(translations_to_process)} chiavi da processare.'})

    with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['key_name', 'key_id', 'languages', 'translation_id', 'translation']
        writer = csv.writer(outfile)
        writer.writerow(fieldnames)

        final_count = 0
        for row in translations_to_process:
            key_id = row['key_id']
            if key_id in all_translations:
                languages = row['languages'].split(',')
                filtered_languages = []
                filtered_translation_ids = []

                for lang in languages:
                    if lang in all_translations[key_id]:
                        filtered_languages.append(lang)
                        filtered_translation_ids.append(all_translations[key_id][lang])

                if filtered_languages:
                    final_count += 1
                    writer.writerow([
                        row['key_name'],
                        key_id,
                        ','.join(filtered_languages),
                        ','.join(filtered_translation_ids),
                        row['translation']
                    ])
        socketio.emit('detailed_log', {'message': f'Filtraggio completato. {final_count} chiavi pronte per la traduzione.'})


def main(config, socketio): # Accetta config per coerenza
    socketio.emit('detailed_log', {'message': 'Preparazione del file finale per il motore di traduzione...'})
    all_translations = load_all_translation_ids(socketio)
    filter_and_save_translations(all_translations, socketio)
    socketio.emit('detailed_log', {'message': f"File per la traduzione salvato in {OUTPUT_FILE.name}."})

if __name__ == "__main__":
    class MockSocket:
        def emit(self, event, data):
            print(f"EMIT: {event} - {data['message']}")
    
    main({}, MockSocket())