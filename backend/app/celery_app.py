from __future__ import annotations

from celery import Celery

from app.core.settings import get_settings


settings = get_settings()


def make_celery() -> Celery:
    broker = settings.celery_broker_url
    backend = settings.celery_result_backend
    celery = Celery(
        "cognivara",
        broker=broker,
        backend=backend,
    )
    celery.conf.update(task_track_started=True)
    return celery


celery_app = make_celery()
