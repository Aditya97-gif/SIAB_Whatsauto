import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import json
import random
from datetime import datetime, timezone
from database import get_db

def parse_iso(dt_str):
    try:
        # Handle trailing Z or normal ISO format
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.now()

def get_system_config():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_config")
    rows = cursor.fetchall()
    conn.close()
    config = {row["key"]: row["value"] for row in rows}
    
    return {
        "threshold_doing_great_hours": float(config.get("threshold_doing_great_hours", 12.0)),
        "threshold_needs_nudge_hours": float(config.get("threshold_needs_nudge_hours", 4.0)),
        "threshold_offline_days": float(config.get("threshold_offline_days", 3.0)),
        "schedule_cron": config.get("schedule_cron", "0 15 * * 5"),
        "schedule_day": config.get("schedule_day", "Friday"),
        "schedule_time": config.get("schedule_time", "15:00"),
        "auto_dispatch_enabled": config.get("auto_dispatch_enabled", "true") == "true",
        "whatsapp_provider": config.get("whatsapp_provider", "simulator")
    }

def get_curriculum_recommendations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM curriculum_modules")
    modules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return modules

def classify_school(school, config, curriculum_list):
    """
    Evaluates telemetry rules and determines bucket + customized message.
    """
    now = datetime.now()
    last_sync_dt = parse_iso(school["last_synced_at"])
    
    # Calculate days since sync (ignoring timezone offset issues if naive)
    if last_sync_dt.tzinfo is not None:
        last_sync_dt = last_sync_dt.replace(tzinfo=None)
    
    delta = now - last_sync_dt
    days_since_sync = max(0, delta.total_seconds() / 86400.0)
    
    weekly_hours = float(school["weekly_usage_hours"])
    teacher_name = school["contact_name"]
    school_name = school["name"]
    district = school["district"]

    # Rule evaluation
    if days_since_sync > config["threshold_offline_days"]:
        bucket = "device_offline"
        days_int = max(1, int(round(days_since_sync)))
        formatted_sync_date = last_sync_dt.strftime("%d %b")
        
        template_name = "device_offline_alert"
        curriculum_suggestion = "Hardware & Power Health Check"
        message_text = (
            f"Namaste {teacher_name} ji! ⚠️ SIAB Support Alert:\n\n"
            f"We noticed that the School-in-a-Box device at {school_name} hasn't synced in {days_int} days (last seen {formatted_sync_date}).\n\n"
            f"Could you please check:\n"
            f"1. Is the power strip turned on?\n"
            f"2. Is the green power light glowing on the SIAB unit?\n"
            f"3. Has there been a power outage in {district}?\n\n"
            f"Reply 'POWER' if there is an outage, or reply here if you need technician assistance."
        )
    elif weekly_hours >= config["threshold_doing_great_hours"]:
        bucket = "doing_great"
        template_name = "doing_great_celebration"
        
        # Pick 1-2 relevant curriculum suggestions
        phet_items = [c for c in curriculum_list if c["module_type"] == "PhET Simulation"]
        tft_items = [c for c in curriculum_list if c["module_type"] == "Toys From Trash"]
        
        phet = random.choice(phet_items) if phet_items else {"title": "PhET Simulation Lab"}
        tft = random.choice(tft_items) if tft_items else {"title": "Toys From Trash Science"}
        
        curriculum_suggestion = f"{tft['title']} & {phet['title']}"
        
        message_text = (
            f"Namaste {teacher_name} ji! 🌟 Amazing week at {school_name}!\n\n"
            f"Your smart classroom logged {weekly_hours} hours of active learning this week. The students are making tremendous progress! 🚀\n\n"
            f"💡 Recommended activities for next week:\n"
            f"• 🔬 {tft['title']} ({tft.get('key_concept', 'Hands-on Science')})\n"
            f"• 💻 {phet['title']} (Grade {phet.get('grade_range', 'All')})\n\n"
            f"All modules are ready offline on your box. Reply here anytime if you'd like lesson plans or activity sheets!"
        )
    else:
        bucket = "needs_nudge"
        template_name = "needs_nudge_support"
        
        math_or_story = [c for c in curriculum_list if c["module_type"] in ["Interactive Story", "Math Challenge", "PhET Simulation"]]
        item = random.choice(math_or_story) if math_or_story else {"title": "15-Minute Math Puzzle"}
        
        curriculum_suggestion = item["title"]
        message_text = (
            f"Namaste {teacher_name} ji! 👋 Warm greetings from the School-in-a-Box team.\n\n"
            f"We noticed the smart class logged {weekly_hours} hours this week. We know school schedules can get very hectic with exams and administrative duties!\n\n"
            f"To get the students excited next week without taking much time, try this quick 15-minute activity:\n"
            f"✨ {item['title']} - {item.get('instructions_summary', 'Easy interactive classroom activity')}\n\n"
            f"Need any help or quick activity ideas? Simply reply to this message and we're here to help!"
        )

    return {
        "school_id": school["id"],
        "school_code": school["school_code"],
        "school_name": school_name,
        "district": district,
        "state": school["state"],
        "contact_name": teacher_name,
        "phone_number": school["phone_number"],
        "weekly_usage_hours": weekly_hours,
        "days_since_sync": round(days_since_sync, 1),
        "last_synced_at": school["last_synced_at"],
        "bucket": bucket,
        "template_name": template_name,
        "curriculum_suggestion": curriculum_suggestion,
        "message_text": message_text
    }

