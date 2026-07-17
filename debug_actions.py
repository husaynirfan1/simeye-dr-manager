"""
Debug script to check action parsing
"""
import psycopg2
import re

DB_CONFIG = {
    "dbname": "maintenance_app",
    "user": "postgres",
    "password": "pwneaw139",
    "host": "172.24.2.46",
    "port": "5432"
}

def parse_action_taken(action_text):
    """Parse ActionTaken text into list of action dictionaries"""
    if not action_text:
        return []

    actions = []
    # Split by carriage return or similar separators
    # Use non-capturing group to match the full sequence
    entries = re.split(r'(?:&#x0D;|\r\n|\n)', action_text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        print(f"Trying to parse: '{entry}'")

        # Parse the entry - format: [date] [user] [description]
        match = re.match(r'\[([^\]]+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]', entry)
        if match:
            actions.append({
                'timestamp': match.group(1),
                'username': match.group(2),
                'description': match.group(3),
                'full': entry
            })
            print(f"  -> Matched! timestamp={match.group(1)}, user={match.group(2)}, desc={match.group(3)}")
        else:
            print(f"  -> No match!")

    return actions

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("CHECKING ACTION DATA")
print("=" * 80)

# Get some deficiencies with actions
cur.execute("""
    SELECT "DeficiencyNumber", "ActionTaken"
    FROM dr_deficiency
    WHERE "ActionTaken" IS NOT NULL AND "ActionTaken" != ''
    LIMIT 5;
""")

rows = cur.fetchall()

for row in rows:
    def_num, action_taken = row
    print(f"\nDeficiency #{def_num}:")
    print(f"Raw ActionTaken: {repr(action_taken)}")
    print(f"Length: {len(action_taken) if action_taken else 0}")

    actions = parse_action_taken(action_taken)
    print(f"Parsed {len(actions)} actions")
    for action in actions:
        print(f"  - {action}")

cur.close()
conn.close()
