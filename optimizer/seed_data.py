"""
Seed the database with sample data for testing.
Run: python seed_data.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ramsys_routing.db')


def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute('DELETE FROM trip_events')
    cursor.execute('DELETE FROM route_stops')
    cursor.execute('DELETE FROM students')
    cursor.execute('DELETE FROM families')
    cursor.execute('DELETE FROM buses')

    # --- Buses ---
    buses = [
        (1, 'Omar', 30, 'standard', 1),
        (2, 'Karim', 12, 'mini', 1),
        (3, 'Ahmed', 30, 'standard', 1),
    ]
    cursor.executemany(
        'INSERT INTO buses (id, driver_name, capacity, bus_type, is_active) VALUES (?, ?, ?, ?, ?)',
        buses
    )

    # --- Families (Constantine area coordinates) ---
    families = [
        (1,  'BENALI',      36.2641, 6.6315, 3, '0555123456', 'MIXED'),
        (2,  'BOUZID',      36.2580, 6.6250, 1, '0661234567', 'MH'),
        (3,  'MANSOURI',    36.2710, 6.6180, 2, '0770654321', 'KP'),
        (4,  'HADDAD',      36.2530, 6.6400, 1, '0555987654', 'MH'),
        (5,  'TALEB',       36.2690, 6.6100, 2, '0661345678', 'MIXED'),
        (6,  'FERHANI',     36.2600, 6.6350, 1, '0770123456', 'KP'),
        (7,  'DJABALLAH',   36.2750, 6.6220, 2, '0555765432', 'MH'),
        (8,  'MEBARKI',     36.2510, 6.6450, 3, '0661987654', 'MIXED'),
        (9,  'HAMIDI',      36.2660, 6.6280, 1, '0770234567', 'KP'),
        (10, 'SELLAMI',     36.2720, 6.6150, 2, '0555345678', 'MH'),
        (11, 'OULD AHMED',  36.2570, 6.6380, 1, '0661654321', 'KP'),
        (12, 'KHELIFI',     36.2630, 6.6320, 2, '0770876543', 'MIXED'),
        (13, 'BOUHALI',     36.2680, 6.6190, 1, '0555456789', 'MH'),
        (14, 'SAIDI',       36.2540, 6.6420, 2, '0661765432', 'KP'),
    ]
    cursor.executemany(
        'INSERT INTO families (id, family_name, latitude, longitude, student_count, phone_number, cycle_profile) VALUES (?, ?, ?, ?, ?, ?, ?)',
        families
    )

    # --- Students ---
    students = [
        # Family 1: BENALI (3 students)
        (1,  'Ali',     'BENALI', 1, 'Primary'),
        (2,  'Fatima',  'BENALI', 1, 'Primary'),
        (3,  'Sara',    'BENALI', 1, 'Kindergarten'),
        # Family 2: BOUZID
        (4,  'Hamza',   'BOUZID', 2, 'Middle'),
        # Family 3: MANSOURI (2 students)
        (5,  'Youssef', 'MANSOURI', 3, 'High School'),
        (6,  'Amina',   'MANSOURI', 3, 'Primary'),
        # Family 4: HADDAD
        (7,  'Rania',   'HADDAD', 4, 'Middle'),
        # Family 5: TALEB (2 students)
        (8,  'Amir',    'TALEB', 5, 'Primary'),
        (9,  'Nadia',   'TALEB', 5, 'Kindergarten'),
        # Family 6: FERHANI
        (10, 'Zakaria', 'FERHANI', 6, 'Middle'),
        # Family 7: DJABALLAH (2 students)
        (11, 'Lina',    'DJABALLAH', 7, 'High School'),
        (12, 'Karim',   'DJABALLAH', 7, 'Primary'),
        # Family 8: MEBARKI (3 students)
        (13, 'Nour',    'MEBARKI', 8, 'Kindergarten'),
        (14, 'Ibrahim', 'MEBARKI', 8, 'Primary'),
        (15, 'Hana',    'MEBARKI', 8, 'Middle'),
        # Family 9: HAMIDI
        (16, 'Omar',    'HAMIDI', 9, 'High School'),
        # Family 10: SELLAMI (2 students)
        (17, 'Mariam',  'SELLAMI', 10, 'Primary'),
        (18, 'Yassine', 'SELLAMI', 10, 'Middle'),
        # Family 11: OULD AHMED
        (19, 'Reda',    'OULD AHMED', 11, 'Primary'),
        # Family 12: KHELIFI (2 students)
        (20, 'Sofia',   'KHELIFI', 12, 'Kindergarten'),
        (21, 'Mehdi',   'KHELIFI', 12, 'Primary'),
        # Family 13: BOUHALI
        (22, 'Dina',    'BOUHALI', 13, 'High School'),
        # Family 14: SAIDI (2 students)
        (23, 'Ayoub',   'SAIDI', 14, 'Middle'),
        (24, 'Layla',   'SAIDI', 14, 'Primary'),
    ]
    cursor.executemany(
        'INSERT INTO students (id, first_name, last_name, family_id, cycle) VALUES (?, ?, ?, ?, ?)',
        students
    )

    # --- Route Stops (Bus 1: morning route) ---
    route_stops_bus1 = [
        (1,  1, 1,  1,  '07:18 AM'),
        (2,  1, 5,  2,  '07:23 AM'),
        (3,  1, 10, 3,  '07:28 AM'),
        (4,  1, 8,  4,  '07:33 AM'),
        (5,  1, 14, 5,  '07:38 AM'),
        (6,  1, 4,  6,  '07:43 AM'),
        (7,  1, 2,  7,  '07:48 AM'),
        (8,  1, 9,  8,  '07:53 AM'),
        (9,  1, 3,  9,  '07:58 AM'),
        (10, 1, 6,  10, '08:03 AM'),
    ]
    cursor.executemany(
        'INSERT INTO route_stops (id, bus_id, family_id, stop_sequence, estimated_pickup_time) VALUES (?, ?, ?, ?, ?)',
        route_stops_bus1
    )

    # --- Route Stops (Bus 2: mini bus, shorter route) ---
    route_stops_bus2 = [
        (11, 2, 7,  1, '07:20 AM'),
        (12, 2, 11, 2, '07:26 AM'),
        (13, 2, 12, 3, '07:32 AM'),
        (14, 2, 13, 4, '07:38 AM'),
    ]
    cursor.executemany(
        'INSERT INTO route_stops (id, bus_id, family_id, stop_sequence, estimated_pickup_time) VALUES (?, ?, ?, ?, ?)',
        route_stops_bus2
    )

    conn.commit()
    conn.close()
    print("Database seeded successfully!")
    print(f"  - 3 buses")
    print(f"  - 14 families")
    print(f"  - 24 students")
    print(f"  - 10 stops (Bus 1)")
    print(f"  - 4 stops (Bus 2)")


if __name__ == '__main__':
    # Initialize DB first
    from init_db import init_db
    init_db()
    seed()
