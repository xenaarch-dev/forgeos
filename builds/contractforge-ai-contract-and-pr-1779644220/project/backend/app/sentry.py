from __future__ import annotations

import sentry_sdk

from .config import settings


def init_sentry() -> None:
    if not settings.sentry_dsn_backend:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn_backend,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )
