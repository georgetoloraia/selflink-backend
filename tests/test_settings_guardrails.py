import pytest
from django.core.exceptions import ImproperlyConfigured

from core.settings import base as base_settings


def test_database_url_guard_raises_in_docker_for_localhost():
    with pytest.raises(ImproperlyConfigured) as excinfo:
        base_settings.validate_database_url_for_docker(
            "postgres://user:pass@localhost:5432/db", True
        )
    assert "localhost" in str(excinfo.value)


def test_database_url_guard_allows_localhost_outside_docker():
    base_settings.validate_database_url_for_docker(
        "postgres://user:pass@localhost:5432/db", False
    )


def test_database_url_guard_allows_service_hostname_in_docker():
    base_settings.validate_database_url_for_docker(
        "postgres://user:pass@pgbouncer:6432/db", True
    )
