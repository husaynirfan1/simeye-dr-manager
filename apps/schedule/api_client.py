"""
External API client for schedule data with fault tolerance.
"""
import requests
from datetime import datetime
from django.conf import settings


class ScheduleAPIError(Exception):
    """Custom exception for schedule API errors"""
    pass


def fetch_schedule_from_api(start_date, end_date):
    """
    Fetch schedule data from external API.
    API returns: [{"d": "24-Jun-2026", "s": "09:00", "e": "10:00", "c": "Customer Name"}]
    Returns list of dicts with date, time_slot, end_time, customer.
    """
    api_url = getattr(settings, 'SCHEDULE_API_URL', '')
    if not api_url:
        raise ScheduleAPIError("SCHEDULE_API_URL not configured")

    try:
        response = requests.get(
            api_url,
            timeout=getattr(settings, 'SCHEDULE_API_TIMEOUT', 10)
        )

        if response.status_code == 200:
            api_data = response.json()

            # Convert API format to our internal format
            schedule_sessions = []
            for session in api_data:
                try:
                    # Parse date from API format (24-Jun-2026) to YYYY-MM-DD
                    date_obj = datetime.strptime(session.get('d', ''), '%d-%b-%Y')
                    date_str = date_obj.strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    continue

                schedule_sessions.append({
                    'date': date_str,
                    'time_slot': session.get('s', ''),
                    'end_time': session.get('e', ''),
                    'customer': session.get('c', ''),
                    'resource': 'AW139'
                })

            return schedule_sessions
        else:
            raise ScheduleAPIError(f"API returned status {response.status_code}")

    except requests.RequestException as e:
        raise ScheduleAPIError(f"Failed to connect to schedule API: {str(e)}")


def sync_schedule_to_db(start_date, end_date):
    """
    Sync schedule data from API to database.
    Returns tuple: (success, message, session_count)
    """
    try:
        sessions = fetch_schedule_from_api(start_date, end_date)

        from .models import ScheduleSession

        count = 0
        for session in sessions:
            # Update or create session in database
            obj, created = ScheduleSession.objects.update_or_create(
                session_date=session['date'],
                time_slot=session['time_slot'],
                resource=session['resource'],
                defaults={
                    'end_time': session.get('end_time', ''),
                    'customer': session.get('customer', ''),
                    'is_booked': bool(session.get('customer'))
                }
            )
            if created or obj:
                count += 1

        return True, f"Synced {count} sessions", count

    except ScheduleAPIError as e:
        return False, str(e), 0
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", 0


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
