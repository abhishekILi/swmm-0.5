import re

from dart.models import InitiateDart

READINESS_GOOD_THRESHOLD = 80
READINESS_AVERAGE_THRESHOLD = 50
HEALTH_WARNING_THRESHOLD = 80
HEALTH_CRITICAL_THRESHOLD = 50


def calculate_percentage_change(current_value, previous_value):
    if previous_value:
        return int(((current_value - previous_value) / previous_value) * 100)
    if current_value:
        return 100
    return 0


def get_readiness_status(value):
    if value >= READINESS_GOOD_THRESHOLD:
        return "Good"
    if value >= READINESS_AVERAGE_THRESHOLD:
        return "Average"
    return "Critical"


def get_health_status(score):
    if score < HEALTH_CRITICAL_THRESHOLD:
        return "critical"
    if score < HEALTH_WARNING_THRESHOLD:
        return "warning"
    return "healthy"


def generate_dart_number(department_name, *args, **kwargs):
    dept_upper = department_name.upper() if department_name else ""
    if "ELECTRICAL" in dept_upper:
        department_code = "L"
    elif "ENGINEERING" in dept_upper or "MARINE" in dept_upper:
        department_code = "E"
    elif "EXCLUSIVE" in dept_upper:
        department_code = "X"
    else:
        department_code = department_name[0].upper() if department_name else "X"
    prefix = f"D-{department_code}-"

    # Filter all records in the entire database starting with the department's prefix
    # to prevent duplicates and handle legacy data inconsistencies mathematically.
    dart_list = InitiateDart.objects.filter(dart_number__startswith=prefix)

    max_val = -1
    for entry in dart_list:
        dn = entry.dart_number
        if dn:
            match = re.search(r"\d+$", dn)
            if match:
                val = int(match.group())
                if val > max_val:
                    max_val = val

    if max_val != -1:
        next_number = max_val + 1
    else:
        next_number = 50001

    return f"{prefix}{next_number}"
