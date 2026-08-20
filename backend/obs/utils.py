import os
import uuid

from drf_spectacular.utils import extend_schema, extend_schema_view


def django_validation_error_detail(error):
    if hasattr(error, "message_dict"):
        return error.message_dict
    if hasattr(error, "messages"):
        return error.messages
    return str(error)


def tagged_viewset(tag, create_examples=None):
    return extend_schema_view(
        list=extend_schema(tags=[tag]),
        create=extend_schema(tags=[tag], examples=create_examples or []),
        retrieve=extend_schema(tags=[tag]),
        update=extend_schema(tags=[tag]),
        partial_update=extend_schema(tags=[tag]),
        destroy=extend_schema(tags=[tag]),
    )


def spare_image_upload_path(instance, filename):
    _, extension = os.path.splitext(filename)
    if extension.lower() not in {".png", ".jpg", ".jpeg"}:
        return "obs/default.png"

    spare_class = instance.equipment_class.spare_class.name
    equipment_class = instance.equipment_class.name
    unique_name = f"{uuid.uuid4().hex}{extension.lower()}"
    return f"obs/{spare_class}/{equipment_class}/{unique_name}"
