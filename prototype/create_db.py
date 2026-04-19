import sqlite3
import csv
from pathlib import Path

# Setup paths
db_path = Path(__file__).parent / "data" / "chicago_crashes.db"
csv_path = Path(__file__).parent / "data" / "chicago_crashes_output.csv"

# Create database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS crashes (
    crash_record_id TEXT PRIMARY KEY,
    crash_date TEXT,
    latitude REAL,
    longitude REAL,
    posted_speed_limit INTEGER,
    crash_type TEXT,
    most_severe_injury TEXT,
    injuries_total INTEGER,
    prim_contributory_cause TEXT,
    location TEXT
)
""")

# Read CSV and insert data
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute("""
            INSERT INTO crashes VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            row['crash_record_id'],
            row['crash_date'],
            float(row['latitude']),
            float(row['longitude']),
            int(row['posted_speed_limit']),
            row['crash_type'],
            row['most_severe_injury'],
            int(row['injuries_total']),
            row['prim_contributory_cause'],
            row['location']
        ))

conn.commit()
conn.close()

print(f"✓ Database created: {db_path}")
print(f"✓ Records inserted from: {csv_path}")
