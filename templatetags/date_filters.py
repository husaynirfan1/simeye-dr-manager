"""
Custom template filters for date formatting and markdown rendering.
"""
from django import template
from datetime import datetime
from django.utils.safestring import mark_safe
import markdown

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


@register.filter
def render_markdown(value):
    """
    Render text as markdown with support for links, formatting, etc.
    Safe for use in templates - sanitizes HTML output.
    """
    if not value:
        return ''

    try:
        # Convert markdown to HTML with sanitization
        md = markdown.Markdown(extensions=['nl2br', 'fenced_code'], safe_mode=True)
        html = md.convert(value)
        return mark_safe(html)
    except Exception:
        # If markdown processing fails, return original text with line breaks
        return mark_safe(value.replace('\n', '<br>'))
