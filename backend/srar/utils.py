import calendar
from datetime import date, datetime, timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

from ems.models import PostEquipmentStateChangeHistorySave

from .models import (
    DGUF,
    DGUFSeaHarbourRunningHourDataInput,
    EEF,
    STP,
    SrarMonthlyHeader,
    AnnualSRMRRoutineUndertaken,
    AnnualSRMRRoutineUndertakenofGTG,
    AvcatStatus,
    DGUFLimits,
    EquipmentRoutineDueOn,
    FPTDieselAlternators,
    FPTEquipmentWise,
    FuelConsumptionMonth,
    FullPowerTrialsMainEngine,
    GasTurbineExploitation,
    GasTurbineGeneratorExploitation,
    GasTurbineGeneratorExploitationGufEntry,
    GTGParameters,
    GTGrecordOfCleaningServiceTank,
    H2SSensor,
    Iccp,
    InjectorFIPCalibrationReplacement,
    MagazineFFSystemFloodingSystem,
    OpsStatusofLubOilandCoolantTestKits,
    ReductionGearExploitation,
    ReductionGearExploitationofGTG,
    ReplacementOfMajorAssemblies,
    ReplacementOfMajorAssembliesofGTG,
    RHExtension,
    SafetyDeviceCheckTrial,
    SrarAdjustment,
    SrarBoilerAlkalinitySalinityDetail,
    SrarCentrifuge,
    SrarEquipmentExploitation,
    SrarMonthlyBoiler,
    SrarMonthlyLubricant,
    SrarMonthlyShipActivity,
    TorsionMeter,
)
from .serializers import (
    AnnualSRMRRoutineUndertakenofGTGSerializer,
    AnnualSRMRRoutineUndertakenSerializer,
    AvcatStatusSerializer,
    DGUFLimitsSerializer,
    DGUFSeaHarbourRunningHourDataInputSerializer,
    DGUFSerializer,
    EEFSerializer,
    EquipmentRoutineDueOnSerializer,
    FPTDieselAlternatorsSerializer,
    FPTEquipmentWiseSerializer,
    FuelConsumptionMonthSerializer,
    FullPowerTrialsMainEngineSerializer,
    GasTurbineExploitationSerializer,
    GasTurbineGeneratorExploitationGufEntrySerializer,
    GasTurbineGeneratorExploitationSerializer,
    GTGParametersSerializer,
    GTGrecordOfCleaningServiceTankSerializer,
    H2SSensorSerializer,
    IccpSerializer,
    InjectorFIPCalibrationReplacementSerializer,
    MagazineFFSystemFloodingSystemSerializer,
    OpsStatusofLubOilandCoolantTestKitsSerializer,
    ReductionGearExploitationofGTGSerializer,
    ReductionGearExploitationSerializer,
    ReplacementOfMajorAssembliesofGTGSerializer,
    ReplacementOfMajorAssembliesSerializer,
    RHExtensionSerializer,
    SafetyDeviceCheckTrialSerializer,
    SrarAdjustmentSerializer,
    SrarBoilerAlkalinitySalinityDetailSerializer,
    SrarCentrifugeSerializer,
    SrarEquipmentExploitationSerializer,
    SrarMonthlyBoilerSerializer,
    SrarMonthlyHeaderSerializer,
    SrarMonthlyLubricantSerializer,
    SrarMonthlyShipActivitySerializer,
    STPSerializer,
    TorsionMeterSerializer,
)


def get_max_hours_for_month(year: int, month: int) -> int:
    """
    Returns maximum possible hours in a month based on calendar days:
    - 31 days month -> 744 hours
    - 30 days month -> 720 hours
    - 29 days month (February in leap year) -> 696 hours
    - 28 days month (February in non-leap year) -> 672 hours
    """
    _, num_days = calendar.monthrange(year, month)
    return num_days * 24


def _month_bounds(year: int, month: int, tz=None):
    """Return (month_start, month_end) as timezone-aware datetimes.
    month_end is start of next month (exclusive)."""
    if tz is None:
        tz = timezone.get_current_timezone()

    # naive datetimes for boundaries
    start_naive = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        next_naive = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        next_naive = datetime(year, month + 1, 1, 0, 0, 0)

    month_start = timezone.make_aware(start_naive, tz)
    month_end = timezone.make_aware(next_naive, tz)
    return month_start, month_end


