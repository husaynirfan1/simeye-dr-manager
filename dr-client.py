import psycopg2
from psycopg2 import sql
import os
import sys
from datetime import datetime

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================
DB_CONFIG = {
    "dbname": "maintenance_app",
    "user": "postgres",
    "password": "pwneaw139",
    "host": "172.24.2.46", # e.g., "192.168.1.100" or "100.x.x.x"
    "port": "5432"
}

# ==============================================================================
# UI HELPERS
# ==============================================================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    print("\n+" + "-"*78 + "+")
    print("|" + title.center(78) + "|")
    print("+" + "-"*78 + "+")

def print_table(headers, rows):
    if not rows:
        print("\n  [ NO RECORDS FOUND ]\n")
        return

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Create format string
    row_format = "| " + " | ".join([f"{{:<{w}}}" for w in col_widths]) + " |"
    separator = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"

    print("\n" + separator)
    print(row_format.format(*headers))
    print(separator)
    for row in rows:
        print(row_format.format(*[str(c) if c is not None else "" for c in row]))
    print(separator + "\n")

# ==============================================================================
# DATABASE OPERATIONS (CRUD)
# ==============================================================================
def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"\n[ERROR] Unable to connect to database: {e}")
        sys.exit(1)

def read_deficiencies():
    print_header("READ: LATEST DEFICIENCIES")
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Added "Issue_Description" to the query
        query = """
            SELECT "DeficiencyNumber", "SiteName", "Resource", "Issue_Description", "Status", "Severity", "RaisedByName"
            FROM dr_deficiency
            ORDER BY "DeficiencyNumber" DESC
            LIMIT 10;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        # Truncate long descriptions to keep the terminal table clean
        display_rows = []
        for row in rows:
            row_list = list(row)
            desc = str(row_list[3]) if row_list[3] else ""
            if len(desc) > 35:
                row_list[3] = desc[:32] + "..."
            display_rows.append(row_list)

        headers = ["Def. Num", "Site", "Resource", "Description", "Status", "Severity", "Raised By"]
        print_table(headers, display_rows)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        cur.close()
        conn.close()


def search_deficiencies():
    print_header("SEARCH: DEFICIENCY DATABASE")
    print(" Search across ID, Site, Resource, Issue Description, or Submitter.")
    search_term = input(" Enter keyword: ").strip()

    if not search_term:
        print("\n[WARNING] Search term cannot be empty.")
        return

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Added "Issue_Description" here as well
        query = """
            SELECT "DeficiencyNumber", "SiteName", "Resource", "Issue_Description", "Status", "Severity", "RaisedByName"
            FROM dr_deficiency
            WHERE "DeficiencyNumber"::text ILIKE %s
               OR "SiteName" ILIKE %s
               OR "Resource" ILIKE %s
               OR "Issue_Description" ILIKE %s
               OR "RaisedByName" ILIKE %s
            ORDER BY "DeficiencyNumber" DESC
            LIMIT 20;
        """
        
        like_term = f"%{search_term}%"
        cur.execute(query, (like_term, like_term, like_term, like_term, like_term))
        rows = cur.fetchall()
        
        # Apply the same truncation logic for search results
        display_rows = []
        for row in rows:
            row_list = list(row)
            desc = str(row_list[3]) if row_list[3] else ""
            if len(desc) > 35:
                row_list[3] = desc[:32] + "..."
            display_rows.append(row_list)
        
        print(f"\n  [ SEARCH RESULTS FOR: '{search_term}' ]")
        headers = ["Def. Num", "Site", "Resource", "Description", "Status", "Severity", "Raised By"]
        print_table(headers, display_rows)
        
    except Exception as e:
        print(f"\n[ERROR] Search execution failed: {e}")
    finally:
        cur.close()
        conn.close()

def create_deficiency():
    print_header("CREATE: NEW DEFICIENCY")
    print("Enter the details below. For this terminal client, core fields are requested.")
    print("Other required schema fields will be auto-populated with defaults.")
    
    site_name = input(" Site Name (max 3 chars)  : ")[:3]
    def_num = input(" Deficiency Number (int)  : ")
    resource = input(" Resource (max 5 chars)   : ")[:5]
    issue_desc = input(" Issue Description        : ")
    severity = input(" Severity (max 3 chars)   : ")[:3]
    raised_by = input(" Raised By Name           : ")

    # Current timestamp strings for required date fields
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_timestamp = datetime.now()

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Note: The schema has many NOT NULL constraints. 
        # This query populates the requested inputs and adds strict defaults for the rest.
        query = """
            INSERT INTO dr_deficiency (
                "SiteName", "DeficiencyNumber", "Resource", "Issue_Description", "Type", 
                "Severity", "CategoryName", "Status", "RaisedByName", "RaisedDate", 
                "EnteredByName", "EnteredDate", "DueDate", "DashboardVisible", "DeficiencyType", 
                "Is_Restricted", "Is_Safety", "Affects_Qualification", "UniqueDBIdentifier", 
                "fldResourceId", "fldRaisedById", "fldEnteredById", "fldRaisedDate", "fldDueDate", 
                "Customer", "_RaisedDate", "_EnteredDate", "_DueDate"
            ) VALUES (
                %s, %s, %s, %s, 'Standard', 
                %s, 'General', 'OPEN', %s, %s, 
                'System', %s, %s, TRUE, 'Operational', 
                FALSE, FALSE, FALSE, %s, 
                1, 1, 1, %s, %s, 
                'Internal', %s, %s, %s
            )
        """
        cur.execute(query, (
            site_name, int(def_num), resource, issue_desc, severity, raised_by, current_date, 
            current_date, current_date, int(def_num), current_date, current_date, 
            current_timestamp, current_timestamp, current_date
        ))
        conn.commit()
        print("\n[SUCCESS] Record inserted successfully.")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Failed to insert record: {e}")
    finally:
        cur.close()
        conn.close()

def update_deficiency():
    print_header("UPDATE: DEFICIENCY STATUS")
    def_num = input(" Enter Deficiency Number to update: ")
    new_status = input(" Enter New Status (e.g., CLOSED)  : ")

    conn = get_connection()
    cur = conn.cursor()
    
    try:
        query = """
            UPDATE dr_deficiency
            SET "Status" = %s
            WHERE "DeficiencyNumber" = %s
        """
        cur.execute(query, (new_status, int(def_num)))
        if cur.rowcount > 0:
            conn.commit()
            print(f"\n[SUCCESS] Deficiency {def_num} updated to {new_status}.")
        else:
            print(f"\n[WARNING] Deficiency {def_num} not found.")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Failed to update record: {e}")
    finally:
        cur.close()
        conn.close()

def delete_deficiency():
    print_header("DELETE: REMOVE DEFICIENCY")
    def_num = input(" Enter Deficiency Number to delete: ")
    confirm = input(f" Are you sure you want to delete {def_num}? (Y/N): ")

    if confirm.upper() == 'Y':
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            query = 'DELETE FROM dr_deficiency WHERE "DeficiencyNumber" = %s'
            cur.execute(query, (int(def_num),))
            if cur.rowcount > 0:
                conn.commit()
                print(f"\n[SUCCESS] Deficiency {def_num} deleted.")
            else:
                print(f"\n[WARNING] Deficiency {def_num} not found.")
        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] Failed to delete record: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("\n[INFO] Deletion cancelled.")

# ==============================================================================
# MAIN APPLICATION LOOP
# ==============================================================================
def main():
    while True:
        clear_screen()
        print_header("DR DEFICIENCY MANAGEMENT SYSTEM")
        print("  [1] View Recent Deficiencies")
        print("  [2] Search Deficiencies")
        print("  [3] Add New Deficiency")
        print("  [4] Update Deficiency Status")
        print("  [5] Delete Deficiency")
        print("  [0] Exit Application")
        print("+" + "-"*78 + "+")
        
        choice = input("\n Select an option: ")

        if choice == '1':
            clear_screen()
            read_deficiencies()
            input(" Press Enter to return to menu...")
        elif choice == '2':
            clear_screen()
            search_deficiencies()
            input(" Press Enter to return to menu...")
        elif choice == '3':
            clear_screen()
            create_deficiency()
            input(" Press Enter to return to menu...")
        elif choice == '4':
            clear_screen()
            update_deficiency()
            input(" Press Enter to return to menu...")
        elif choice == '5':
            clear_screen()
            delete_deficiency()
            input(" Press Enter to return to menu...")
        elif choice == '0':
            clear_screen()
            print("\n  Closing connection. Goodbye.\n")
            sys.exit(0)
        else:
            input("\n [INVALID] Please select a valid option. Press Enter to try again.")

if __name__ == "__main__":
    main()
