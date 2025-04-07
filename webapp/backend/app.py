from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# Corretto percorso assoluto rispetto al file app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "reports"))

@app.route('/files', methods=['GET'])
def list_files():
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')]
    return jsonify(files)

@app.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    df = pd.read_csv(os.path.join(REPORTS_DIR, filename))
    return df.to_json(orient='records')

@app.route('/files/<filename>', methods=['POST'])
def update_file(filename):
    data = request.json
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(REPORTS_DIR, filename), index=False)
    return jsonify({"message": "File aggiornato con successo."})

if __name__ == '__main__':
    app.run(port=5050, debug=False, use_reloader=False)
