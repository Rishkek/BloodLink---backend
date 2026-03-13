import sqlite3
import time
import random
import sys
import pandas as pd

BLOOD_GROUPS = ['O_pos', 'O_neg', 'A_pos', 'A_neg', 'B_pos', 'B_neg', 'AB_pos', 'AB_neg']
# Real-world rarity weights (approximate percentages to dictate which blood gets used)
WEIGHTS = [0.37, 0.01, 0.22, 0.005, 0.32, 0.005, 0.069, 0.001]

CRISIS_CASES = {
    0: {'amount': 1, 'duration': 9, 'name': 'Minor'},
    1: {'amount': 2, 'duration': 20, 'name': 'Small'},
    2: {'amount': 3, 'duration': 30, 'name': 'Medium'},
    3: {'amount': 4, 'duration': 35, 'name': 'Large'}
}


def trigger_crisis():
    # 1. Get hospital IDs
    hosp_input = input("Enter the hospital index IDs (comma-separated, e.g., 1,4,15): ")
    try:
        hosp_ids = [int(x.strip()) for x in hosp_input.split(',')]
    except ValueError:
        print("Invalid input. Please enter numbers only.")
        return

    # 2. Get Crisis Case
    print("\nCrisis Cases:")
    print("0 = Minor  (1 unit/sec for 9s)")
    print("1 = Small  (2 units/sec for 20s)")
    print("2 = Medium (3 units/sec for 30s)")
    print("3 = Large  (4 units/sec for 35s)")
    case_input = input("Select crisis case (0-3): ")

    try:
        case_idx = int(case_input.strip())
        if case_idx not in CRISIS_CASES:
            raise ValueError
    except ValueError:
        print("Invalid case selected.")
        return

    crisis = CRISIS_CASES[case_idx]
    amount_per_sec = crisis['amount']
    duration = crisis['duration']

    conn = sqlite3.connect('hospitals.db')
    cursor = conn.cursor()

    print(f"\n[!] INITIATING {crisis['name'].upper()} CRISIS ON HOSPITALS: {hosp_ids}")
    print(f"[-] Dropping {amount_per_sec} units/sec for {duration} seconds...\n")

    # Fetch initial data
    placeholders = ','.join('?' for _ in hosp_ids)
    cursor.execute(f"SELECT id, name, {', '.join(BLOOD_GROUPS)} FROM hospitals WHERE id IN ({placeholders})", hosp_ids)

    tracking = {}
    for row in cursor.fetchall():
        tracking[row[0]] = {
            'name': row[1],
            'inventory': list(row[2:]),
            'total': sum(row[2:])
        }

    # 3. Real-time countdown loop
    for sec in range(1, duration + 1):
        for hid, h_data in tracking.items():

            # Pick which blood types to decrease, heavily weighted towards common types
            types_to_decrease = random.choices(range(len(BLOOD_GROUPS)), weights=WEIGHTS, k=amount_per_sec)

            for bg_idx in types_to_decrease:
                if h_data['inventory'][bg_idx] > 0:
                    h_data['inventory'][bg_idx] -= 1
                    h_data['total'] -= 1

            # Instantly update the database
            cursor.execute(f"""
                UPDATE hospitals
                SET O_pos=?, O_neg=?, A_pos=?, A_neg=?, B_pos=?, B_neg=?, AB_pos=?, AB_neg=?, Total_Units=?
                WHERE id=?
            """, (*h_data['inventory'], h_data['total'], hid))

        conn.commit()

        # Print a live updating status bar in the terminal
        status_string = " | ".join([f"{data['name'][:12]}: {data['total']}u" for data in tracking.values()])
        sys.stdout.write(f"\r[Time: {sec:02d}s / {duration}s] => {status_string}    ")
        sys.stdout.flush()

        time.sleep(1)

    print("\n\n[!] Crisis simulation complete.")

    # Sync the final devastation to the CSV
    pd.read_sql("SELECT * FROM hospitals", conn).to_csv("hospitals.csv", index=False)
    conn.close()
    print("[-] hospitals.csv updated with crisis data.")


if __name__ == "__main__":
    trigger_crisis()
