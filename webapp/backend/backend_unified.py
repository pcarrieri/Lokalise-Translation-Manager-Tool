# webapp/backend/backend_unified.py
import os
import sys
import importlib
import json
import pandas as pd
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

# --- Configurazione App ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Percorsi ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
CONFIG_DIR = ROOT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "user_config.json"

REPORTS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)


# --- MODIFICATO: Elenco degli step ---
steps_part_1 = [
    ("download", "Downloading Lokalise files...", "lokalise_translation_manager.download.download_lokalise_files", "main"),
    ("ios_scan", "Running iOS scanner...", "lokalise_translation_manager.scanner.ios_scanner", "main"),
    ("android_scan", "Running Android scanner...", "lokalise_translation_manager.scanner.android_scanner", "main"),
    ("merge", "Merging iOS and Android missing translations...", "lokalise_translation_manager.utils.merge_translations", "run_merge"),
    ("download_keys", "Downloading all Lokalise keys...", "lokalise_translation_manager.utils.download_lokalise_keys", "main"),
    ("normalize", "Normalizing data for translation...", "lokalise_translation_manager.utils.normalize_translations", "process_normalization"),
    ("prepare", "Preparing final file for translation engine...", "lokalise_translation_manager.utils.prepare_translations", "main"),
    ("translate", "Performing translations with OpenAI...", "lokalise_translation_manager.translator.translate_with_openai", "main"),
    # Lo step di cleanup (solo analisi) è ora l'ultimo della prima parte
    ("cleanup_analysis", "Analyzing unused keys from Lokalise...", "lokalise_translation_manager.utils.cleanup_unused_keys", "main"),
]

# La Parte 2 ora contiene solo l'upload
steps_part_2 = [
    ("upload", "Uploading translations to Lokalise...", "lokalise_translation_manager.utils.upload_translations", "main"),
]

# Dentro webapp/backend/backend_unified.py

# Dentro webapp/backend/backend_unified.py

def run_steps(steps, initial_config):
    """Funzione generica per eseguire una lista di step."""
    config = initial_config
    last_result = None
    try:
        sys.path.insert(0, str(ROOT_DIR))

        for i, (step_id, message, module_name, func_name) in enumerate(steps):

            socketio.emit('progress', {'step': step_id, 'message': message, 'status': 'running'})

            # --- NUOVA MODIFICA ---
            # Aggiungiamo un log per vedere se il problema è nel caricamento del modulo
            socketio.emit('detailed_log', {'message': f"Caricamento modulo: {module_name}..."})
            socketio.sleep(0.1)

            module = importlib.import_module(module_name)
            func = getattr(module, func_name)

            socketio.emit('detailed_log', {'message': "Esecuzione funzione principale del modulo..."})
            socketio.sleep(0.1)

            result = func(config, socketio)
            last_result = result
            if isinstance(result, dict):
                config = result

            socketio.emit('detailed_log', {'message': f"✅ {message.replace('...', ' completato.')}"})
            socketio.sleep(0.5)

        return config, last_result

    except Exception as e:
        import traceback
        error_message = f"❌ An error occurred: {str(e)}\n{traceback.format_exc()}"
        socketio.emit('error', {'error': error_message})
        return None, None
    finally:
        if str(ROOT_DIR) in sys.path:
            sys.path.remove(str(ROOT_DIR))

def run_pre_review_steps():
    """Esegue tutti gli step fino alla revisione."""
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    final_config, last_step_result = run_steps(steps_part_1, config)
    
    if final_config:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(final_config, f, indent=4)
        
        # L'ultimo risultato della Parte 1 è la lista di chiavi da `cleanup_unused_keys`
        keys_for_cleanup = last_step_result
        
        # Emette l'evento per la revisione delle traduzioni
        socketio.emit('awaiting_review', {'filename': 'translation_done.csv'})

        # Se ci sono chiavi da cancellare, emette un altro evento per la decisione
        if keys_for_cleanup:
            socketio.emit('awaiting_cleanup_decision', {'keys': keys_for_cleanup})

def run_post_review_steps():
    """Esegue gli step dopo l'approvazione dell'utente."""
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        
    final_config, _ = run_steps(steps_part_2, config)
    
    if final_config:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(final_config, f, indent=4)
        
        socketio.emit('completed', {'status': 'success', 'message': '✅ All steps completed successfully!'})


# --- Endpoint API e Socket.IO ---

@app.route('/run-tool', methods=['POST'])
def run_tool_endpoint():
    socketio.start_background_task(run_pre_review_steps)
    return jsonify({'message': 'Tool execution (Part 1) started.'}), 202

@app.route('/resume-upload', methods=['POST'])
def resume_upload_endpoint():
    socketio.emit('progress', {'step': 'resume', 'message': 'Processo ripreso. Inizio upload...', 'status': 'running'})
    socketio.start_background_task(run_post_review_steps)
    return jsonify({'message': 'Process resumed for upload (Part 2).'}), 202

# --- NUOVO ENDPOINT PER ESEGUIRE LA CANCELLAZIONE ---
@app.route('/execute-cleanup', methods=['POST'])
def execute_cleanup_endpoint():
    data = request.json
    keys_to_delete = data.get('keys')

    if not keys_to_delete:
        return jsonify({"error": "No keys provided for deletion"}), 400

    from lokalise_translation_manager.utils.cleanup_unused_keys import delete_keys_from_lokalise
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    socketio.start_background_task(delete_keys_from_lokalise, keys_to_delete, config, socketio)
    
    return jsonify({"message": "Cleanup process started."}), 202
    
@app.route('/get-config', methods=['GET'])
def get_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    else:
        return jsonify({
            "lokalise": {"project_id": "", "api_key": ""},
            "openai": {"api_key": ""},
            "project_paths": {"ios": "", "android": ""}
        })

@app.route('/save-config', methods=['POST'])
def save_config():
    try:
        config_data = request.json
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return jsonify({'message': 'Configuration saved.'}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files', methods=['GET'])
def list_files():
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')]
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    try:
        df = pd.read_csv(os.path.join(REPORTS_DIR, filename))
        return df.to_json(orient='records')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files/<filename>', methods=['POST'])
def update_file(filename):
    try:
        data = request.json
        df = pd.DataFrame(data)
        df.to_csv(os.path.join(REPORTS_DIR, filename), index=False)
        return jsonify({"message": "File updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    print("Backend server starting on http://localhost:5050")
    socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False)