def calculate_month_running_hours(equipment, year: int, month: int, tz=None):
    """
    Returns (total_hours, breakdown_list)
    breakdown_list: list of dicts {history_id, clipped_start, clipped_stop, hours, location}
    """
    if tz is None:
        tz = timezone.get_current_timezone()

    month_start, month_end = _month_bounds(year, month, tz)

    # Query history entries that might overlap the month:
    qs = (
        PostEquipmentStateChangeHistorySave.objects.filter(
            equipment_name__sfd_equipment=equipment,
            start_time__lt=month_end,  # started before month end
        )
        .filter(
            models.Q(stop_time__isnull=True)
            | models.Q(
                stop_time__gt=month_start
            )  # still running or stopped after month start
        )
        .order_by("start_time")
    )

    total_seconds = 0.0
    breakdown = []
    now = timezone.now().astimezone(tz)

    for h in qs:
        s = h.start_time
        e = h.stop_time or now

        # Ensure awareness and convert both into the same tz
        if timezone.is_naive(s):
            s = timezone.make_aware(s, tz)
        else:
            s = s.astimezone(tz)

        if timezone.is_naive(e):
            e = timezone.make_aware(e, tz)
        else:
            e = e.astimezone(tz)

        # Clip interval to the month window
        clip_start = s if s > month_start else month_start
        clip_end = e if e < month_end else month_end

        if clip_end > clip_start:
            secs = (clip_end - clip_start).total_seconds()
            total_seconds += secs
            breakdown.append(
                {
                    "history_id": h.pk,
                    "clipped_start": clip_start,
                    "clipped_stop": clip_end,
                    "minutes": round(secs / 60.0, 2),
                    # 'hours': round(secs / 3600.0, 3),  # keep more precision in breakdown
                    "location": h.started_at_location,
                }
            )
    total_minutes = round(total_seconds / 60.0, 2)
    hh_mm = minutes_to_hhmm(int(total_minutes))
    return total_minutes, hh_mm, breakdown


def minutes_to_hhmm(total):
    if total is None:
        return "0:00"
    h = total // 60
    m = total % 60
    return f"{h}:{m:02d}"


