import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(__file__))

import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from database import get_db, init_db
from classifier_engine import run_classification_engine, get_system_config
from whatsapp_service import (
    send_whatsapp_message, 
    handle_incoming_teacher_message, 
    active_websockets, 
    broadcast_ws
)
from scheduler import scheduler_instance
from seed_data import seed_database

# Ensure database is created and seeded
init_db()
conn = get_db()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM schools")
if cursor.fetchone()[0] == 0:
    conn.close()
    seed_database(575)
else:
    conn.close()

# Start background scheduler
scheduler_instance.start()

app = FastAPI(
    title="School-In-A-Box WhatsApp Automated Impact System",
    description="Zero-touch automated WhatsApp monitoring, intelligent 3-bucket classification, and 2-way teacher support bot.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# ==================== WEBSOCKET ====================

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process client ping if needed
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# ==================== DASHBOARD STATS ====================

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), SUM(students_count), SUM(weekly_usage_hours), SUM(smart_class_sessions) FROM schools WHERE status = 'active'")
    row = cursor.fetchone()
    total_schools = row[0] or 0
    total_students = row[1] or 0
    total_weekly_hours = round(row[2] or 0.0, 1)
    total_sessions = row[3] or 0

    # Bucket distribution
    cursor.execute("SELECT current_bucket, COUNT(*) FROM schools WHERE status = 'active' GROUP BY current_bucket")
    bucket_rows = cursor.fetchall()
    buckets = {"doing_great": 0, "needs_nudge": 0, "device_offline": 0}
    for b_row in bucket_rows:
        buckets[b_row[0]] = b_row[1]

    # Sync health (synced in last 3 days)
    now = datetime.now()
    cursor.execute("SELECT last_synced_at FROM schools WHERE status = 'active'")
    all_syncs = cursor.fetchall()
    synced_online_count = 0
    for s in all_syncs:
        try:
            dt_str = s[0].replace("Z", "") if s[0].endswith("Z") else s[0]
            s_dt = datetime.fromisoformat(dt_str)
            if s_dt.tzinfo is not None:
                s_dt = s_dt.replace(tzinfo=None)
            if (now - s_dt).total_seconds() <= 3 * 86400:
                synced_online_count += 1
        except Exception:
            pass

    sync_health_pct = round((synced_online_count / total_schools * 100) if total_schools > 0 else 0, 1)

    # Nudges dispatched stats
    cursor.execute("SELECT COUNT(*), status FROM nudges_log GROUP BY status")
    nudge_stats = {r[1]: r[0] for r in cursor.fetchall()}
    total_nudges = sum(nudge_stats.values())

    # Tickets stats
    cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
    ticket_stats = {r[0]: r[1] for r in cursor.fetchall()}

    # Recent activity stream
    cursor.execute("""
    SELECT n.id, n.school_id, s.name as school_name, s.district, n.bucket, n.message_text, n.status, n.dispatched_at
    FROM nudges_log n
    JOIN schools s ON n.school_id = s.id
    ORDER BY n.id DESC LIMIT 10
    """)
    recent_nudges = [dict(r) for r in cursor.fetchall()]

    # State / District breakdown
    cursor.execute("SELECT state, COUNT(*) as count FROM schools GROUP BY state ORDER BY count DESC LIMIT 8")
    state_breakdown = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_schools": total_schools,
        "total_students": total_students,
        "total_weekly_hours": total_weekly_hours,
        "total_sessions": total_sessions,
        "sync_health_percentage": sync_health_pct,
        "buckets": buckets,
        "nudges_summary": {
            "total_sent": total_nudges,
            "by_status": nudge_stats
        },
        "tickets_summary": ticket_stats,
        "state_breakdown": state_breakdown,
        "recent_nudges": recent_nudges
    }

# ==================== SCHOOLS FLEET ====================

