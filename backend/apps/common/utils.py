import secrets

from django.utils import timezone


def generate_code(prefix):
    """Ex : RES-261015-A1B2C3"""
    return f"{prefix}-{timezone.now():%y%m%d}-{secrets.token_hex(3).upper()}"


def format_ar(value):
    """20000 -> '20 000 Ar' (format unique, arrondi à l'ariary)."""
    return f"{int(round(float(value))):,}".replace(',', ' ') + ' Ar'
