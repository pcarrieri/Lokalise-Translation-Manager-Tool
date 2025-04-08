from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import signal

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "reports"))

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
        return jsonify({"message": "File aggiornato con successo."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import sys
    import atexit

    # Salva il PID in /tmp/flask.pid per gestione automatica
    with open("/tmp/flask.pid", "w") as f:
        f.write(str(os.getpid()))

    def cleanup():
        if os.path.exists("/tmp/flask.pid"):
            os.remove("/tmp/flask.pid")

    atexit.register(cleanup)

    app.run(port=5050, debug=False, use_reloader=False)
