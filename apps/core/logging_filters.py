from __future__ import annotations

import logging


class StripRequestBodyFilter(logging.Filter):
    """
    Drop request body/content fields from log records to avoid leaking PII.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        for attr in ("request", "request_body", "data", "body"):
            if hasattr(record, attr):
                setattr(record, attr, None)
        return True
