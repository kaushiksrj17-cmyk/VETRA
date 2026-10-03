# VETRA — Phase 14 Architecture & Technical Specification
## Production Deployment, Security & Enterprise Hardening

---

### 1. Objective

Phase 14 transitions the VETRA intelligent livestock health platform from a multi-phase feature-complete prototype (Phases 1–13) into a battle-hardened, production-ready enterprise deployment architecture. The hardening spans environment-aware configuration, cryptographic credential security, API defense in depth, robust WebSocket session isolation, multi-stage non-root containerization, structured observability, and continuous health probes.

---

### 2. End-to-End Enterprise Architecture

```
[ External User / Farmer / Vet / Officer / IoT Device ]
                         │
                         ▼
        [ Reverse Proxy / TLS 1.3 Termination ]
       (Security Headers, SSL Offloading, HSTS)
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
[ vetra-frontend:8501 ]           [ vetra-backend:8000 ]
(Streamlit UI Container)          (FastAPI Uvicorn Container)
  - Headless Execution              - Security Middleware
  - Session State Mgmt              - Rate Limiter (In-Memory/Sliding)
  - RBAC UI Routing                 - JWT Validation (HS256)
  - Graceful Fallback               - Structured JSON Logging
        │                                 │
        └────────────────┬────────────────┘
                         │
                         ▼
             [ MongoDB Atlas Cluster ]
         - Connection Pooling (5-50 connections)
         - Auto-reconnect & Retries (retryWrites=True)
         - Server Selection Timeout: 5000ms
         - Zero Baseline Mutation Guarantee
```

---

### 3. Security Architecture & Defense in Depth

VETRA implements defense-in-depth principles across 7 security rings:
1. **Network Ring**: Reverse proxy with TLS 1.3, strict CORS whitelisting, and no wildcard origins with credentials in production.
2. **Edge API Ring**: Centralized middleware injecting `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Request-ID`.
3. **Payload Ring**: 25 MB payload bounding via `Content-Length` enforcement rejecting HTTP 413 over-sized floods.
4. **Rate Limiting Ring**: Sliding window rate limiter throttling brute-force attempts on `/auth/login` (10 req/min) and `/auth/register` (5 req/min).
5. **Authentication Ring**: Bcrypt salted password hashing and stateless HS256 JWT tokens with server-side claim validation and generic failure responses.
6. **Authorization Ring**: Strict server-side RBAC and multi-tenant farm isolation ensuring zero cross-tenant leakages.
7. **Storage Ring**: SHA-256 content-addressed media storage in isolated directory trees with strict path traversal defenses and image magic-byte verification.

---

### 4. Authentication Hardening

- **Password Hashing**: Bcrypt with unique salts per user.
- **Generic Failure Responses**: All failed authentication attempts return HTTP 401 with standard `WWW-Authenticate: Bearer` and generic message `Invalid email or password.` to eliminate username enumeration.
- **Audit Logging**: Failed login attempts trigger an asynchronous entry in `audit_logs` (`USER_LOGIN_FAILED`) tracking timestamps and originating IP/email without logging raw passwords.

---

### 5. Authorization & Multi-Tenant RBAC

| Role | Farm Scope | Telemedicine | Disease Clusters | Epidemiological Events | Government Packages | Admin Config |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Farmer** | Own Farm Only | Request / View | View Public Alerts | Signal Submission | Denied | Denied |
| **Veterinarian** | Assigned Herds | Clinical Consult | Investigate / Note | Clinical Review | Draft Preparation | Denied |
| **Institutional Officer** | Regional Herds | Oversight | Cross-Farm Monitor | Review & Confirm | Generate & Approve | Denied |
| **Administrator** | System-Wide | System-Wide | System-Wide | Full Administration | System-Wide | Full Control |

- **Strict Tenant Verification**: Farmers attempting to query animals, devices, or records from other farms are intercepted at the route handler level via database tenant matching (`owner_id == current_user["sub"]`).
- **Anti-Autonomous Outbreak Rule**: Only humans with Institutional Officer or Admin roles can formally confirm an epidemiological event; all automated algorithms are restricted to `SIGNAL` or `SUSPECT`.

---

### 6. JWT Security

