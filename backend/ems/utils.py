from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from .models import MeasurementFuelsondingFinal


def float_hours_to_pseudo(hours):
    total_minutes = round(float(hours) * 60)
    hour_value = total_minutes // 60
    minute_value = total_minutes % 60
    return float(f"{hour_value}.{minute_value:02d}")


def pseudo_hours_to_hhmm(pseudo_value):
    if not pseudo_value:
        return "0:00"
    try:
        pseudo_value = float(pseudo_value)
        hour_value = int(pseudo_value)
        minute_value = round((pseudo_value - hour_value) * 100)
        if minute_value >= 60:
            hour_value += minute_value // 60
            minute_value %= 60
        return f"{hour_value}:{minute_value:02d}"
    except (TypeError, ValueError):
        return "0:00"


def add_hours_to_pseudo(pseudo_value, hour_difference):
    pseudo_value = float(pseudo_value or 0.0)
    pseudo_hours = int(pseudo_value)
    pseudo_minutes = round((pseudo_value - pseudo_hours) * 100)
    total_minutes = (
        pseudo_hours * 60 + pseudo_minutes + round(float(hour_difference) * 60)
    )
    new_hours = total_minutes // 60
    new_minutes = total_minutes % 60
    return float(f"{new_hours}.{new_minutes:02d}")


def get_due_status(due_date):
    if not due_date:
        return "-", "white"

    if isinstance(due_date, datetime):
        due_date = due_date.date()
    elif isinstance(due_date, str):
        try:
            due_date = datetime.strptime(due_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return "-", "white"

    today = date.today()
    if due_date < today:
        return "Routine Due", "#FF9999"

    difference_in_months = (due_date - today).days / 30
    if difference_in_months <= 3:
        color = "#f7e687"
    elif difference_in_months <= 6:
        color = "orange"
    else:
        color = "white"

    delta = relativedelta(due_date, today)
    parts = []
    if delta.years > 0:
        parts.append(f"{delta.years}Y")
    if delta.months > 0:
        parts.append(f"{delta.months}M")
    if delta.days > 0:
        parts.append(f"{delta.days}D")

    if not parts:
        return "Due Today", "#f7e687"
    return f"Due In {' '.join(parts)}", color


def generate_routine_dart_number(department, maintenance_type, last_entry):
    department_codes = {
        "ELECTRICAL": "L",
        "ENGINEERING": "E",
        "EXCLUSIVE": "X",
        "HULL": "H",
    }
    department_code = department_codes.get(department.upper(), "X")
    prefix = f"M-{department_code}-"
    next_number = int(last_entry) + 1 if int(last_entry) >= 50000 else 50000
    return f"{prefix}{next_number}", next_number


def calculate_volume_weight(mm_value, tank_type=None, tank_name=None):
    queryset = MeasurementFuelsondingFinal.objects.all()
    if tank_type:
        queryset = queryset.filter(tank_type=tank_type)
    if tank_name:
        queryset = queryset.filter(tank_name=tank_name)

    try:
        mm_value = float(mm_value)
    except (TypeError, ValueError):
        return 0, 0, False, None, None

    base_mm = int(mm_value // 100) * 100
    remainder = mm_value - base_mm
    base_row = queryset.filter(mm=base_mm).first()
    if not base_row:
        return 0, 0, False, None, None

    base_volume = float(base_row.volume or 0)
    base_tone = float(base_row.tone or 0)
    if remainder == 0:
        return base_volume, base_tone, False, None, None

    lower_bracket = int(remainder // 10) * 10
    upper_bracket = lower_bracket + 10
    if lower_bracket == 0:
        lower_volume = base_volume
        lower_tone = base_tone
    else:
        lower_value = getattr(base_row, f"field_{lower_bracket}mm", None)
        lower_volume = float(lower_value) if lower_value is not None else base_volume
        lower_tone = float(lower_value) if lower_value is not None else base_tone

    if upper_bracket == 100:
        next_row = queryset.filter(mm=base_mm + 100).first()
        upper_volume = (
            float(next_row.volume or lower_volume) if next_row else lower_volume
        )
        upper_tone = float(next_row.tone or lower_tone) if next_row else lower_tone
    else:
        upper_value = getattr(base_row, f"field_{upper_bracket}mm", None)
        upper_volume = float(upper_value) if upper_value is not None else lower_volume
        upper_tone = float(upper_value) if upper_value is not None else lower_tone

    factor = (remainder - lower_bracket) / 10
    interpolated_volume = lower_volume + factor * (upper_volume - lower_volume)
    interpolated_weight = lower_tone + factor * (upper_tone - lower_tone)
    return (
        round(interpolated_volume, 2),
        round(interpolated_weight, 2),
        True,
        base_mm,
        remainder,
    )
