"""
DR Deficiency Management System - Web Server
Flask application with full CRUD operations and action tracking
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor, DictCursor
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect
import os
import re

# ==============================================================================
# CONFIGURATION
# ==============================================================================
DB_CONFIG = {
    "dbname": "maintenance_app",
    "user": "postgres",
    "password": "pwneaw139",
    "host": "172.24.2.46",
    "port": "5432"
}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
csrf = CSRFProtect(app)

# ==============================================================================
# DATABASE HELPERS
# ==============================================================================
def get_connection():
    """Get database connection with DictCursor for named columns"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def execute_query(query, params=None, fetch=True):
    """Execute query and return results"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params or ())

        if fetch:
            if query.strip().upper().startswith('SELECT'):
                result = cur.fetchall()
                return result
            else:
                conn.commit()
                return {'rowcount': cur.rowcount, 'success': True}
        else:
            conn.commit()
            return {'rowcount': cur.rowcount, 'success': True}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ==============================================================================
# ACTION FORMATTING HELPERS
# ==============================================================================
def format_action_entry(username, action_text):
    """
    Format action entry in the same style as existing data:
    [MMM DD YYYY HH:MMam/pm] [Username] [Action Description]
    """
    now = datetime.now()
    timestamp = now.strftime("%b %d %Y %I:%M%p")

    # Remove leading zero from hour for consistency with existing data
    timestamp = re.sub(r' 0(\d):', r'  \1:', timestamp)
    timestamp = re.sub(r'^0(\d):', r'\1:', timestamp)

    return f"[{timestamp}] [{username}] [{action_text}]"

def parse_action_taken(action_text):
    """
    Parse ActionTaken text into list of action dictionaries
    Format: [Date] [User] [Description]
    """
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

        # Parse the entry - format: [date] [user] [description]
        match = re.match(r'\[([^\]]+)\]\s+\[([^\]]+)\]\s+\[([^\]]+)\]', entry)
        if match:
            actions.append({
                'timestamp': match.group(1),
                'username': match.group(2),
                'description': match.group(3),
                'full': entry
            })

    return actions

def append_action(existing_actions, username, new_action):
    """
    Append new action to existing actions string
    """
    new_entry = format_action_entry(username, new_action)

    if existing_actions:
        # Check if it ends with a delimiter
        if not existing_actions.endswith(('&#x0D;', '\r\n', '\n')):
            new_entry = existing_actions + '&#x0D; ' + new_entry
        else:
            new_entry = existing_actions + new_entry
    else:
        new_entry = new_entry

    return new_entry

# ==============================================================================
# JOURNEY LOG HELPERS
# ==============================================================================
def format_journey_log_site(site_value, site_other):
    """Format site value for journey log display"""
    if site_value == 'Others':
        return site_other or ''
    return site_value

def format_journey_log_resource_type(type_value, type_other):
    """Format resource type value for journey log display"""
    if type_value == 'Others':
        return type_other or ''
    return type_value

def format_journey_log_session_type(type_value, type_other):
    """Format session type value for journey log display"""
    if type_value == 'Others':
        return type_other or ''
    return type_value

def format_journey_log_training_type(type_value, type_other):
    """Format training type value for journey log display"""
    if type_value == 'Others':
        return type_other or ''
    return type_value

# ==============================================================================
# ROUTES
# ==============================================================================
@app.route('/')
def index():
    """Dashboard page"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get recent deficiencies
        cur.execute("""
            SELECT "DeficiencyNumber" AS deficiencynumber, "SiteName" AS sitename,
                   "Resource" AS resource, "Issue_Description" AS issue_description,
                   "Status" AS status, "Severity" AS severity,
                   "RaisedByName" AS raisedbyname, "RaisedDate" AS raiseddate,
                   "DueDate" AS duedate, "CategoryName" AS categoryname,
                   "DeficiencyType" AS deficiencytype, "ActionTaken" AS actiontaken
            FROM dr_deficiency
            ORDER BY "DeficiencyNumber" DESC
            LIMIT 20;
        """)
        recent_deficiencies = cur.fetchall()

        # Get summary statistics
        cur.execute("""
            SELECT "Status" AS status, COUNT(*) AS count
            FROM dr_deficiency
            GROUP BY "Status"
            ORDER BY count DESC;
        """)
        status_counts = cur.fetchall()

        cur.execute("""
            SELECT "Severity" AS severity, COUNT(*) AS count
            FROM dr_deficiency
            GROUP BY "Severity"
            ORDER BY count DESC;
        """)
        severity_counts = cur.fetchall()

        return render_template('index.html',
                               recent_deficiencies=recent_deficiencies,
                               status_counts=status_counts,
                               severity_counts=severity_counts)
    finally:
        conn.close()

