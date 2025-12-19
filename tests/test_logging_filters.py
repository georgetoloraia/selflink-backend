from __future__ import annotations

import logging

from apps.core.logging_filters import StripRequestBodyFilter


def test_strip_request_body_filter_redacts_fields():
    record = logging.LogRecord("test", logging.INFO, "path", 1, "msg", args=(), exc_info=None)
    record.request = "req"
    record.request_body = "secret"
    record.data = {"password": "secret"}
    record.body = "secret"

    filt = StripRequestBodyFilter()
    assert filt.filter(record) is True
    assert record.request is None
    assert record.request_body is None
    assert record.data is None
    assert record.body is None

