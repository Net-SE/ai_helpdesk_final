# AI Helpdesk Operations Runbook

## Health check

- Browser/API: `GET /core/healthz/`
- System metrics: `GET /core/metrics/`
- Manager dashboard: `/ops/`
- CLI check: `python manage.py ops_health_check`

## Backup

SQLite:

```bash
python manage.py backup_db --retention-days 30
```

PostgreSQL uses `pg_dump` and creates a custom-format `.dump` file.
Schedule the command with cron/Task Scheduler. A practical demo schedule is once per day.

## Restore

Always restore into an isolated database first when possible:

```bash
python manage.py restore_db backups/sqlite_backup_YYYYMMDD_HHMMSS.sqlite3
```

A restore report is written to `backups/last_restore_report.txt` by default.

## RTO/RPO demo targets

For the assignment demo, document the chosen values explicitly. Example:

- RPO: 24 hours (maximum intended data loss between daily backups)
- RTO: 60 minutes (target time to restore the application and database)

These are project targets, not guarantees. Production values should be based on business requirements and infrastructure.

## Incident response

1. Confirm `/core/healthz/` and `/core/metrics/`.
2. Check application logs using the request ID returned in `X-Request-ID`.
3. Check CPU, memory, storage and recent 5xx response counts.
4. If a recent release caused the issue, rollback the container/application image to the previous known-good tag.
5. Restore the database only when data corruption/loss requires it; prefer application rollback without DB restore when possible.
6. Record root cause, impact, timeline, recovery actions and prevention steps.

## Alert demo

```bash
HEALTH_URL=http://127.0.0.1:8000/core/healthz/ ./scripts/health_alert.sh
```

An external scheduler/monitor should execute this script and send the failure output to the team's chosen alert channel.
