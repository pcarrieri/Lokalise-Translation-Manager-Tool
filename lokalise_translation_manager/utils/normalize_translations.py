# utils/normalize_translations.py - Normalize and prepare translations for OpenAI

import csv
import time
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR.parent / "reports"
READY_DIR = BASE_DIR.parent / "ready_to_be_translated"
MERGED_RESULT_FILE = REPORTS_DIR / "merged_result.csv"
EN_TRANSLATIONS_FILE = REPORTS_DIR / "en_translations.csv"
OUTPUT_FILE = READY_DIR / "merged_translations_result.csv"

# Mappa per normalizzare i codici lingua
LOKALISE_LANGUAGES = {
    "en": "en", "de": "de", "fr": "fr", "it": "it", "pl": "pl",
    "sv": "sv", "nb": "nb", "da": "da", "fi": "fi",
    "lt": "lt_LT", "lv": "lv_LV", "et": "et_EE"
}


def normalize_languages(languages_str, normalization_count):
    normalized = []
    languages = [lang.strip() for lang in languages_str.split(',')]
    
    for lang in languages:
        if lang in LOKALISE_LANGUAGES:
            normalized_lang = LOKALISE_LANGUAGES[lang]
            normalized.append(normalized_lang)
            normalization_count.setdefault(normalized_lang, 0)
            normalization_count[normalized_lang] += 1
        elif lang:
            normalized.append(lang)
            normalization_count.setdefault(lang, 0)
            normalization_count[lang] += 1
            
    return ','.join(normalized)

def process_normalization(config, socketio):
    normalization_count = {}
    start_time = time.time()

    try:
        READY_DIR.mkdir(parents=True, exist_ok=True)
        socketio.emit('detailed_log', {'message': "Normalizzazione dei dati per il motore di traduzione..."})

        with MERGED_RESULT_FILE.open('r', encoding='utf-8') as merged_file:
            merged_reader = csv.DictReader(merged_file)
            merged_data = {row['key_id']: row for row in merged_reader if row.get('key_id') and row.get('key_id') != 'NOT_FOUND'}

        with EN_TRANSLATIONS_FILE.open('r', encoding='utf-8') as en_file:
            en_reader = csv.DictReader(en_file)
            en_data = {row['key_id']: row for row in en_reader}
        
        socketio.emit('detailed_log', {'message': f"Trovate {len(merged_data)} chiavi con traduzioni mancanti e {len(en_data)} traduzioni inglesi."})

        output_data = []
        for key_id, merged_row in merged_data.items():
            if key_id in en_data:
                normalized_languages_str = normalize_languages(merged_row['languages'], normalization_count)
                
                if normalized_languages_str:
                    output_data.append({
                        'key_name': merged_row['key_name'],
                        'key_id': key_id,
                        'languages': normalized_languages_str,
                        'translation_id': en_data[key_id]['translation_id'],
                        'translation': en_data[key_id]['translation']
                    })

        with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as output_file:
            fieldnames = ['key_name', 'key_id', 'languages', 'translation_id', 'translation']
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)

        socketio.emit('detailed_log', {'message': f"Normalizzazione completata. {len(output_data)} chiavi pronte per il prossimo step."})

    except Exception as e:
        import traceback
        socketio.emit('detailed_log', {'message': f"ERRORE durante la normalizzazione: {e}\n{traceback.format_exc()}"})

    finally:
        elapsed = time.time() - start_time
        socketio.emit('detailed_log', {'message': f"Tempo di esecuzione normalizzazione: {elapsed:.2f} secondi."})
        
        # --- NUOVO: Invia dati strutturati per il grafico ---
        # Filtra solo le lingue con almeno una traduzione da fare
        chart_data = {lang: count for lang, count in normalization_count.items() if count > 0}
        
        if chart_data:
            summary_data = {
                'title': 'Conteggio Traduzioni per Lingua',
                'type': 'bar',
                'data': {
                    'labels': list(chart_data.keys()),
                    'values': list(chart_data.values())
                }
            }
            socketio.emit('summary_data', summary_data)

if __name__ == "__main__":
    import json
    class MockSocket:
        def emit(self, event, data):
            # Per il test, stampiamo sia i log che i dati dei riepiloghi
            if event == 'summary_data':
                print(f"EMIT SUMMARY: {data['title']} - {data['data']}")
            else:
                print(f"EMIT: {event} - {data['message']}")
    
    process_normalization({}, MockSocket())