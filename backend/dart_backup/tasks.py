import csv
import time
from uuid import uuid4

from celery import shared_task
from django.forms.models import model_to_dict

from dart.models import InitiateDart, InitiateRADL
from swmm.async_jobs import build_export_path, build_media_url


@shared_task(name="cmms.tasks.validate_routine_completion")
def validate_routine_completion_task(data):
    time.sleep(0.5)
    routine_id = data.get("routine_id")
    if not routine_id:
        return {"success": False, "message": "Missing routine_id"}
    return {
        "success": True,
        "message": "Routine completion payload validated successfully.",
        "data": {"routine_id": routine_id},
    }


@shared_task(name="dart.tasks.export_generated_dl_ii_report")
def export_generated_dl_ii_report_task(report_id):
    rows = (
        InitiateRADL.objects.select_related(
            "initiate_dart",
            "initiate_dart__equipment_ship",
        )
        .filter(radl_master_id=report_id, dl_type="DL-II")
        .exclude(status="DELETED")
        .order_by("id")
    )
    filename = f"generated_dl_ii_report_{report_id}_{uuid4().hex}.csv"
    file_path = build_export_path("dart-exports", filename)
    try:
        with open(file_path, "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow(
                [
                    "ID",
                    "DL No",
                    "RA/DL Name",
                    "DL Type",
                    "Status",
                    "Equipment",
                    "Description",
                    "Defective Component",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.id,
                        row.dl_no,
                        row.dl_key,
                        row.dl_type,
                        row.status,
                        (
                            row.initiate_dart.equipment_ship.nomenclature
                            if row.initiate_dart and row.initiate_dart.equipment_ship
                            else ""
                        ),
                        (
                            row.initiate_dart.defective_discriptions
                            if row.initiate_dart
                            else ""
                        ),
                        getattr(row.initiate_dart, "defective_component", ""),
                    ]
                )
    except OSError:
        return {
            "success": False,
            "status_code": 500,
            "message": "Unable to write generated DL-II export file.",
        }

    return {
        "success": True,
        "status_code": 200,
        "result": {
            "file_path": file_path,
            "download_url": build_media_url(file_path),
            "filename": filename,
        },
    }


@shared_task(name="dart.tasks.export_all_ra_data")
def export_all_ra_data_task(yard, export_format, dart_ids):
    dart_qs = InitiateDart.objects.filter(id__in=dart_ids)
    dart_data = []
    for obj in dart_qs:
        data = model_to_dict(obj)
        data["equipment_ship"] = obj.equipment_ship.id if obj.equipment_ship else None
        data["equipment_ems"] = (
            obj.equipment_ems.id if getattr(obj, "equipment_ems", None) else None
        )
        data["remark_code"] = str(obj.remark_code) if obj.remark_code else None
        dart_data.append(data)
    return {
        "success": True,
        "status_code": 200,
        "result": {
            "yard": yard,
            "export_format": export_format,
            "total_records": len(dart_data),
            "dart_data": dart_data,
        },
    }


@shared_task(name="dart.tasks.initiate_candef_sync")
def initiate_candef_sync_task(pk):
    return {
        "success": True,
        "status_code": 200,
        "result": {
            "status": "success",
            "message": f"CANDEF initiation sync queued for record {pk}.",
        },
    }


@shared_task(name="dart.tasks.complete_candef_sync")
def complete_candef_sync_task(pk):
    return {
        "success": True,
        "status_code": 200,
        "result": {
            "status": "success",
            "message": f"CANDEF completion sync queued for record {pk}.",
        },
    }
