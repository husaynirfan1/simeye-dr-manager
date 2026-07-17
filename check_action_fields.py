"""
Check database for action-related fields and patterns
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

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("CHECKING FOR ACTION-RELATED COLUMNS")
print("=" * 80)

cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'dr_deficiency'
    AND (column_name ILIKE '%action%' OR column_name ILIKE '%corrective%')
    ORDER BY column_name;
""")

action_cols = cur.fetchall()
if action_cols:
    for col in action_cols:
        print(f"  {col[0]} - {col[1]}")
else:
    print("  No action-related columns found")

print("\n" + "=" * 80)
print("ALL COLUMN NAMES FOR REFERENCE")
print("=" * 80)

cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'dr_deficiency'
    ORDER BY column_name;
""")

all_cols = cur.fetchall()
for i, (col,) in enumerate(all_cols, 1):
    print(f"{i:2}. {col}")

print("\n" + "=" * 80)
print("SAMPLE DATA - FULL RECORD WITH ACTIONS")
print("=" * 80)

cur.execute("""
    SELECT *
    FROM dr_deficiency
    WHERE "ActionTaken" IS NOT NULL AND "ActionTaken" != ''
    LIMIT 1;
""")

row = cur.fetchone()
col_names = [desc[0] for desc in cur.description]

print(f"\nDeficiency #{row[1]} ({row[0]} - {row[2]}):\n")

for i, (name, value) in enumerate(zip(col_names, row)):
    if value is not None and str(value).strip():
        # Truncate long values
        val_str = str(value)
        if len(val_str) > 100:
            val_str = val_str[:97] + "..."
        print(f"  {name:40} : {val_str}")

print("\n" + "=" * 80)
print("MULTIPLE ACTION SAMPLES TO UNDERSTAND PATTERNS")
print("=" * 80)

cur.execute("""
    SELECT "DeficiencyNumber", "ActionTaken", "Status", "Type", "CategoryName",
           "Severity", "DeficiencyType"
    FROM dr_deficiency
    WHERE "ActionTaken" IS NOT NULL AND "ActionTaken" != ''
    ORDER BY "DeficiencyNumber" DESC
    LIMIT 10;
""")

rows = cur.fetchall()

for row in rows:
    def_num, action, status, type_val, category, severity, def_type = row
    print(f"\nDR #{def_num} | Status: {status} | Type: {type_val} | Severity: {severity}")
    print(f"ActionTaken: {action}")

print("\n" + "=" * 80)
print("CHECKING FOR RELATED TABLES")
print("=" * 80)

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND (table_name ILIKE '%action%' OR table_name ILIKE '%history%'
         OR table_name ILIKE '%log%' OR table_name ILIKE '%corrective%')
    ORDER BY table_name;
""")

tables = cur.fetchall()
for (table,) in tables:
    print(f"  Table: {table}")

    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table}'
        ORDER BY ordinal_position;
    """)

    cols = cur.fetchall()
    print(f"    Columns: {', '.join([f'{c[0]}({c[1]})' for c in cols[:8]])}")
    if len(cols) > 8:
        print(f"             ... and {len(cols) - 8} more")

cur.close()
conn.close()
