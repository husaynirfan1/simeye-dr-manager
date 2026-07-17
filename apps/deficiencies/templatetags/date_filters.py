"""
Custom template filters for date formatting.
"""
from django import template
from datetime import datetime

register = template.Library()


@register.filter
def format_date_ddmmyyyy(value):
    """
    Format date value to DD-MM-YYYY format for display.
    Handles both date objects and string dates.
    """
    if value is None:
        return '-'

    try:
        if isinstance(value, str):
            # If it's already a string, try to parse and format
            # Try YYYY-MM-DD format first
            try:
                date_obj = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                # Try DD-MMM-YYYY format (database format)
                try:
                    date_obj = datetime.strptime(value, '%d-%b-%Y')
                except ValueError:
                    # Try DD-MM-YYYY format (already in display format)
                    try:
                        date_obj = datetime.strptime(value, '%d-%m-%Y')
                    except ValueError:
                        return value  # Return as-is if parsing fails
            return date_obj.strftime('%d-%m-%Y')
        else:
            # It's a date/datetime object
            return value.strftime('%d-%m-%Y')
    except (ValueError, AttributeError, TypeError):
        return str(value) if value else '-'


@register.filter
def format_datetime_ddmmyyyy(value):
    """
    Format datetime value to DD-MM-YYYY HH:MM format for display.
    """
    if value is None:
        return '-'

    try:
        if isinstance(value, str):
            # Try to parse various datetime formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d-%b-%Y %H:%M', '%d-%m-%Y %H:%M']:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    return date_obj.strftime('%d-%m-%Y %H:%M')
                except ValueError:
                    continue
            return value  # Return as-is if parsing fails
        else:
            # It's a datetime object
            return value.strftime('%d-%m-%Y %H:%M')
    except (ValueError, AttributeError, TypeError):
        return str(value) if value else '-'
