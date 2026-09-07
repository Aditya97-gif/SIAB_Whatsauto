import random
import json
from datetime import datetime, timedelta
from database import get_db, init_db

DISTRICTS = [
    ("Pune", "Maharashtra"),
    ("Satara", "Maharashtra"),
    ("Nashik", "Maharashtra"),
    ("Kolhapur", "Maharashtra"),
    ("Mysuru", "Karnataka"),
    ("Dharwad", "Karnataka"),
    ("Tumakuru", "Karnataka"),
    ("Jaipur", "Rajasthan"),
    ("Udaipur", "Rajasthan"),
    ("Jodhpur", "Rajasthan"),
    ("Varanasi", "Uttar Pradesh"),
    ("Lucknow", "Uttar Pradesh"),
    ("Prayagraj", "Uttar Pradesh"),
    ("Bhopal", "Madhya Pradesh"),
    ("Indore", "Madhya Pradesh"),
    ("Cuttack", "Odisha"),
    ("Sambalpur", "Odisha"),
    ("Madurai", "Tamil Nadu"),
    ("Coimbatore", "Tamil Nadu"),
    ("Patna", "Bihar"),
    ("Gaya", "Bihar"),
    ("Vadodara", "Gujarat"),
    ("Rajkot", "Gujarat"),
    ("Bankura", "West Bengal"),
    ("Purulia", "West Bengal")
]

TEACHER_NAMES = [
    "Sunita Sharma", "Ramesh Patil", "Pooja Deshmukh", "Anand Verma", "Lakshmi Iyer",
    "Suresh Kumar", "Deepa Rao", "Vijay Jadhav", "Meena Kulkarni", "Rajesh Rathore",
    "Kavita Singh", "Manoj Mishra", "Geeta Patel", "Dinesh Shinde", "Anjali Joshi",
    "Prakash Nayak", "Rekha Gupta", "Sunil Chougule", "Sanjay More", "Savita Gaikwad",
    "Arun Tiwari", "Priyanka Yadav", "Rakesh Chouhan", "Vandana Nair", "Amit Sen",
    "Shweta Kadam", "Santosh Mohite", "Hemant Tripathi", "Sonal Sawant", "Rohit Waghmare"
]

SCHOOL_PREFIXES = [
    "Zilla Parishad High School",
    "Government Primary School",
    "Adarsh Vidyalaya",
    "Kasturba Gandhi Balika Vidyalaya",
    "Prathmik Shala",
    "Vikas Mandir Ashram School",
    "Samarth Madhyamik Vidyalaya",
    "Model Public School",
    "Gram Panchayat Secondary School",
    "Saraswati Vidya Mandir"
]

CURRICULUM_DATA = [
    {
        "code": "PHET-ELEC-01",
        "title": "PhET: Circuit Construction Kit (DC)",
        "subject": "Science",
        "grade_range": "Grade 4-8",
        "module_type": "PhET Simulation",
        "description": "Interactive virtual circuit lab where students connect batteries, light bulbs, switches, and resistors to explore open and closed circuits safely.",
        "key_concept": "Electric current, conductivity, open vs closed circuits",
        "instructions_summary": "Guide students to build a simple bulb circuit, then test with conductor vs insulator objects.",
        "sample_prompt": "Try connecting two bulbs in series and watch if they get dimmer!",
        "link_url": "offline://siab/modules/phet/circuit-construction-kit-dc"
    },
    {
        "code": "PHET-FRAC-02",
        "title": "PhET: Fractions Intro & Matcher",
        "subject": "Maths",
        "grade_range": "Grade 2-5",
        "module_type": "PhET Simulation",
        "description": "Visualizing fractions using colorful pizza slices, water beakers, and balance scale mini-games.",
        "key_concept": "Numerator, denominator, equal partitioning",
        "instructions_summary": "Ask students to drag fraction shapes and match halves and quarters to solve the puzzle levels.",
        "sample_prompt": "Show students how 2/4 is equal to 1/2 using the fraction scale game!",
        "link_url": "offline://siab/modules/phet/fractions-intro"
    },
    {
        "code": "PHET-STAT-03",
        "title": "PhET: States of Matter: Basics",
        "subject": "Science",
        "grade_range": "Grade 3-7",
        "module_type": "PhET Simulation",
        "description": "Heat, cool, and compress atoms and molecules to see how solid ice turns into liquid water and water vapor.",
        "key_concept": "Solids, liquids, gases, melting and boiling points",
        "instructions_summary": "Pump heat into the chamber and watch the neon particles jump excitedly as temperature rises.",
        "sample_prompt": "Ask kids what happens to steam when you cool the beaker down!",
        "link_url": "offline://siab/modules/phet/states-of-matter-basics"
    },
    {
        "code": "TFT-GEN-01",
        "title": "Toys From Trash: CD Motor Generator",
        "subject": "STEM",
        "grade_range": "Grade 5-8",
        "module_type": "Toys From Trash",
        "description": "Building a working electrical generator using an old compact disc, small toy motor, rubber band, and LED.",
        "key_concept": "Mechanical energy to electrical energy conversion",
        "instructions_summary": "Spin the CD pulley handle briskly to generate current and light up the red LED bulb without batteries.",
        "sample_prompt": "Have students count how fast they need to spin the wheel to light the LED!",
        "link_url": "offline://siab/modules/toysfromtrash/cd-motor-generator"
    },
    {
        "code": "TFT-HOV-02",
        "title": "Toys From Trash: Balloon Hovercraft",
        "subject": "Science",
        "grade_range": "Grade 1-6",
        "module_type": "Toys From Trash",
        "description": "A frictionless gliding hovercraft made from a scrap plastic bottle cap, discarded CD, and an inflated balloon.",
        "key_concept": "Air pressure, air cushion, friction reduction",
        "instructions_summary": "Inflate the balloon on the nozzle and release it on the floor. It glides smoothly across the classroom!",
        "sample_prompt": "Let students race two hovercrafts across the floor to explore friction!",
        "link_url": "offline://siab/modules/toysfromtrash/balloon-hovercraft"
    },
    {
        "code": "TFT-STR-03",
        "title": "Toys From Trash: Paper Straw Whistle & Flute",
        "subject": "Arts & Music",
        "grade_range": "Grade 1-5",
        "module_type": "Toys From Trash",
        "description": "Creating musical sound pitches by snipping different lengths of drinking straws or rolled paper tubes.",
        "key_concept": "Sound waves, frequency, vibration, column length",
        "instructions_summary": "Snip small triangular reeds at the tip of the straw and blow gently to produce clear musical notes.",
        "sample_prompt": "Cut the straw shorter while blowing and hear the pitch go higher and higher!",
        "link_url": "offline://siab/modules/toysfromtrash/straw-whistle"
    },
    {
        "code": "STW-ENG-01",
        "title": "StoryWeaver: Interactive Animal Kingdom Audio Stories",
        "subject": "English",
        "grade_range": "Grade 1-4",
        "module_type": "Interactive Story",
        "description": "Illustrated bilingual audio storybooks with follow-along highlighted vocabulary and phonics practice.",
        "key_concept": "Reading comprehension, vocabulary, pronunciation",
        "instructions_summary": "Play the audio aloud while projecting the colorful slides on the classroom display.",
        "sample_prompt": "Ask 3 students to act out the lion and the rabbit characters after the reading!",
        "link_url": "offline://siab/modules/storyweaver/animal-tales"
    },
    {
        "code": "MATH-GEO-01",
        "title": "Matchstick Geometry & Tangram Puzzles",
        "subject": "Maths",
        "grade_range": "Grade 3-6",
        "module_type": "Math Challenge",
        "description": "Solving geometric riddles by rearranging 4 matchsticks to create polygons, angles, and symmetry shapes.",
        "key_concept": "Perimeter, area, 2D shapes, spatial reasoning",
        "instructions_summary": "Challenge groups to form 3 squares using only 8 matchsticks with no leftover sticks.",
        "sample_prompt": "Turn this into a 10-minute Friday classroom relay quiz!",
        "link_url": "offline://siab/modules/maths/matchstick-geometry"
    }
]