@app.get("/api/schools")
def list_schools(
    search: Optional[str] = None,
    bucket: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "id"
):
    conn = get_db()
    cursor = conn.cursor()

    conditions = ["status = 'active'"]
    params = []

    if search:
        conditions.append("(name LIKE ? OR school_code LIKE ? OR contact_name LIKE ? OR phone_number LIKE ?)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if bucket and bucket != "all":
        conditions.append("current_bucket = ?")
        params.append(bucket)

    if district and district != "all":
        conditions.append("district = ?")
        params.append(district)

    if state and state != "all":
        conditions.append("state = ?")
        params.append(state)

    where_clause = " AND ".join(conditions)

    # Count total matching
    cursor.execute(f"SELECT COUNT(*) FROM schools WHERE {where_clause}", params)
    total_count = cursor.fetchone()[0]

    # Order clause
    valid_sorts = {
        "id": "id ASC",
        "name": "name ASC",
        "usage_desc": "weekly_usage_hours DESC",
        "usage_asc": "weekly_usage_hours ASC",
        "sync_desc": "last_synced_at DESC",
        "sync_asc": "last_synced_at ASC",
        "students": "students_count DESC"
    }
    order_clause = valid_sorts.get(sort_by, "id ASC")

    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    cursor.execute(f"""
    SELECT * FROM schools 
    WHERE {where_clause}
    ORDER BY {order_clause}
    LIMIT ? OFFSET ?
    """, params)

    schools = [dict(r) for r in cursor.fetchall()]

    for s in schools:
        try:
            s["subjects"] = json.loads(s["subjects_json"])
        except Exception:
            s["subjects"] = {}

    conn.close()

    return {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size,
        "schools": schools
    }

@app.get("/api/schools/{school_id}")
def get_school_detail(school_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM schools WHERE id = ?", (school_id,))
    school = cursor.fetchone()
    if not school:
        conn.close()
        raise HTTPException(status_code=404, detail="School not found")

    school_dict = dict(school)
    try:
        school_dict["subjects"] = json.loads(school_dict["subjects_json"])
    except Exception:
        school_dict["subjects"] = {}

    # Fetch recent telemetry logs
    cursor.execute("SELECT * FROM telemetry_logs WHERE school_id = ? ORDER BY id DESC LIMIT 10", (school_id,))
    telemetry = [dict(r) for r in cursor.fetchall()]
    for t in telemetry:
        try:
            t["active_apps"] = json.loads(t["active_apps_json"])
        except Exception:
            t["active_apps"] = []

    # Fetch chat history
    cursor.execute("SELECT * FROM chat_messages WHERE school_id = ? ORDER BY id ASC", (school_id,))
    chat_history = [dict(r) for r in cursor.fetchall()]

    # Fetch tickets
    cursor.execute("SELECT * FROM tickets WHERE school_id = ? ORDER BY id DESC", (school_id,))
    tickets = [dict(r) for r in cursor.fetchall()]

    # Fetch nudges sent
    cursor.execute("SELECT * FROM nudges_log WHERE school_id = ? ORDER BY id DESC LIMIT 10", (school_id,))
    nudges = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "school": school_dict,
        "telemetry_logs": telemetry,
        "chat_history": chat_history,
        "tickets": tickets,
        "nudges_history": nudges
    }

@app.get("/api/districts")
def list_districts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT district, state FROM schools ORDER BY state, district")
    rows = cursor.fetchall()
    conn.close()
    return [{"district": r["district"], "state": r["state"]} for r in rows]

# ==================== AUTOMATION ENGINE ====================

@app.get("/api/automation/preview")
def preview_automation_run():
    """Generates dry-run classification for all schools with generated message copy."""
    results = run_classification_engine(dry_run=True)
    return results

@app.post("/api/automation/run")
async def execute_automation_run(body: dict = Body(default={})):
    """Executes live classification run, updates DB, generates nudges and dispatches."""
    school_ids = body.get("school_ids")
    results = run_classification_engine(dry_run=False, school_ids=school_ids)
    
    # Broadcast to live websockets
    await broadcast_ws({
        "event": "automation_completed",
        "data": {
            "timestamp": results["timestamp"],
            "total_evaluated": results["total_evaluated"],
            "bucket_counts": results["bucket_counts"]
        }
    })

    return results

@app.get("/api/automation/config")
def get_automation_config():
    return get_system_config()

@app.post("/api/automation/config")
def update_automation_config(payload: dict = Body(...)):
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()

    for key, val in payload.items():
        cursor.execute("""
        INSERT OR REPLACE INTO system_config (key, value, updated_at)
        VALUES (?, ?, ?)
        """, (str(key), str(val), now_iso))

    conn.commit()
    conn.close()

    return {"success": True, "updated_config": get_system_config()}

# ==================== 2-WAY WHATSAPP & SIMULATOR ====================

@app.get("/api/chat/{school_id}")
def get_chat_history(school_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_messages WHERE school_id = ? ORDER BY id ASC", (school_id,))
    messages = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"school_id": school_id, "messages": messages}

@app.post("/api/whatsapp/send")
async def send_message(payload: dict = Body(...)):
    """Outbound message sent by operator or system to school."""
    school_id = payload.get("school_id")
    message_text = payload.get("message")
    
    if not school_id or not message_text:
        raise HTTPException(status_code=400, detail="school_id and message are required")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number FROM schools WHERE id = ?", (school_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="School not found")

    phone = row["phone_number"]
    res = send_whatsapp_message(school_id, phone, message_text, template_name="operator_custom")

    await broadcast_ws({
        "event": "new_chat_message",
        "data": {
            "school_id": school_id,
            "sender": "system",
            "message_text": message_text,
            "created_at": datetime.now().isoformat()
        }
    })

    return res

@app.post("/api/whatsapp/simulate-incoming")
async def simulate_incoming_teacher_message(payload: dict = Body(...)):
    """Simulates an incoming WhatsApp message sent by a teacher (interactive simulator)."""
    school_id = payload.get("school_id")
    text = payload.get("message")

    if not school_id or not text:
        raise HTTPException(status_code=400, detail="school_id and message are required")

    result = handle_incoming_teacher_message(school_id, text)

    # Broadcast to websockets for real-time live update
    await broadcast_ws({
        "event": "teacher_interaction",
        "data": result
    })

    return result

@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Universal Webhook receiver for Meta WhatsApp Cloud API / Twilio / WhatsAuto."""
    try:
        body = await request.json()
        print(f"[Webhook Received]: {body}")
        
        # Parse Meta WhatsApp Cloud API payload format
        if "entry" in body:
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for msg in messages:
                        from_number = msg.get("from") # e.g. "919820000001"
                        text = msg.get("text", {}).get("body", "")
                        
                        # Find school by phone number
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM schools WHERE phone_number LIKE ?", (f"%{from_number[-10:]}%",))
                        s_row = cursor.fetchone()
                        conn.close()

                        if s_row:
                            school_id = s_row["id"]
                            res = handle_incoming_teacher_message(school_id, text)
                            await broadcast_ws({"event": "teacher_interaction", "data": res})

        # Parse WhatsAuto / Generic payload format
        elif "message" in body and ("phone" in body or "recipient" in body or "sender" in body):
            phone = body.get("phone") or body.get("sender") or body.get("recipient")
            text = body.get("message", "")
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM schools WHERE phone_number LIKE ?", (f"%{phone[-10:]}%",))
            s_row = cursor.fetchone()
            conn.close()

            if s_row:
                school_id = s_row["id"]
                res = handle_incoming_teacher_message(school_id, text)
                await broadcast_ws({"event": "teacher_interaction", "data": res})

        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/whatsapp/webhook")
def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """Meta Webhook Challenge Verification."""
    if hub_mode == "subscribe" and hub_verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    return "Verification failed"

# ==================== TICKETS DESK ====================

@app.get("/api/tickets")
def list_tickets(status: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT t.*, s.name as school_name, s.district, s.state, s.contact_name, s.phone_number, s.device_id
    FROM tickets t
    JOIN schools s ON t.school_id = s.id
    """
    params = []
    if status and status != "all":
        query += " WHERE t.status = ?"
        params.append(status)

    query += " ORDER BY t.id DESC"

    cursor.execute(query, params)
    tickets = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"tickets": tickets}