@app.route('/deficiencies')
def list_deficiencies():
    """List all deficiencies with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    # Get filter parameters
    status_filter = request.args.get('status', '')
    severity_filter = request.args.get('severity', '')
    search = request.args.get('search', '')
    site_filter = request.args.get('site', '')
    resource_filter = request.args.get('resource', '')

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Build query with filters
        where_clauses = []
        params = []

        if status_filter:
            where_clauses.append('"Status" = %s')
            params.append(status_filter)

        if severity_filter:
            where_clauses.append('"Severity" = %s')
            params.append(severity_filter)

        if site_filter:
            where_clauses.append('"SiteName" = %s')
            params.append(site_filter)

        if resource_filter:
            where_clauses.append('"Resource" = %s')
            params.append(resource_filter)

        if search:
            where_clauses.append('''
                CAST("DeficiencyNumber" AS VARCHAR) ILIKE %s
                OR "SiteName" ILIKE %s
                OR "Resource" ILIKE %s
                OR "Issue_Description" ILIKE %s
                OR "RaisedByName" ILIKE %s
            ''')
            search_term = f"%{search}%"
            params.extend([search_term] * 5)

        where_clause = ''
        if where_clauses:
            where_clause = 'WHERE ' + ' AND '.join(where_clauses)

        # Get total count
        count_query = f'SELECT COUNT(*) FROM dr_deficiency {where_clause}'
        cur.execute(count_query, params)
        total_count = cur.fetchone()['count']

        # Get paginated results
        query = f'''
            SELECT "DeficiencyNumber" AS deficiencynumber, "SiteName" AS sitename,
                   "Resource" AS resource, "Issue_Description" AS issue_description,
                   "Status" AS status, "Severity" AS severity,
                   "RaisedByName" AS raisedbyname, "RaisedDate" AS raiseddate,
                   "DueDate" AS duedate, "CategoryName" AS categoryname,
                   "DeficiencyType" AS deficiencytype, "AssigneeName" AS assigneename,
                   "AssigneeGroupName" AS assigneegroupname
            FROM dr_deficiency
            {where_clause}
            ORDER BY "DeficiencyNumber" DESC
            LIMIT %s OFFSET %s;
        '''
        cur.execute(query, params + [per_page, offset])
        deficiencies = cur.fetchall()

        # Get unique values for filters
        cur.execute('SELECT DISTINCT "Status" AS status FROM dr_deficiency ORDER BY "Status";')
        statuses = [r['status'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Severity" AS severity FROM dr_deficiency ORDER BY "Severity";')
        severities = [r['severity'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "SiteName" AS sitename FROM dr_deficiency ORDER BY "SiteName";')
        sites = [r['sitename'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Resource" AS resource FROM dr_deficiency ORDER BY "Resource";')
        resources = [r['resource'] for r in cur.fetchall()]

        total_pages = (total_count + per_page - 1) // per_page

        return render_template('deficiencies/list.html',
                               deficiencies=deficiencies,
                               statuses=statuses,
                               severities=severities,
                               sites=sites,
                               resources=resources,
                               page=page,
                               total_pages=total_pages,
                               total_count=total_count,
                               status_filter=status_filter,
                               severity_filter=severity_filter,
                               search=search,
                               site_filter=site_filter,
                               resource_filter=resource_filter)
    finally:
        conn.close()

@app.route('/deficiency/<int:deficiency_number>')
def view_deficiency(deficiency_number):
    """View single deficiency details"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
            SELECT
                "SiteName" AS sitename, "DeficiencyNumber" AS deficiencynumber,
                "Resource" AS resource, "Issue_Description" AS issue_description,
                "AssigneeName" AS assigneename, "AssigneeGroupName" AS assigneegroupname,
                "ActionTaken" AS actiontaken, "Type" AS type,
                "Severity" AS severity, "CategoryName" AS categoryname,
                "Status" AS status, "SubStatusName" AS substatusname,
                "RaisedByName" AS raisedbyname, "RaisedDate" AS raiseddate,
                "EnteredByName" AS enteredbyname, "EnteredDate" AS entereddate,
                "ClearedbyName" AS clearedbyname, "ClearedDate" AS cleareddate,
                "DueDate" AS duedate, "DownTime" AS downtime,
                "SPR" AS spr, "TrackingNumber" AS trackingnumber,
                "DashboardVisible" AS dashboardvisible, "DeficiencyType" AS deficiencytype,
                "Is_Restricted" AS is_restricted, "Is_Safety" AS is_safety,
                "Affects_Qualification" AS affects_qualification,
                "System" AS system, "SubSystem" AS subsystem,
                "InterruptMinutes" AS interruptminutes,
                "DeviceInterruptMinutes" AS deviceinterruptminutes,
                "UniqueDBIdentifier" AS uniquedbidentifier, "fldResourceId" AS fldresourceid,
                "fldRaisedById" AS fldraisedbyid, "fldEnteredById" AS fldenteredid,
                "Conversion" AS conversion, "Configuration" AS configuration,
                "fldRaisedDate" AS fldraiseddate, "fldDueDate" AS fldduedate,
                "fldLastActionTakenDate" AS fldlastactiontakendate,
                "NAADueDate" AS naaduedate, "OnOfferDate" AS onofferdate,
                "Restriction" AS restriction, "AlternateMethod" AS alternatemethod,
                "Customer" AS customer, "_RaisedDate" AS _raiseddate,
                "_EnteredDate" AS _entereddate, "_ClearedDate" AS _cleareddate,
                "_DueDate" AS _duedate
            FROM dr_deficiency
            WHERE "DeficiencyNumber" = %s;
        ''', (deficiency_number,))

        deficiency = cur.fetchone()

        if not deficiency:
            flash('Deficiency not found', 'error')
            return redirect(url_for('list_deficiencies'))

        # Parse actions for display
        actions = parse_action_taken(deficiency.get('actiontaken', ''))

        return render_template('deficiencies/view.html',
                               deficiency=deficiency,
                               actions=actions)
    finally:
        conn.close()

@app.route('/deficiency/new', methods=['GET', 'POST'])
@app.route('/deficiency/new/<int:reserved_dr>', methods=['GET', 'POST'])
def new_deficiency(reserved_dr=None):
    """Create new deficiency"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get the next DR number for display
        if reserved_dr:
            next_num = reserved_dr
        else:
            cur.execute('SELECT COALESCE(MAX("DeficiencyNumber"), 0) + 1 as next_num FROM dr_deficiency;')
            next_num = cur.fetchone()['next_num']

        if request.method == 'POST':
            data = request.form.to_dict()

            try:
                # Use the reserved number or get the next available
                dr_number = data.get('dr_number')
                if dr_number:
                    try:
                        dr_number = int(dr_number)
                    except ValueError:
                        dr_number = next_num
                else:
                    dr_number = next_num

                # Verify the DR number is still available
                cur.execute('SELECT COUNT(*) as cnt FROM dr_deficiency WHERE "DeficiencyNumber" = %s;', (dr_number,))
                if cur.fetchone()['cnt'] > 0:
                    # Number taken, get next available
                    cur.execute('SELECT COALESCE(MAX("DeficiencyNumber"), 0) + 1 as next_num FROM dr_deficiency;')
                    dr_number = cur.fetchone()['next_num']

                # Current date/time
                now = datetime.now()
                current_date = now.strftime('%d-%b-%Y').upper()
                current_timestamp = now
                fld_date = now.strftime('%m/%d/%Y')

                # Insert query with all columns
                insert_query = '''
                    INSERT INTO dr_deficiency (
                        "SiteName", "DeficiencyNumber", "Resource", "Issue_Description",
                        "AssigneeName", "AssigneeGroupName", "ActionTaken", "Type",
                        "Severity", "CategoryName", "Status", "SubStatusName",
                        "RaisedByName", "RaisedDate", "EnteredByName", "EnteredDate",
                        "ClearedbyName", "ClearedDate", "DueDate", "DownTime",
                        "SPR", "TrackingNumber", "DashboardVisible", "DeficiencyType",
                        "Is_Restricted", "Is_Safety", "Affects_Qualification",
                        "System", "SubSystem", "InterruptMinutes", "DeviceInterruptMinutes",
                        "UniqueDBIdentifier", "fldResourceId", "fldRaisedById",
                        "fldEnteredById", "Conversion", "Configuration",
                        "fldRaisedDate", "fldDueDate", "fldLastActionTakenDate",
                        "NAADueDate", "OnOfferDate", "Restriction", "AlternateMethod",
                        "Customer", "_RaisedDate", "_EnteredDate", "_ClearedDate", "_DueDate"
                    ) VALUES (
                        %s, %s, %s, %s,  -- SiteName, DeficiencyNumber, Resource, Issue_Description
                        %s, %s, %s, %s,  -- AssigneeName, AssigneeGroupName, ActionTaken, Type
                        %s, %s, %s, %s,  -- Severity, CategoryName, Status, SubStatusName
                        %s, %s, %s, %s,  -- RaisedByName, RaisedDate, EnteredByName, EnteredDate
                        %s, %s, %s, %s,  -- ClearedbyName, ClearedDate, DueDate, DownTime
                        %s, %s, %s, %s,  -- SPR, TrackingNumber, DashboardVisible, DeficiencyType
                        %s, %s, %s, %s,  -- Is_Restricted, Is_Safety, Affects_Qualification, System
                        %s, %s, %s, %s,  -- SubSystem, InterruptMinutes, DeviceInterruptMinutes, UniqueDBIdentifier
                        %s, %s, %s, %s,  -- fldResourceId, fldRaisedById, fldEnteredById, Conversion
                        %s, %s, %s, %s,  -- Configuration, fldRaisedDate, fldDueDate, fldLastActionTakenDate
                        %s, %s, %s, %s,  -- NAADueDate, OnOfferDate, Restriction, AlternateMethod
                        %s, %s, %s, %s, %s  -- Customer, _RaisedDate, _EnteredDate, _ClearedDate, _DueDate
                    )
                '''

                params = (
                    # Required fields from form
                    data.get('site_name', 'GEN'),
                    dr_number,
                    data.get('resource', 'GEN'),
                    data.get('issue_description', ''),

                    # Optional fields
                    data.get('assignee_name') or None,
                    data.get('assignee_group') or None,
                    None,  # ActionTaken - initially empty
                    data.get('type', 'Hardware'),

                    data.get('severity', 'C'),
                    data.get('category_name', 'General'),
                    data.get('status', 'OPEN'),
                    data.get('sub_status') or None,

                    data.get('raised_by', 'System'),
                    current_date,
                    data.get('entered_by', data.get('raised_by', 'System')),
                    current_date,

                    None, None,  # ClearedbyName, ClearedDate
                    data.get('due_date') or current_date,
                    int(data.get('downtime', 0)),

                    data.get('spr') or None,
                    data.get('tracking_number') or None,
                    data.get('dashboard_visible', 'true').lower() == 'true',
                    data.get('deficiency_type', 'Maintenance'),

                    data.get('is_restricted', 'false').lower() == 'true',
                    data.get('is_safety', 'false').lower() == 'true',
                    data.get('affects_qualification', 'false').lower() == 'true',

                    data.get('system') or None,
                    data.get('subsystem') or None,
                    int(data.get('interrupt_minutes', 0)),
                    int(data.get('device_interrupt_minutes', 0)),

                    dr_number,  # UniqueDBIdentifier
                    int(data.get('fld_resource_id', 1)),
                    int(data.get('fld_raised_id', 1)),
                    int(data.get('fld_entered_id', 1)),

                    data.get('conversion') or None,
                    data.get('configuration') or None,

                    fld_date,
                    fld_date,
                    None,  # fldLastActionTakenDate

                    data.get('naa_due_date') or None,
                    data.get('on_offer_date') or None,
                    data.get('restriction') or None,
                    data.get('alternate_method') or None,

                    data.get('customer', 'Internal'),
                    current_timestamp,
                    current_timestamp,
                    None,  # _ClearedDate
                    current_date
                )

                cur.execute(insert_query, params)
                conn.commit()

                flash(f'Deficiency #{dr_number} created successfully!', 'success')
                return redirect(url_for('view_deficiency', deficiency_number=dr_number))

            except Exception as e:
                conn.rollback()
                flash(f'Error creating deficiency: {str(e)}', 'error')

        # GET request - show form
        # Get lookup values
        cur.execute('SELECT DISTINCT "CategoryName" AS categoryname FROM dr_deficiency ORDER BY "CategoryName";')
        categories = [r['categoryname'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "System" AS system FROM dr_deficiency WHERE "System" IS NOT NULL ORDER BY "System";')
        systems = [r['system'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "SubSystem" AS subsystem FROM dr_deficiency WHERE "SubSystem" IS NOT NULL ORDER BY "SubSystem";')
        subsystems = [r['subsystem'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Type" AS type FROM dr_deficiency ORDER BY "Type";')
        types = [r['type'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Customer" AS customer FROM dr_deficiency ORDER BY "Customer";')
        customers = [r['customer'] for r in cur.fetchall()]

        # Site Names, Resources, Raised By Names
        cur.execute('SELECT DISTINCT "SiteName" AS sitename FROM dr_deficiency ORDER BY "SiteName";')
        site_names = [r['sitename'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Resource" AS resource FROM dr_deficiency ORDER BY "Resource";')
        resources = [r['resource'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "RaisedByName" AS raisedbyname FROM dr_deficiency ORDER BY "RaisedByName";')
        raised_by_names = [r['raisedbyname'] for r in cur.fetchall()]

        return render_template('deficiencies/new.html',
                               categories=categories,
                               systems=systems,
                               subsystems=subsystems,
                               types=types,
                               customers=customers,
                               next_dr_number=next_num,
                               site_names=site_names,
                               resources=resources,
                               raised_by_names=raised_by_names)
    finally:
        conn.close()

@app.route('/deficiency/<int:deficiency_number>/edit', methods=['GET', 'POST'])
def edit_deficiency(deficiency_number):
    """Edit existing deficiency"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if request.method == 'POST':
            data = request.form.to_dict()

            try:
                # Build dynamic update query
                update_fields = []
                params = []

                # Fields that can be updated
                editable_fields = [
                    'SiteName', 'Resource', 'Issue_Description', 'AssigneeName',
                    'AssigneeGroupName', 'Type', 'Severity', 'CategoryName',
                    'Status', 'SubStatusName', 'ClearedbyName', 'ClearedDate',
                    'DueDate', 'DownTime', 'SPR', 'TrackingNumber',
                    'DashboardVisible', 'DeficiencyType', 'Is_Restricted',
                    'Is_Safety', 'Affects_Qualification', 'System', 'SubSystem',
                    'InterruptMinutes', 'DeviceInterruptMinutes', 'Conversion',
                    'Configuration', 'fldLastActionTakenDate', 'NAADueDate',
                    'OnOfferDate', 'Restriction', 'AlternateMethod'
                ]

                for field in editable_fields:
                    form_key = field.lower()
                    if form_key in data:
                        update_fields.append(f'"{field}" = %s')

                        value = data[form_key]
                        if value == '':
                            value = None
                        elif form_key in ['is_restricted', 'is_safety', 'affects_qualification', 'dashboard_visible']:
                            value = value.lower() == 'true'
                        elif form_key in ['downtime', 'interrupt_minutes', 'device_interrupt_minutes']:
                            value = int(value) if value else 0

                        params.append(value)

                # Add ClearedDate timestamp if status changed to Cleared
                if data.get('status') == 'Cleared':
                    update_fields.append('"ClearedDate" = %s')
                    params.append(datetime.now().strftime('%d-%b-%Y').upper())

                    update_fields.append('"_ClearedDate" = %s')
                    params.append(datetime.now())

                params.append(deficiency_number)

                query = f'''
                    UPDATE dr_deficiency
                    SET {', '.join(update_fields)}
                    WHERE "DeficiencyNumber" = %s;
                '''

                cur.execute(query, params)
                conn.commit()

                flash(f'Deficiency #{deficiency_number} updated successfully!', 'success')
                return redirect(url_for('view_deficiency', deficiency_number=deficiency_number))

            except Exception as e:
                conn.rollback()
                flash(f'Error updating deficiency: {str(e)}', 'error')

        # GET request - show edit form
        cur.execute('''
            SELECT
                "SiteName" AS sitename, "DeficiencyNumber" AS deficiencynumber,
                "Resource" AS resource, "Issue_Description" AS issue_description,
                "AssigneeName" AS assigneename, "AssigneeGroupName" AS assigneegroupname,
                "ActionTaken" AS actiontaken, "Type" AS type,
                "Severity" AS severity, "CategoryName" AS categoryname,
                "Status" AS status, "SubStatusName" AS substatusname,
                "RaisedByName" AS raisedbyname, "RaisedDate" AS raiseddate,
                "EnteredByName" AS enteredbyname, "EnteredDate" AS entereddate,
                "ClearedbyName" AS clearedbyname, "ClearedDate" AS cleareddate,
                "DueDate" AS duedate, "DownTime" AS downtime,
                "SPR" AS spr, "TrackingNumber" AS trackingnumber,
                "DashboardVisible" AS dashboardvisible, "DeficiencyType" AS deficiencytype,
                "Is_Restricted" AS is_restricted, "Is_Safety" AS is_safety,
                "Affects_Qualification" AS affects_qualification,
                "System" AS system, "SubSystem" AS subsystem,
                "InterruptMinutes" AS interruptminutes,
                "DeviceInterruptMinutes" AS deviceinterruptminutes,
                "UniqueDBIdentifier" AS uniquedbidentifier, "fldResourceId" AS fldresourceid,
                "fldRaisedById" AS fldraisedbyid, "fldEnteredById" AS fldenteredid,
                "Conversion" AS conversion, "Configuration" AS configuration,
                "fldRaisedDate" AS fldraiseddate, "fldDueDate" AS fldduedate,
                "fldLastActionTakenDate" AS fldlastactiontakendate,
                "NAADueDate" AS naaduedate, "OnOfferDate" AS onofferdate,
                "Restriction" AS restriction, "AlternateMethod" AS alternatemethod,
                "Customer" AS customer
            FROM dr_deficiency
            WHERE "DeficiencyNumber" = %s;
        ''', (deficiency_number,))
        deficiency = cur.fetchone()

        if not deficiency:
            flash('Deficiency not found', 'error')
            return redirect(url_for('list_deficiencies'))

        # Get lookup values
        cur.execute('SELECT DISTINCT "CategoryName" AS categoryname FROM dr_deficiency ORDER BY "CategoryName";')
        categories = [r['categoryname'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "System" AS system FROM dr_deficiency WHERE "System" IS NOT NULL ORDER BY "System";')
        systems = [r['system'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "SubSystem" AS subsystem FROM dr_deficiency WHERE "SubSystem" IS NOT NULL ORDER BY "SubSystem";')
        subsystems = [r['subsystem'] for r in cur.fetchall()]

        cur.execute('SELECT DISTINCT "Type" AS type FROM dr_deficiency ORDER BY "Type";')
        types = [r['type'] for r in cur.fetchall()]

        return render_template('deficiencies/edit.html',
                               deficiency=deficiency,
                               categories=categories,
                               systems=systems,
                               subsystems=subsystems,
                               types=types)
    finally:
        conn.close()

@app.route('/deficiency/<int:deficiency_number>/action', methods=['POST'])
def add_action(deficiency_number):
    """Add action to deficiency"""
    data = request.form.to_dict()
    username = data.get('username', 'System')
    action_text = data.get('action_text', '')
    action_type = data.get('action_type', '')

    if not action_text:
        flash('Action text is required', 'error')
        return redirect(url_for('view_deficiency', deficiency_number=deficiency_number))

    # Prepend action type if specified
    if action_type:
        action_text = f'{action_type}: {action_text}'

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get current ActionTaken
        cur.execute('SELECT "ActionTaken" AS actiontaken, "fldLastActionTakenDate" AS fldlastactiontakendate FROM dr_deficiency WHERE "DeficiencyNumber" = %s;',
                    (deficiency_number,))
        result = cur.fetchone()

        if not result:
            flash('Deficiency not found', 'error')
            return redirect(url_for('list_deficiencies'))

        current_actions = result['actiontaken'] or ''
        new_actions = append_action(current_actions, username, action_text)

        # Update
        now = datetime.now()
        fld_date = now.strftime('%m/%d/%Y')

        cur.execute('''
            UPDATE dr_deficiency
            SET "ActionTaken" = %s, "fldLastActionTakenDate" = %s
            WHERE "DeficiencyNumber" = %s;
        ''', (new_actions, fld_date, deficiency_number))

        conn.commit()
        flash('Action added successfully!', 'success')

        return redirect(url_for('view_deficiency', deficiency_number=deficiency_number))
    finally:
        conn.close()

@app.route('/deficiency/<int:deficiency_number>/delete', methods=['POST'])
def delete_deficiency(deficiency_number):
    """Delete deficiency"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM dr_deficiency WHERE "DeficiencyNumber" = %s;', (deficiency_number,))
        conn.commit()

        flash(f'Deficiency #{deficiency_number} deleted successfully!', 'success')
        return redirect(url_for('list_deficiencies'))
    finally:
        conn.close()

# ==============================================================================
# ==============================================================================
# API ROUTES
# ==============================================================================
@app.route('/api/search')
def api_search():
    """API for autocomplete/search"""
    search = request.args.get('q', '')
    field = request.args.get('field', 'all')

    if not search:
        return jsonify([])

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        search_term = f"%{search}%"

        if field == 'deficiency_number':
            cur.execute('''
                SELECT DISTINCT "DeficiencyNumber" AS deficiencynumber
                FROM dr_deficiency
                WHERE CAST("DeficiencyNumber" AS VARCHAR) ILIKE %s
                ORDER BY "DeficiencyNumber" DESC
                LIMIT 20;
            ''', (search_term,))
        elif field == 'site':
            cur.execute('''
                SELECT DISTINCT "SiteName" AS sitename
                FROM dr_deficiency
                WHERE "SiteName" ILIKE %s
                ORDER BY "SiteName"
                LIMIT 20;
            ''', (search_term,))
        elif field == 'resource':
            cur.execute('''
                SELECT DISTINCT "Resource" AS resource
                FROM dr_deficiency
                WHERE "Resource" ILIKE %s
                ORDER BY "Resource"
                LIMIT 20;
            ''', (search_term,))
        else:
            cur.execute('''
                SELECT "DeficiencyNumber" AS deficiencynumber, "SiteName" AS sitename,
                       "Resource" AS resource, "Issue_Description" AS issue_description,
                       "Status" AS status
                FROM dr_deficiency
                WHERE CAST("DeficiencyNumber" AS VARCHAR) ILIKE %s
                   OR "SiteName" ILIKE %s
                   OR "Resource" ILIKE %s
                   OR "Issue_Description" ILIKE %s
                ORDER BY "DeficiencyNumber" DESC
                LIMIT 20;
            ''', (search_term, search_term, search_term, search_term))

        results = cur.fetchall()
        return jsonify(results)
    finally:
        conn.close()

@app.route('/api/deficiency/<int:deficiency_number>')
def api_deficiency(deficiency_number):
    """API for single deficiency"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM dr_deficiency WHERE "DeficiencyNumber" = %s;', (deficiency_number,))
        result = cur.fetchone()

        if result:
            result['actions'] = parse_action_taken(result.get('actiontaken', ''))
            return jsonify(result)
        else:
            return jsonify({'error': 'Not found'}), 404
    finally:
        conn.close()

# ==============================================================================
# JOURNEY LOG SYSTEM
# ==============================================================================

def init_journey_log_tables():
    """Initialize journey log tables if they don't exist"""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Journey logs main table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dr_journey_log (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                log_date DATE,
                site VARCHAR(50),
                resource_type VARCHAR(50),
                resource VARCHAR(100),
                session_type VARCHAR(50),
                training_type VARCHAR(50),
                report_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Add schedule_slot_id column if it doesn't exist
        try:
            cur.execute('ALTER TABLE dr_journey_log ADD COLUMN schedule_slot_id INTEGER;')
        except:
            pass  # Column already exists

        # Journey log crew members table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dr_journey_log_crew (
                id SERIAL PRIMARY KEY,
                journey_log_id INTEGER REFERENCES dr_journey_log(id) ON DELETE CASCADE,
                crew_name VARCHAR(255),
                license_number VARCHAR(100),
                crew_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Journey log linked DRs table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dr_journey_log_dr (
                id SERIAL PRIMARY KEY,
                journey_log_id INTEGER REFERENCES dr_journey_log(id) ON DELETE CASCADE,
                deficiency_number INTEGER,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()
        print("Journey log tables initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing journey log tables: {e}")
    finally:
        conn.close()

@app.route('/journey-logs')
def list_journey_logs():
    """List all journey logs"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT jl.*,
                   COUNT(DISTINCT jld.deficiency_number) as linked_dr_count
            FROM dr_journey_log jl
            LEFT JOIN dr_journey_log_dr jld ON jl.id = jld.journey_log_id
            GROUP BY jl.id
            ORDER BY jl.log_date DESC, jl.created_at DESC;
        ''')
        journey_logs = cur.fetchall()
        return render_template('journey_logs/list.html', journey_logs=journey_logs)
    finally:
        conn.close()

