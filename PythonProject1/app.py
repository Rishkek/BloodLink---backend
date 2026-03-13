from flask import Flask, render_template, jsonify, request
import pandas as pd
import threading
import time
import subprocess
import os
import sqlite3
from cause_crisis import trigger_crisis_api

app = Flask(__name__)


# --- Background Simulator Thread ---
def run_simulator_background():
    """Runs blood_simulator.py silently in the background."""
    print("Starting Blood Simulator background process...")
    subprocess.Popen(["python", "blood_simulator.py"])


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """Reads directly from the robust SQLite database to avoid CSV file lock crashes."""
    try:
        conn = sqlite3.connect('hospitals.db')
        df = pd.read_sql('SELECT * FROM hospitals', conn)
        conn.close()
        return df.to_json(orient='records')
    except Exception as e:
        print(f"Database read error: {e}")
        return jsonify([])


@app.route('/api/trigger_crisis', methods=['POST'])
def api_trigger_crisis():
    """Receives the queue from the frontend and fires the crisis script."""
    payload = request.json
    trigger_crisis_api(payload)
    return jsonify({"status": "Crisis Initiated!"})


if __name__ == '__main__':
    thread = threading.Thread(target=run_simulator_background)
    thread.daemon = True
    thread.start()

    app.run(debug=True, port=5000)