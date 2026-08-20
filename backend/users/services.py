from datetime import date, datetime, timedelta

from dart.models import InitiateDart
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from ems.models import AddRoutineDetails, PlannedRoutineDescription, RoutineDescription
from master.models import (
    CoMessage,
    MemberDetail,
    OrderDuty,
    ShipRole,
    ShipRoleImage,
    UpdateEntry,
)
from obs.models import Issue, PostSurvey, Receive

from .models import CustomUserProfile


def ordinal(number):
    if number is None:
        return ""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def file_url(file_field, request=None):
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def profile_name(profile):
    if not profile:
        return ""
    return f"{profile.firstname or ''} {profile.lastname or ''}".strip()


def profile_payload(profile, request=None):
    if not profile:
        return None
    return {
        "id": profile.id,
        "firstname": profile.firstname,
        "lastname": profile.lastname,
        "name": profile_name(profile),
        "personal_number": profile.personal_number,
        "designation": profile.designation
        or (
            profile.designation_master.designation_name
            if profile.designation_master_id
            else ""
        ),
        "rank": profile.rank.name if profile.rank_id else "",
        "department": profile.department_id,
        "department_name": profile.department.name if profile.department_id else "",
        "ship": profile.ship_id,
        "ship_name": profile.ship.name if profile.ship_id else "",
        "date_of_birth": profile.date_of_birth,
        "marriage_date": profile.marriage_date,
    }


def order_duty_payload(item, request=None):
    return {
        "id": item.id,
        "filename": item.filename,
        "uploaded_at": item.uploaded_at,
        "source": item.source,
        "pdf_path": file_url(item.pdf_path, request),
        "roster_name": item.roster_name,
        "from_date": item.from_date,
        "to_date": item.to_date,
        "description": item.description,
        "date": item.date,
        "officer_details": item.officer_details,
        "routine_details": item.routine_details,
    }


def update_payload(item, request=None):
    uploaded_date = timezone.localtime(item.uploaded_date).date()
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    return {
        "id": item.id,
        "uploaded_date": item.uploaded_date,
        "from_date": item.from_date,
        "to_date": item.to_date,
        "update_text": item.update_text,
        "event_file": file_url(item.event_file, request),
        "is_new": uploaded_date in {today, yesterday},
    }


def member_payload(item, request=None):
    return {
        "id": item.id,
        "name": item.name,
        "designation": item.designation,
        "rank": item.rank,
        "image_path": file_url(item.image_path, request),
        "uploaded_date": item.uploaded_date,
    }


def ship_role_payload(item, request=None):
    if not item:
        return None
    return {
        "id": item.id,
        "role_title": item.role_title,
        "current_text": item.current_text,
        "uploaded_date": item.uploaded_date,
    }


def ship_role_image_payload(item, request=None):
    return {
        "id": item.id,
        "ship": item.ship_id,
        "image": file_url(item.image, request),
    }


def upcoming_events_payload():
    today = date.today()
    seven_days_later = today + timedelta(days=7)
    events = []
    profiles = CustomUserProfile.objects.select_related(
        "rank", "designation_master"
    ).all()

    for profile in profiles:
        _append_birthday_event(events, profile, today, seven_days_later)
        _append_anniversary_event(events, profile, today, seven_days_later)

    events.sort(key=lambda item: item["event_date"])
    return events


def _next_date_for_month_day(value, today):
    try:
        current_year_date = date(today.year, value.month, value.day)
    except ValueError:
        current_year_date = date(today.year, 3, 1)

    if current_year_date >= today:
        return current_year_date

    if value.month == 2 and value.day == 29:
        return date(today.year + 1, 3, 1)
    return date(today.year + 1, value.month, value.day)


def _append_birthday_event(events, profile, today, seven_days_later):
    if not profile.date_of_birth:
        return
    next_date = _next_date_for_month_day(profile.date_of_birth, today)
    if today <= next_date <= seven_days_later:
        age = next_date.year - profile.date_of_birth.year
        events.append(
            {
                "type": "birthday",
                "name": profile_name(profile),
                "personal_number": profile.personal_number,
                "designation": profile.designation
                or (
                    profile.designation_master.designation_name
                    if profile.designation_master_id
                    else ""
                ),
                "event_date": next_date,
                "age": age,
                "years": None,
                "event_label": f"{ordinal(age)} Birthday",
            }
        )


