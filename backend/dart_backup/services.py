import json

from .models import CompleteDefectDart, InitiateDart, InitiateRADL


DART_HISTORY_DATE_FORMAT = "%d %b %Y"


def get_generated_dl_ii_rows(report_id):
    return (
        InitiateRADL.objects.select_related(
            "initiate_dart",
            "initiate_dart__equipment_ship",
        )
        .filter(radl_master_id=report_id, dl_type="DL-II")
        .exclude(status="DELETED")
        .order_by("id")
    )


def get_closed_dart_history_queryset():
    return InitiateDart.objects.closed().with_history_relations().order_by("-id")


def get_pending_defects_for_export():
    return (
        InitiateDart.objects.open()
        .filter(is_ra_initiate=False)
        .with_non_empty_description()
        .select_related("equipment_ship", "equipment_ship__equipment", "severity_code")
        .order_by("id")
    )


def build_pending_defect_export_rows():
    rows = []
    for index, defect in enumerate(get_pending_defects_for_export(), start=1):
        equipment_ship = defect.equipment_ship
        equipment = equipment_ship.equipment if equipment_ship else None
        rows.append(
            [
                index,
                defect.dart_number or "",
                (
                    defect.dart_date.strftime(DART_HISTORY_DATE_FORMAT)
                    if defect.dart_date
                    else ""
                ),
                equipment.equipment_class if equipment else "",
                equipment_ship.nomenclature if equipment_ship else "",
                defect.defective_component or "",
                defect.defective_discriptions or "",
                defect.severity_code.severity_name if defect.severity_code else "",
                defect.dart_occasion or defect.maintenance_period or "",
            ]
        )
    return rows


def get_export_dart_ids(payload):
    dart_ids = payload.get("dart_ids") or []
    if isinstance(dart_ids, str):
        dart_ids = json.loads(dart_ids or "[]")

    row_data = payload.get("row_data")
    if row_data and not dart_ids:
        if isinstance(row_data, str):
            row_data = json.loads(row_data or "[]")
        dart_ids = [row.get("dart_id") for row in row_data if row.get("dart_id")]

    return [int(dart_id) for dart_id in dart_ids if dart_id]


def build_dl_ii_export_rows(dart_ids):
    defects = (
        InitiateDart.objects.filter(id__in=dart_ids)
        .select_related("equipment_ship", "equipment_ship__equipment", "severity_code")
        .order_by("id")
    )
    rows = []
    for index, defect in enumerate(defects, start=1):
        equipment_ship = defect.equipment_ship
        equipment = equipment_ship.equipment if equipment_ship else None
        rows.append(
            [
                index,
                defect.dart_number or "",
                equipment.equipment_class if equipment else "",
                equipment_ship.nomenclature if equipment_ship else "",
                defect.defective_component or "",
                defect.defective_discriptions or "",
                defect.severity_code.severity_name if defect.severity_code else "",
                defect.maintenance_period or "",
                defect.dart_occasion or "",
            ]
        )
    return rows


def build_simple_pdf(title, lines):
    escaped_lines = [
        str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in [title, "", *lines]
    ]
    text_commands = ["BT", "/F1 12 Tf", "50 790 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            text_commands.append("0 -18 Td")
        text_commands.append(f"({line}) Tj")
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("utf-8")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)


def get_latest_radl_key(dart, dl_types):
    dl_types = {dl_types} if isinstance(dl_types, str) else set(dl_types)
    entries = getattr(dart, "_prefetched_objects_cache", {}).get("ra_dl_entries")
    if entries is None:
        latest_entry = (
            dart.ra_dl_entries.filter(dl_type__in=dl_types).order_by("-id").first()
        )
    else:
        matching_entries = [entry for entry in entries if entry.dl_type in dl_types]
        latest_entry = max(matching_entries, key=lambda entry: entry.id, default=None)
    return latest_entry.dl_key if latest_entry else "NA"


def build_dart_history_row(dart, maintenance_key, maintenance_default=""):
    equipment_ship = dart.equipment_ship
    equipment = equipment_ship.equipment if equipment_ship else None
    sub_department = (
        getattr(equipment_ship, "sub_department_f_key", None)
        if equipment_ship
        else None
    )
    department = getattr(equipment_ship, "department", None) if equipment_ship else None
    complete_dart = CompleteDefectDart.objects.filter(dart_details=dart).first()

    return {
        "dartNo": dart.dart_number or "",
        "cmmsSyncStatus": getattr(dart, "cmms_sync_status", False),
        "opraNo": get_latest_radl_key(dart, "RA"),
        "raRaised": dart.is_ra_initiate or False,
        "dlNo": get_latest_radl_key(dart, {"DL-II", "DL-III"}),
        "dlRaised": getattr(dart, "is_dl_initiate", False),
        "equipmentName": equipment.equipment_class if equipment else "",
        "equipmentNomenclature": equipment_ship.nomenclature if equipment_ship else "",
        "defectDescription": dart.defective_discriptions or "",
        "subDepartment": sub_department.name if sub_department else "",
        "department": department.name if department else "",
        "symptomCode": (
            dart.symptom_code.symptom_code
            if dart.symptom_code and getattr(dart.symptom_code, "symptom_code", None)
            else ""
        ),
        "severityCode": (
            dart.severity_code.severity_name
            if dart.severity_code and getattr(dart.severity_code, "severity_name", None)
            else ""
        ),
        "closureDate": (
            complete_dart.rectified_date
            if complete_dart and getattr(complete_dart, "closureDate", None)
            else ""
        ),
        "repairAgency": (
            complete_dart.repair_agency_code.name
            if complete_dart and getattr(complete_dart.repair_agency_code, "name", None)
            else ""
        ),
        "diagnosisCode": (
            complete_dart.diagnostic_code.diagnostic_name
            if complete_dart
            and getattr(complete_dart.diagnostic_code, "diagnostic_name", None)
            else ""
        ),
        "daysDelayed": (
            complete_dart.days_delay
            if complete_dart and getattr(complete_dart, "days_delay", None)
            else ""
        ),
        "delayReason": (
            complete_dart.other_reasons
            if complete_dart and getattr(complete_dart, "other_reasons", None)
            else ""
        ),
        "lessonLearnt": (
            complete_dart.lesson_learnt
            if complete_dart and getattr(complete_dart, "lesson_learnt", None)
            else ""
        ),
        "dartOccasion": dart.dart_occasion or "",
        "defectDate": (
            dart.dart_date.strftime(DART_HISTORY_DATE_FORMAT) if dart.dart_date else ""
        ),
        "shipRemarks": dart.remark_code.description if dart.remark_code else "",
        "id": dart.id,
        maintenance_key: dart.maintenance_period or maintenance_default,
        "refitType": dart.maintenance_period or "",
    }