- **Algorithm**: HMAC-SHA256 (`HS256`).
- **Secret Entropy**: Minimum 32 high-entropy characters enforced by `Settings.validate_production_settings()`.
- **Expiration**: Configurable via `JWT_EXPIRE_MINUTES` (defaults to 1440 minutes in development, recommended 720 minutes in production).
- **Claim Integrity**: Decodes and verifies `sub`, `email`, `role`, `exp`, and `iat`. Expired and forged signatures are rejected with HTTP 401.

---

### 7. CORS Hardening

- **Configurable Origins**: Controlled via `ALLOWED_ORIGINS` environment variable.
- **Production Ban on Wildcard**: `Settings.validate_production_settings()` explicitly rejects `*` wildcard origins when `APP_ENV=production`.
- **Default Development Origins**: Restricted to `http://localhost:8501`, `http://127.0.0.1:8501`, `http://localhost:8000`, `http://127.0.0.1:8000`, and `http://localhost:3000`.

---

### 8. Rate Limiting

- **Implementation**: Process-local sliding window rate limiter (`backend/app/middleware.py`).
- **Endpoint Limits**:
  - `POST /auth/login`: 10 requests / 60 seconds
  - `POST /auth/register`: 5 requests / 60 seconds
  - `POST /government-packages/generate`: 20 requests / 60 seconds
  - `POST /visual-health/analyze`: 30 requests / 60 seconds
  - General API: 120 requests / 60 seconds
- **Response**: HTTP 429 Too Many Requests with `Retry-After` header and structured JSON body.

---

### 9. WebSocket Security

- **Endpoint**: `/ws/monitoring`
- **Authentication**: Accepts JWT via `?token=` query parameter or in-band `{"type": "auth", "token": "..."}` message.
- **Policy Violation**: Invalid or expired tokens trigger an immediate WebSocket close with RFC 6455 status code `1008` (Policy Violation).
- **Heartbeat Preservation**: Ping/pong heartbeat frames continue to operate cleanly for UI health indicators and IoT simulator telemetry.

---

### 10. File Upload & Media Security

- **Path Traversal Defense**: All filenames are passed through `sanitize_filename()` stripping `..`, `/`, `\`, null bytes, and control characters.
- **Storage Isolation**: Files are written into isolated directories (`media/images/`, `media/videos/`) under SHA-256 hash-derived filenames (`{sha256[:16]}_{timestamp}.{ext}`).
- **Format Whitelist**: Strictly `.jpg`, `.jpeg`, `.png`, `.webp` for images; `.mp4`, `.avi`, `.mov` for video.
- **Magic Byte Verification**: Verified via PIL `Image.verify()` and binary file signature validation.

---

### 11. MongoDB Production Hardening

- **Connection Pool**: `minPoolSize=5`, `maxPoolSize=50`.
- **Timeouts**: `connectTimeoutMS=5000`, `serverSelectionTimeoutMS=5000`.
- **Safe Lifecycle**: `check_database_readiness()` performs ping checks without exposing connection URLs in error traces.

---

### 12. Structured Logging

- **Format**: Machine-readable JSON output via `StructuredLogFormatter`.
- **Attributes**: `timestamp`, `level`, `logger`, `message`, `request_id`, `method`, `path`, `status_code`, `duration_ms`, `client_ip`.
- **PII / Secret Masking**: Automatic regex redaction of keys containing `password`, `token`, `secret`, `api_key`, `authorization`, `credentials`.

---

### 13. Health & Readiness Probes

- **Liveness Probe**: `GET /health` (lightweight ping, returns HTTP 200).
- **Readiness Probe**: `GET /health/ready` (validates MongoDB connection pool and production settings, returns HTTP 200 if ready, HTTP 503 if degraded).

---

### 14. Containerized Docker Deployment

- **Base Image**: `python:3.11-slim`
- **Non-Root User**: `vetra` (UID 1000)
- **Compose Services**: `vetra-backend` (FastAPI) and `vetra-frontend` (Streamlit)
- **Volume Mounts**: Isolated named volumes for media storage and runtime logs.

---

### 15. Known Limitations & Production Recommendations

1. **Distributed Rate Limiting**: In multi-instance / autoscaled deployments, replace the in-memory sliding window rate limiter with a Redis-backed gateway rate limiter.
2. **Reverse Proxy TLS**: TLS certificates must be managed at the reverse proxy layer (Nginx/Cloudflare/AWS ALB). VETRA does not bundle fake certificates.
3. **Government Integration**: The government integration adapter state remains `NOT_CONFIGURED` until genuine statutory credentials and data-sharing agreements are configured.