@app.route('/journey-log/new')
def new_journey_log():
    """Create new journey log form"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=DictCursor)

        # Get unique values from deficiencies for dropdowns
        cur.execute('SELECT DISTINCT "SiteName" FROM dr_deficiency ORDER BY "SiteName";')
        sites = [row[0] for row in cur.fetchall() if row[0]]

        cur.execute('SELECT DISTINCT "Resource" FROM dr_deficiency ORDER BY "Resource";')
        resources = [row[0] for row in cur.fetchall() if row[0]]

        return render_template('journey_logs/new.html',
                             sites=sites,
                             resources=resources)
    finally:
        conn.close()

@app.route('/journey-log/create', methods=['POST'])
def create_journey_log():
    """Create a new journey log"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get form data
        customer_name = request.form.get('customer_name', '')
        log_date = request.form.get('log_date')
        site = request.form.get('site', '')
        resource_type = request.form.get('resource_type', '')
        resource = request.form.get('resource', '')
        session_type = request.form.get('session_type', '')
        training_type = request.form.get('training_type', '')
        report_by = request.form.get('report_by', '')
        schedule_slot_id = request.form.get('schedule_slot_id')

        # Insert journey log
        cur.execute('''
            INSERT INTO dr_journey_log
            (customer_name, log_date, site, resource_type, resource, session_type, training_type, report_by, schedule_slot_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        ''', (customer_name, log_date, site, resource_type, resource,
              session_type, training_type, report_by, schedule_slot_id))

        journey_log_id = cur.fetchone()['id']

        # Link journey log to schedule slot if provided
        if schedule_slot_id:
            cur.execute('''
                UPDATE dr_schedule_sessions
                SET journey_log_id = %s
                WHERE id = %s;
            ''', (journey_log_id, schedule_slot_id))

        # Insert crew members
        crew_names = request.form.getlist('crew_name[]')
        license_numbers = request.form.getlist('license_number[]')
        crew_types = request.form.getlist('crew_type[]')

        for i, name in enumerate(crew_names):
            if name.strip():
                license_num = license_numbers[i] if i < len(license_numbers) else ''
                crew_type = crew_types[i] if i < len(crew_types) else ''

                cur.execute('''
                    INSERT INTO dr_journey_log_crew
                    (journey_log_id, crew_name, license_number, crew_type)
                    VALUES (%s, %s, %s, %s);
                ''', (journey_log_id, name, license_num, crew_type))

        # Link DRs if provided
        linked_drs = request.form.getlist('linked_dr_numbers[]')
        for dr_num in linked_drs:
            if dr_num.strip().isdigit():
                cur.execute('''
                    INSERT INTO dr_journey_log_dr
                    (journey_log_id, deficiency_number)
                    VALUES (%s, %s);
                ''', (journey_log_id, int(dr_num)))

        conn.commit()
        flash('Journey Log created successfully!', 'success')
        return redirect(url_for('view_journey_log', journey_log_id=journey_log_id))

    except Exception as e:
        conn.rollback()
        flash(f'Error creating journey log: {e}', 'error')
        return redirect(url_for('new_journey_log'))
    finally:
        conn.close()

