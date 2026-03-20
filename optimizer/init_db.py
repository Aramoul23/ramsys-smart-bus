"""
Ramsys Smart Bus — Database Initializer
Creates the trip_events table and ensures the schema is compatible
with the transportation optimizer's database.

Usage: python init_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ramsys_routing.db')


def init_db():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Enable WAL mode for concurrent access (matches transportation app)
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")

    # --- Tables matching the transportation optimizer schema ---

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS families (
            id             INTEGER PRIMARY KEY,
            family_name    TEXT,
            latitude       REAL,
            longitude      REAL,
            student_count  INTEGER DEFAULT 0,
            phone_number   TEXT,
            cycle_profile  TEXT DEFAULT 'MIXED'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id           INTEGER PRIMARY KEY,
            first_name   TEXT,
            last_name    TEXT,
            family_id    INTEGER REFERENCES families(id),
            original_lat REAL,
            original_lon REAL,
            is_active    BOOLEAN DEFAULT 1,
            address      TEXT,
            cycle        TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buses (
            id          INTEGER PRIMARY KEY,
            driver_name TEXT,
            capacity    INTEGER,
            bus_type    TEXT,
            is_active   BOOLEAN DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS route_stops (
            id                    INTEGER PRIMARY KEY,
            bus_id                INTEGER REFERENCES buses(id),
            family_id             INTEGER REFERENCES families(id),
            stop_sequence         INTEGER,
            estimated_pickup_time TEXT,
            session               TEXT DEFAULT 'morning'
        )
    ''')

    # --- Trip events table (driver app writes via WiFi sync) ---

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trip_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id           INTEGER  NOT NULL,
            family_id        INTEGER,
            stop_sequence    INTEGER  NOT NULL DEFAULT 0,
            event_type       TEXT     NOT NULL,
            boarded_count    INTEGER  DEFAULT 0,
            absent_count     INTEGER  DEFAULT 0,
            boarded_names    TEXT,
            absent_names     TEXT,
            actual_time      TEXT     NOT NULL,
            session          TEXT     DEFAULT 'morning',
            notes            TEXT,
            FOREIGN KEY (bus_id)    REFERENCES buses    (id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_trip_events_bus_date
            ON trip_events (bus_id, actual_time)
    ''')

    # --- Scenario config (if not already present from transportation app) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenario_config (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            description TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == '__main__':
    init_db()
