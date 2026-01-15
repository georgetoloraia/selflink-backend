#!/usr/bin/env python
import os
import sys


def main() -> None:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE")
    if not settings_module:
        if "test" in sys.argv:
            settings_module = "core.settings.test"
        else:
            settings_module = "core.settings.base"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
