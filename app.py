from flask import Flask, render_template, jsonify, request
import pandas as pd
import threading
import subprocess
import os
import sqlite3
import json
from cause_crisis import trigger_crisis_api

app = Flask(__name__)


# --- Background Daemon Threads ---
def run_simulator_background():
    print("Starting Blood Simulator daemon...")
    subprocess.Popen(["python", "blood_simulator.py"])


def run_supply_pipe_background():
    print("Starting Supply Engine (Pipes & Trucks)...")
    subprocess.Popen(["python", "supply_pipe.py"])


def run_truck_background():
    print("Starting Truck Controller...")
    subprocess.Popen(["python", "truck_availability_controller.py"])


def run_temperature_background():
    print("Starting Temperature Daemon...")
    subprocess.Popen(["python", "temperature_daemon.py"])


# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """Reads directly from the robust SQLite database to avoid file lock crashes."""
    try:
        conn = sqlite3.connect('hospitals.db')
        df = pd.read_sql('SELECT * FROM hospitals', conn)
        conn.close()
        return df.to_json(orient='records')
    except Exception as e:
        print(f"Database read error: {e}")
        return jsonify([])


@app.route('/api/routes', methods=['GET'])
def get_active_routes():
    """Returns the currently active road routes drawn."""
    if not os.path.exists('active_routes.json'):
        return jsonify([])
    try:
        with open('active_routes.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Returns the live terminal feed for the frontend console."""
    if not os.path.exists('supply_logs.json'):
        return jsonify([])
    try:
        with open('supply_logs.json', 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])


@app.route('/api/trigger_crisis', methods=['POST'])
def api_trigger_crisis():
    """Receives the queue from the frontend and fires the crisis script."""
    payload = request.json
    trigger_crisis_api(payload)
    return jsonify({"status": "Crisis Initiated!"})


@app.route('/api/timescale', methods=['POST'])
def update_timescale():
    """Receives the timescale multiplier and writes it for daemons to read."""
    data = request.json
    timescale = data.get('timescale', 1.0)
    with open('timescale.txt', 'w') as f:
        f.write(str(timescale))
    return jsonify({"status": f"Timescale updated to {timescale}x"})


if __name__ == '__main__':
    # Initialize timescale.txt to 1.0x on server start
    if not os.path.exists('timescale.txt'):
        with open('timescale.txt', 'w') as f:
            f.write("1.0")

    # Start ALL background threads before launching the server
    threading.Thread(target=run_simulator_background, daemon=True).start()
    threading.Thread(target=run_supply_pipe_background, daemon=True).start()
    threading.Thread(target=run_truck_background, daemon=True).start()
    threading.Thread(target=run_temperature_background, daemon=True).start()  # <--- NEW DAEMON ADDED

    app.run(debug=True, port=5000)