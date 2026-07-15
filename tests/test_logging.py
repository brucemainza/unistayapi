"""Tests for production log redaction."""

import json
import logging

from app.logging_config import _JsonFormatter


def test_json_formatter_redacts_sensitive_extra_values():
    record = logging.LogRecord(
        "unistay.test", logging.INFO, __file__, 1, "request failed", (), None
    )
    record.api_key = "api-secret-value"
    record.request_data = {"password": "plain-text", "name": "Test"}
    record.upstream_url = "https://example.test?token=abc123&key=maps-secret"

    rendered = json.loads(_JsonFormatter().format(record))

    assert rendered["api_key"] == "<REDACTED>"
    assert rendered["request_data"]["password"] == "<REDACTED>"
    assert rendered["request_data"]["name"] == "Test"
    assert "abc123" not in rendered["upstream_url"]
    assert "maps-secret" not in rendered["upstream_url"]
