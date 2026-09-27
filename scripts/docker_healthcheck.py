import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
except Exception as exc:
    print(f"healthcheck failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

print("ok")
