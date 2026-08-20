try:
    from .celery import app as celery_app
except ImportError:  # pragma: no cover - local dev fallback when celery is absent
    celery_app = None

__all__ = ("celery_app",)
