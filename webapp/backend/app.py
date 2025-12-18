"""
Flask Backend API for Lokalise Translation Manager Tool

This module provides a REST API for the web UI to interact with CSV reports.
It allows viewing, editing, and saving translation reports through HTTP endpoints.

Features:
    - List all available CSV files in reports directory
    - Read CSV file contents as JSON
    - Update CSV file contents from JSON
    - CORS enabled for frontend integration
    - Automatic PID management for process control

Endpoints:
    GET  /files           - List all CSV files
    GET  /files/<filename> - Get file contents as JSON
    POST /files/<filename> - Update file contents from JSON

Usage:
    python3 webapp/backend/app.py

    The server starts on port 5050 and listens for connections from the
    React frontend (typically running on port 5173).

Example Requests:
    # List files
    GET http://localhost:5050/files
    Response: ["translation_done.csv", "final_report.csv", ...]

    # Get file
    GET http://localhost:5050/files/translation_done.csv
    Response: [{"key_name": "ms_test", "key_id": "123", ...}, ...]

    # Update file
    POST http://localhost:5050/files/translation_done.csv
    Body: [{"key_name": "ms_test", "key_id": "123", ...}, ...]
    Response: {"message": "File updated successfully."}

Security Notes:
    - CORS is enabled for all origins (development setup)
    - No authentication implemented
    - File operations limited to reports directory
    - PID file stored in /tmp/flask.pid for process management
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import signal
from typing import Dict, List, Any
from pathlib import Path

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR.parent.parent / "reports"


@app.route('/files', methods=['GET'])
def list_files() -> tuple:
    """
    List all CSV files in the reports directory.

    Returns:
        tuple: JSON response with list of filenames and HTTP status code

    Response Format:
        Success (200): ["file1.csv", "file2.csv", ...]
        Error (500): {"error": "error message"}

    Example:
        GET /files
        Response: ["translation_done.csv", "final_report.csv"]
    """
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')]
        return jsonify(files), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/files/<filename>', methods=['GET'])
def get_file(filename: str) -> tuple:
    """
    Get the contents of a specific CSV file as JSON.

    Args:
        filename: Name of the CSV file to read

    Returns:
        tuple: JSON response with file contents and HTTP status code

    Response Format:
        Success (200): [{"col1": "val1", "col2": "val2"}, ...]
        Error (500): {"error": "error message"}

    Example:
        GET /files/translation_done.csv
        Response: [
            {"key_name": "ms_test", "key_id": "123", "translation": "Hello"},
            ...
        ]

    Note:
        The CSV is automatically parsed by pandas and converted to JSON
        with 'records' orientation (list of dictionaries).
    """
    try:
        file_path = REPORTS_DIR / filename
        df = pd.read_csv(file_path)
        return df.to_json(orient='records'), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/files/<filename>', methods=['POST'])
def update_file(filename: str) -> tuple:
    """
    Update a CSV file with new contents from JSON.

    Args:
        filename: Name of the CSV file to update

    Request Body:
        JSON array of objects (same format as GET response)

    Returns:
        tuple: JSON response with success message and HTTP status code

    Response Format:
        Success (200): {"message": "File updated successfully."}
        Error (500): {"error": "error message"}

    Example:
        POST /files/translation_done.csv
        Body: [
            {"key_name": "ms_test", "key_id": "123", "translation": "Hello"},
            ...
        ]
        Response: {"message": "File updated successfully."}

    Note:
        The existing file is completely replaced with the new data.
        CSV index is not included in the output file.
    """
    try:
        data = request.json
        df = pd.DataFrame(data)
        file_path = REPORTS_DIR / filename
        df.to_csv(file_path, index=False)
        return jsonify({"message": "File updated successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import sys
    import atexit

    # Save PID to /tmp/flask.pid for automatic process management
    pid_file = Path("/tmp/flask.pid")
    pid_file.write_text(str(os.getpid()))

    def cleanup():
        """Remove PID file on exit"""
        if pid_file.exists():
            pid_file.unlink()

    atexit.register(cleanup)

    print(f"Flask backend starting on http://localhost:5050")
    print(f"Serving reports from: {REPORTS_DIR}")
    print(f"PID: {os.getpid()} (saved to {pid_file})")

    app.run(port=5050, debug=False, use_reloader=False)
