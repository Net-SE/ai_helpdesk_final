import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore a PostgreSQL backup and write a restore report."

    def add_arguments(self, parser):
        parser.add_argument("backup_file", type=str)
        parser.add_argument("--report", type=str, default="")

    def handle(self, *args, **options):
        backup_file = Path(options["backup_file"]).resolve()
        if not backup_file.exists():
            raise CommandError(f"Backup file does not exist: {backup_file}")
        db = settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError("PostgreSQL is required for restore_db in this version.")
        cmd = ["pg_restore", "--clean", "--if-exists", "-h", db.get("HOST") or "localhost", "-p", str(db.get("PORT") or 5432), "-U", db.get("USER") or "", "-d", db.get("NAME") or "", str(backup_file)]
        env_vars = os.environ.copy()
        env_vars["PGPASSWORD"] = db.get("PASSWORD") or ""
        try:
            subprocess.run(cmd, env=env_vars, check=True)
        except FileNotFoundError as exc:
            raise CommandError("pg_restore is not installed or not on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"Database restore failed with exit code {exc.returncode}") from exc
        report = Path(options["report"] or (settings.BASE_DIR / "backups" / "last_restore_report.txt"))
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(f"Restore successful\nBackup: {backup_file}\nDatabase engine: postgresql\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Restore successful. Report: {report}"))