def _append_anniversary_event(events, profile, today, seven_days_later):
    if not profile.marriage_date:
        return
    next_date = _next_date_for_month_day(profile.marriage_date, today)
    if today <= next_date <= seven_days_later:
        years = next_date.year - profile.marriage_date.year
        events.append(
            {
                "type": "anniversary",
                "name": profile_name(profile),
                "personal_number": profile.personal_number,
                "designation": profile.designation
                or (
                    profile.designation_master.designation_name
                    if profile.designation_master_id
                    else ""
                ),
                "event_date": next_date,
                "age": None,
                "years": years,
                "event_label": f"{ordinal(years)} Anniversary",
            }
        )


def build_home_dashboard_payload(request):
    current_profile = getattr(request.user, "user_profile", None)
    ship_data = ShipRole.objects.order_by("-uploaded_date").first()
    ship_images = ShipRoleImage.objects.select_related("ship").all()

    return {
        "current_user_profile": profile_payload(current_profile, request),
        "members_dropdown": [
            profile_payload(profile, request)
            for profile in CustomUserProfile.objects.select_related(
                "rank", "designation_master", "department", "ship"
            ).order_by("firstname", "lastname")
        ],
        "ship_data": ship_role_payload(ship_data, request),
        "ship_images": [
            ship_role_image_payload(image, request) for image in ship_images
        ],
        "image_paths": [
            file_url(image.image, request) for image in ship_images if image.image
        ],
        "daily_orders": [
            order_duty_payload(item, request)
            for item in OrderDuty.objects.filter(source="daily order").order_by(
                "-uploaded_at"
            )[:5]
        ],
        "duty_roster": [
            order_duty_payload(item, request)
            for item in OrderDuty.objects.filter(source="duty roster").order_by(
                "-uploaded_at"
            )
        ],
        "running_updates": [
            update_payload(item, request)
            for item in UpdateEntry.objects.order_by("-uploaded_date")
        ],
        "members": [
            member_payload(item, request) for item in MemberDetail.objects.all()
        ],
        "officers": [
            profile_payload(profile, request)
            for profile in CustomUserProfile.objects.select_related(
                "rank", "designation_master", "department", "ship"
            )
            .filter(user_active=True)
            .order_by("firstname")
        ],
        "routines": ["Normal Routine", "Make and Mend Routine", "Sunday Routine"],
        "command_messages_count": CoMessage.objects.filter(
            valid_till_date__gte=date.today()
        ).count(),
        "upcoming_events": upcoming_events_payload(),
        "count": CustomUserProfile.objects.filter(is_role=False).count(),
    }


def _profile_department(profile):
    return profile.department if profile and profile.department_id else None


def _total_maintops(profile):
    department = _profile_department(profile)
    routines = AddRoutineDetails.objects.exclude(
        routine_name__name__icontains="refit"
    ).exclude(routine_category="ALTERNATE PERIODIC")
    if department:
        routines = routines.filter(equipment_name__section__department=department)

    planned_ids = PlannedRoutineDescription.objects.filter(
        is_deleted=False
    ).values_list("routine_description_id_id", flat=True)
    routine_descriptions = RoutineDescription.objects.filter(
        equipment_name=OuterRef("equipment_name"),
        routine_name=OuterRef("routine_name"),
    ).exclude(id__in=planned_ids)
    return (
        routines.annotate(has_routine_description=Exists(routine_descriptions))
        .filter(has_routine_description=True)
        .count()
    )


def _total_planned_routines(profile):
    planned_ids = (
        PlannedRoutineDescription.objects.filter(is_deleted=False)
        .values_list("routine_description_id_id", flat=True)
        .distinct()
    )
    add_routine_ids = (
        RoutineDescription.objects.filter(id__in=planned_ids)
        .values_list("add_routine_details_id", flat=True)
        .distinct()
    )
    routines = AddRoutineDetails.objects.filter(id__in=add_routine_ids)
    if profile and profile.access_level != "0" and profile.department_id:
        routines = routines.filter(
            equipment_name__section__department=profile.department
        )
    return routines.count()


def _open_darts(profile):
    queryset = InitiateDart.objects.filter(
        is_closed=False,
        is_ra_initiate=False,
        is_ra_draft=False,
        is_dl_draft=False,
    )
    if profile and profile.department_id:
        queryset = queryset.filter(department_id=profile.department)
    return queryset


def _due_for_receipt(profile):
    queryset = Receive.objects.filter(quantity_toreceive__gt=0)
    if profile and profile.department_id:
        queryset = queryset.filter(
            spare__equipment_class__spare_class__department=profile.department
        )
    return queryset.count()


