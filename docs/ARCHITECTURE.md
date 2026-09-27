# AI-Assisted IT Help Desk Architecture

```text
Browser
  |
  v
Django Web Application
  |-- Accounts / RBAC
  |-- Tickets / SLA / Attachments
  |-- Knowledge Base
  |-- AI Assist (rule-based classifier + KB suggestions + fallback)
  |-- Notifications
  |-- Audit Log
  |-- Dashboard / Reports
  |-- Operations / Metrics / Health
  |
  +---- PostgreSQL (staging/production)
  +---- Media volume
  +---- Backup volume
```

## AI fallback

The current AI-assist implementation is deterministic/rule-based. It returns a category, priority and confidence score and provides a fallback response when the AI suggestion endpoint encounters an error. This is intentionally explainable for an academic demonstration.

## Deployment environments

- Development: `.env`, local SQLite or Docker PostgreSQL.
- Staging: `.env.staging`, separate PostgreSQL volume/database and HTTPS settings.
- Production: use a separately managed database, secret manager, TLS termination, backups and monitoring.
