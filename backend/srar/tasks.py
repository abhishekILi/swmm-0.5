import json

from celery import shared_task
from swmm.async_jobs import build_export_path, build_media_url

from srar.models import SrarMonthlyHeader
from srar.services import save_srar_report
from srar.utils import build_srar_report_payload


@shared_task(name="srar.tasks.export_report_pdf")
def export_report_pdf_task(header_id):
    header = SrarMonthlyHeader.objects.get(pk=header_id)
    payload = build_srar_report_payload(header)
    filename = f"SRAR_{header.srar_year}_{header.srar_month}.json"
    file_path = build_export_path("srar-exports", filename)
    with open(file_path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=2, default=str)
    return {
        "success": True,
        "status_code": 200,
        "result": {
            "file_path": file_path,
            "download_url": build_media_url(file_path),
            "filename": filename,
        },
    }


@shared_task(name="srar.tasks.save_report")
def save_report_task(payload, user_id):
    return {
        "success": True,
        "status_code": 200,
        "result": save_srar_report(payload),
    }
