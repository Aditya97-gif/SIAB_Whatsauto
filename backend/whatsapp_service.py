import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import json
import re
import requests
from datetime import datetime
from database import get_db

# WebSocket connection manager hook
active_websockets = []

async def broadcast_ws(payload: dict):
    """Broadcasts a JSON event to all connected dashboard websockets."""
    for ws in list(active_websockets):
        try:
            await ws.send_json(payload)
        except Exception:
            if ws in active_websockets:
                active_websockets.remove(ws)

def send_whatsapp_message(school_id: int, phone_number: str, message_text: str, template_name: str = "custom", curriculum_suggestion: str = None):
    """
    Dispatches a WhatsApp message using the configured provider.
    Supports: Simulator, Meta Cloud API, Twilio, WhatsAuto webhook.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT key, value FROM system_config")
    config = {row["key"]: row["value"] for row in cursor.fetchall()}
    provider = config.get("whatsapp_provider", "simulator")
    
    now_iso = datetime.now().isoformat()
    dispatch_status = "sent"

    if provider == "meta_cloud_api" and config.get("meta_api_token") and config.get("meta_phone_number_id"):
        try:
            url = f"https://graph.facebook.com/v18.0/{config['meta_phone_number_id']}/messages"
            headers = {
                "Authorization": f"Bearer {config['meta_api_token']}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number.replace("+", ""),
                "type": "text",
                "text": {"body": message_text}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                dispatch_status = "delivered"
            else:
                dispatch_status = "failed"
        except Exception as e:
            print(f"Meta API dispatch error: {e}")
            dispatch_status = "failed"

    elif provider == "twilio" and config.get("twilio_account_sid") and config.get("twilio_auth_token"):
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{config['twilio_account_sid']}/Messages.json"
            auth = (config["twilio_account_sid"], config["twilio_auth_token"])
            data = {
                "From": config.get("twilio_from_number", "whatsapp:+14155238886"),
                "To": f"whatsapp:{phone_number}",
                "Body": message_text
            }
            resp = requests.post(url, auth=auth, data=data, timeout=10)
            if resp.status_code in [200, 201]:
                dispatch_status = "delivered"
            else:
                dispatch_status = "failed"
        except Exception as e:
            print(f"Twilio dispatch error: {e}")
            dispatch_status = "failed"

    elif provider == "whatsauto_webhook" and config.get("whatsauto_webhook_url"):
        try:
            url = config["whatsauto_webhook_url"]
            payload = {
                "app": "School-In-A-Box",
                "recipient": phone_number,
                "message": message_text,
                "timestamp": now_iso
            }
            requests.post(url, json=payload, timeout=8)
            dispatch_status = "delivered"
        except Exception as e:
            print(f"WhatsAuto webhook error: {e}")
            dispatch_status = "failed"

    else:
        # Default / Simulator mode
        dispatch_status = "delivered"

    # Log to nudges_log
    cursor.execute("""
    INSERT INTO nudges_log (
        school_id, phone_number, bucket, template_name, message_text,
        curriculum_suggestion, status, channel, dispatched_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        school_id, phone_number, "manual_or_api", template_name, message_text,
        curriculum_suggestion or "", dispatch_status, provider, now_iso
    ))
    nudge_id = cursor.lastrowid

    # Log to chat_messages
    cursor.execute("""
    INSERT INTO chat_messages (
        school_id, sender, message_text, intent, created_at
    ) VALUES (?, ?, ?, ?, ?)
    """, (
        school_id, "system", message_text, "outbound_message", now_iso
    ))
    msg_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "nudge_id": nudge_id,
        "message_id": msg_id,
        "school_id": school_id,
        "status": dispatch_status,
        "provider": provider,
        "dispatched_at": now_iso
    }

def classify_teacher_intent(text: str) -> str:
    """Classify incoming message intent from teacher."""
    t = text.lower()
    
    if any(k in t for k in ["power", "transformer", "bijli", "light cut", "blackout", "load shedding", "current", "charging"]):
        return "power_issue"
    elif any(k in t for k in ["broken", "damage", "no display", "monitor", "hdmi", "cable", "mouse", "keyboard", "crash", "screen black", "dead", "fault"]):
        return "hardware_fault"
    elif any(k in t for k in ["phet", "toy", "trash", "experiment", "science", "math", "activity", "story", "lesson plan", "simulation", "straw whistle", "balloon", "circuit", "teach", "video"]):
        return "curriculum_request"
    elif any(k in t for k in ["thank", "thanks", "dhanyavad", "shukriya", "great", "awesome", "good", "happy", "namaste", "hello"]):
        return "gratitude"
    elif any(k in t for k in ["help", "madad", "support", "call", "urgent"]):
        return "general_help"
    else:
        return "general_query"

