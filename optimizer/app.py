"""
Ramsys Smart Bus — Optimizer Flask App
Handles route export, trip summary sync, attendance reporting, and QR generation.
"""

import sqlite3
import os
import io
import base64
from datetime import datetime, date

import qrcode
from flask import Flask, jsonify, request, render_template, send_from_directory, abort

from phone_utils import to_international

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ramsys_routing.db')


def get_db():
    """Get a database connection with row factory and WAL mode for concurrency."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_current_session():
    """Determine current session based on time of day."""
    current_hour = datetime.now().hour
    return 'afternoon' if current_hour >= 12 else 'morning'


# ---------------------------------------------------------------------------
# Endpoint 1: Export Route as Playlist JSON
# ---------------------------------------------------------------------------
@app.route('/api/export-route/<int:bus_id>/<string:date_str>')
def export_route(bus_id, date_str):
    """
    GET /api/export-route/<bus_id>/<date>
    Returns the playlist JSON consumed by the driver PWA.
    Filters by the current session (morning/afternoon).
    """
    conn = get_db()

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        conn.close()
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Check bus exists
    bus = conn.execute(
        'SELECT * FROM buses WHERE id = ? AND is_active = 1', (bus_id,)
    ).fetchone()
    if not bus:
        conn.close()
        return jsonify({"error": f"Bus {bus_id} not found or inactive."}), 404

    # Determine session based on current time
    session = get_current_session()

    # Check route exists for this bus/session
    stops = conn.execute('''
        SELECT rs.*, f.family_name, f.latitude, f.longitude,
               f.phone_number, f.student_count, f.cycle_profile
        FROM route_stops rs
        JOIN families f ON rs.family_id = f.id
        WHERE rs.bus_id = ? AND rs.session = ?
        ORDER BY rs.stop_sequence
    ''', (bus_id, session)).fetchall()

    if not stops:
        conn.close()
        return jsonify({"error": f"No route found for bus {bus_id} ({session} session)."}), 404

    # Build playlist JSON
    playlist_stops = []
    total_students = 0

    for stop in stops:
        family_id = stop['family_id']

        # Get students for this family
        students = conn.execute(
            'SELECT id, first_name, last_name, cycle FROM students WHERE family_id = ?',
            (family_id,)
        ).fetchall()

        student_list = [
            {
                "student_id": s['id'],
                "first_name": s['first_name'],
                "cycle": s['cycle'] or 'Unknown'
            }
            for s in students
        ]

        total_students += len(student_list)

        # Determine afternoon status based on morning events (only for afternoon session)
        afternoon_status = 'active'
        if session == 'afternoon':
            morning_event = conn.execute('''
                SELECT event_type FROM trip_events
                WHERE family_id = ? AND DATE(actual_time) = ? AND session = 'morning'
                ORDER BY actual_time DESC LIMIT 1
            ''', (family_id, date_str)).fetchone()

            if morning_event and morning_event['event_type'] == 'absent':
                afternoon_status = 'skip'

        # Format phone number
        raw_phone = stop['phone_number'] or ''
        formatted_phone = to_international(raw_phone)

        playlist_stops.append({
            "stop_sequence": stop['stop_sequence'],
            "family_id": family_id,
            "family_name": stop['family_name'],
            "estimated_pickup_time": stop['estimated_pickup_time'],
            "lat": stop['latitude'],
            "lng": stop['longitude'],
            "parent_phone": formatted_phone,
            "students": student_list,
            "total_students": len(student_list),
            "morning_status": "pending",
            "afternoon_status": afternoon_status
        })

    # Departure/deadline times from config (match transportation app)
    departure_time = "07:15" if session == 'morning' else "16:00"
    school_deadline = "08:30" if session == 'morning' else "17:30"

    playlist = {
        "route_id": f"bus_{bus_id}_{date_str}_{session}",
        "bus_id": bus_id,
        "driver_name": bus['driver_name'],
        "bus_capacity": bus['capacity'],
        "date": date_str,
        "session": session,
        "departure_time": departure_time,
        "school_deadline": school_deadline,
        "school": {
            "name": "Ramsys School",
            "lat": 36.24502366420027,
            "lng": 6.579864240305483
        },
        "stops": playlist_stops,
        "total_stops": len(playlist_stops),
        "total_students": total_students
    }

    conn.close()
    return jsonify(playlist)


# ---------------------------------------------------------------------------
# Endpoint 2: Receive Trip Summary (WiFi Sync)
# ---------------------------------------------------------------------------
@app.route('/api/trip-summary/<int:bus_id>', methods=['POST'])
def trip_summary(bus_id):
    """
    POST /api/trip-summary/<bus_id>
    Receives event array from driver PWA and saves to trip_events.
    Must be idempotent — skip duplicates.
    """
    conn = get_db()

    # Validate bus exists
    bus = conn.execute('SELECT id FROM buses WHERE id = ?', (bus_id,)).fetchone()
    if not bus:
        conn.close()
        return jsonify({"error": f"Bus {bus_id} not found."}), 404

    events = request.get_json()
    if not events or not isinstance(events, list):
        conn.close()
        return jsonify({"error": "Request body must be a JSON array of events."}), 400

    saved_count = 0

    for event in events:
        family_id = event.get('family_id', 0)
        event_type = event.get('event_type', '')
        timestamp = event.get('timestamp_local', datetime.now().isoformat())

        # Check for duplicate (same bus, family, event_type within same minute)
        # Use timestamp truncated to minute for idempotency
        ts_minute = timestamp[:16] if len(timestamp) >= 16 else timestamp

        existing = conn.execute('''
            SELECT id FROM trip_events
            WHERE bus_id = ? AND family_id = ? AND event_type = ?
            AND SUBSTR(actual_time, 1, 16) = ?
        ''', (bus_id, family_id, event_type, ts_minute)).fetchone()

        if existing:
            continue  # skip duplicate

        stop_sequence = event.get('stop_sequence', 0)

        # Build boarded/absent names from student arrays if provided
        boarded_names = event.get('boarded_names', '')
        absent_names = event.get('absent_names', '')
        boarded_count = len(event.get('boarded_students', []))
        absent_count = len(event.get('absent_students', []))

        # If counts not provided, try to derive from names
        if boarded_count == 0 and boarded_names:
            boarded_count = len([n for n in boarded_names.split(',') if n.strip()])
        if absent_count == 0 and absent_names:
            absent_count = len([n for n in absent_names.split(',') if n.strip()])

        conn.execute('''
            INSERT INTO trip_events
            (bus_id, family_id, stop_sequence, event_type,
             boarded_count, absent_count, boarded_names, absent_names,
             actual_time, session, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bus_id,
            family_id,
            stop_sequence,
            event_type,
            boarded_count,
            absent_count,
            boarded_names,
            absent_names,
            timestamp,
            event.get('session', 'morning'),
            event.get('notes', '')
        ))
        saved_count += 1

    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "saved": saved_count})


# ---------------------------------------------------------------------------
# Endpoint 3: Today's Attendance (Admin Dashboard)
# ---------------------------------------------------------------------------
@app.route('/api/attendance-today')
def attendance_today():
    """
    GET /api/attendance-today
    Returns aggregated attendance across all buses for today.
    Uses Algeria timezone (UTC+1) for date filtering.
    """
    from datetime import timedelta, timezone

    conn = get_db()

    # Get today in Algeria (UTC+1)
    algeria_tz = timezone(timedelta(hours=1))
    now_algeria = datetime.now(algeria_tz)
    today_algeria = now_algeria.date().isoformat()
    yesterday_algeria = (now_algeria - timedelta(days=1)).date().isoformat()

    # Search both today and yesterday (in case event timestamps are slightly off)
    events = conn.execute('''
        SELECT te.*, b.driver_name, f.family_name
        FROM trip_events te
        LEFT JOIN buses b ON te.bus_id = b.id
        LEFT JOIN families f ON te.family_id = f.id AND te.family_id > 0
        WHERE DATE(te.actual_time) = ? OR DATE(te.actual_time) = ?
        ORDER BY te.actual_time
    ''', (today_algeria, yesterday_algeria)).fetchall()

    if not events:
        conn.close()
        return jsonify({
            "status": "waiting",
            "message": "En attente des données des chauffeurs."
        })

    # Aggregate stats
    total_boarded = 0
    total_absent = 0
    buses_reporting = set()

    for event in events:
        total_boarded += event['boarded_count'] or 0
        total_absent += event['absent_count'] or 0
        buses_reporting.add(event['bus_id'])

    result = {
        "status": "ok",
        "date": today_algeria,
        "total_boarded": total_boarded,
        "total_absent": total_absent,
        "buses_reporting": len(buses_reporting),
        "events": []
    }

    for event in events:
        if event['family_id'] == 0:
            # Metadata event (route_started, arrived_school)
            result['events'].append({
                "bus_id": event['bus_id'],
                "driver_name": event['driver_name'],
                "event_type": event['event_type'],
                "time": event['actual_time'],
                "session": event['session']
            })
        else:
            result['events'].append({
                "bus_id": event['bus_id'],
                "driver_name": event['driver_name'],
                "family_name": event['family_name'],
                "event_type": event['event_type'],
                "boarded_names": event['boarded_names'],
                "absent_names": event['absent_names'],
                "boarded_count": event['boarded_count'],
                "absent_count": event['absent_count'],
                "time": event['actual_time'],
                "session": event['session']
            })

    conn.close()
    return jsonify(result)


# ---------------------------------------------------------------------------
# Endpoint 4: QR Code Generator
# ---------------------------------------------------------------------------
@app.route('/api/driver-qr/<int:bus_id>')
def driver_qr(bus_id):
    """
    GET /api/driver-qr/<bus_id>
    Returns an HTML page with a QR code encoding the export route URL.
    """
    conn = get_db()
    bus = conn.execute('SELECT * FROM buses WHERE id = ?', (bus_id,)).fetchone()
    conn.close()

    if not bus:
        return jsonify({"error": f"Bus {bus_id} not found."}), 404

    today = date.today().isoformat()

    # Build the export URL — prefer X-Forwarded-Host or the actual host
    # This helps when accessed from a phone on the same LAN
    host = request.headers.get('X-Forwarded-Host', request.host)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    server_url = f"{scheme}://{host}".rstrip('/')
    export_url = f"{server_url}/api/export-route/{bus_id}/{today}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(export_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>QR — Bus {bus_id} — {bus["driver_name"]}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 40px;
                background: #f5f5f5;
            }}
            .card {{
                background: white;
                border-radius: 12px;
                padding: 30px;
                display: inline-block;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 90%;
            }}
            h1 {{ color: #1a1a2e; margin-bottom: 5px; }}
            h2 {{ color: #555; font-weight: normal; margin-top: 0; }}
            img {{ margin: 20px 0; max-width: 280px; height: auto; }}
            p {{ color: #888; font-size: 14px; }}
            .url {{ font-size: 11px; color: #aaa; word-break: break-all; }}
            .warning {{ color: #e74c3c; font-size: 12px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚌 Ramsys School</h1>
            <h2>Bus {bus_id} — {bus["driver_name"]}</h2>
            <img src="data:image/png;base64,{qr_base64}" alt="QR Code">
            <p>Scannez ce code pour charger la route du {today}</p>
            <p class="url">{export_url}</p>
            <p class="warning">⚠️ Le téléphone du chauffeur doit être sur le même réseau WiFi que ce serveur.</p>
        </div>
    </body>
    </html>
    '''


# ---------------------------------------------------------------------------
# Admin: View all buses
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Simple admin dashboard showing buses."""
    conn = get_db()
    buses = conn.execute('SELECT * FROM buses WHERE is_active = 1').fetchall()
    conn.close()
    return render_template('index.html', buses=buses)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "ramsys-smart-bus"})


# ---------------------------------------------------------------------------
# Serve Driver PWA
# ---------------------------------------------------------------------------
DRIVER_PWA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'driver-pwa')


@app.route('/driver-pwa/<path:filename>')
def driver_pwa_static(filename):
    return send_from_directory(DRIVER_PWA_DIR, filename)


@app.route('/driver-pwa/')
def driver_pwa_index():
    return send_from_directory(DRIVER_PWA_DIR, 'index.html')


if __name__ == '__main__':
    # Initialize DB if it doesn't exist
    from init_db import init_db
    if not os.path.exists(DB_PATH):
        init_db()

    app.run(host='0.0.0.0', port=5000, debug=True)
