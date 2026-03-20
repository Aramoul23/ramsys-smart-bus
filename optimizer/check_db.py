import sqlite3
import os

DB_PATH = 'ramsys_routing.db'

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"File {DB_PATH} not found.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(table[0])
        
    print("\n--- Student Count ---")
    try:
        cursor.execute("SELECT COUNT(*) FROM students")
        print(f"Students: {cursor.fetchone()[0]}")
    except:
        print("Table 'students' not found or error.")
        
    print("\n--- Family Count ---")
    try:
        cursor.execute("SELECT COUNT(*) FROM families")
        print(f"Families: {cursor.fetchone()[0]}")
    except:
        print("Table 'families' not found or error.")
        
    conn.close()

if __name__ == "__main__":
    check_db()
