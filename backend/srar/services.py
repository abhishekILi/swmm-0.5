from django.db import transaction
from rest_framework.exceptions import ValidationError


def get_previous_month_header(ship_id, month, year):
    """Returns the SrarMonthlyHeader for the calendar month immediately
    before (month, year) for the given ship, or None if none was filed.
    Mirrors save_srar_report's existing_filter convention: a missing ship
    is treated as the "no ship" bucket (ship__isnull=True), not an error."""
    from srar.models import SrarMonthlyHeader

    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1

    filters = {"srar_month": prev_month, "srar_year": prev_year}
    if ship_id:
        filters["ship_id"] = ship_id
    else:
        filters["ship__isnull"] = True

    return SrarMonthlyHeader.objects.filter(**filters).first()


def _validated_save(serializer, field_name, item_id=None):
    if not serializer.is_valid():
        error = {"errors": serializer.errors}
        if item_id is not None:
            error["id"] = item_id
        raise ValidationError({field_name: error})
    return serializer.save()


def _sync_relation(header, field_name, model, key_field, data_list, serializer_class):
    if data_list is None:
        return

    existing_ids = set(
        model.objects.filter(**{key_field: header}).values_list("id", flat=True)
    )
    new_ids = set()

    for item in data_list:
        payload = dict(item)
        payload[key_field] = header.id
        item_id = payload.get("id")

        if item_id and int(item_id) in existing_ids:
            obj = model.objects.get(id=int(item_id))
            serializer = serializer_class(obj, data=payload, partial=True)
            new_ids.add(int(item_id))
        else:
            serializer = serializer_class(data=payload)

        saved_obj = _validated_save(serializer, field_name, item_id=item_id)
        new_ids.add(saved_obj.id)

    stale_ids = existing_ids - new_ids
    if stale_ids:
        model.objects.filter(id__in=stale_ids).delete()


def _sync_single_relation(header, field_name, model, key_field, data, serializer_class):
    if data is None:
        return

    payload = dict(data)
    payload[key_field] = header.id
    obj = model.objects.filter(**{key_field: header}).first()
    if obj:
        serializer = serializer_class(obj, data=payload, partial=True)
    else:
        serializer = serializer_class(data=payload)
    _validated_save(serializer, field_name, item_id=payload.get("id"))