def _pts_survey_pending(profile):
    queryset = PostSurvey.objects.filter(
        survey_number__in=["PTS", "OPDEM", "ONETIME APPROVAL"],
        has_pts=True,
    )
    if profile and profile.department_id:
        queryset = queryset.filter(
            spare__equipment_class__spare_class__department=profile.department
        )
    return queryset.count()


def _issued_spares_count(profile):
    queryset = Issue.objects.filter(is_deleted=False)
    if profile and profile.department_id:
        queryset = queryset.filter(
            spare__equipment_class__spare_class__department=profile.department
        )
    return queryset.count()


def _dart_trend(profile):
    today = date.today()
    first_day = today.replace(day=1)
    months = []
    for month_offset in range(11, -1, -1):
        year = first_day.year
        month = first_day.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(date(year, month, 1))

    data = []
    for month in months:
        base_filter = {
            "dart_date__year": month.year,
            "dart_date__month": month.month,
        }
        open_queryset = InitiateDart.objects.filter(**base_filter, is_closed=False)
        closed_queryset = InitiateDart.objects.filter(**base_filter, is_closed=True)
        if profile and profile.department_id:
            open_queryset = open_queryset.filter(department_id=profile.department)
            closed_queryset = closed_queryset.filter(department_id=profile.department)
        data.append(
            {
                "month": month.strftime("%b"),
                "open_dart": open_queryset.count(),
                "closed_dart": closed_queryset.count(),
            }
        )
    return data


def build_home_dashboard_kpi_payload(request):
    profile = getattr(request.user, "user_profile", None)
    return {
        "total_maintops": _total_maintops(profile),
        "total_outstanding_darts": _open_darts(profile).count(),
        "total_planned_routines": _total_planned_routines(profile),
        "due_for_receipt": _due_for_receipt(profile),
        "pts_survey_pending": _pts_survey_pending(profile),
        "total_issued_spares": _issued_spares_count(profile),
        "data1chart": _dart_trend(profile),
        "count": CustomUserProfile.objects.filter(is_role=False).count(),
    }


def parse_date(value, field_name):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name} format. Use YYYY-MM-DD.") from exc


def search_history_payload(query_params, request=None):
    data_type = query_params.get("type")
    if data_type == "daily_order":
        return _search_daily_orders(query_params, request)
    if data_type == "duty_roster":
        return _search_duty_roster(query_params, request)
    raise ValueError("Invalid type parameter.")


def _search_daily_orders(query_params, request=None):
    query = Q(source="daily order")
    start_date = parse_date(query_params.get("start_date"), "start_date")
    end_date = parse_date(query_params.get("end_date"), "end_date")
    selected_date = parse_date(query_params.get("date"), "date")

    if start_date and end_date:
        query &= Q(from_date__gte=start_date, to_date__lte=end_date)
    elif selected_date:
        query &= Q(from_date=selected_date, to_date=selected_date)

    records = OrderDuty.objects.filter(query).order_by("-uploaded_at")
    data = [order_duty_payload(record, request) for record in records]
    return {"success": True, "data": data, "count": len(data)}


def _search_duty_roster(query_params, request=None):
    query = Q(source="duty roster")
    roster_date = parse_date(query_params.get("roster_date"), "roster_date")
    roster_name = str(query_params.get("roster_name", "")).strip()

    if roster_date:
        query &= Q(date=roster_date)
    if roster_name:
        query &= Q(roster_name__icontains=roster_name)

    records = OrderDuty.objects.filter(query).order_by("-uploaded_at")
    data = [order_duty_payload(record, request) for record in records]
    return {"success": True, "data": data, "count": len(data)}


def get_history_payload(query_params, request=None):
    selected_date = parse_date(query_params.get("date"), "date")
    data_type = query_params.get("type")
    if not selected_date or not data_type:
        raise ValueError("Missing parameters.")

    if data_type == "daily_order":
        records = OrderDuty.objects.filter(
            source="daily order", uploaded_at__date=selected_date
        )
    elif data_type == "duty_roster":
        records = OrderDuty.objects.filter(
            source="duty roster", uploaded_at__date=selected_date
        )
    else:
        raise ValueError("Invalid type parameter.")

    data = [order_duty_payload(record, request) for record in records]
    return {
        "success": True,
        "data": data,
        "selected_date": selected_date.strftime("%d %b %Y"),
    }
