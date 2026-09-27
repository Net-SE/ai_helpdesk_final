import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PostgreSQL database backup and optionally delete backups older than N days."

    def add_arguments(self, parser):
        parser.add_argument("--retention-days", type=int, default=30)

    def handle(self, *args, **options):
        backups_dir = Path(settings.BASE_DIR) / "backups"
        backups_dir.mkdir(exist_ok=True)
        db = settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError("PostgreSQL is required for backup_db in this version.")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = backups_dir / f"pg_backup_{ts}.dump"
        cmd = ["pg_dump", "-Fc", "-h", db.get("HOST") or "localhost", "-p", str(db.get("PORT") or 5432), "-U", db.get("USER") or "", "-f", str(out), db.get("NAME") or ""]
        env_vars = os.environ.copy()
        env_vars["PGPASSWORD"] = db.get("PASSWORD") or ""
        try:
            subprocess.run(cmd, env=env_vars, check=True)
        except FileNotFoundError as exc:
            raise CommandError("pg_dump is not installed or not on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"Database backup failed with exit code {exc.returncode}") from exc
        self.stdout.write(self.style.SUCCESS(f"Backup created: {out}"))
        retention_days = options["retention_days"]
        if retention_days > 0:
            cutoff = datetime.now().timestamp() - timedelta(days=retention_days).total_seconds()
            for backup in backups_dir.glob("pg_backup_*"):
                if backup.is_file() and backup.stat().st_mtime < cutoff:
                    backup.unlink()
