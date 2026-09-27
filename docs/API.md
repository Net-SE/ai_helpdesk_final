# API / HTTP Endpoints

The application is primarily a server-rendered Django web application. The following JSON/HTTP endpoints are provided for integrations and monitoring.

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/core/healthz/` | No | DB/application health check |
| GET | `/core/metrics/` | No | CPU, memory and disk metrics |
| GET | `/ai/suggest/?text=...` | Login | AI category/priority/KB suggestions |
| GET | `/notifications/api/unread/` | Login | Notification unread count |
| GET | `/accounts/me/` | Login | Current user identity/role |

The AI endpoint is rate-limited to 30 requests/minute per authenticated user. Health and metrics endpoints should normally be protected at the network/load-balancer layer in production if exposing them outside the trusted network.
