from collections import defaultdict
from datetime import date, timedelta

from django.utils import timezone

from .models import InitiateDart, InitiateRADL


class DartDashboardService:
    PERIOD_DAYS = {
        "6M": 180,
        "1Y": 365,
        "2Y": 730,
    }

    ACTIVITY_DAYS = {
        "today": 1,
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
    }

    @classmethod
    def get_dashboard(
        cls,
        period="ALL",
        department=None,
        activity_period="month",
    ):
        darts = InitiateDart.objects.select_related(
            "symptom_code",
            "severity_code",
            "remark_code",
            "require_assistance_for_code",
            "department_id",
            "equipment_ship",
            "equipment_ems",
        )

        period_start = cls._get_period_start(period)

        if period_start:
            darts = darts.filter(
                dart_date__gte=period_start,
            )

        if department:
            darts = darts.filter(
                department_id__isnull=False,
            )
            darts = [dart for dart in darts if cls._department_name(dart) == department]

        if isinstance(darts, list):
            dashboard_darts = darts
            open_darts = [dart for dart in darts if not dart.is_closed]
        else:
            dashboard_darts = darts
            open_darts = darts.open()

        return {
            "cards": cls._cards(dashboard_darts, open_darts),
            "alerts": cls._alerts(open_darts),
            "quick_actions": cls._quick_actions(),
            "open_darts_by_department": cls._open_darts_by_department(open_darts),
            "open_darts_by_severity": cls._open_darts_by_severity(open_darts),
            "dart_lifecycle_trend": cls._lifecycle_trend(dashboard_darts),
            "dart_load_by_department": cls._dart_load_by_department(open_darts),
            "recent_activity": cls._recent_activity(
                activity_period=activity_period,
                department=department,
            ),
        }

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    @classmethod
    def _cards(cls, darts, open_darts):
        severity_counts = defaultdict(int)

        for dart in open_darts:
            severity = cls._severity_name(dart)

            if severity:
                severity_counts[cls._normalize(severity)] += 1

        opdef_count = sum(
            count
            for severity, count in severity_counts.items()
            if severity
            in {
                "opdef",
                "opdef (sta)",
            }
        )

        guarantee_alerts = sum(1 for dart in open_darts if dart.is_guarantee_defect)

        active_ra_count = (
            InitiateRADL.objects.filter(
                is_active=True,
            )
            .exclude(
                status="DELETED",
            )
            .count()
        )

        return {
            "total_active_defects": {
                "value": len(open_darts),
                "available": True,
            },
            "opdef_opdef_sta": {
                "value": opdef_count,
                "available": True,
            },
            "ra_with_fmu_yard": {
                "value": active_ra_count,
                "available": True,
                "note": (
                    "Total active RA/DL records. "
                    "FMU/Yard split requires the FMU business field."
                ),
            },
            "guarantee_exposure_alerts": {
                "value": guarantee_alerts,
                "available": True,
            },
            "certificates_issued": {
                "value": None,
                "available": False,
                "note": (
                    "CertificateTypeMaster contains certificate types, "
                    "not issued certificates."
                ),
            },
        }

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    @classmethod
    def _alerts(cls, open_darts):
        darts = list(open_darts)

        darts.sort(
            key=lambda dart: (
                dart.dart_date or date.min,
                dart.id,
            ),
            reverse=True,
        )

        alerts = []

        for dart in darts[:10]:
            severity = cls._severity_name(dart)

            if dart.is_guarantee_defect:
                alert_type = "Guarantee"
            elif severity and "opdef" in severity.lower():
                alert_type = "DART"
            else:
                alert_type = "DART"

            alerts.append(
                {
                    "id": dart.id,
                    "dart_number": dart.dart_number,
                    "title": (f"{dart.dart_number or 'DART'} raised"),
                    "equipment": cls._equipment_name(dart),
                    "severity": severity,
                    "department": cls._department_name(dart),
                    "type": alert_type,
                    "status": "In Progress",
                    "date": dart.dart_date,
                }
            )

        return alerts

    # ------------------------------------------------------------------
    # Quick actions
    # ------------------------------------------------------------------

    @staticmethod
    def _quick_actions():
        return [
            {
                "key": "add_defect",
                "label": "Add Defect / DART",
                "action": "ADD_DEFECT",
            },
            {
                "key": "approval_ra_status",
                "label": "View Approval / RA Status",
                "action": "VIEW_RA_STATUS",
            },
            {
                "key": "guarantee",
                "label": "Add / Extend Guarantee",
                "action": "ADD_GUARANTEE",
            },
        ]

    # ------------------------------------------------------------------
    # Open DARTs by department
    # ------------------------------------------------------------------

    @classmethod
    def _open_darts_by_department(cls, darts):
        counts = defaultdict(int)

        for dart in darts:
            department = cls._department_name(dart)

            if department:
                counts[department] += 1

        return [
            {
                "department": department,
                "count": count,
            }
            for department, count in sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    # ------------------------------------------------------------------
    # Open DARTs by severity
    # ------------------------------------------------------------------

    @classmethod
    def _open_darts_by_severity(cls, darts):
        counts = defaultdict(int)

        for dart in darts:
            severity = cls._severity_name(dart)

            if severity:
                counts[severity] += 1

        return [
            {
                "severity": severity,
                "count": count,
            }
            for severity, count in sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    # ------------------------------------------------------------------
    # DART lifecycle trend
    # ------------------------------------------------------------------

    @classmethod
    def _lifecycle_trend(cls, darts):
        today = timezone.now().date()

        months = {}

        for offset in range(5, -1, -1):
            month_date = cls._subtract_months(today, offset)

            key = month_date.strftime("%Y-%m")

            months[key] = {
                "month": month_date.strftime("%b"),
                "raised": 0,
                "closed": 0,
                "reopened": 0,
            }

        for dart in darts:
            if not dart.dart_date:
                continue

            key = dart.dart_date.strftime("%Y-%m")

            if key not in months:
                continue

            months[key]["raised"] += 1

            if dart.is_closed:
                months[key]["closed"] += 1

            # The supplied model does not contain a dedicated
            # reopened_date/reopened flag.
            #
            # Therefore this cannot be reliably calculated.
            months[key]["reopened"] = 0

        return list(months.values())

    # ------------------------------------------------------------------
    # DART load
    # ------------------------------------------------------------------

    @classmethod
    def _dart_load_by_department(cls, darts):
        return cls._open_darts_by_department(darts)

    # ------------------------------------------------------------------
    # Recent activity
    # ------------------------------------------------------------------

    @classmethod
    def _recent_activity(
        cls,
        activity_period,
        department=None,
    ):
        days = cls.ACTIVITY_DAYS.get(
            activity_period.lower(),
            cls.ACTIVITY_DAYS["month"],
        )

        start_date = timezone.now().date() - timedelta(days=days)

        queryset = InitiateDart.objects.select_related(
            "severity_code",
            "department_id",
            "equipment_ship",
            "equipment_ems",
        ).filter(
            dart_date__gte=start_date,
        )

        queryset = queryset.order_by(
            "-dart_date",
            "-id",
        )

        result = []

        for dart in queryset:
            dart_department = cls._department_name(dart)

            if department and dart_department != department:
                continue

            result.append(
                {
                    "id": dart.id,
                    "date": dart.dart_date,
                    "equipment": cls._equipment_name(dart),
                    "action": ("Closed" if dart.is_closed else "Raised"),
                    "department": dart_department,
                    "reason": cls._severity_name(dart),
                    "status": ("Verified" if dart.is_closed else "In Progress"),
                }
            )

            if len(result) >= 50:
                break

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_name(dart):
        if not dart.severity_code:
            return None

        return str(dart.severity_code)

    @staticmethod
    def _department_name(dart):
        if not dart.department_id:
            return None

        return str(dart.department_id)

    @staticmethod
    def _equipment_name(dart):
        if dart.equipment_ems:
            return str(dart.equipment_ems)

        if dart.equipment_ship:
            return str(dart.equipment_ship)

        return dart.defective_component

    @staticmethod
    def _normalize(value):
        return " ".join(value.lower().split())

    @classmethod
    def _get_period_start(cls, period):
        period = period.upper()

        if period == "ALL":
            return None

        days = cls.PERIOD_DAYS.get(period)

        if not days:
            return None

        return timezone.now().date() - timedelta(days=days)

    @staticmethod
    def _subtract_months(value, months):
        month = value.month - months
        year = value.year

        while month <= 0:
            month += 12
            year -= 1

        return value.replace(
            year=year,
            month=month,
            day=1,
        )
