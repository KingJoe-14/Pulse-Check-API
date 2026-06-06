# Pulse-Check-API — Dead Man's Switch Monitor

A production-grade backend service that monitors remote devices (solar farms, weather stations, etc.) and triggers escalating alerts when a device stops sending heartbeats.

Built with **Python + Django + Redis**.

---

## Architecture Diagram
[Device] ──POST /monitors──────────────► [Django API]
│
Save to Redis
Start TTL key
│
[Device] ──POST /heartbeat─────────────► [Django API]
│
Reset TTL key
│
Timer expires?
│
[Redis keyspace event]
│
[Listener command]
│
┌──────────▼──────────┐
│   Alert 1 WARNING   │ immediately
│   Alert 2 URGENT    │ +30s
│   Alert 3 CRITICAL  │ +90s
└─────────────────────┘

---

## How It Works

1. A device registers a monitor with a timeout (e.g. 60 seconds)
2. Redis starts a countdown (TTL key)
3. The device sends heartbeats to reset the timer
4. If no heartbeat arrives before the timer hits zero, Redis fires an expiry event
5. A background listener catches the event and fires escalating alerts
6. A maintenance technician can pause monitoring to avoid false alarms

---

## Setup Instructions

### Requirements
- Python 3.10+
- Redis server
- pip

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/pulse-check-api.git
cd pulse-check-api
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create your `.env` file**
```bash
cp .env.example .env
```

**5. Start Redis**
```bash
sudo service redis-server start
```

**6. Enable Redis keyspace notifications**
```bash
redis-cli config set notify-keyspace-events Ex
```

**7. Run database-free check**
```bash
python manage.py check
```

### Running the Service

You need **two terminals** running simultaneously:

**Terminal 1 — API server**
```bash
python manage.py runserver
```

**Terminal 2 — Keyspace listener**
```bash
python manage.py start_listener
```

---

## API Documentation

### Base URL
http://127.0.0.1:8000

---

### 1. Register a Monitor
**POST** `/monitors/`

Registers a new device monitor and starts the countdown timer.

**Request body:**
```json
{
    "id": "device-123",
    "timeout": 60,
    "alert_email": "admin@critmon.com"
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| 201 | Monitor created successfully |
| 400 | Missing or invalid fields |
| 409 | Monitor with this ID already exists |

**Example response (201):**
```json
{
    "message": "Monitor for device-123 created successfully",
    "monitor": {
        "id": "device-123",
        "timeout": 60,
        "alert_email": "admin@critmon.com",
        "status": "active",
        "created_at": "2026-06-06T19:37:30.260117+00:00"
    }
}
```

---

### 2. Send Heartbeat
**POST** `/monitors/{id}/heartbeat/`

Resets the countdown timer. Automatically unpauses a paused monitor.

**No request body needed.**

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Timer reset successfully |
| 404 | Monitor not found |
| 400 | Monitor is down — re-register to resume |

**Example response (200):**
```json
{
    "id": "device-123",
    "status": "active",
    "message": "Heartbeat received — timer reset",
    "updated_at": "2026-06-06T19:45:00.000000+00:00"
}
```

---

### 3. Pause a Monitor
**POST** `/monitors/{id}/pause/`

Freezes the timer completely. No alerts will fire while paused.
Sending a heartbeat automatically resumes the monitor.

**No request body needed.**

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Monitor paused successfully |
| 400 | Monitor is already paused or is down |
| 404 | Monitor not found |

**Example response (200):**
```json
{
    "id": "device-123",
    "status": "paused",
    "message": "Monitor paused — no alerts will fire",
    "updated_at": "2026-06-06T19:50:00.000000+00:00"
}
```

---

### 4. List All Monitors
**GET** `/monitors/`

Returns all registered monitors and their current status.

**Example response (200):**
```json
[
    {
        "id": "device-123",
        "timeout": "60",
        "alert_email": "admin@critmon.com",
        "status": "active",
        "created_at": "2026-06-06T19:37:30.260117+00:00",
        "updated_at": "2026-06-06T19:45:00.000000+00:00"
    }
]
```

---

### 5. Get Single Monitor
**GET** `/monitors/{id}/`

Returns a single monitor by ID.

**Responses:**

| Status | Description |
|--------|-------------|
| 200 | Monitor found |
| 404 | Monitor not found |

---

## Alert System

When a device misses its heartbeat the system fires three escalating alerts logged to the listener console:

| Alert | Severity | When |
|-------|----------|------|
| Alert 1 | WARNING  | Immediately when timer expires |
| Alert 2 | URGENT   | 30 seconds after Alert 1 |
| Alert 3 | CRITICAL | 90 seconds after Alert 2 |

**Example alert output:**
```json
{"ALERT": "Device device-123 is down!", "severity": "WARNING", "email": "admin@critmon.com", "time": "2026-06-06T21:13:49.500142+00:00"}
{"ALERT": "Device device-123 is still down!", "severity": "URGENT", "email": "admin@critmon.com", "time": "2026-06-06T21:14:19.578988+00:00"}
{"ALERT": "Device device-123 is still down!", "severity": "CRITICAL", "email": "admin@critmon.com", "time": "2026-06-06T21:15:49.612045+00:00"}
```

Alerts stop escalating as soon as the device sends a heartbeat again.

---

## Developer's Choice — Exponential Backoff Alerts

### What it is
Instead of firing a single alert when a device goes down, the system escalates notifications with increasing urgency over time.

### Why it was added
A single alert is easy to miss. In a critical infrastructure context (solar farms, unmanned weather stations), a missed alert could mean hours of downtime before anyone responds. Escalating alerts ensure that:

- A first responder sees the WARNING immediately
- If unacknowledged, the URGENT alert creates pressure to act
- The CRITICAL alert signals a serious outage requiring immediate deployment

### How it works
Redis backoff keys with expiring TTLs drive the escalation. Each alert schedules the next one by setting a new key with a delay. If the device recovers and sends a heartbeat, the backoff keys are cleared and escalation stops.

---

## Project Structure
pulse-check-api/
├── config/                          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── monitors/                        # Core app
│   ├── views.py                     # API endpoints
│   ├── urls.py                      # URL routing
│   ├── services/
│   │   ├── monitor_service.py       # Register, heartbeat, pause logic
│   │   └── alert_service.py        # Alert firing and backoff
│   └── management/commands/
│       └── start_listener.py        # Redis keyspace event listener
├── redis_client/
│   └── client.py                    # Redis singleton
├── .env.example                     # Environment variable template
├── requirements.txt
└── manage.py

---

## Pre-Submission Checklist

- ✅ Repository is public
- ✅ No `node_modules`, `.env`, or sensitive files committed
- ✅ Server starts with `python manage.py runserver`
- ✅ Architecture diagram included
- ✅ Original instructions replaced with this README
- ✅ All endpoints documented with example requests
- ✅ Multiple meaningful commits