@app.post("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, payload: dict = Body(...)):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")

    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    resolved_at = now_iso if new_status in ["resolved", "closed"] else None

    cursor.execute("""
    UPDATE tickets
    SET status = ?, updated_at = ?, resolved_at = ?
    WHERE id = ?
    """, (new_status, now_iso, resolved_at, ticket_id))

    conn.commit()
    conn.close()

    await broadcast_ws({
        "event": "ticket_updated",
        "data": {"ticket_id": ticket_id, "status": new_status, "updated_at": now_iso}
    })

    return {"success": True, "ticket_id": ticket_id, "status": new_status}

# ==================== CURRICULUM ====================

@app.get("/api/curriculum")
def list_curriculum():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM curriculum_modules ORDER BY subject, grade_range")
    modules = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"modules": modules}

# ==================== TELEMETRY INGESTION ====================

@app.post("/api/telemetry/ingest")
async def ingest_telemetry(payload: dict = Body(...)):
    """Allows SIAB box or IoT edge sync daemon to push usage and health telemetry."""
    device_id = payload.get("device_id")
    usage_hours = float(payload.get("usage_hours", 0.0))
    active_apps = payload.get("active_apps", [])
    system_health = payload.get("system_health", "ok")

    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, weekly_usage_hours FROM schools WHERE device_id = ?", (device_id,))
    s_row = cursor.fetchone()

    if not s_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Device ID not registered")

    school_id = s_row["id"]
    current_weekly = float(s_row["weekly_usage_hours"])
    new_weekly = round(current_weekly + usage_hours, 1)
    now_iso = datetime.now().isoformat()

    # Insert telemetry log
    cursor.execute("""
    INSERT INTO telemetry_logs (school_id, synced_at, usage_hours, active_apps_json, system_health, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (school_id, now_iso, usage_hours, json.dumps(active_apps), system_health, now_iso))

    # Update school last sync and usage
    cursor.execute("""
    UPDATE schools
    SET last_synced_at = ?, weekly_usage_hours = ?
    WHERE id = ?
    """, (now_iso, new_weekly, school_id))

    conn.commit()
    conn.close()

    await broadcast_ws({
        "event": "telemetry_synced",
        "data": {
            "device_id": device_id,
            "school_id": school_id,
            "synced_at": now_iso,
            "weekly_usage_hours": new_weekly
        }
    })

    return {"success": True, "school_id": school_id, "synced_at": now_iso, "new_weekly_hours": new_weekly}

# ==================== STATIC FRONTEND ====================

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{full_path:path}")
def serve_frontend_assets(full_path: str):
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