@app.route('/journey-log/<int:journey_log_id>')
def view_journey_log(journey_log_id):
    """View a journey log with linked DRs"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get journey log
        cur.execute('SELECT * FROM dr_journey_log WHERE id = %s;', (journey_log_id,))
        journey_log = cur.fetchone()

        if not journey_log:
            flash('Journey Log not found', 'error')
            return redirect(url_for('list_journey_logs'))

        # Get crew members
        cur.execute('SELECT * FROM dr_journey_log_crew WHERE journey_log_id = %s ORDER BY id;', (journey_log_id,))
        crew = cur.fetchall()

        # Get linked DRs with details
        cur.execute('''
            SELECT jld.deficiency_number,
                   d."Issue_Description",
                   d."Status",
                   d."Severity",
                   d."SiteName",
                   d."Resource"
            FROM dr_journey_log_dr jld
            LEFT JOIN dr_deficiency d ON jld.deficiency_number = d."DeficiencyNumber"
            WHERE jld.journey_log_id = %s
            ORDER BY jld.deficiency_number;
        ''', (journey_log_id,))
        linked_drs = cur.fetchall()

        # Get all DRs for potential linking
        cur.execute('''
            SELECT "DeficiencyNumber", "Issue_Description", "Status"
            FROM dr_deficiency
            ORDER BY "DeficiencyNumber" DESC
            LIMIT 100;
        ''')
        all_drs = cur.fetchall()

        return render_template('journey_logs/view.html',
                             journey_log=journey_log,
                             crew=crew,
                             linked_drs=linked_drs,
                             all_drs=all_drs)
    finally:
        conn.close()

@app.route('/journey-log/<int:journey_log_id>/generate')
def generate_journey_log(journey_log_id):
    """Generate journey log for printing"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get journey log
        cur.execute('SELECT * FROM dr_journey_log WHERE id = %s;', (journey_log_id,))
        journey_log = cur.fetchone()

        if not journey_log:
            flash('Journey Log not found', 'error')
            return redirect(url_for('list_journey_logs'))

        # Mark schedule slot as completed if linked
        if journey_log.get('schedule_slot_id'):
            cur.execute('''
                UPDATE dr_schedule_sessions
                SET is_completed = TRUE
                WHERE id = %s;
            ''', (journey_log['schedule_slot_id'],))
            conn.commit()

        # Get crew members
        cur.execute('SELECT * FROM dr_journey_log_crew WHERE journey_log_id = %s ORDER BY id;', (journey_log_id,))
        crew = cur.fetchall()

        # Get linked DRs
        cur.execute('''
            SELECT jld.deficiency_number,
                   d."Issue_Description",
                   d."Status",
                   d."Severity"
            FROM dr_journey_log_dr jld
            LEFT JOIN dr_deficiency d ON jld.deficiency_number = d."DeficiencyNumber"
            WHERE jld.journey_log_id = %s
            ORDER BY jld.deficiency_number;
        ''', (journey_log_id,))
        linked_drs = cur.fetchall()

        return render_template('journey_logs/generate.html',
                             journey_log=journey_log,
                             crew=crew,
                             linked_drs=linked_drs)
    finally:
        conn.close()

