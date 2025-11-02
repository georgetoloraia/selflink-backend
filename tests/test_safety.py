from django.conf import settings


def test_throttle_defaults():
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user"] == "120/min"
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] == "60/min"


def test_feature_flags_present():
    assert "soulmatch" in settings.FEATURE_FLAGS
    assert "payments" in settings.FEATURE_FLAGS
