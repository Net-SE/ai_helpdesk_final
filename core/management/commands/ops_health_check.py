import logging
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check database connectivity and emit an operational health result."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.stdout.write(self.style.SUCCESS("HEALTHY: database is reachable."))
        except Exception as exc:
            logger.exception("OPS health check failed")
            self.stderr.write(self.style.ERROR("UNHEALTHY: database is unavailable."))
            raise SystemExit(1) from exc