def handle_incoming_teacher_message(school_id: int, incoming_text: str, sender_phone: str = None):
    """
    2-Way Conversational Automation:
    Processes incoming message from teacher, determines intent, performs automated actions
    (e.g., ticket creation or pedagogical resource retrieval), and returns conversational reply.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get school details
    cursor.execute("SELECT * FROM schools WHERE id = ?", (school_id,))
    school = cursor.fetchone()
    if not school:
        conn.close()
        return {"error": "School not found"}

    school = dict(school)
    teacher_name = school["contact_name"]
    district = school["district"]
    school_name = school["name"]
    now_iso = datetime.now().isoformat()

    intent = classify_teacher_intent(incoming_text)

    # 1. Log incoming teacher message
    cursor.execute("""
    INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (school_id, "teacher", incoming_text, intent, now_iso))

    bot_reply = ""
    ticket_info = None

    # 2. Automated Smart Response Logic based on Intent
    if intent == "power_issue":
        ticket_code = f"TKT-PWR-{school_id:04d}-{int(datetime.now().timestamp())%10000}"
        cursor.execute("""
        INSERT INTO tickets (ticket_code, school_id, category, priority, title, description, status, assigned_to, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_code, school_id, "power_cut", "high",
            f"Power Outage reported at {district}",
            f"Teacher {teacher_name} reported: '{incoming_text}'. SIAB box temporarily offline due to power issues.",
            "open", f"Field Coordinator - {district}", now_iso, now_iso
        ))
        ticket_info = {"code": ticket_code, "category": "power_cut", "priority": "high"}
        bot_reply = (
            f"Namaste {teacher_name} ji! 🛠️ Thank you for alerting us.\n\n"
            f"We have registered Ticket #{ticket_code} for your school. Our Field Coordinator for {district} has been notified.\n\n"
            f"⚡ Once electricity is restored, please turn the SIAB unit switch ON and it will automatically sync. Feel free to message here if you need battery pack backup support!"
        )

    elif intent == "hardware_fault":
        ticket_code = f"TKT-HW-{school_id:04d}-{int(datetime.now().timestamp())%10000}"
        cursor.execute("""
        INSERT INTO tickets (ticket_code, school_id, category, priority, title, description, status, assigned_to, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_code, school_id, "hardware_broken", "urgent",
            f"Hardware / Display Issue at {school_name}",
            f"Teacher reported issue: '{incoming_text}'. Device ID: {school['device_id']}",
            "open", f"Technical Support Desk", now_iso, now_iso
        ))
        ticket_info = {"code": ticket_code, "category": "hardware_broken", "priority": "urgent"}
        bot_reply = (
            f"Namaste {teacher_name} ji! 🔧 We're sorry for the trouble.\n\n"
            f"We have opened Urgent Support Ticket #{ticket_code} for device {school['device_id']}.\n\n"
            f"Quick troubleshooting in the meantime:\n"
            f"• Please check if the HDMI cable between the SIAB box and TV/monitor is plugged in tightly.\n"
            f"• If the red/blue light does not turn on, try a different wall socket.\n\n"
            f"Our technician will call you shortly on {school['phone_number']} to assist!"
        )

    elif intent == "curriculum_request":
        # Search curriculum matching keywords
        cursor.execute("SELECT * FROM curriculum_modules")
        modules = [dict(m) for m in cursor.fetchall()]
        
        matched = None
        t_low = incoming_text.lower()
        for m in modules:
            if m["title"].lower() in t_low or m["subject"].lower() in t_low or m["module_type"].lower() in t_low:
                matched = m
                break
        
        if not matched:
            matched = modules[0] # Default to first rich module

        bot_reply = (
            f"Namaste {teacher_name} ji! 📚 Here is an awesome offline activity for your class:\n\n"
            f"🎯 {matched['title']} ({matched['grade_range']})\n"
            f"📖 Concept: {matched['key_concept']}\n"
            f"💡 Quick Classroom Guide:\n{matched['instructions_summary']}\n\n"
            f"🚀 Teacher Tip: {matched['sample_prompt']}\n\n"
            f"You can launch this directly on your SIAB screen under '{matched['subject']}' tab!"
        )

    elif intent == "gratitude":
        bot_reply = (
            f"You're very welcome, {teacher_name} ji! 🙏\n\n"
            f"It is inspiring to see the wonderful learning happening at {school_name}. "
            f"Keep up the fantastic work with the kids! Reach out anytime whenever you need fresh activity ideas or support. Have a wonderful day! 🌟"
        )

    else:
        bot_reply = (
            f"Namaste {teacher_name} ji! 👋 School-in-a-Box Support here.\n\n"
            f"We received your message: \"{incoming_text}\".\n\n"
            f"How can we best help you today?\n"
            f"1️⃣ Reply 'ACTIVITIES' for fun offline science/math simulations\n"
            f"2️⃣ Reply 'POWER' to report local electricity cuts\n"
            f"3️⃣ Reply 'HELP' for hardware or display issues\n\n"
            f"Or type your question and our team will get back to you!"
        )

    # 3. Log bot response
    cursor.execute("""
    INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (school_id, "agent", bot_reply, f"{intent}_response", now_iso))
    bot_msg_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "success": True,
        "school_id": school_id,
        "teacher_message": incoming_text,
        "intent": intent,
        "bot_reply": bot_reply,
        "ticket_created": ticket_info,
        "timestamp": now_iso
    }
