import sqlite3
import requests
import re
import time
import pandas as pd
import os


def get_weather_desc(code):
    """Converts standard WMO weather codes into readable text."""
    mapping = {
        0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
        55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
    }
    return mapping.get(code, "Unknown")


def run_temperature_daemon():
    print("Starting Temperature & Weather Daemon (Updates every 10 minutes)...")

    while True:
        try:
            conn = sqlite3.connect('hospitals.db', timeout=10)
            cursor = conn.cursor()

            # Ensure columns exist
            new_columns = [("Temperature", "REAL"), ("Weather", "TEXT"), ("Rain_mm", "REAL"), ("Altitude", "REAL")]
            for col_name, data_type in new_columns:
                try:
                    cursor.execute(f"ALTER TABLE hospitals ADD COLUMN {col_name} {data_type}")
                except sqlite3.OperationalError:
                    pass

            cursor.execute("SELECT id, name, location FROM hospitals")
            hospitals = cursor.fetchall()

            for hospital_id, name, location in hospitals:
                coords = re.findall(r"[-+]?\d*\.\d+", str(location))
                if len(coords) < 2:
                    continue

                lat, lon = coords[0], coords[1]

                # Fetch from Open-Meteo
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,weather_code"
                response = requests.get(url, timeout=5).json()

                if "current" in response:
                    temp = response["current"]["temperature_2m"]
                    rain = response["current"]["precipitation"]
                    weather_desc = get_weather_desc(response["current"]["weather_code"])
                    altitude = response.get("elevation", 0.0)

                    cursor.execute("""
                                   UPDATE hospitals
                                   SET Temperature=?,
                                       Weather=?,
                                       Rain_mm=?,
                                       Altitude=?
                                   WHERE id = ?
                                   """, (temp, weather_desc, rain, altitude, hospital_id))

                    # Tiny sleep to avoid hammering the API and getting instantly blocked
                    time.sleep(0.1)

            # Save to DB and instantly sync to CSV
            conn.commit()
            pd.read_sql("SELECT * FROM hospitals", conn).to_csv("hospitals.csv", index=False)
            conn.close()

            # Print a silent timestamp to let you know it worked
            print(f"[{time.strftime('%H:%M:%S')}] Weather data successfully updated for all hospitals.")

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Temperature Daemon Error: {e}")

        # Sleep for 10 minutes (600 seconds)
        time.sleep(600)


if __name__ == '__main__':
    run_temperature_daemon()