@transaction.atomic
def save_srar_report(payload, user=None):
    from srar.models import (
        AnnualSRMRRoutineUndertaken,
        AnnualSRMRRoutineUndertakenofGTG,
        AvcatStatus,
        DGUF,
        DGUFSeaHarbourRunningHourDataInput,
        DGUFLimits,
        EEF,
        EquipmentRoutineDueOn,
        FPTDieselAlternators,
        FPTEquipmentWise,
        FuelConsumptionMonth,
        FullPowerTrialsMainEngine,
        GTGParameters,
        GTGrecordOfCleaningServiceTank,
        GasTurbineExploitation,
        GasTurbineGeneratorExploitation,
        GasTurbineGeneratorExploitationGufEntry,
        H2SSensor,
        Iccp,
        InjectorFIPCalibrationReplacement,
        MagazineFFSystemFloodingSystem,
        OpsStatusofLubOilandCoolantTestKits,
        RHExtension,
        ReductionGearExploitation,
        ReductionGearExploitationofGTG,
        ReplacementOfMajorAssemblies,
        ReplacementOfMajorAssembliesofGTG,
        STP,
        SafetyDeviceCheckTrial,
        SrarAdjustment,
        SrarBoilerAlkalinitySalinityDetail,
        SrarCentrifuge,
        SrarEquipmentExploitation,
        SrarMonthlyBoiler,
        SrarMonthlyHeader,
        SrarMonthlyLubricant,
        SrarMonthlyShipActivity,
        TorsionMeter,
    )
    from srar.serializers import (
        AnnualSRMRRoutineUndertakenSerializer,
        AnnualSRMRRoutineUndertakenofGTGSerializer,
        AvcatStatusSerializer,
        DGUFSeaHarbourRunningHourDataInputSerializer,
        DGUFSerializer,
        DGUFLimitsSerializer,
        EEFSerializer,
        EquipmentRoutineDueOnSerializer,
        FPTDieselAlternatorsSerializer,
        FPTEquipmentWiseSerializer,
        FuelConsumptionMonthSerializer,
        FullPowerTrialsMainEngineSerializer,
        GTGParametersSerializer,
        GTGrecordOfCleaningServiceTankSerializer,
        GasTurbineExploitationSerializer,
        GasTurbineGeneratorExploitationGufEntrySerializer,
        GasTurbineGeneratorExploitationSerializer,
        H2SSensorSerializer,
        IccpSerializer,
        InjectorFIPCalibrationReplacementSerializer,
        MagazineFFSystemFloodingSystemSerializer,
        OpsStatusofLubOilandCoolantTestKitsSerializer,
        RHExtensionSerializer,
        ReductionGearExploitationSerializer,
        ReductionGearExploitationofGTGSerializer,
        ReplacementOfMajorAssembliesSerializer,
        ReplacementOfMajorAssembliesofGTGSerializer,
        STPSerializer,
        SafetyDeviceCheckTrialSerializer,
        SrarAdjustmentSerializer,
        SrarBoilerAlkalinitySalinityDetailSerializer,
        SrarCentrifugeSerializer,
        SrarEquipmentExploitationSerializer,
        SrarMonthlyBoilerSerializer,
        SrarMonthlyHeaderSerializer,
        SrarMonthlyLubricantSerializer,
        SrarMonthlyShipActivitySerializer,
        TorsionMeterSerializer,
    )

    header_data = payload.get("header", {})
    header_id = header_data.get("id")

    if header_id:
        header = SrarMonthlyHeader.objects.get(pk=header_id)
        header_serializer = SrarMonthlyHeaderSerializer(
            header, data=header_data, partial=True
        )
    else:
        existing_filter = {
            "srar_month": header_data.get("srar_month"),
            "srar_year": header_data.get("srar_year"),
        }
        if header_data.get("ship"):
            existing_filter["ship_id"] = header_data.get("ship")
        else:
            existing_filter["ship__isnull"] = True
        header = SrarMonthlyHeader.objects.filter(**existing_filter).first()
        if header:
            header_serializer = SrarMonthlyHeaderSerializer(
                header, data=header_data, partial=True
            )
        else:
            header_serializer = SrarMonthlyHeaderSerializer(data=header_data)

    header = _validated_save(header_serializer, "header", item_id=header_id)

    relation_configs = [
        (
            "tab_1_equipment_exploitations",
            SrarEquipmentExploitation,
            SrarEquipmentExploitationSerializer,
        ),
        ("tab_2_boiler_data", SrarMonthlyBoiler, SrarMonthlyBoilerSerializer),
        (
            "tab_2_boiler_alkalinity",
            SrarBoilerAlkalinitySalinityDetail,
            SrarBoilerAlkalinitySalinityDetailSerializer,
        ),
        (
            "tab_3_ship_activities",
            SrarMonthlyShipActivity,
            SrarMonthlyShipActivitySerializer,
        ),
        (
            "tab_4_fuel_consumptions",
            FuelConsumptionMonth,
            FuelConsumptionMonthSerializer,
        ),
        ("tab_4_torsion_meters", TorsionMeter, TorsionMeterSerializer),
        ("tab_5_iccp", Iccp, IccpSerializer),
        ("tab_5_h2s", H2SSensor, H2SSensorSerializer),
        ("tab_5_stp", STP, STPSerializer),
        (
            "tab_5_magazine",
            MagazineFFSystemFloodingSystem,
            MagazineFFSystemFloodingSystemSerializer,
        ),
        ("tab_6_centrifuges", SrarCentrifuge, SrarCentrifugeSerializer),
        (
            "tab_6_test_kits",
            OpsStatusofLubOilandCoolantTestKits,
            OpsStatusofLubOilandCoolantTestKitsSerializer,
        ),
        (
            "tab_7_safety_device_checks",
            SafetyDeviceCheckTrial,
            SafetyDeviceCheckTrialSerializer,
        ),
        (
            "tab_7_calibrations",
            InjectorFIPCalibrationReplacement,
            InjectorFIPCalibrationReplacementSerializer,
        ),
        ("tab_8_dguf", DGUF, DGUFSerializer),
        ("tab_8_dguf_limits", DGUFLimits, DGUFLimitsSerializer),
        (
            "tab_9_fpt_me",
            FullPowerTrialsMainEngine,
            FullPowerTrialsMainEngineSerializer,
        ),
        ("tab_9_fpt_eq", FPTEquipmentWise, FPTEquipmentWiseSerializer),
        (
            "tab_9_fpt_da",
            FPTDieselAlternators,
            FPTDieselAlternatorsSerializer,
        ),
        (
            "tab_10_reduction_gear",
            ReductionGearExploitation,
            ReductionGearExploitationSerializer,
        ),
        (
            "tab_10_gas_turbine",
            GasTurbineExploitation,
            GasTurbineExploitationSerializer,
        ),
        (
            "tab_10_replacements",
            ReplacementOfMajorAssemblies,
            ReplacementOfMajorAssembliesSerializer,
        ),
        (
            "tab_10_srmr",
            AnnualSRMRRoutineUndertaken,
            AnnualSRMRRoutineUndertakenSerializer,
        ),
        (
            "tab_11_gtg",
            GasTurbineGeneratorExploitation,
            GasTurbineGeneratorExploitationSerializer,
        ),
        (
            "tab_11_gtg_guf",
            GasTurbineGeneratorExploitationGufEntry,
            GasTurbineGeneratorExploitationGufEntrySerializer,
        ),
        (
            "tab_11_gtg_rg",
            ReductionGearExploitationofGTG,
            ReductionGearExploitationofGTGSerializer,
        ),
        (
            "tab_11_gtg_rep",
            ReplacementOfMajorAssembliesofGTG,
            ReplacementOfMajorAssembliesofGTGSerializer,
        ),
        (
            "tab_11_gtg_srmr",
            AnnualSRMRRoutineUndertakenofGTG,
            AnnualSRMRRoutineUndertakenofGTGSerializer,
        ),
        ("tab_11_gtg_params", GTGParameters, GTGParametersSerializer),
        (
            "tab_11_gtg_tanks",
            GTGrecordOfCleaningServiceTank,
            GTGrecordOfCleaningServiceTankSerializer,
        ),
        (
            "tab_12_lubricants",
            SrarMonthlyLubricant,
            SrarMonthlyLubricantSerializer,
        ),
        ("tab_13_rh_extensions", RHExtension, RHExtensionSerializer),
        (
            "tab_15_routine_due",
            EquipmentRoutineDueOn,
            EquipmentRoutineDueOnSerializer,
        ),
        ("tab_15_adjustments", SrarAdjustment, SrarAdjustmentSerializer),
    ]

    for field_name, model, serializer_class in relation_configs:
        _sync_relation(
            header=header,
            field_name=field_name,
            model=model,
            key_field="srar_monthly_header",
            data_list=payload.get(field_name),
            serializer_class=serializer_class,
        )

    _sync_single_relation(
        header=header,
        field_name="tab_4_avcat_status",
        model=AvcatStatus,
        key_field="srar_monthly_header",
        data=payload.get("tab_4_avcat_status"),
        serializer_class=AvcatStatusSerializer,
    )
    _sync_single_relation(
        header=header,
        field_name="tab_8_dguf_running_hours",
        model=DGUFSeaHarbourRunningHourDataInput,
        key_field="srar_monthly_header",
        data=payload.get("tab_8_dguf_running_hours"),
        serializer_class=DGUFSeaHarbourRunningHourDataInputSerializer,
    )
    _sync_single_relation(
        header=header,
        field_name="tab_14_eef",
        model=EEF,
        key_field="srar_monthly_header",
        data=payload.get("tab_14_eef"),
        serializer_class=EEFSerializer,
    )

    return {
        "status": "success",
        "message": "Report saved successfully",
        "id": header.id,
    }