class relativedelta:
    def __init__(self, years=0, months=0, days=0):
        self.years = years
        self.months = months
        self.days = days

    def __radd__(self, other):
        return self._apply(other)

    def __add__(self, other):
        return self._apply(other)

    def _apply(self, value):
        if not isinstance(value, (date, datetime)):
            return NotImplemented

        month_index = value.month - 1 + self.months + (self.years * 12)
        year = value.year + (month_index // 12)
        month = (month_index % 12) + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        updated = value.replace(year=year, month=month, day=day)
        if self.days:
            updated = updated + timedelta(days=self.days)
        return updated


def build_srar_context(header):
    month, year = header.srar_month, header.srar_year
    total_minutes = header.hours_underway_month_minutes or 0
    header.hh = total_minutes // 60
    header.mm = total_minutes % 60

    try:
        max_hours = calendar.monthrange(year, month)[1] * 24
    except Exception:
        max_hours = 744

    # Fetch related lists
    iccp_saved = Iccp.objects.filter(srar_monthly_header=header).select_related(
        "sfd_details", "sfd_details__equipment"
    )
    h2s_saved = H2SSensor.objects.filter(srar_monthly_header=header).select_related(
        "sfd_details", "sfd_details__equipment"
    )
    stp_saved = STP.objects.filter(srar_monthly_header=header).select_related(
        "sfd_details", "sfd_details__equipment"
    )
    magazine_saved = MagazineFFSystemFloodingSystem.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details", "sfd_details__equipment")
    testkits_saved = OpsStatusofLubOilandCoolantTestKits.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details", "sfd_details__equipment")
    centrifuge_saved = SrarCentrifuge.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details", "sfd_details__equipment")

    expo_saved = SrarEquipmentExploitation.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    boiler_saved = SrarMonthlyBoiler.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    alkalinity_saved = SrarBoilerAlkalinitySalinityDetail.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")

    ship_activity_saved = SrarMonthlyShipActivity.objects.filter(
        srar_monthly_header=header
    ).select_related(
        "ship_activity_detail", "ship_activity_type", "ship_location", "ship_state"
    )
    fuel_saved = FuelConsumptionMonth.objects.filter(srar_monthly_header=header)
    avcat_saved = AvcatStatus.objects.filter(srar_monthly_header=header).first()
    torsion_saved = TorsionMeter.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")

    safety_device_saved = SafetyDeviceCheckTrial.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    calibration_saved = InjectorFIPCalibrationReplacement.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    dguf_saved = DGUF.objects.filter(srar_monthly_header=header).select_related(
        "sfd_details"
    )
    dguf_running_hours_saved = DGUFSeaHarbourRunningHourDataInput.objects.filter(
        srar_monthly_header=header
    ).first()
    dguf_limits_saved = DGUFLimits.objects.filter(srar_monthly_header=header)

    fpt_me_saved = FullPowerTrialsMainEngine.objects.filter(srar_monthly_header=header)
    fpt_eq_saved = FPTEquipmentWise.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details", "fpt_main_engine")
    fpt_da_saved = FPTDieselAlternators.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")

    rg_saved = ReductionGearExploitation.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    gt_saved = GasTurbineExploitation.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    replacement_saved = ReplacementOfMajorAssemblies.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    srmr_saved = AnnualSRMRRoutineUndertaken.objects.filter(
        srar_monthly_header=header
    ).select_related("equipment")

    gtg_saved = GasTurbineGeneratorExploitation.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    gtg_guf_saved = GasTurbineGeneratorExploitationGufEntry.objects.filter(
        srar_monthly_header=header
    )
    gtg_rg_saved = ReductionGearExploitationofGTG.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    gtg_rep_saved = ReplacementOfMajorAssembliesofGTG.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    gtg_srmr_saved = AnnualSRMRRoutineUndertakenofGTG.objects.filter(
        srar_monthly_header=header
    ).select_related("equipment")
    gtg_params_saved = GTGParameters.objects.filter(
        srar_monthly_header=header
    ).select_related("gtg_exploitation")
    gtg_tank_saved = GTGrecordOfCleaningServiceTank.objects.filter(
        srar_monthly_header=header
    ).select_related("gtg_exploitation")

    lubricant_saved = SrarMonthlyLubricant.objects.filter(
        srar_monthly_header=header
    ).select_related("lubricant")
    rh_extension_saved = RHExtension.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    eef_saved = EEF.objects.filter(srar_monthly_header=header).first()
    routine_due_saved = EquipmentRoutineDueOn.objects.filter(
        srar_monthly_header=header
    ).select_related("sfd_details")
    adjustment_saved = SrarAdjustment.objects.filter(
        srar_monthly_header=header
    ).select_related("ship", "sfd_details")

    context = {
        "srar_header": header,
        "srar_month": month,
        "srar_year": year,
        "max_hours": max_hours,
        "iccp_saved": iccp_saved,
        "h2s_saved": h2s_saved,
        "stp_saved": stp_saved,
        "magazine_saved": magazine_saved,
        "testkits_saved": testkits_saved,
        "centrifuge_saved": centrifuge_saved,
        "expo_saved": expo_saved,
        "boiler_saved": boiler_saved,
        "alkalinity_saved": alkalinity_saved,
        "ship_activity_saved": ship_activity_saved,
        "fuel_saved": fuel_saved,
        "avcat_saved": avcat_saved,
        "torsion_saved": torsion_saved,
        "safety_device_saved": safety_device_saved,
        "calibration_saved": calibration_saved,
        "dguf_saved": dguf_saved,
        "dguf_running_hours_saved": dguf_running_hours_saved,
        "dguf_limits_saved": dguf_limits_saved,
        "fpt_me_saved": fpt_me_saved,
        "fpt_eq_saved": fpt_eq_saved,
        "fpt_da_saved": fpt_da_saved,
        "rg_saved": rg_saved,
        "gt_saved": gt_saved,
        "replacement_saved": replacement_saved,
        "srmr_saved": srmr_saved,
        "gtg_saved": gtg_saved,
        "gtg_guf_saved": gtg_guf_saved,
        "gtg_rg_saved": gtg_rg_saved,
        "gtg_rep_saved": gtg_rep_saved,
        "gtg_srmr_saved": gtg_srmr_saved,
        "gtg_params_saved": gtg_params_saved,
        "gtg_tank_saved": gtg_tank_saved,
        "lubricant_saved": lubricant_saved,
        "rh_extension_saved": rh_extension_saved,
        "eef_saved": eef_saved,
        "routine_due_saved": routine_due_saved,
        "adjustment_saved": adjustment_saved,
    }
    return context


def build_srar_report_payload(header):
    ctx = build_srar_context(header)
    return {
        "header": SrarMonthlyHeaderSerializer(header).data,
        "tab_1_equipment_exploitations": SrarEquipmentExploitationSerializer(
            ctx["expo_saved"], many=True
        ).data,
        "tab_2_boiler_data": SrarMonthlyBoilerSerializer(
            ctx["boiler_saved"], many=True
        ).data,
        "tab_2_boiler_alkalinity": SrarBoilerAlkalinitySalinityDetailSerializer(
            ctx["alkalinity_saved"], many=True
        ).data,
        "tab_3_ship_activities": SrarMonthlyShipActivitySerializer(
            ctx["ship_activity_saved"], many=True
        ).data,
        "tab_4_fuel_consumptions": FuelConsumptionMonthSerializer(
            ctx["fuel_saved"], many=True
        ).data,
        "tab_4_avcat_status": (
            AvcatStatusSerializer(ctx["avcat_saved"]).data
            if ctx["avcat_saved"]
            else None
        ),
        "tab_4_torsion_meters": TorsionMeterSerializer(
            ctx["torsion_saved"], many=True
        ).data,
        "tab_5_iccp": IccpSerializer(ctx["iccp_saved"], many=True).data,
        "tab_5_h2s": H2SSensorSerializer(ctx["h2s_saved"], many=True).data,
        "tab_5_stp": STPSerializer(ctx["stp_saved"], many=True).data,
        "tab_5_magazine": MagazineFFSystemFloodingSystemSerializer(
            ctx["magazine_saved"], many=True
        ).data,
        "tab_6_centrifuges": SrarCentrifugeSerializer(
            ctx["centrifuge_saved"], many=True
        ).data,
        "tab_6_test_kits": OpsStatusofLubOilandCoolantTestKitsSerializer(
            ctx["testkits_saved"], many=True
        ).data,
        "tab_7_safety_device_checks": SafetyDeviceCheckTrialSerializer(
            ctx["safety_device_saved"], many=True
        ).data,
        "tab_7_calibrations": InjectorFIPCalibrationReplacementSerializer(
            ctx["calibration_saved"], many=True
        ).data,
        "tab_8_dguf": DGUFSerializer(ctx["dguf_saved"], many=True).data,
        "tab_8_dguf_running_hours": (
            DGUFSeaHarbourRunningHourDataInputSerializer(
                ctx["dguf_running_hours_saved"]
            ).data
            if ctx["dguf_running_hours_saved"]
            else None
        ),
        "tab_8_dguf_limits": DGUFLimitsSerializer(
            ctx["dguf_limits_saved"], many=True
        ).data,
        "tab_9_fpt_me": FullPowerTrialsMainEngineSerializer(
            ctx["fpt_me_saved"], many=True
        ).data,
        "tab_9_fpt_eq": FPTEquipmentWiseSerializer(ctx["fpt_eq_saved"], many=True).data,
        "tab_9_fpt_da": FPTDieselAlternatorsSerializer(
            ctx["fpt_da_saved"], many=True
        ).data,
        "tab_10_reduction_gear": ReductionGearExploitationSerializer(
            ctx["rg_saved"], many=True
        ).data,
        "tab_10_gas_turbine": GasTurbineExploitationSerializer(
            ctx["gt_saved"], many=True
        ).data,
        "tab_10_replacements": ReplacementOfMajorAssembliesSerializer(
            ctx["replacement_saved"], many=True
        ).data,
        "tab_10_srmr": AnnualSRMRRoutineUndertakenSerializer(
            ctx["srmr_saved"], many=True
        ).data,
        "tab_11_gtg": GasTurbineGeneratorExploitationSerializer(
            ctx["gtg_saved"], many=True
        ).data,
        "tab_11_gtg_guf": GasTurbineGeneratorExploitationGufEntrySerializer(
            ctx["gtg_guf_saved"], many=True
        ).data,
        "tab_11_gtg_rg": ReductionGearExploitationofGTGSerializer(
            ctx["gtg_rg_saved"], many=True
        ).data,
        "tab_11_gtg_rep": ReplacementOfMajorAssembliesofGTGSerializer(
            ctx["gtg_rep_saved"], many=True
        ).data,
        "tab_11_gtg_srmr": AnnualSRMRRoutineUndertakenofGTGSerializer(
            ctx["gtg_srmr_saved"], many=True
        ).data,
        "tab_11_gtg_params": GTGParametersSerializer(
            ctx["gtg_params_saved"], many=True
        ).data,
        "tab_11_gtg_tanks": GTGrecordOfCleaningServiceTankSerializer(
            ctx["gtg_tank_saved"], many=True
        ).data,
        "tab_12_lubricants": SrarMonthlyLubricantSerializer(
            ctx["lubricant_saved"], many=True
        ).data,
        "tab_13_rh_extensions": RHExtensionSerializer(
            ctx["rh_extension_saved"], many=True
        ).data,
        "tab_14_eef": (
            EEFSerializer(ctx["eef_saved"]).data if ctx["eef_saved"] else None
        ),
        "tab_15_routine_due": EquipmentRoutineDueOnSerializer(
            ctx["routine_due_saved"], many=True
        ).data,
        "tab_15_adjustments": SrarAdjustmentSerializer(
            ctx["adjustment_saved"], many=True
        ).data,
    }


def get_dynamic_kpis_data():
    """
    Computes dynamic KPI metrics from Django ORM database queries.
    """
    today = date.today()
    six_months_ago = today - timedelta(days=180)

    past_6_months_count = SrarMonthlyHeader.objects.filter(
        Q(created_on__gte=six_months_ago) | Q(srar_year__gt=today.year - 1)
    ).count()

    total_reports = SrarMonthlyHeader.objects.count()
    drafts_count = SrarMonthlyHeader.objects.filter(
        send_to_co=False, is_saved=True
    ).count()
    pending_co_count = SrarMonthlyHeader.objects.filter(
        send_to_co=True, is_saved=False, cmms_sync_status=False
    ).count()
    co_approved_count = SrarMonthlyHeader.objects.filter(
        send_to_co=True, is_saved=True, cmms_sync_status=False
    ).count()
    synced_count = SrarMonthlyHeader.objects.filter(cmms_sync_status=True).count()

    editable_srar_count = SrarMonthlyHeader.objects.filter(
        is_saved=True, send_to_co=False
    ).count()

    return {
        "past_6_months_count": past_6_months_count,
        "active_status_count": co_approved_count + synced_count,
        "pending_drafts_count": drafts_count,
        "application_status": {
            "draft": drafts_count,
            "pending_co_review": pending_co_count,
            "co_approved": co_approved_count,
            "synced": synced_count,
            "total": total_reports,
        },
        "editable_srar_count": editable_srar_count,
        "history_logs_count": total_reports,
    }


def get_dynamic_monthly_trend_data():
    """
    Computes dynamic month-by-month submission trend for the past 6 to 12 months.
    """
    today = date.today()
    trend = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        if month <= 0:
            month += 12
            year -= 1

        month_name = calendar.month_abbr[month]
        month_label = f"{month_name} {year}"

        qs = SrarMonthlyHeader.objects.filter(srar_year=year, srar_month=month)
        total_count = qs.count()
        submitted_count = qs.filter(send_to_co=True).count()
        draft_count = qs.filter(send_to_co=False).count()

        trend.append(
            {
                "month": month_label,
                "month_num": month,
                "year": year,
                "submitted": submitted_count,
                "draft": draft_count,
                "total": total_count,
            }
        )

    return {"trend": trend}


def get_dynamic_yearly_status_data():
    """
    Computes dynamic status distribution for current calendar year.
    """
    current_year = date.today().year
    qs_year = SrarMonthlyHeader.objects.filter(srar_year=current_year)
    total_year_count = qs_year.count()

    drafts = qs_year.filter(send_to_co=False).count()
    pending_co = qs_year.filter(
        send_to_co=True, is_saved=False, cmms_sync_status=False
    ).count()
    co_approved = qs_year.filter(
        send_to_co=True, is_saved=True, cmms_sync_status=False
    ).count()
    cmms_synced = qs_year.filter(cmms_sync_status=True).count()

    def calc_pct(val):
        if total_year_count > 0:
            return round((val / total_year_count) * 100, 1)
        return 0.0

    distribution = [
        {
            "status": "Draft",
            "count": drafts,
            "percentage": calc_pct(drafts),
        },
        {
            "status": "Pending CO Review",
            "count": pending_co,
            "percentage": calc_pct(pending_co),
        },
        {
            "status": "CO Approved",
            "count": co_approved,
            "percentage": calc_pct(co_approved),
        },
        {
            "status": "CMMS Synced",
            "count": cmms_synced,
            "percentage": calc_pct(cmms_synced),
        },
    ]

    return {
        "year": current_year,
        "total_year_records": total_year_count,
        "lifecycle_distribution": distribution,
    }