def run_classification_engine(dry_run=True, school_ids=None):
    """
    Executes the 3-step automation engine across all schools or selected subset.
    If dry_run=True, returns generated results without updating DB or dispatching.
    If dry_run=False, updates school buckets, logs nudges, and triggers dispatch.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    config = get_system_config()
    curriculum_list = get_curriculum_recommendations()

    if school_ids and len(school_ids) > 0:
        placeholders = ",".join("?" for _ in school_ids)
        cursor.execute(f"SELECT * FROM schools WHERE id IN ({placeholders})", school_ids)
    else:
        cursor.execute("SELECT * FROM schools WHERE status = 'active'")
        
    schools = [dict(row) for row in cursor.fetchall()]
    
    results = []
    bucket_counts = {"doing_great": 0, "needs_nudge": 0, "device_offline": 0}
    now_iso = datetime.now().isoformat()

    for s in schools:
        classified = classify_school(s, config, curriculum_list)
        results.append(classified)
        bucket_counts[classified["bucket"]] += 1

        if not dry_run:
            # Update school bucket in database
            cursor.execute("""
            UPDATE schools 
            SET current_bucket = ?
            WHERE id = ?
            """, (classified["bucket"], classified["school_id"]))

            # Insert into nudges_log
            cursor.execute("""
            INSERT INTO nudges_log (
                school_id, phone_number, bucket, template_name, 
                message_text, curriculum_suggestion, status, channel, dispatched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                classified["school_id"], classified["phone_number"], classified["bucket"],
                classified["template_name"], classified["message_text"],
                classified["curriculum_suggestion"], "sent", "whatsapp", now_iso
            ))

            # Also log message to chat_messages
            cursor.execute("""
            INSERT INTO chat_messages (
                school_id, sender, message_text, intent, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                classified["school_id"], "system", classified["message_text"],
                "automated_nudge", now_iso
            ))

    if not dry_run:
        cursor.execute("""
        INSERT OR REPLACE INTO system_config (key, value, updated_at)
        VALUES ('last_automated_run_at', ?, ?)
        """, (now_iso, now_iso))
        conn.commit()

    conn.close()

    return {
        "timestamp": now_iso,
        "dry_run": dry_run,
        "total_evaluated": len(schools),
        "bucket_counts": bucket_counts,
        "results": results
    }

if __name__ == "__main__":
    test_run = run_classification_engine(dry_run=True)
    print(f"Classification test run completed: {test_run['total_evaluated']} schools evaluated.")
    print("Bucket distribution:", test_run["bucket_counts"])
    print("\nSample Generated Message (Doing Great):")
    sample_dg = next(r for r in test_run["results"] if r["bucket"] == "doing_great")
    print(sample_dg["message_text"])
    print("\nSample Generated Message (Needs Nudge):")
    sample_nn = next(r for r in test_run["results"] if r["bucket"] == "needs_nudge")
    print(sample_nn["message_text"])
    print("\nSample Generated Message (Device Offline):")
    sample_off = next(r for r in test_run["results"] if r["bucket"] == "device_offline")
    print(sample_off["message_text"])
