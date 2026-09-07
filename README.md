# School-In-A-Box (SIAB) WhatsApp Automated Follow-Up System

> **Automating Impact**: Zero-touch telemetry monitoring, intelligent 3-bucket classification, and 2-way conversational WhatsApp follow-up engine for **240,000+ students across 575+ (scaling to 5,000+) School-In-A-Box deployments**.

---

## 🌟 Key Features

1. **3-Step Automation Engine**:
   - **Step 1: Monitor Data**: Taps into remote monitoring telemetry for weekly usage hours, subject engagement, and last "Synced Upto" dates.
   - **Step 2: Logic Script**: Evaluates weekly rules and categorizes schools into 3 buckets:
     - 🌟 **Doing Great (≥12 hrs/week)**: Celebratory human-tone messages with curated offline curriculum suggestions (*PhET Simulations*, *Toys From Trash*, *STEM Challenges*).
     - 👋 **Needs a Nudge (<4 hrs/week)**: Gentle, empathetic check-ins offering bite-sized 10–15 min fun activities without adding teacher stress.
     - ⚠️ **Device Offline (>3 days unsynced)**: Proactive support alert diagnosing power switch, adapter, or local grid outages before devices sit idle.
   - **Step 3: Trigger WhatsApp API**: Dispatches personalized, human-tone messages via WhatsApp Cloud API, Twilio, WhatsAuto, or the built-in Interactive Simulator.

2. **2-Way WhatsApp Conversational Bot**:
   - **Curriculum Guidance**: Automatically responds to teacher queries for science experiments, math games, or PhET simulations.
   - **Auto-Ticketing Desk**: Automatically detects power outage or broken hardware reports, generates high-priority support tickets, and notifies district field coordinators.
   - **Human Escalation**: Allows operations staff to inspect live chat threads and reply manually from the dashboard.

3. **Modern Operations Dashboard & Interactive Smartphone Simulator**:
   - Executive fleet analytics: student reach, weekly classroom hours, sync health %, bucket distribution charts.
   - School Fleet Monitor: Search, district filter, live sync badges, and detailed telemetry drawer.
   - WhatsApp Smartphone Simulator: Test teacher interactions, quick simulation chips (*Report Power Cut*, *Ask for PhET*, *Report Fault*), and inspect real-time bot responses and tickets.

---

## 🚀 Quick Start

### 1. Launch the Application
Run the one-line startup script:
```bash
./run.sh
```
Or run directly via Python:
```bash
python3 backend/seed_data.py
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Open the Dashboard & Simulator
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 📁 System Architecture

```
SIAB-Whatsauto/
├── backend/
│   ├── app.py                 # FastAPI REST API, WebSocket & static file server
│   ├── classifier_engine.py   # 3-Step automation classification logic & message generator
│   ├── database.py            # SQLite database schema, tables & connection helpers
│   ├── scheduler.py           # Background Friday automation scheduler
│   ├── seed_data.py           # 575+ realistic schools, telemetry logs & curriculum modules
│   └── whatsapp_service.py    # Multi-provider WhatsApp Gateway (Cloud API/Twilio/WhatsAuto/Simulator) & 2-Way Bot
├── frontend/
│   ├── index.html             # Single-page dashboard & WhatsApp smartphone simulator
│   ├── styles.css             # Modern Glassmorphism styling, responsive layouts & themes
│   └── app.js                 # UI controller, Chart.js integrations & live WebSocket feed
├── tests/
│   └── test_engine.py         # Automated unit tests for classification, intent parsing & ticketing
├── run.sh                     # Launch script
└── README.md                  # System documentation
```

---

## 🔌 WhatsApp Provider Configuration

You can configure your WhatsApp Gateway in the **3-Step Engine** tab or via `/api/automation/config`:

- **Interactive Simulator (Default)**: Test without external credentials. Messages update directly inside the built-in smartphone preview.
- **Meta WhatsApp Cloud API**: Set `meta_api_token` and `meta_phone_number_id`. Webhook endpoint: `POST /api/whatsapp/webhook`.
- **Twilio WhatsApp**: Set `twilio_account_sid`, `twilio_auth_token`, and `twilio_from_number`.
- **WhatsAuto / Custom Gateway**: Set `whatsauto_webhook_url`.

---

## 🧪 Running Automated Tests

Run the test suite:
```bash
python3 tests/test_engine.py
```
