# IT Assist API

The project exposes JSON endpoints under `/api/` and uses HTTP Basic Authentication for protected endpoints.

## Health
`GET /api/health/`

## Login check
`POST /api/auth/login/`
```json
{"username":"req1_demo","password":"Password123!"}
```

## Tickets
- `GET /api/tickets/`
- `POST /api/tickets/`
- `GET /api/tickets/{id}/`
- `PATCH /api/tickets/{id}/`
- `PATCH /api/tickets/{id}/status/`
- `POST /api/tickets/{id}/assign/`
- `POST /api/tickets/{id}/comments/`

Create ticket example:
```json
{"title":"Printer is not working","description":"The printer cannot print documents."}
```

## Knowledge Base
- `GET /api/kb/`
- `GET /api/kb/{id}/`

## AI
`POST /api/ai/suggest/`
```json
{"title":"Printer is not working","description":"The printer cannot print documents."}
```

## Dashboard
`GET /api/dashboard/` — Manager/Admin only.

## Local PostgreSQL
Create a PostgreSQL database and user, then put this in `.env`:
`DATABASE_URL=postgresql://helpdesk:helpdesk@localhost:5432/it_assist`

Run:
```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

API base URL: `http://127.0.0.1:8000/api/`