def seed_database(total_schools=575):
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM schools")
    count = cursor.fetchone()[0]
    if count >= total_schools:
        print(f"Database already contains {count} schools. Skipping seed.")
        conn.close()
        return

    print("Clearing and re-seeding database with fresh SIAB data...")
    cursor.execute("DELETE FROM schools")
    cursor.execute("DELETE FROM telemetry_logs")
    cursor.execute("DELETE FROM nudges_log")
    cursor.execute("DELETE FROM chat_messages")
    cursor.execute("DELETE FROM tickets")
    cursor.execute("DELETE FROM curriculum_modules")

    # 1. Seed Curriculum Modules
    for curr in CURRICULUM_DATA:
        cursor.execute("""
        INSERT INTO curriculum_modules (code, title, subject, grade_range, module_type, description, key_concept, instructions_summary, sample_prompt, link_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            curr["code"], curr["title"], curr["subject"], curr["grade_range"], curr["module_type"],
            curr["description"], curr["key_concept"], curr["instructions_summary"], curr["sample_prompt"], curr["link_url"]
        ))

    # 2. Seed Schools & Telemetry
    now = datetime.utcnow()
    
    # Bucket distribution target:
    # ~58% Doing Great (330 schools)
    # ~27% Needs Nudge (155 schools)
    # ~15% Device Offline (90 schools)
    
    doing_great_target = int(total_schools * 0.58)
    needs_nudge_target = int(total_schools * 0.27)
    offline_target = total_schools - doing_great_target - needs_nudge_target

    buckets = (['doing_great'] * doing_great_target) + (['needs_nudge'] * needs_nudge_target) + (['device_offline'] * offline_target)
    random.shuffle(buckets)

    phone_base = 9820000000

    for i in range(total_schools):
        school_num = i + 1
        bucket = buckets[i]
        district, state = random.choice(DISTRICTS)
        prefix = random.choice(SCHOOL_PREFIXES)
        school_name = f"{prefix} - {district} #{school_num}"
        school_code = f"SIAB-{state[:2].upper()}-{district[:3].upper()}-{school_num:04d}"
        teacher_name = random.choice(TEACHER_NAMES)
        phone = f"+91{phone_base + school_num}"
        students_count = random.randint(120, 750)
        device_id = f"SIAB-BOX-{school_num:05d}"
        
        # Telemetry characteristics based on bucket
        if bucket == 'doing_great':
            # 12 to 32 hours weekly usage
            weekly_hours = round(random.uniform(12.5, 31.0), 1)
            smart_class_sessions = random.randint(14, 38)
            # Synced very recently (0 to 24 hours ago)
            hours_ago = random.uniform(0.5, 22.0)
            last_sync = (now - timedelta(hours=hours_ago)).isoformat()
            
            science_pct = random.randint(30, 45)
            maths_pct = random.randint(25, 35)
            arts_pct = random.randint(10, 20)
            eng_pct = random.randint(10, 20)
            phys_pct = 100 - (science_pct + maths_pct + arts_pct + eng_pct)
            
        elif bucket == 'needs_nudge':
            # 0.2 to 4.5 hours weekly usage
            weekly_hours = round(random.uniform(0.2, 4.4), 1)
            smart_class_sessions = random.randint(1, 5)
            # Synced relatively recently (0.5 to 2.5 days ago)
            hours_ago = random.uniform(2.0, 50.0)
            last_sync = (now - timedelta(hours=hours_ago)).isoformat()
            
            science_pct = random.randint(20, 30)
            maths_pct = random.randint(20, 30)
            arts_pct = random.randint(10, 20)
            eng_pct = random.randint(10, 20)
            phys_pct = 100 - (science_pct + maths_pct + arts_pct + eng_pct)
            
        else: # device_offline
            # 0 hours or minimal usage from previous cycle
            weekly_hours = round(random.uniform(0.0, 1.2), 1)
            smart_class_sessions = random.randint(0, 2)
            # Synced 3.5 to 19 days ago
            days_ago = random.uniform(3.5, 18.0)
            last_sync = (now - timedelta(days=days_ago)).isoformat()
            
            science_pct = 20
            maths_pct = 20
            arts_pct = 20
            eng_pct = 20
            phys_pct = 20

        subjects_dict = {
            "Science": f"{science_pct}%",
            "Maths": f"{maths_pct}%",
            "Arts": f"{arts_pct}%",
            "English": f"{eng_pct}%",
            "Phys Ed": f"{max(0, phys_pct)}%"
        }

        cursor.execute("""
        INSERT INTO schools (
            school_code, name, district, state, contact_name, contact_role,
            phone_number, students_count, device_id, device_model,
            last_synced_at, weekly_usage_hours, smart_class_sessions,
            subjects_json, current_bucket, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            school_code, school_name, district, state, teacher_name, "Head Teacher",
            phone, students_count, device_id, "SIAB-Pi-4K-v2",
            last_sync, weekly_hours, smart_class_sessions,
            json.dumps(subjects_dict), bucket, "active", (now - timedelta(days=90)).isoformat()
        ))
        school_id = cursor.lastrowid

        # Insert telemetry logs for past 5 syncs
        for sync_idx in range(5):
            t_sync = now - timedelta(days=(sync_idx * 1.5))
            t_usage = round(max(0.0, weekly_hours / 5.0 + random.uniform(-0.5, 0.5)), 1)
            apps = ["PhET Circuit Lab", "StoryWeaver Audio", "Toys From Trash Flute", "Maths Matchstick Quiz"]
            cursor.execute("""
            INSERT INTO telemetry_logs (school_id, synced_at, usage_hours, active_apps_json, system_health, battery_level, power_cycles, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                school_id, t_sync.isoformat(), t_usage, json.dumps(apps[:random.randint(1, 4)]),
                "ok" if bucket != "device_offline" else "warning",
                random.randint(70, 100), random.randint(1, 3), t_sync.isoformat()
            ))

        # For the first 15 schools, seed sample realistic nudges and 2-way chat interactions
        if school_num <= 15:
            if bucket == 'doing_great':
                nudge_msg = f"Namaste {teacher_name} ji! 🌟 Amazing week at {school_name}! Your smart class logged {weekly_hours} hours of active learning. The kids are loving it! To switch things up next week, try showing them the 'Toys From Trash' CD Motor Generator or PhET Circuit simulations! Reply here if you need lesson plans."
                curr_sugg = "Toys From Trash: CD Motor Generator"
                cursor.execute("""
                INSERT INTO nudges_log (school_id, phone_number, bucket, template_name, message_text, curriculum_suggestion, status, dispatched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (school_id, phone, bucket, "doing_great_celebration", nudge_msg, curr_sugg, "delivered", (now - timedelta(hours=3)).isoformat()))
                
                # Chat message exchange
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "system", nudge_msg, "automated_nudge", (now - timedelta(hours=3)).isoformat()))
                
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "teacher", "Thank you! The students really enjoyed the circuit experiment today. Can you send details for the paper straw whistle?", "curriculum_request", (now - timedelta(hours=2)).isoformat()))
                
                bot_reply = "Here you go! 🎵 'Toys From Trash: Paper Straw Whistle & Flute' is ready on your SIAB box under Arts & Music. Snip the reed tip and blow gently to demonstrate pitch changes. Have fun!"
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "agent", bot_reply, "curriculum_response", (now - timedelta(hours=1, minutes=55)).isoformat()))

            elif bucket == 'needs_nudge':
                nudge_msg = f"Namaste {teacher_name} ji! 👋 Just checking in from School-in-a-Box team. We noticed the smart class had only {weekly_hours} hours logged this week. If you're busy with exams or need quick 10-minute fun activities, reply here and we'll send easy suggestions!"
                curr_sugg = "PhET: Fractions Intro & Matcher"
                cursor.execute("""
                INSERT INTO nudges_log (school_id, phone_number, bucket, template_name, message_text, curriculum_suggestion, status, dispatched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (school_id, phone, bucket, "needs_nudge_support", nudge_msg, curr_sugg, "read", (now - timedelta(hours=4)).isoformat()))
                
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "system", nudge_msg, "automated_nudge", (now - timedelta(hours=4)).isoformat()))

                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "teacher", "Hello team. Yes, we had annual sports day this week so classes were short. Will resume full sessions on Monday!", "general_query", (now - timedelta(hours=3, minutes=10)).isoformat()))

                bot_reply = "Understood {teacher_name} ji! Best wishes for the sports day! 🏆 Next week you can start with a 15-minute quick math puzzle to kick off the classes."
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "agent", bot_reply, "support_acknowledgement", (now - timedelta(hours=3)).isoformat()))

            else: # device_offline
                last_sync_dt = datetime.fromisoformat(last_sync)
                days_off = (now - last_sync_dt).days
                nudge_msg = f"⚠️ Alert from SIAB Support! {school_name}'s smart box hasn't synced in {days_off} days (Last sync: {last_sync_dt.strftime('%d %b')}). Could you please double-check the power switch and WiFi/SIM light? Reply 'POWER' if there is an outage or 'HELP' if device is damaged."
                curr_sugg = "Hardware & Power Health Check"
                cursor.execute("""
                INSERT INTO nudges_log (school_id, phone_number, bucket, template_name, message_text, curriculum_suggestion, status, dispatched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (school_id, phone, bucket, "device_offline_alert", nudge_msg, curr_sugg, "sent", (now - timedelta(hours=5)).isoformat()))
                
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "system", nudge_msg, "automated_nudge", (now - timedelta(hours=5)).isoformat()))

                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "teacher", "There was severe lightning in our village and the power transformer failed 4 days ago. Electric department is fixing it tomorrow.", "power_issue", (now - timedelta(hours=2, minutes=30)).isoformat()))

                # Ticket created
                ticket_code = f"TKT-PWR-{school_id:04d}"
                cursor.execute("""
                INSERT INTO tickets (ticket_code, school_id, category, priority, title, description, status, assigned_to, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticket_code, school_id, "power_cut", "high",
                    f"Transformer failure & power cut at {district}",
                    f"Teacher reported village power cut due to lightning 4 days ago. Expected restoration in 24-48h.",
                    "in_progress", "Field Coordinator - " + district,
                    (now - timedelta(hours=2, minutes=30)).isoformat(), (now - timedelta(hours=2, minutes=30)).isoformat()
                ))

                bot_reply = f"Thank you for informing us {teacher_name} ji! 🛠️ We have logged Ticket #{ticket_code} with our field coordinator ({district}). Please turn on the box once the line is restored and it will auto-sync."
                cursor.execute("""
                INSERT INTO chat_messages (school_id, sender, message_text, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (school_id, "agent", bot_reply, "ticket_creation", (now - timedelta(hours=2, minutes=25)).isoformat()))

    conn.commit()
    conn.close()
    print(f"Successfully seeded {total_schools} schools with realistic SIAB telemetries and curriculum modules!")

if __name__ == "__main__":
    seed_database(575)
