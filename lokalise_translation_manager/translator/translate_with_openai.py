# lokalise_translation_manager/translator/translate_with_openai.py

import csv
import json
import time
from pathlib import Path
from openai import OpenAI
import importlib.util

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
INPUT_FILE = REPORTS_DIR / "ready_to_translations.csv"
OUTPUT_FILE = REPORTS_DIR / "translation_done.csv"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"

def translate_text(client, text, lang, prompt="", socketio=None):
    """Esegue la traduzione di un singolo testo usando l'API di OpenAI."""
    try:
        instructions = (
            f"Translate the following English text to the language with ISO code '{lang}'. "
            f"Preserve any HTML tags or placeholders like %s, %d, %@, %1$s, etc., exactly as they are. {prompt}"
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if socketio:
            socketio.emit('detailed_log', {'message': f"ERRORE: La traduzione per '{lang}' è fallita - {e}"})
        return f"TRANSLATION_ERROR: {text}"

def load_completed_keys():
    """Carica gli ID delle chiavi già tradotte per poter riprendere il processo."""
    if not OUTPUT_FILE.exists():
        return set()
    with OUTPUT_FILE.open('r', encoding='utf-8') as f:
        try:
            return {row['key_id'] for row in csv.DictReader(f)}
        except (csv.Error, KeyError):
            return set()

def discover_plugins():
    # ... (funzione invariata)
    prompt_plugins, action_plugins, extension_plugins = [], [], []
    if PLUGINS_DIR.exists():
        for f in PLUGINS_DIR.glob('*.py'):
            if f.name == '__init__.py': continue
            content = f.read_text()
            if "[PROMPT]" in content:
                prompt_plugins.append(f.name)
            if "[ACTION]" in content:
                action_plugins.append(f.name)
            if "[EXTENSION]" in content:
                extension_plugins.append(f.name)
    return prompt_plugins, action_plugins, extension_plugins


def load_prompt_plugins(plugin_names, socketio):
    # ... (funzione invariata)
    texts = []
    for name in plugin_names:
        path = PLUGINS_DIR / name
        try:
            content = path.read_text()
            texts.append(content)
            socketio.emit('detailed_log', {'message': f'Caricato plugin PROMPT: {name}'})
        except Exception as e:
            socketio.emit('detailed_log', {'message': f'Fallito caricamento plugin PROMPT {name}: {e}'})
    return " ".join(texts)

def run_plugins(plugin_names, plugin_type, socketio):
    # ... (funzione invariata)
    for name in plugin_names:
        path = PLUGINS_DIR / name
        socketio.emit('detailed_log', {'message': f'Esecuzione plugin {plugin_type}: {name}'})
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'run'):
                module.run()
        except Exception as e:
            socketio.emit('detailed_log', {'message': f'Fallita esecuzione plugin {name}: {e}'})


def show_summary(socketio, prompt_plugins, action_plugins, extension_plugins):
    # ... (funzione invariata)
    summary = [
        "\n--- Riepilogo Configurazione OpenAI ---",
        f"Modello: GPT-4o",
        f"File di input: {INPUT_FILE.name}",
        f"File di output: {OUTPUT_FILE.name}",
        f"Plugin PROMPT ({len(prompt_plugins)}): {', '.join(prompt_plugins) or 'Nessuno'}",
        f"Plugin ACTION ({len(action_plugins)}): {', '.join(action_plugins) or 'Nessuno'}",
        f"Plugin EXTENSION ({len(extension_plugins)}): {', '.join(extension_plugins) or 'Nessuno'}"
    ]
    socketio.emit('detailed_log', {'message': "\n".join(summary)})


def run_translation(api_key, socketio):
    client = OpenAI(api_key=api_key)
    completed_keys = load_completed_keys()

    prompt_plugins, action_plugins, extension_plugins = discover_plugins()
    show_summary(socketio, prompt_plugins, action_plugins, extension_plugins)

    run_plugins(action_plugins, "ACTION", socketio)
    prompt_text = load_prompt_plugins(prompt_plugins, socketio)
    
    rows_to_translate = []
    if INPUT_FILE.exists():
         with INPUT_FILE.open('r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows_to_translate = [row for row in reader if row['key_id'] not in completed_keys]

    if not rows_to_translate:
        socketio.emit('detailed_log', {'message': "Nessuna nuova chiave da tradurre trovata."})
        run_plugins(extension_plugins, "EXTENSION", socketio)
        return

    total_translations = sum(len(row['languages'].split(',')) for row in rows_to_translate)
    socketio.emit('detailed_log', {'message': f"Trovate {len(rows_to_translate)} chiavi da tradurre, per un totale di {total_translations} traduzioni."})
    
    with OUTPUT_FILE.open('a', newline='', encoding='utf-8') as outfile:
        fieldnames = rows_to_translate[0].keys() if rows_to_translate else []
        if 'translated' not in fieldnames:
             fieldnames = list(fieldnames) + ['translated']

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if outfile.tell() == 0:
            writer.writeheader()

        start_time = time.time()
        completed_count = 0

        for row in rows_to_translate:
            langs = row['languages'].split(',')
            translations = []
            
            socketio.emit('detailed_log', {'message': f"Traduco '{row['key_name']}' in {len(langs)} lingue..."})

            for lang in langs:
                translation = translate_text(client, row['translation'], lang, prompt_text, socketio)
                translations.append(translation)
                completed_count += 1
                
                percent = (completed_count / total_translations) * 100 if total_translations > 0 else 0
                
                # --- MODIFICA CHIAVE: Invia l'aggiornamento per la barra di avanzamento ---
                socketio.emit('progress_update', {'percentage': percent})
                
                socketio.emit('detailed_log', {'message': f"  > {lang}: completato. ({completed_count}/{total_translations})"})

            row['translated'] = '|'.join(translations)
            writer.writerow(row)

    elapsed = time.time() - start_time
    socketio.emit('detailed_log', {'message': f"\nSalvataggio delle traduzioni completato in {OUTPUT_FILE.name}."})
    
    summary_data = {
        'title': 'Riepilogo Traduzioni OpenAI',
        'type': 'bar',
        'data': {
            'labels': ['Traduzioni Eseguite', 'Tempo (secondi)'],
            'values': [completed_count, round(elapsed, 2)]
        }
    }
    socketio.emit('summary_data', summary_data)
    
    run_plugins(extension_plugins, "EXTENSION", socketio)

def main(config, socketio):
    api_key = config.get("openai", {}).get("api_key")
    if not api_key:
        socketio.emit('detailed_log', {'message': "ERRORE: Chiave API di OpenAI non trovata nella configurazione."})
        raise ValueError("OpenAI API key not found in config")
    run_translation(api_key, socketio)

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