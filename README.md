# Ramsys Smart Bus — School Bus Driver PWA

A Progressive Web App for bus drivers at Ramsys School (Constantine, Algeria) to manage morning and afternoon student pickup routes.

## Project Structure

```
ramsys-smart-bus/
├── optimizer/              # Flask backend
│   ├── app.py              # Main Flask app (4 endpoints)
│   ├── init_db.py          # Database schema initialization
│   ├── seed_data.py        # Sample data for testing
│   ├── phone_utils.py      # Algerian phone number formatter
│   ├── requirements.txt    # Python dependencies
│   ├── ramsys_routing.db   # SQLite database
│   └── templates/
│       └── index.html      # Admin dashboard
├── driver-pwa/             # Driver mobile app
│   ├── index.html          # Single-file PWA (HTML + CSS + JS)
│   ├── sw.js               # Service Worker (offline caching)
│   └── manifest.json       # PWA manifest
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
cd optimizer
pip install -r requirements.txt
```

### 2. Initialize Database & Seed Data

```bash
python3 seed_data.py
```

This creates the database with 3 buses, 14 families, 24 students, and sample routes.

### 3. Start the Server

```bash
python3 app.py
```

Server runs on `http://0.0.0.0:5000`.

### 4. Access the App

| URL | Description |
|-----|-------------|
| `http://localhost:5000/` | Admin dashboard |
| `http://localhost:5000/driver-pwa/` | Driver PWA |
| `http://localhost:5000/api/health` | Health check |
| `http://localhost:5000/api/export-route/1/2026-03-20` | Route JSON |
| `http://localhost:5000/api/attendance-today` | Today's attendance |
| `http://localhost:5000/api/driver-qr/1` | QR code for Bus 1 |

## API Endpoints

### GET /api/export-route/:bus_id/:date
Returns the playlist JSON for a specific bus and date. The driver PWA fetches this once at route start.

### POST /api/trip-summary/:bus_id
Receives an array of trip events from the driver PWA (WiFi sync). Idempotent — skips duplicates.

### GET /api/attendance-today
Returns aggregated attendance data for all buses today.

### GET /api/driver-qr/:bus_id
Returns an HTML page with a QR code encoding the export route URL. Admin can screenshot and share via WhatsApp.

## Driver PWA Features

- **Offline-first**: Playlist cached in IndexedDB, works without internet
- **GPS tracking**: Automatic approach SMS at 600m, timer starts at 50m
- **SMS notifications**: French SMS to parents via SMS Gateway app on driver's phone
- **Student toggles**: Tap to mark students present/absent per stop
- **3-minute timer**: Visual countdown at each stop (does NOT auto-mark absent)
- **Charger enforcement**: Blocks app if not charging at startup; warns mid-route
- **Partial pickup**: Supports some siblings boarding, some absent
- **Background sync**: Events sync to server every 30 seconds when WiFi available
- **Attendance report**: End-of-route summary, printable
- **Connectivity indicator**: 🟢 synced, 🔴 offline

## SMS Gateway Setup

Install "SMS Gateway" by HTTP SMS (free on Play Store) on the driver's Android phone.

1. Install the app
2. Enable the HTTP server (default port 8080)
3. The driver PWA sends SMS via `http://localhost:8080/send`
4. Uses the phone's existing SIM contract — no extra cost

## Configuration

Key constants in `driver-pwa/index.html`:

```javascript
const SMS_GATEWAY_URL = 'http://localhost:8080/send';
const APPROACH_DISTANCE_METERS = 600;
const ARRIVAL_DISTANCE_METERS = 50;
const DRIVER_STOP_WAIT_SECONDS = 180;  // 3 minutes
const SYNC_INTERVAL = 30000;           // 30 seconds
```

## Phone Number Format

All phone numbers are converted to E.164 format (`+213XXXXXXXXX`) before:
- Including in the playlist JSON export
- Sending SMS via the gateway

Supported input formats:
- `0555-123-456` → `+213555123456`
- `0770 654 321` → `+213770654321`
- `+213555123456` → `+213555123456` (unchanged)

## Implementation Phases

## 🔗 Connection to Ramsys Transportation (Optimizer)

This application is designed to work in tandem with the **[Ramsys Transportation Optimizer](https://github.com/Aramoul23/ramsys-transportation)**.

### Data Flow
1. **Optimization**: Run the improved optimization engine in the `ramsys-transportation` project to generate the most efficient bus routes.
2. **Synchronization**: The optimization results are saved in a database file named `ramsys_routing.db`.
3. **Deployment**: To update the driver PWA with the new routes:
   - Copy the `ramsys_routing.db` file from the optimizer's folder.
   - Paste it into the `optimizer/` directory of **this** project (overwriting the existing one).
4. **Activation**: The Smart Bus API will instantly begin serving the new routes to the drivers via the QR code or the `/driver-pwa/` interface.

---
© 2026 RAMSYS Transportation — Groupement Scolaire Ramsys, Constantine.
