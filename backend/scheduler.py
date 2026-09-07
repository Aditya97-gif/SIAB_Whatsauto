import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import threading
import time
from datetime import datetime
from classifier_engine import run_classification_engine, get_system_config
from database import get_db

class AutomationScheduler:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self._lock = threading.Lock()
        self.last_run_status = None

    def start(self):
        with self._lock:
            if not self.is_running:
                self.is_running = True
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                print("[Scheduler] Automation background service started.")

    def stop(self):
        with self._lock:
            self.is_running = False
            print("[Scheduler] Automation background service stopped.")

    def trigger_now(self, dry_run=False, school_ids=None):
        """Manually trigger the automation engine."""
        print(f"[Scheduler] Manual trigger invoked. dry_run={dry_run}")
        result = run_classification_engine(dry_run=dry_run, school_ids=school_ids)
        self.last_run_status = {
            "timestamp": result["timestamp"],
            "dry_run": result["dry_run"],
            "total_evaluated": result["total_evaluated"],
            "bucket_counts": result["bucket_counts"]
        }
        return result

    def _run_loop(self):
        while self.is_running:
            try:
                config = get_system_config()
                if config.get("auto_dispatch_enabled"):
                    now = datetime.now()
                    # Check if today matches scheduled day (e.g. Friday is weekday 4 in python 0-indexed Mon-Sun)
                    # Friday == 4
                    target_day = config.get("schedule_day", "Friday").strip().lower()
                    target_time = config.get("schedule_time", "15:00").strip() # HH:MM
                    
                    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    current_day_name = day_names[now.weekday()]
                    current_time_str = now.strftime("%H:%M")

                    # Check if already ran in the last 2 hours
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT value FROM system_config WHERE key = 'last_automated_run_at'")
                    row = cursor.fetchone()
                    conn.close()

                    last_run_str = row["value"] if row and row["value"] else ""
                    should_run = False
                    
                    if current_day_name == target_day and current_time_str == target_time:
                        if not last_run_str:
                            should_run = True
                        else:
                            try:
                                last_run_dt = datetime.fromisoformat(last_run_str)
                                if (now - last_run_dt).total_seconds() > 3600 * 20: # Haven't run today
                                    should_run = True
                            except Exception:
                                should_run = True

                    if should_run:
                        print(f"[Scheduler] Triggering scheduled Friday automation at {now.isoformat()}...")
                        self.trigger_now(dry_run=False)

            except Exception as e:
                print(f"[Scheduler] Error in scheduler loop: {e}")

            time.sleep(30) # Check every 30 seconds

scheduler_instance = AutomationScheduler()
