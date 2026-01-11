import logging

from django.test import override_settings

from core.routing import get_websocket_urlpatterns


def test_channels_disabled_by_default():
    with override_settings(REALTIME_CHANNELS_ENABLED=False):
        assert get_websocket_urlpatterns() == []


def test_channels_warning_when_enabled(caplog):
    with override_settings(REALTIME_CHANNELS_ENABLED=True):
        caplog.set_level(logging.WARNING, logger="core.routing")
        patterns = get_websocket_urlpatterns()
    assert patterns
    assert "deprecated" in caplog.text
