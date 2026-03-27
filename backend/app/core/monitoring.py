from __future__ import annotations

import sentry_sdk

from app.core.settings import get_settings


def init_monitoring() -> None:
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.2,
        )

