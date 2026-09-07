import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "siab.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Schools table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        contact_name TEXT NOT NULL,
        contact_role TEXT NOT NULL DEFAULT 'Teacher',
        phone_number TEXT NOT NULL,
        students_count INTEGER NOT NULL DEFAULT 100,
        device_id TEXT UNIQUE NOT NULL,
        device_model TEXT NOT NULL DEFAULT 'SIAB-Pi-4K-v2',
        last_synced_at TEXT NOT NULL,
        weekly_usage_hours REAL NOT NULL DEFAULT 0.0,
        smart_class_sessions INTEGER NOT NULL DEFAULT 0,
        subjects_json TEXT NOT NULL DEFAULT '{}',
        current_bucket TEXT NOT NULL DEFAULT 'needs_nudge',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL
    )
    """)

    # Telemetry logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        synced_at TEXT NOT NULL,
        usage_hours REAL NOT NULL,
        active_apps_json TEXT NOT NULL,
        system_health TEXT NOT NULL DEFAULT 'ok',
        battery_level INTEGER DEFAULT 100,
        power_cycles INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # Nudges / Automation Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nudges_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        phone_number TEXT NOT NULL,
        bucket TEXT NOT NULL,
        template_name TEXT NOT NULL,
        message_text TEXT NOT NULL,
        curriculum_suggestion TEXT,
        status TEXT NOT NULL DEFAULT 'sent', -- queued, sent, delivered, read, failed
        channel TEXT NOT NULL DEFAULT 'whatsapp',
        dispatched_at TEXT NOT NULL,
        delivery_receipt_at TEXT,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # 2-Way Chat Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id INTEGER NOT NULL,
        sender TEXT NOT NULL, -- 'teacher' or 'system' or 'agent'
        message_text TEXT NOT NULL,
        intent TEXT, -- 'curriculum_request', 'power_issue', 'hardware_fault', 'general_query', 'gratitude'
        media_url TEXT,
        created_at TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # Support Escalation Tickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT UNIQUE NOT NULL,
        school_id INTEGER NOT NULL,
        category TEXT NOT NULL, -- 'power_cut', 'hardware_broken', 'sync_failure', 'training_request'
        priority TEXT NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open', -- 'open', 'in_progress', 'resolved', 'closed'
        assigned_to TEXT DEFAULT 'Field Coordinator',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
    )
    """)

    # Curriculum Modules table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS curriculum_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        subject TEXT NOT NULL, -- 'Science', 'Maths', 'Arts', 'English', 'STEM'
        grade_range TEXT NOT NULL, -- 'Grade 1-3', 'Grade 4-6', 'Grade 7-8'
        module_type TEXT NOT NULL, -- 'PhET Simulation', 'Toys From Trash', 'Interactive Story', 'Math Challenge'
        description TEXT NOT NULL,
        key_concept TEXT NOT NULL,
        instructions_summary TEXT NOT NULL,
        sample_prompt TEXT NOT NULL,
        link_url TEXT NOT NULL
    )
    """)

    # System Configuration table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Default configurations
    default_configs = [
        ("threshold_doing_great_hours", "12.0"),
        ("threshold_needs_nudge_hours", "4.0"),
        ("threshold_offline_days", "3.0"),
        ("schedule_cron", "0 15 * * 5"), # Friday 3:00 PM
        ("schedule_day", "Friday"),
        ("schedule_time", "15:00"),
        ("auto_dispatch_enabled", "true"),
        ("whatsapp_provider", "simulator"), # 'simulator', 'meta_cloud_api', 'twilio', 'whatsauto_webhook'
        ("meta_api_token", ""),
        ("meta_phone_number_id", ""),
        ("twilio_account_sid", ""),
        ("twilio_auth_token", ""),
        ("twilio_from_number", "whatsapp:+14155238886"),
        ("whatsauto_webhook_url", ""),
        ("last_automated_run_at", "")
    ]

    for key, val in default_configs:
        cursor.execute("""
        INSERT OR IGNORE INTO system_config (key, value, updated_at)
        VALUES (?, ?, ?)
        """, (key, val, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
