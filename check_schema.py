"""
Temporary script to check database schema for web app development
"""
import psycopg2
from psycopg2 import sql

DB_CONFIG = {
    "dbname": "maintenance_app",
    "user": "postgres",
    "password": "pwneaw139",
    "host": "172.24.2.46",
    "port": "5432"
}

def check_schema():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get columns for dr_deficiency table
    print("=" * 80)
    print("DR_DEFICIENCY TABLE SCHEMA")
    print("=" * 80)

    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'dr_deficiency'
        ORDER BY ordinal_position;
    """)

    columns = cur.fetchall()
    for col in columns:
        print(f"{col[0]:40} {col[1]:20} NULL: {col[2]:5} DEFAULT: {col[3]}")

    print("\n" + "=" * 80)
    print("SAMPLE DATA (First 2 records)")
    print("=" * 80)

    cur.execute("""
        SELECT * FROM dr_deficiency LIMIT 2;
    """)
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    for row in rows:
        print("\nRecord:")
        for i, val in enumerate(row):
            print(f"  {col_names[i]}: {val}")

    print("\n" + "=" * 80)
    print("CHECKING FOR ACTION/HISTORY TABLES")
    print("=" * 80)

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE '%action%' OR table_name LIKE '%history%' OR table_name LIKE '%log%'
        ORDER BY table_name;
    """)

    tables = cur.fetchall()
    for table in tables:
        print(f"Found table: {table[0]}")

        cur.execute(sql.SQL("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = {} ORDER BY ordinal_position").format(sql.Literal(table[0])))
        cols = cur.fetchall()
        print("  Columns:", ", ".join([f"{c[0]}({c[1]})" for c in cols[:10]]))
        print()

    print("\n" + "=" * 80)
    print("ALL TABLES IN DATABASE")
    print("=" * 80)

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)

    all_tables = cur.fetchall()
    for table in all_tables:
        print(f"  - {table[0]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
