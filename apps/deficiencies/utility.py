from datetime import datetime

def normalize_date(value):
    if not value:
        return value

    if isinstance(value, str):
        # Try multiple date formats in order of likelihood for this application
        # Format list:
        # 1. YYYY-MM-DD - Django/ISO standard (check first to avoid unnecessary conversion)
        # 2. MM/DD/YYYY - US format (common in browser date pickers with US locale)
        # 3. DD/MM/YYYY - UK/Australian format (common in legacy data)
        # 4. DD-MM-YYYY - European format with dashes
        # 5. DD-MMM-YYYY - Legacy Oracle format (e.g., 07-JUN-2026)
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue

    # If already a date object or datetime, return the date portion
    if hasattr(value, 'date'):
        return value.date()

    return value