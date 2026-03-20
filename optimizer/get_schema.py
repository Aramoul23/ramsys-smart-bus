import sqlite3
import os

db_path = 'c:/Users/Ali_r/Downloads/Ramsys school apps/ramsys-smart-bus/optimizer/ramsys_routing_old.db'

def get_schema():
    if not os.path.exists(db_path):
        print(f"File {db_path} not found.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='trip_events';")
    row = cursor.fetchone()
    if row:
        print(row[0])
    else:
        print("Table 'trip_events' not found.")
    conn.close()

if __name__ == "__main__":
    get_schema()
