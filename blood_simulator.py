import sqlite3
import time
import random
import pandas as pd
import os
import sys

try:
    import msvcrt
except ImportError:
    print("Warning: msvcrt module not found. The 'Enter to skip' feature only works on Windows.")
    msvcrt = None

BLOOD_GROUPS = ['O_pos', 'O_neg', 'A_pos', 'A_neg', 'B_pos', 'B_neg', 'AB_pos', 'AB_neg']

# separated 'use_prob' (high chance) and 'don_prob' (low chance)
SIMULATION_PROFILES = {
    '1': {'use_prob': 0.50, 'don_prob': 0.15, 'use_min': 1, 'use_max': 2, 'don_min': 15, 'don_max': 30},  # Excellent
    '2': {'use_prob': 0.60, 'don_prob': 0.12, 'use_min': 1, 'use_max': 3, 'don_min': 15, 'don_max': 25},  # Good
    '3': {'use_prob': 0.70, 'don_prob': 0.10, 'use_min': 1, 'use_max': 3, 'don_min': 10, 'don_max': 25},  # Stable
    '4': {'use_prob': 0.80, 'don_prob': 0.08, 'use_min': 2, 'use_max': 4, 'don_min': 10, 'don_max': 20},  # Low risk
    '5': {'use_prob': 0.85, 'don_prob': 0.05, 'use_min': 2, 'use_max': 5, 'don_min': 10, 'don_max': 20},  # Medium risk
    '6': {'use_prob': 0.90, 'don_prob': 0.03, 'use_min': 3, 'use_max': 6, 'don_min': 10, 'don_max': 15},  # High risk
    '7': {'use_prob': 0.95, 'don_prob': 0.01, 'use_min': 4, 'use_max': 8, 'don_min': 5, 'don_max': 15},  # Critical
}

# The minimum safe threshold of blood required based on hospital size
MIN_REQUIREMENTS = {
    "Large": 150,
    "Big": 100,
    "Moderate": 75,
    "Medium": 50,
    "Clinic": 25,
    "Small": 10
}


def update_csv():
    conn = sqlite3.connect("hospitals.db")
    pd.read_sql("SELECT * FROM hospitals", conn).to_csv("hospitals.csv", index=False)
    conn.close()


def get_simulation_key():
    if not os.path.exists('key.txt'):
        print("Error: key.txt not found. Please run generate_key.py first.")
        return None
    with open('key.txt', 'r') as file:
        return file.read().strip()


def wait_with_skip(seconds):
    if msvcrt is None:
        time.sleep(seconds)
        return

    while msvcrt.kbhit():
        msvcrt.getch()

    spinner_chars = ['|', '/', '-', '\\']
    total_ticks = seconds * 10

    for tick in range(total_ticks):
        rem_sec = seconds - (tick // 10)
        spin = spinner_chars[tick % 4]

        sys.stdout.write(f"\r[{spin}] Waiting {rem_sec}s... (Press ENTER to force update)   ")
        sys.stdout.flush()

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':
                sys.stdout.write("\r" + " " * 65 + "\r")
                sys.stdout.flush()
                print("\n >> SKIP INITIATED! Forcing immediate high-speed inventory update...")
                return
        time.sleep(0.1)

    sys.stdout.write("\r" + " " * 65 + "\r")
    sys.stdout.flush()


def simulate_blood_flow(sim_key):
    conn = sqlite3.connect('hospitals.db')
    cursor = conn.cursor()

    cursor.execute(f"SELECT id, name, Size, {', '.join(BLOOD_GROUPS)} FROM hospitals ORDER BY id")
    hospitals = cursor.fetchall()

    bulk_update_data = []
    tickets = []

    for index, hospital in enumerate(hospitals):
        hosp_id = hospital[0]
        hosp_name = hospital[1]
        hosp_size = hospital[2] if hospital[2] else 'Medium'

        hospital_sim_digit = sim_key[index] if index < len(sim_key) else '3'
        profile = SIMULATION_PROFILES.get(hospital_sim_digit, SIMULATION_PROFILES['3'])

        inventory = list(hospital[3:])
        hit_zero = False

        for i in range(len(BLOOD_GROUPS)):
            # 1. CONSTANT USAGE: Independent high probability roll
            if random.random() < profile['use_prob']:
                used_amount = random.randint(profile['use_min'], profile['use_max'])
                if inventory[i] - used_amount <= 0:
                    hit_zero = True
                inventory[i] = max(0, inventory[i] - used_amount)

            # 2. RARE DONATION: Independent low probability roll
            if random.random() < profile['don_prob']:
                donated_amount = random.randint(profile['don_min'], profile['don_max'])
                inventory[i] += donated_amount

        new_total = sum(inventory)
        bulk_update_data.append((*inventory, new_total, hosp_id))

        min_required = MIN_REQUIREMENTS.get(hosp_size, 50)

        if hit_zero or new_total < min_required:
            required_units = max(min_required - new_total, 15)
            tickets.append({
                "Sl.no": hosp_id,
                "Hospital Name": hosp_name,
                "Required Units": required_units
            })

    cursor.executemany("""
                       UPDATE hospitals
                       SET O_pos       = ?,
                           O_neg       = ?,
                           A_pos       = ?,
                           A_neg       = ?,
                           B_pos       = ?,
                           B_neg       = ?,
                           AB_pos      = ?,
                           AB_neg      = ?,
                           Total_Units = ?
                       WHERE id = ?
                       """, bulk_update_data)

    conn.commit()
    conn.close()

    if tickets:
        pd.DataFrame(tickets).to_csv("ticket.csv", index=False)
        print(f"   --> ⚠️ ALERT: Generated {len(tickets)} emergency resupply tickets in ticket.csv!")
    else:
        if os.path.exists("ticket.csv"):
            os.remove("ticket.csv")


if __name__ == "__main__":
    sim_key = get_simulation_key()
    if sim_key:
        print("Starting High-Speed BloodLink Real-Time Simulation using key.txt...")
        print("Press Ctrl+C to stop the script entirely.\n")

        try:
            simulate_blood_flow(sim_key)
            update_csv()
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] Initial inventory update complete.")
            print("-" * 50)

            while True:
                wait_with_skip(60)

                start_time = time.time()
                simulate_blood_flow(sim_key)
                update_csv()
                exec_time = time.time() - start_time

                current_time = time.strftime("%H:%M:%S")
                print(f"[{current_time}] Successfully updated DB & CSV in {exec_time:.3f} seconds.")
                print("-" * 50)

        except KeyboardInterrupt:
            print("\nSimulation stopped safely.")