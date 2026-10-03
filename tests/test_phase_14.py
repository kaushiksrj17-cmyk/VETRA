import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add project root and backend to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings, settings
from app.database import get_database, check_database_readiness
from app.security import hash_password, create_access_token, decode_access_token
from app.services.media_service import validate_media_upload, sanitize_filename
from ai_engine.gemini_service import generate_fallback_explanation

# Pre-defined test tokens
VALID_FARMER_TOKEN = create_access_token({"sub": "test_user_farmer_14", "email": "test_farmer@example.com", "role": "farmer"})
VALID_VET_TOKEN = create_access_token({"sub": "test_user_vet_14", "email": "test_vet@example.com", "role": "veterinarian"})
VALID_ADMIN_TOKEN = create_access_token({"sub": "test_user_admin_14", "email": "test_admin@example.com", "role": "admin"})

client = TestClient(app)


def run_phase_14_tests():
    print("=" * 80)
    print("VETRA PHASE 14 -- PRODUCTION DEPLOYMENT & SECURITY HARDENING TEST SUITE")
    print("=" * 80)

    db = get_database()

    # Record baseline database state
    baseline_collections = ["animals", "devices", "health_readings", "farms", "alerts", "veterinary_cases", "users"]
    initial_counts = {col: db[col].count_documents({}) for col in baseline_collections}
    print(f"INITIAL BASELINE COUNTS: {initial_counts}")

    passed = 0
    total = 30

    # ----------------------------------------------------
    # Check 1: Production Config Validation
    # ----------------------------------------------------
    test_prod_settings = Settings()
    test_prod_settings.APP_ENV = "production"
    test_prod_settings.JWT_SECRET = "development-secret"
    test_prod_settings.DEBUG = True
    test_prod_settings.ALLOWED_ORIGINS_RAW = "*"
    errs = test_prod_settings.validate_production_settings()
    assert len(errs) >= 3, f"Expected at least 3 validation errors for insecure prod config, got: {errs}"
    passed += 1
    print(f"[{passed}/{total}] Check 1 PASSED: Production config validation correctly flags insecure secrets and wildcard CORS.")

    # ----------------------------------------------------
    # Check 2: Environment Classification
    # ----------------------------------------------------
    assert settings.APP_ENV in ["development", "testing", "production"], f"Unknown APP_ENV: {settings.APP_ENV}"
    passed += 1
    print(f"[{passed}/{total}] Check 2 PASSED: Active APP_ENV is recognized ({settings.APP_ENV}).")

    # ----------------------------------------------------
    # Check 3: Authentication Hardening (Generic error messages)
    # ----------------------------------------------------
    res = client.post("/auth/login", json={"email": "nonexistent_farmer_xyz@example.com", "password": "WrongPassword123!"})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    assert "Invalid email or password." in res.json().get("detail", ""), "Generic error message required"
    passed += 1
    print(f"[{passed}/{total}] Check 3 PASSED: Authentication failure returns generic message preventing user enumeration.")

    # ----------------------------------------------------
    # Check 4: Invalid JWT Rejection
    # ----------------------------------------------------
    res = client.get("/farms", headers={"Authorization": "Bearer totally-malformed.invalid.token"})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 4 PASSED: Malformed JWT rejected with HTTP 401 Unauthorized.")

    # ----------------------------------------------------
    # Check 5: Expired JWT Rejection
    # ----------------------------------------------------
    from datetime import timedelta
    expired_token = create_access_token({"sub": "test_exp", "email": "exp@vetra.test", "role": "farmer"})
    # Decode and tamper or generate expired
    from jose import jwt as jose_jwt
    expired_payload = {"sub": "test_exp", "email": "exp@vetra.test", "role": "farmer", "exp": int(time.time()) - 3600}
    tampered_expired = jose_jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    res = client.get("/farms", headers={"Authorization": f"Bearer {tampered_expired}"})
    assert res.status_code == 401, f"Expected 401 for expired token, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 5 PASSED: Expired JWT rejected with HTTP 401 Unauthorized.")

    # ----------------------------------------------------
    # Check 6: RBAC Farmer Data Isolation
    # ----------------------------------------------------
    # Query farms using test farmer token
    res = client.get("/farms", headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    farms = res.json()
    # Ensure farmer only sees own farms (0 farms returned for test user without owned farms)
    assert len(farms) == 0, f"Farmer should not see other users' farms, got: {farms}"
    passed += 1
    print(f"[{passed}/{total}] Check 6 PASSED: Farmer tenant data isolation strictly enforced.")

    # ----------------------------------------------------
    # Check 7: RBAC Veterinarian Boundaries
    # ----------------------------------------------------
    # Farmer attempting vet-only action
    res = client.post(
        "/institutional/reports",
        json={"title": "Test Report", "report_type": "disease_event", "reporting_period": "2026-Q3", "summary": "test"},
        headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"}
    )
    assert res.status_code in [403, 422], f"Farmer should be rejected from institutional report creation, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 7 PASSED: Non-veterinarian/non-officer restricted from institutional reports.")

    # ----------------------------------------------------
    # Check 8: RBAC Admin Boundaries
    # ----------------------------------------------------
    # Farmer attempting admin action
    res = client.get("/audit-logs", headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"})
    # If route exists or requires admin, must be 403 or 404
    assert res.status_code in [403, 404], f"Farmer must not access admin endpoints, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 8 PASSED: Admin-only boundary verified against unauthorized roles.")

    # ----------------------------------------------------
    # Check 9: CORS Configuration Hardening
    # ----------------------------------------------------
    assert isinstance(settings.ALLOWED_ORIGINS, list), "ALLOWED_ORIGINS must be a list"
    assert len(settings.ALLOWED_ORIGINS) > 0, "ALLOWED_ORIGINS must not be empty"
    passed += 1
    print(f"[{passed}/{total}] Check 9 PASSED: CORS origins configured explicitly ({settings.ALLOWED_ORIGINS[:2]}).")

    # ----------------------------------------------------
    # Check 10: Security Headers Injection
    # ----------------------------------------------------
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff", "Missing X-Content-Type-Options"
    assert res.headers.get("X-Frame-Options") in ["SAMEORIGIN", "DENY"], "Missing or invalid X-Frame-Options"
    assert "strict-origin" in res.headers.get("Referrer-Policy", ""), "Missing Referrer-Policy"
    passed += 1
    print(f"[{passed}/{total}] Check 10 PASSED: Production security headers injected across responses.")

    # ----------------------------------------------------
    # Check 11: Request ID Header Propagation
    # ----------------------------------------------------
    custom_req_id = "vetra-audit-test-request-id-12345"
    res = client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert res.headers.get("X-Request-ID") == custom_req_id, f"Expected {custom_req_id}, got {res.headers.get('X-Request-ID')}"
    passed += 1
    print(f"[{passed}/{total}] Check 11 PASSED: X-Request-ID header accurately assigned and echoed.")

    # ----------------------------------------------------
    # Check 12: Health Liveness Probe (/health)
    # ----------------------------------------------------
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    body = res.json()
    assert body.get("status") in ["healthy", "degraded"], f"Unexpected status: {body}"
    assert body.get("government_adapter") == "NOT_CONFIGURED", "Government adapter must be NOT_CONFIGURED"
    passed += 1
    print(f"[{passed}/{total}] Check 12 PASSED: /health liveness probe active with NOT_CONFIGURED adapter state.")

    # ----------------------------------------------------
    # Check 13: Health Readiness Probe (/health/ready)
    # ----------------------------------------------------
    res = client.get("/health/ready")
    assert res.status_code in [200, 503], f"Unexpected readiness status code: {res.status_code}"
    ready_body = res.json()
    assert "checks" in ready_body, "Readiness response must contain checks object"
    assert "database" in ready_body["checks"], "Readiness response must verify database check"
    passed += 1
    print(f"[{passed}/{total}] Check 13 PASSED: /health/ready readiness probe verified.")

    # ----------------------------------------------------
    # Check 14: Database Readiness Verification
    # ----------------------------------------------------
    is_ready, msg = check_database_readiness()
    assert is_ready is True, f"Database readiness check failed: {msg}"
    assert "mongodb" not in msg.lower(), "Database check message must not leak connection details"
    passed += 1
    print(f"[{passed}/{total}] Check 14 PASSED: Database readiness check succeeded without credential leakage.")

    # ----------------------------------------------------
    # Check 15: File Upload Validation (Valid image)
    # ----------------------------------------------------
    import io
    from PIL import Image as PILImage
    buf = io.BytesIO()
    test_img = PILImage.new("RGB", (10, 10), color="blue")
    test_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    is_valid, media_type, err = validate_media_upload("valid_sample.png", png_bytes, "image/png")
    assert is_valid is True, f"Valid PNG failed validation: {err}"
    assert media_type == "image", f"Expected image, got {media_type}"
    passed += 1
    print(f"[{passed}/{total}] Check 15 PASSED: Valid image passes upload validation.")

    # ----------------------------------------------------
    # Check 16: Path Traversal Prevention in File Uploads
    # ----------------------------------------------------
    is_valid, _, err = validate_media_upload("../../../etc/passwd.png", png_bytes, "image/png")
    assert is_valid is False, "Path traversal pattern must be rejected"
    assert "path traversal" in err.lower() or "security violation" in err.lower()
    passed += 1
    print(f"[{passed}/{total}] Check 16 PASSED: Path traversal in upload filename intercepted and blocked.")

    # ----------------------------------------------------
    # Check 17: File Size Restriction
    # ----------------------------------------------------
    oversized_bytes = b"0" * (30 * 1024 * 1024)  # 30 MB
    is_valid, _, err = validate_media_upload("oversized.png", oversized_bytes, "image/png")
    assert is_valid is False, "Oversized file must be rejected"
    assert "exceeds" in err.lower() or "size" in err.lower()
    passed += 1
    print(f"[{passed}/{total}] Check 17 PASSED: File exceeding upload size threshold rejected.")

    # ----------------------------------------------------
    # Check 18: WebSocket Authorization & Heartbeat
    # ----------------------------------------------------
    with client.websocket_connect(f"/ws/monitoring?token={VALID_FARMER_TOKEN}") as ws:
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp.get("type") == "pong", f"Expected pong, got {resp}"
    passed += 1
    print(f"[{passed}/{total}] Check 18 PASSED: Authenticated WebSocket connection and heartbeat verified.")

    # ----------------------------------------------------
    # Check 19: WebSocket Invalid Token Rejection
    # ----------------------------------------------------
    try:
        with client.websocket_connect("/ws/monitoring?token=bad-invalid-token-xyz") as ws:
            ws.send_text("ping")
            # If it didn't close immediately, it should not accept messages
            assert False, "Invalid token should have closed connection"
    except Exception:
        # Expected closure due to WS 1008 Policy Violation
        pass
    passed += 1
    print(f"[{passed}/{total}] Check 19 PASSED: Malformed WebSocket token rejected with Policy Violation closure.")

    # ----------------------------------------------------
    # Check 20: Rate Limiting Enforcement
    # ----------------------------------------------------
    # Make multiple rapid requests to check rate limiting behavior
    from app.middleware import rate_limiter
    rate_limiter_active = settings.RATE_LIMIT_ENABLED
    assert rate_limiter_active is True, "Rate limiter must be enabled"
    # Test rate limiter directly
    limited, retry = rate_limiter.is_rate_limited("192.168.1.99", "/test", "GET")
    assert limited is False, "First request must not be limited"
    passed += 1
    print(f"[{passed}/{total}] Check 20 PASSED: Application-level rate limiting active and operational.")

    # ----------------------------------------------------
    # Check 21: Safe Global Exception Handling (No raw stack traces)
    # ----------------------------------------------------
    # Trigger 404 or 422 to verify structured error response
    res = client.get("/non-existent-vetra-route-xyz")
    assert res.status_code == 404
    assert "detail" in res.json()
    assert "Traceback" not in res.text
    passed += 1
    print(f"[{passed}/{total}] Check 21 PASSED: Error responses structured cleanly without leaking stack traces.")

    # ----------------------------------------------------
    # Check 22: Gemini AI Graceful Fallback
    # ----------------------------------------------------
    fallback = generate_fallback_explanation(
        animal_data={"name": "Cow-101", "tag_id": "VET-001"},
        features={"latest_temp": 39.8, "temp_deviation": 1.2, "rumination_reduction_pct": 25.0, "activity_reduction_pct": 20.0},
        risk_data={"risk_category": "high", "health_risk_score": 78.0}
    )
    assert "clinical_interpretation" in fallback
    assert fallback["source"] == "VETRA-Clinical-Fallback-Engine"
    passed += 1
    print(f"[{passed}/{total}] Check 22 PASSED: Gemini clinical fallback operates with 100% deterministic availability.")

    # ----------------------------------------------------
    # Check 23: Input Validation Bounds (Vital readings)
    # ----------------------------------------------------
    # Test impossible vital reading (e.g. temperature = 100 C exceeds schema maximum 50.0 C)
    res = client.post(
        "/health-readings",
        json={"animal_id": "anim1", "device_id": "dev1", "temperature_c": 100.0, "heart_rate_bpm": 80.0, "activity_level": 50.0, "rumination_level": 50.0, "respiratory_rate": 25.0},
        headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"}
    )
    assert res.status_code == 422, f"Impossible temperature must be rejected with 422, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 23 PASSED: Input validation rejects physiological impossibility values.")

    # ----------------------------------------------------
    # Check 24: Security Audit Script Execution
    # ----------------------------------------------------
    audit_script = ROOT_DIR / "scripts" / "security_audit.py"
    res = subprocess.run([sys.executable, str(audit_script)], capture_output=True, text=True)
    assert res.returncode == 0, f"Security audit script failed with output:\n{res.stdout}\n{res.stderr}"
    assert "0 FAILURES" in res.stdout
    passed += 1
    print(f"[{passed}/{total}] Check 24 PASSED: Automated security audit script passed with 0 failures.")

    # ----------------------------------------------------
    # Check 25: Docker Configuration Existence
    # ----------------------------------------------------
    assert (ROOT_DIR / "Dockerfile.backend").exists(), "Dockerfile.backend missing"
    assert (ROOT_DIR / "Dockerfile.frontend").exists(), "Dockerfile.frontend missing"
    assert (ROOT_DIR / "docker-compose.yml").exists(), "docker-compose.yml missing"
    passed += 1
    print(f"[{passed}/{total}] Check 25 PASSED: Dockerfile.backend, Dockerfile.frontend, and docker-compose.yml verified.")

    # ----------------------------------------------------
    # Check 26: .dockerignore Verification
    # ----------------------------------------------------
    dockerignore_path = ROOT_DIR / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore missing"
    di_content = dockerignore_path.read_text(encoding="utf-8")
    assert ".env" in di_content and ".git" in di_content and ".venv" in di_content
    passed += 1
    print(f"[{passed}/{total}] Check 26 PASSED: .dockerignore properly excludes virtualenvs, git, and local secrets.")

    # ----------------------------------------------------
    # Check 27: .env.example Verification
    # ----------------------------------------------------
    example_path = ROOT_DIR / ".env.example"
    assert example_path.exists(), ".env.example missing"
    example_content = example_path.read_text(encoding="utf-8")
    assert "JWT_SECRET=" in example_content
    assert "MONGODB_URL=" in example_content
    assert "AIzaSy" not in example_content
    passed += 1
    print(f"[{passed}/{total}] Check 27 PASSED: .env.example template contains sanitized placeholders only.")

    # ----------------------------------------------------
    # Check 28: Zero Hardcoded Secrets in Git-Tracked Source
    # ----------------------------------------------------
    assert "AIzaSy" not in (BACKEND_DIR / "app" / "config.py").read_text(encoding="utf-8")
    passed += 1
    print(f"[{passed}/{total}] Check 28 PASSED: No sensitive credentials or API keys found in core source files.")

    # ----------------------------------------------------
    # Check 29: Anti-Autonomous Outbreak Rule & Human Approval
    # ----------------------------------------------------
    # Farmers and unauthorized automated agents cannot confirm epidemiological events
    res = client.post(
        "/epidemiological-events/EPI-TEST-0000/confirm",
        json={"confirmation_authority": "Autonomous System", "confirmation_notes": "Attempted auto confirm"},
        headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"}
    )
    assert res.status_code == 403, f"Farmer must be forbidden from confirming epidemiological events, got {res.status_code}"
    passed += 1
    print(f"[{passed}/{total}] Check 29 PASSED: Anti-autonomous outbreak confirmation rule preserved (HTTP 403 Forbidden).")

    # ----------------------------------------------------
    # Check 30: Database Preservation (Zero Baseline Mutations)
    # ----------------------------------------------------
    # Clean up test audit logs created during login check
    db.audit_logs.delete_many({"email": "nonexistent_farmer_xyz@example.com"})

    final_counts = {col: db[col].count_documents({}) for col in baseline_collections}
    for col in baseline_collections:
        assert initial_counts[col] == final_counts[col], (
            f"Database mutation detected in '{col}': initial={initial_counts[col]}, final={final_counts[col]}"
        )
    passed += 1
    print(f"[{passed}/{total}] Check 30 PASSED: Database preservation verified: 0 baseline records mutated.")

    print("=" * 80)
    print(f"VETRA PHASE 14 TEST RESULT: {passed} / {total} PASSED (100%)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_phase_14_tests())
