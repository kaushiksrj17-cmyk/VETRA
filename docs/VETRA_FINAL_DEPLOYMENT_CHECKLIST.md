# VETRA — Final Production Deployment Checklist
## Operational Readiness, Pre-Flight Verification & Go-Live Protocol

**Platform:** VETRA Intelligent Livestock Health Platform  
**Document:** `docs/VETRA_FINAL_DEPLOYMENT_CHECKLIST.md`  
**Version:** `15.0.0-SIH-FINAL`  

---

## 1. Pre-Flight Verification Matrix

| Checklist Category | Verification Item | Production Requirement | Verification Method | Status |
|---|---|---|---|:---:|
| **Environment & Config** | Environment Classification | `APP_ENV=production` | Checked via `app.config.Settings.APP_ENV` | **READY** |
| **Environment & Config** | Secret Hygiene | 256-bit cryptographic `JWT_SECRET`; zero default strings | Verified via `validate_production_settings()` | **READY** |
| **Environment & Config** | Debug Mode Disabled | `DEBUG=false` strictly enforced in production | Verified via `app.config.Settings.DEBUG` | **READY** |
| **Environment & Config** | Logging Configuration | JSON structured logging with PII/key redaction active | Tested via `app.logging_config.setup_logging` | **READY** |
| **Database & Persistence** | MongoDB Connection Pool | `minPoolSize=5`, `maxPoolSize=50` | Validated in `app.database.get_database` | **READY** |
| **Database & Persistence** | Socket Timeouts | `connectTimeoutMS=5000`, `serverSelectionTimeoutMS=5000` | Configured in MongoDB client factory | **READY** |
| **Database & Persistence** | Unique Indexes | Compound unique indexes on all primary business keys | Validated across all phase schema tests | **READY** |
| **Database & Persistence** | Baseline Preservation | Production collections intact (11 animals, 847 vitals) | Confirmed: 0 baseline mutations | **READY** |
| **Security & Middleware** | Rate Limiting | Sliding window (120 req / 60s per IP) enabled | Verified via `tests/test_phase_14.py` | **READY** |
| **Security & Middleware** | Security Headers | `nosniff`, `SAMEORIGIN`, `strict-origin`, `X-Request-ID` | Confirmed via `tests/test_phase_15.py::test_37` | **READY** |
| **Security & Middleware** | CORS Protection | Strict origin whitelisting; wildcards (`*`) blocked | Validated in `app.main.py` CORS setup | **READY** |
| **Security & Middleware** | WebSocket Auth | RFC 6455 policy violation `1008` closure for invalid tokens | Validated in `app.routes.websocket.py` | **READY** |
| **Security & Middleware** | File Upload Security | Magic byte validation, filename sanitization, 25MB ceiling | Validated in `app.services.media_service.py` | **READY** |
| **Containers & Runtime** | Non-Root Container User | Docker containers execute as user `vetra` (UID 1000) | Inspected in `Dockerfile.backend` & `frontend` | **READY** |
| **Containers & Runtime** | Orchestration Network | Isolated bridge network `vetra-net` | Confirmed in `docker-compose.yml` | **READY** |
| **Containers & Runtime** | Volume Mounts | Dedicated persistent volumes for `media/` and `logs/` | Verified in `docker-compose.yml` | **READY** |
| **Containers & Runtime** | Liveness & Readiness | Automated HTTP health checks against `/health` and `/health/ready` | Configured with 30s interval, 3 retries | **READY** |
| **AI & Clinical Safety** | Deterministic Fallback | Tier 1 algorithms operational if Gemini API is offline | Tested in `tests/test_phase_15.py::test_08` | **READY** |
| **AI & Clinical Safety** | Clinical Triage Disclaimer | Disclaimers attached to all risk models and CV outputs | Verified across all AI schemas | **READY** |
| **AI & Clinical Safety** | Outbreak Prohibition | Anti-autonomous outbreak rule active (HTTP 403) | Tested in `tests/test_phase_15.py::test_15` | **READY** |
| **Statutory Integration**| Adapter Sandbox State | Government adapter defaults to `NOT_CONFIGURED` | Verified in `tests/test_phase_15.py::test_22` | **READY** |
| **Statutory Integration**| Gate 5 Dispatch Blocking| Live transmissions safely halted at Gate 5 | Verified in `tests/test_phase_15.py::test_23` | **READY** |
| **Statutory Integration**| Statutory Disclaimer | Watermark: *"Government-ready export package — not an official submission"* | Verified in `tests/test_phase_15.py::test_24` | **READY** |

---

## 2. Step-by-Step Go-Live Runbook

### Step 1: Host Preparation
- Verify Docker 24.0+ and Docker Compose v2.20+ are installed.
- Ensure host ports `8000` (FastAPI) and `8501` (Streamlit) are available and unallocated.

### Step 2: Environment Configuration
1. Copy `.env.example` to production `.env`:
   ```bash
   cp .env.example .env
   ```
2. Populate the production `.env` variables:
   - Generate a secure 32-byte secret: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Assign `JWT_SECRET=<generated_token>`
   - Provide production MongoDB Atlas connection string: `MONGODB_URL=mongodb+srv://...`
   - Set `APP_ENV=production` and `DEBUG=false`
   - Specify allowed origins: `ALLOWED_ORIGINS=https://vetra.yourdomain.in`

### Step 3: Container Build & Launch
Execute Docker Compose with container build and detached execution:
```bash
docker compose up -d --build
```

### Step 4: Post-Launch Liveness Probes
1. **API Liveness Check:**
   ```bash
   curl -f http://localhost:8000/health
   ```
   *Expected Response:* `{"status": "healthy", "database": "connected", "backend": "online", ...}`
2. **Readiness Probe:**
   ```bash
   curl -f http://localhost:8000/health/ready
   ```
   *Expected Response:* HTTP 200 `{"status": "ready", "database": "connected", ...}`
3. **Frontend Accessibility:**
   Open browser at `http://localhost:8501` and verify the VETRA Command Center loads with the top navigation bar.

### Step 5: Automated Security Verification
Run the automated security audit against the running instance:
```bash
.\.venv\Scripts\python.exe scripts\security_audit.py
```
*Requirement:* Must return `10 PASSED | 0 WARNINGS | 0 FAILURES`.

---

## 3. Disaster Recovery & Rollback Protocol

- **Recovery Point Objective (RPO):** < 15 minutes (via MongoDB continuous automated cloud backups).
- **Recovery Time Objective (RTO):** < 5 minutes (container restart / rollback).
- **Fast Rollback Command:**
  ```bash
  docker compose down
  docker compose up -d --no-build
  ```
- **Audit Ledger Immutability:** In the event of system restart or failover, the `audit_logs` collection preserves cryptographic SHA-256 historical action entries.
