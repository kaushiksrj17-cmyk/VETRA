# VETRA — Platform Deployment Guide
## Production & Local Environment Runbook

---

### Overview

VETRA supports two distinct, isolated deployment modes:
1. **Mode A: Local Development** (Python Virtual Environment on Windows / Linux / macOS)
2. **Mode B: Containerized Production** (Docker Compose with hardened non-root containers)

Neither mode requires Node.js, npm, or external frontend build tooling.

---

### Mode A: Local Development

#### Prerequisites
- Python 3.11 installed
- MongoDB Atlas cluster URL (or local MongoDB 6+)
- Google Gemini API key (optional for core telemetry, required for AI narratives)

#### Step 1: Virtual Environment Activation
Open PowerShell in the project root:

```powershell
cd D:\VETRA
.\.venv\Scripts\Activate.ps1
```

#### Step 2: Environment Configuration
Copy `.env.example` to `.env` if not already present:

```powershell
cp .env.example .env
```

Ensure the following variables are configured in `.env`:
```env
APP_NAME=VETRA
APP_ENV=development
DEBUG=true
MONGODB_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=vetra
GEMINI_API_KEY=<your-gemini-key>
JWT_SECRET=development-secret-for-local-testing-only
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
RATE_LIMIT_ENABLED=true
SECURITY_HEADERS_ENABLED=true
```

#### Step 3: Run FastAPI Backend
In Terminal 1:

```powershell
cd D:\VETRA\backend
..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base:** `http://127.0.0.1:8000`
- **Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs`
- **Liveness Probe:** `http://127.0.0.1:8000/health`
- **Readiness Probe:** `http://127.0.0.1:8000/health/ready`

#### Step 4: Run Streamlit Frontend
In Terminal 2:

```powershell
cd D:\VETRA
.\.venv\Scripts\Activate.ps1
streamlit run .\frontend\app.py --server.port=8501
```

The UI dashboard will open at:
- **Web App:** `http://localhost:8501`

#### Step 5: (Optional) Run IoT Telemetry Simulator
In Terminal 3:

```powershell
cd D:\VETRA
.\.venv\Scripts\Activate.ps1
python simulator/iot_simulator.py
```

---

### Mode B: Containerized Production (Docker Compose)

#### Architecture
```
  [ Reverse Proxy / HTTPS Load Balancer ]
                    │
            ┌───────┴───────┐
            │               │
            ▼               ▼
      [Port 8501]       [Port 8000]
    vetra-frontend     vetra-backend
   (Streamlit App)    (FastAPI Service)
            │               │
            └───────┬───────┘
                    │
                    ▼
          [ MongoDB Atlas (SaaS) ]
```

#### Step 1: Configure Production Environment
Create `.env` in the project root:

```env
APP_NAME=VETRA
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=https://vetra.yourdomain.com,https://api.vetra.yourdomain.com
MONGODB_URL=mongodb+srv://<prod-user>:<prod-password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=vetra
GEMINI_API_KEY=<your-production-gemini-key>
JWT_SECRET=<generate-at-least-32-random-alphanumeric-characters>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=720
SECURITY_HEADERS_ENABLED=true
MAX_UPLOAD_SIZE_MB=25
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
WEBSOCKET_AUTH_REQUIRED=false
```

#### Step 2: Build Containers
```bash
docker compose build
```

#### Step 3: Launch Services in Background
```bash
docker compose up -d
```

#### Step 4: Verify Deployment Health
```bash
# Verify container statuses
docker compose ps

# Check backend liveness and readiness
curl -f http://localhost:8000/health
curl -f http://localhost:8000/health/ready

# Check Streamlit health
curl -f http://localhost:8501/_stcore/health
```

#### Step 5: View Logs
```bash
# Tail structured JSON logs from backend
docker compose logs -f vetra-backend

# Tail frontend logs
docker compose logs -f vetra-frontend
```

#### Step 6: Teardown / Stop Containers
```bash
docker compose down
```

---

### Mode C: Reverse Proxy & HTTPS Configuration (Nginx Reference)

For public enterprise deployments, place Nginx in front of Docker containers with TLS certificates managed via Let's Encrypt / Certbot:

```nginx
# Upstream definitions
upstream vetra_backend {
    server 127.0.0.1:8000;
}

upstream vetra_frontend {
    server 127.0.0.1:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name vetra.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name vetra.example.com;

    ssl_certificate /etc/letsencrypt/live/vetra.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vetra.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Streamlit UI
    location / {
        proxy_pass http://vetra_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # FastAPI REST & WebSocket
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://vetra_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