@app.route('/journey-log/<int:journey_log_id>/link-dr', methods=['POST'])
def link_dr_to_journey_log(journey_log_id):
    """Link DRs to a journey log"""
    conn = get_connection()
    try:
        dr_numbers = request.form.getlist('dr_numbers[]')

        for dr_num in dr_numbers:
            if dr_num.strip().isdigit():
                cur = conn.cursor()
                # Check if already linked
                cur.execute('''
                    SELECT COUNT(*) FROM dr_journey_log_dr
                    WHERE journey_log_id = %s AND deficiency_number = %s;
                ''', (journey_log_id, int(dr_num)))

                if cur.fetchone()[0] == 0:
                    cur.execute('''
                        INSERT INTO dr_journey_log_dr (journey_log_id, deficiency_number)
                        VALUES (%s, %s);
                    ''', (journey_log_id, int(dr_num)))

        conn.commit()
        flash('Deficiencies linked successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error linking deficiencies: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('view_journey_log', journey_log_id=journey_log_id))

@app.route('/journey-log/<int:journey_log_id>/unlink-dr/<int:deficiency_number>', methods=['POST'])
def unlink_dr_from_journey_log(journey_log_id, deficiency_number):
    """Unlink a DR from a journey log"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            DELETE FROM dr_journey_log_dr
            WHERE journey_log_id = %s AND deficiency_number = %s;
        ''', (journey_log_id, deficiency_number))
        conn.commit()
        flash('Deficiency unlinked successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error unlinking deficiency: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('view_journey_log', journey_log_id=journey_log_id))

@app.route('/journey-log/<int:journey_log_id>/delete', methods=['POST'])
def delete_journey_log(journey_log_id):
    """Delete a journey log"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM dr_journey_log WHERE id = %s;', (journey_log_id,))
        conn.commit()
        flash('Journey Log deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting journey log: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('list_journey_logs'))

# ==============================================================================
# SCHEDULE SYSTEM
# ==============================================================================

import requests
from datetime import date, timedelta

# Schedule API Configuration
SCHEDULE_API_URL = "http://172.24.2.46:5000/api/schedule"

def init_schedule_tables():
    """Initialize schedule tables if they don't exist"""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Schedule sessions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS dr_schedule_sessions (
                id SERIAL PRIMARY KEY,
                session_date DATE NOT NULL,
                time_slot VARCHAR(20) NOT NULL,
                end_time VARCHAR(20),
                resource VARCHAR(50) DEFAULT 'AW139',
                customer VARCHAR(255),
                is_booked BOOLEAN DEFAULT FALSE,
                is_completed BOOLEAN DEFAULT FALSE,
                journey_log_id INTEGER REFERENCES dr_journey_log(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_date, time_slot, resource)
            );
        ''')

        # Add new columns if table already exists
        try:
            cur.execute('ALTER TABLE dr_schedule_sessions ADD COLUMN end_time VARCHAR(20);')
        except:
            pass
        try:
            cur.execute('ALTER TABLE dr_schedule_sessions ADD COLUMN customer VARCHAR(255);')
        except:
            pass

        conn.commit()
        print("Schedule tables initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing schedule tables: {e}")
    finally:
        conn.close()

def fetch_schedule_from_api(start_date, end_date):
    """
    Fetch schedule data from external API.
    API returns: [{"d": "24-Jun-2026", "s": "09:00", "e": "10:00", "c": "Customer Name"}]
    """
    try:
        response = requests.get(SCHEDULE_API_URL, timeout=10)
        if response.status_code == 200:
            api_data = response.json()

            # Convert API format to our internal format
            # API: {"d": "24-Jun-2026", "s": "09:00", "e": "10:00", "c": "Customer"}
            # Our format: {"date": "2026-06-24", "time_slot": "09:00", "customer": "Customer Name"}
            schedule_sessions = []
            for session in api_data:
                # Parse date from API format (24-Jun-2026) to YYYY-MM-DD
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(session.get('d', ''), '%d-%b-%Y')
                    date_str = date_obj.strftime('%Y-%m-%d')
                except:
                    continue

                schedule_sessions.append({
                    'date': date_str,
                    'time_slot': session.get('s', ''),  # Start time as slot identifier
                    'end_time': session.get('e', ''),
                    'customer': session.get('c', ''),
                    'resource': 'AW139'
                })

            return schedule_sessions
        else:
            print(f"API returned status {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

def generate_time_slots():
    """Generate standard time slots for the schedule"""
    slots = []
    # Morning slots (8 AM - 12 PM)
    for hour in range(8, 13):
        slots.append(f"{hour:02d}:00")
        slots.append(f"{hour:02d}:30")

    # Afternoon slots (1 PM - 5 PM)
    for hour in range(13, 18):
        slots.append(f"{hour:02d}:00")
        slots.append(f"{hour:02d}:30")

    return slots

@app.route('/schedule')
def schedule_view():
    """View schedule for journey log creation"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get date range (next 7 days)
        today = date.today()
        dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

        # Get time slots
        time_slots = generate_time_slots()

        # Fetch existing sessions from database with customer info
        # Build IN clause for dates
        date_placeholders = ','.join(['%s'] * len(dates))
        cur.execute(f'''
            SELECT session_date, time_slot, end_time, customer, is_booked, is_completed, journey_log_id
            FROM dr_schedule_sessions
            WHERE session_date::text IN ({date_placeholders})
            AND resource = 'AW139'
            ORDER BY session_date, time_slot;
        ''', dates)

        existing_sessions = {}
        for row in cur.fetchall():
            key = f"{row['session_date']}_{row['time_slot']}"
            existing_sessions[key] = {
                'is_booked': row['is_booked'],
                'is_completed': row['is_completed'],
                'journey_log_id': row['journey_log_id'],
                'customer': row.get('customer', ''),
                'end_time': row.get('end_time', '')
            }

        # Fetch from external API and store/update in database
        api_sessions = fetch_schedule_from_api(dates[0], dates[-1])

        for session in api_sessions:
            key = f"{session.get('date')}_{session.get('time_slot')}"

            # Check if session exists in database
            if key not in existing_sessions:
                # Insert new session from API
                try:
                    cur.execute('''
                        INSERT INTO dr_schedule_sessions
                        (session_date, time_slot, end_time, resource, customer, is_booked)
                        VALUES (%s, %s, %s, 'AW139', %s, TRUE)
                        ON CONFLICT (session_date, time_slot, resource)
                        DO UPDATE SET customer = EXCLUDED.customer, end_time = EXCLUDED.end_time;
                    ''', (session.get('date'), session.get('time_slot'),
                          session.get('end_time'), session.get('customer', '')))

                    existing_sessions[key] = {
                        'is_booked': True,
                        'is_completed': False,
                        'journey_log_id': None,
                        'customer': session.get('customer', ''),
                        'end_time': session.get('end_time', '')
                    }
                except Exception as e:
                    print(f"Error inserting session: {e}")
            else:
                # Update existing session with API data (customer might have changed)
                if session.get('customer') and session.get('customer') != existing_sessions[key].get('customer'):
                    try:
                        cur.execute('''
                            UPDATE dr_schedule_sessions
                            SET customer = %s, end_time = %s
                            WHERE session_date = %s AND time_slot = %s AND resource = 'AW139';
                        ''', (session.get('customer'), session.get('end_time'),
                              session.get('date'), session.get('time_slot')))
                        existing_sessions[key]['customer'] = session.get('customer')
                        existing_sessions[key]['end_time'] = session.get('end_time')
                    except Exception as e:
                        print(f"Error updating session: {e}")

        conn.commit()

        return render_template('schedule/index.html',
                             dates=dates,
                             time_slots=time_slots,
                             sessions=existing_sessions)
    finally:
        conn.close()

@app.route('/schedule/book', methods=['POST'])
def book_schedule_slot():
    """Book a schedule slot and redirect to journey log creation"""
    session_date = request.form.get('session_date')
    time_slot = request.form.get('time_slot')

    if not session_date or not time_slot:
        flash('Invalid schedule slot', 'error')
        return redirect(url_for('schedule_view'))

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Check if slot exists and is available
        cur.execute('''
            SELECT id, is_booked, is_completed, journey_log_id
            FROM dr_schedule_sessions
            WHERE session_date = %s AND time_slot = %s AND resource = 'AW139';
        ''', (session_date, time_slot))

        slot = cur.fetchone()

        if slot and slot['is_completed']:
            flash('This session has already been completed', 'error')
            return redirect(url_for('schedule_view'))

        # If slot doesn't exist, create it
        if not slot:
            cur.execute('''
                INSERT INTO dr_schedule_sessions (session_date, time_slot, resource, is_booked)
                VALUES (%s, %s, 'AW139', TRUE)
                RETURNING id;
            ''', (session_date, time_slot))
            slot_id = cur.fetchone()['id']
        else:
            # Mark as booked
            cur.execute('''
                UPDATE dr_schedule_sessions
                SET is_booked = TRUE
                WHERE id = %s;
            ''', (slot['id'],))
            slot_id = slot['id']

        conn.commit()

        # Fetch customer name for pre-filling
        cur.execute('''
            SELECT customer, end_time
            FROM dr_schedule_sessions
            WHERE id = %s;
        ''', (slot_id,))
        slot_info = cur.fetchone()

        # Redirect to journey log creation with pre-filled data
        return redirect(url_for('new_journey_log_with_schedule',
                              slot_id=slot_id,
                              session_date=session_date,
                              time_slot=time_slot,
                              customer_name=slot_info.get('customer', '') if slot_info else ''))

    except Exception as e:
        conn.rollback()
        flash(f'Error booking slot: {e}', 'error')
        return redirect(url_for('schedule_view'))
    finally:
        conn.close()

@app.route('/journey-log/new/schedule')
def new_journey_log_with_schedule():
    """Create journey log from schedule slot"""
    slot_id = request.args.get('slot_id')
    session_date = request.args.get('session_date')
    time_slot = request.args.get('time_slot')
    customer_name = request.args.get('customer_name', '')

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=DictCursor)

        # Get unique values from deficiencies for dropdowns
        cur.execute('SELECT DISTINCT "SiteName" FROM dr_deficiency ORDER BY "SiteName";')
        sites = [row[0] for row in cur.fetchall() if row[0]]

        cur.execute('SELECT DISTINCT "Resource" FROM dr_deficiency ORDER BY "Resource";')
        resources = [row[0] for row in cur.fetchall() if row[0]]

        return render_template('journey_logs/new.html',
                             sites=sites,
                             resources=resources,
                             slot_id=slot_id,
                             session_date=session_date,
                             time_slot=time_slot,
                             customer_name=customer_name)
    finally:
        conn.close()

@app.route('/api/schedule/refresh')
def refresh_schedule():
    """API endpoint to refresh schedule data from external API"""
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    if not start_date or not end_date:
        return jsonify({'error': 'Missing date range'}), 400

    sessions = fetch_schedule_from_api(start_date, end_date)

    # Update database with API data
    conn = get_connection()
    try:
        cur = conn.cursor()
        for session in sessions:
            cur.execute('''
                INSERT INTO dr_schedule_sessions (session_date, time_slot, resource)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_date, time_slot, resource)
                DO UPDATE SET updated_at = CURRENT_TIMESTAMP;
            ''', (session.get('date'), session.get('time_slot'), 'AW139'))
        conn.commit()
        return jsonify({'success': True, 'sessions': len(sessions)})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Initialize schedule tables on startup
init_schedule_tables()

# ==============================================================================
# ERROR HANDLERS
# ==============================================================================
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == '__main__':
    # Initialize journey log tables on first startup
    init_journey_log_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
