# AI-Assisted IT Help Desk

Django 4.2 application implementing the Project requirements for an AI-assisted IT Help Desk.

## 1. Main functional workflow

1. User logs in.
2. Requester creates a ticket with title, description, category, priority and optional attachments.
3. AI Assist classifies category/priority and provides a confidence score, KB suggestions and troubleshooting steps.
4. Manager assigns the ticket to a technician.
5. Technician adds comments/internal notes and changes status.
6. Resolution requires a resolution note.
7. Notifications are created when ticket events occur.
8. SLA response/resolution deadlines are calculated from priority.
9. Managers use dashboard, SLA breach views and CSV reporting.
10. Users search tickets and Knowledge Base solutions.

## 2. Requirements coverage

| Requirement | Implementation |
|---|---|
| APP-01 | Django login/logout |
| APP-02 | Role-based backend permissions |
| APP-03 | Ticket/KB CRUD, status, assignment and archive |
| APP-04 | Search/filter/pagination |
| APP-05 | Django forms/model validation + upload validation |
| APP-06 | Dashboard and operations dashboard |
| APP-07 | Custom error pages + generic API errors |
| APP-08 | Django migrations |
| APP-09 | `seed_demo` management command |
| APP-10 | Audit log |
| ENV-01..08 | Dockerfile, Compose, env configuration, persistent volumes, healthcheck |
| TST-01..06 | Unit/integration/permission/fallback/load-test examples |
| SEC-01..05 | Sessions/logout, HTTPS settings, least-privilege roles, upload validation, rate limiting |
| OPS-01..10 | Request logs/IDs, metrics, health alert, backup/restore, RTO/RPO/runbook/incident template |

The core HD-01 through HD-10 workflow is implemented in the `tickets`, `knowledgebase`, `notifications`, `aiassist` and `dashboard` apps.

## 3. Local development without Docker

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Demo accounts created by `seed_demo` are printed by the command. Do not use demo passwords in production.

## 4. Docker development

```bash
copy .env.example .env
# PostgreSQL is the required database; set DATABASE_URL in .env.
docker compose up --build
```

The web service listens on port 8000.

## 5. Staging

1. Copy `.env.staging.example` to `.env.staging`.
2. Replace every placeholder secret and domain.
3. Build/publish the image through GitHub Actions.
4. Set `HELP_DESK_IMAGE` to the release tag.
5. Run:

```bash
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d
python scripts/smoke_test.py http://127.0.0.1:8001
```

## 6. CI/CD

`.github/workflows/ci.yml` performs:

- Python compilation
- Ruff static analysis
- Django checks
- migrations
- automated tests
- dependency vulnerability audit
- secret scanning
- Docker build
- optional GHCR publish and staging deployment on manual workflow dispatch from `main`

A failing required test occurs before the publish/deployment jobs, so the release is not deployed.

## 7. Backup and recovery

```bash
python manage.py backup_db --retention-days 30
python manage.py restore_db backups/<backup-file>
```

See `docs/OPS_RUNBOOK.md` for scheduling, RTO/RPO and incident procedures.

## 8. Monitoring

- `/core/healthz/` is the container health endpoint.
- `/core/metrics/` is restricted to manager/admin users.
- `/ops/` shows request count, error rate and latency for the last hour.
- `X-Request-ID` is returned on every request for log correlation.
- `scripts/health_alert.sh` can be scheduled by an external monitor.

## 9. AI note

The included AI Assist is a deterministic/rule-based implementation, not an external LLM. It is explainable and includes a fallback response when the suggestion endpoint fails. A production system could replace `aiassist/services.py` with an approved AI provider while retaining the same fallback contract.

## 10. Important production rules

- Never commit `.env`, database files, media uploads, private keys or API tokens.
- Use HTTPS and secure cookies in staging/production.
- Use a separate staging database from development.
- Run backups on a schedule and test restores.
- Protect health/metrics endpoints at the network boundary.
- Review audit logs and alerts during incidents.
