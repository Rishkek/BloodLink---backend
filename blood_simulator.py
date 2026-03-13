import sqlite3
import time
import random
import pandas as pd

# The exact column names for the blood types in your database
BLOOD_GROUPS = ['O_pos', 'O_neg', 'A_pos', 'A_neg', 'B_pos', 'B_neg', 'AB_pos', 'AB_neg']


def update_csv():
    """Fetches the updated data from the DB and overwrites the CSV."""
    conn = sqlite3.connect("hospitals.db")
    # Read the updated SQLite table and write it to the CSV just like converter.py
    pd.read_sql("SELECT * FROM hospitals", conn).to_csv("hospitals.csv", index=False)
    conn.close()


def simulate_blood_flow():
    """Simulates real-world usage and donations for all hospitals."""
    conn = sqlite3.connect('hospitals.db')
    cursor = conn.cursor()

    # Fetch current inventory for all hospitals
    cursor.execute(f"SELECT id, name, {', '.join(BLOOD_GROUPS)} FROM hospitals")
    hospitals = cursor.fetchall()

    for hospital in hospitals:
        hosp_id = hospital[0]
        hosp_name = hospital[1]

        # Convert the fetched blood group tuple into a mutable dictionary
        inventory = {BLOOD_GROUPS[i]: hospital[i + 2] for i in range(len(BLOOD_GROUPS))}

        for bg in BLOOD_GROUPS:
            # 40% chance that ANY activity happens for a specific blood group in this 60s window
            if random.random() < 0.40:

                # 80% chance blood is USED (Down value weighted more)
                if random.random() < 0.80:
                    # Usually 1 to 3 units are used at a time
                    used_amount = random.randint(1, 3)
                    inventory[bg] = max(0, inventory[bg] - used_amount)

                # 20% chance blood is DONATED (Up values are higher)
                else:
                    # Donations come in batches, so 5 to 15 units are added
                    donated_amount = random.randint(5, 15)
                    inventory[bg] += donated_amount

        # Calculate the new Total_Units
        new_total = sum(inventory.values())

        # Update the database for this specific hospital
        cursor.execute(f"""
            UPDATE hospitals 
            SET O_pos = ?, O_neg = ?, A_pos = ?, A_neg = ?, 
                B_pos = ?, B_neg = ?, AB_pos = ?, AB_neg = ?, 
                Total_Units = ?
            WHERE id = ?
        """, (
            inventory['O_pos'], inventory['O_neg'], inventory['A_pos'], inventory['A_neg'],
            inventory['B_pos'], inventory['B_neg'], inventory['AB_pos'], inventory['AB_neg'],
            new_total, hosp_id
        ))

    # Commit all changes to the database
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Starting BloodLink Real-Time Simulation...")
    print("Press Ctrl+C to stop the script.\n")

    try:
        while True:
            # 1. Run the simulation on the database
            simulate_blood_flow()

            # 2. Sync the updated database to hospitals.csv
            update_csv()

            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] Updated inventory for all hospitals. Waiting 60 seconds...")

            # 3. Wait 60 seconds before the next cycle
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nSimulation stopped safely.")