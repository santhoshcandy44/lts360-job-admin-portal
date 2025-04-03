import datetime
from datetime import timedelta

from django import template

register = template.Library()

@register.filter
def add_days(value, days):
    """Adds a given number of days to a date string."""
    try:
        # Convert string to date object
        date_obj = datetime.datetime.strptime(value, "%Y-%m-%d").date()
        # Add days
        new_date = date_obj + datetime.timedelta(days=int(days))
        return new_date.strftime("%Y-%m-%d")  # Convert back to string
    except Exception:
        return value  # Return original value if an error occurs