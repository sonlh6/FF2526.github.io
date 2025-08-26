#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Thay đổi 'your_project_name.settings' thành tên dự án của bạn.
    # Dựa trên cấu trúc file của bạn, tên dự án có vẻ là 'Fantasy'.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Fantasy.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
