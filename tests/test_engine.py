import unittest
import json
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database import init_db, get_db
from classifier_engine import classify_school, get_system_config, get_curriculum_recommendations, run_classification_engine
from whatsapp_service import classify_teacher_intent, handle_incoming_teacher_message
from datetime import datetime, timedelta

class TestSIABAutomation(unittest.TestCase):
    def setUp(self):
        init_db()
        self.config = get_system_config()
        self.curriculum = get_curriculum_recommendations()

    def test_classifier_doing_great(self):
        """School with 18 hours usage and recent sync should be in 'doing_great' bucket."""
        school = {
            "id": 9991,
            "school_code": "TEST-01",
            "name": "Adarsh Vidyalaya Test",
            "district": "Pune",
            "state": "Maharashtra",
            "contact_name": "Test Teacher",
            "phone_number": "+919999999991",
            "weekly_usage_hours": 18.5,
            "last_synced_at": datetime.now().isoformat()
        }
        res = classify_school(school, self.config, self.curriculum)
        self.assertEqual(res["bucket"], "doing_great")
        self.assertEqual(res["template_name"], "doing_great_celebration")
        self.assertIn("Amazing week", res["message_text"])
        self.assertIn("18.5 hours", res["message_text"])

    def test_classifier_needs_nudge(self):
        """School with 2.5 hours usage and recent sync should be in 'needs_nudge' bucket."""
        school = {
            "id": 9992,
            "school_code": "TEST-02",
            "name": "Zilla Parishad Test",
            "district": "Satara",
            "state": "Maharashtra",
            "contact_name": "Test Teacher 2",
            "phone_number": "+919999999992",
            "weekly_usage_hours": 2.5,
            "last_synced_at": datetime.now().isoformat()
        }
        res = classify_school(school, self.config, self.curriculum)
        self.assertEqual(res["bucket"], "needs_nudge")
        self.assertEqual(res["template_name"], "needs_nudge_support")
        self.assertIn("noticed the smart class logged 2.5 hours", res["message_text"])

    def test_classifier_device_offline(self):
        """School not synced for 6 days should be in 'device_offline' bucket regardless of usage."""
        old_sync = (datetime.now() - timedelta(days=6)).isoformat()
        school = {
            "id": 9993,
            "school_code": "TEST-03",
            "name": "Govt High School Test",
            "district": "Mysuru",
            "state": "Karnataka",
            "contact_name": "Test Teacher 3",
            "phone_number": "+919999999993",
            "weekly_usage_hours": 15.0, # even with hours, offline takes precedence
            "last_synced_at": old_sync
        }
        res = classify_school(school, self.config, self.curriculum)
        self.assertEqual(res["bucket"], "device_offline")
        self.assertEqual(res["template_name"], "device_offline_alert")
        self.assertIn("hasn't synced in 6 days", res["message_text"])

    def test_intent_classification(self):
        """Verify intent parsing for teacher messages."""
        self.assertEqual(classify_teacher_intent("There is a severe power cut and transformer issue"), "power_issue")
        self.assertEqual(classify_teacher_intent("The monitor display is broken and screen is black"), "hardware_fault")
        self.assertEqual(classify_teacher_intent("Please send the PhET simulation for electric circuit"), "curriculum_request")
        self.assertEqual(classify_teacher_intent("Toys from trash balloon hovercraft activity details"), "curriculum_request")
        self.assertEqual(classify_teacher_intent("Thank you so much, kids are very happy!"), "gratitude")

    def test_two_way_power_ticket_flow(self):
        """Verify 2-way bot opens support ticket when teacher reports power outage."""
        res = handle_incoming_teacher_message(1, "Our village transformer failed due to lightning, power cut for 3 days.")
        self.assertTrue(res["success"])
        self.assertEqual(res["intent"], "power_issue")
        self.assertIsNotNone(res["ticket_created"])
        self.assertEqual(res["ticket_created"]["category"], "power_cut")
        self.assertIn("Ticket #TKT-PWR-", res["bot_reply"])

    def test_two_way_curriculum_flow(self):
        """Verify 2-way bot responds with offline curriculum guide when teacher asks for PhET or science activity."""
        res = handle_incoming_teacher_message(1, "Can you suggest PhET simulation or science experiment for tomorrow?")
        self.assertTrue(res["success"])
        self.assertEqual(res["intent"], "curriculum_request")
        self.assertIn("offline activity for your class", res["bot_reply"])

    def test_batch_classification_run(self):
        """Verify batch classification runs smoothly."""
        res = run_classification_engine(dry_run=True)
        self.assertGreater(res["total_evaluated"], 500)
        self.assertIn("doing_great", res["bucket_counts"])
        self.assertIn("needs_nudge", res["bucket_counts"])
        self.assertIn("device_offline", res["bucket_counts"])

if __name__ == "__main__":
    unittest.main()
