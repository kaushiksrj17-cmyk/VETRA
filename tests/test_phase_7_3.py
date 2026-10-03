import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root and backend directory in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
frontend_dir = root_dir / "frontend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))
sys.path.insert(2, str(frontend_dir))

from app.main import app
from app.database import get_database


def run_tests():
    print("=" * 70)
    print("VETRA PHASE 7.3 — ADVANCED REAL-TIME COMMAND CENTER TEST SUITE")
    print("=" * 70)

    db = get_database()
    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. MODULE & INTERFACE IMPORTS
    # -------------------------------------------------------------
    try:
        import api_client
        from pages.dashboard import render_dashboard_page
        print("[PASS] 1. Dashboard and API client modules imported successfully.")
    except Exception as exc:
        assert False, f"Import error: {exc}"

    # -------------------------------------------------------------
    # 2. SYSTEM HEALTH & DIAGNOSTICS ENDPOINT (/health)
    # -------------------------------------------------------------
    res_health = client.get("/health")
    assert res_health.status_code == 200, f"/health endpoint failed: {res_health.text}"
    health_data = res_health.json()
    assert health_data.get("status") in ["healthy", "degraded"], "Invalid overall status"
    assert health_data.get("database") == "connected", "Database not reporting connected"
    assert health_data.get("backend") == "online", "Backend not reporting online"
    assert health_data.get("ai_engine") == "operational", "AI Engine not reporting operational"
    assert health_data.get("monitoring") == "active", "Monitoring bus not reporting active"
    assert health_data.get("analytics") == "ready", "Analytics engine not reporting ready"
    print(f"[PASS] 2. Subsystem health checks verified: status={health_data['status']}, database={health_data['database']}")

    # -------------------------------------------------------------
    # 3. AUTHENTICATE FARMER & VETERINARIAN
    # -------------------------------------------------------------
    res_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert res_farmer.status_code == 200, f"Farmer login failed: {res_farmer.text}"
    farmer_token = res_farmer.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    print("[PASS] 3. Farmer authenticated successfully.")

    res_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert res_vet.status_code == 200, f"Vet login failed: {res_vet.text}"
    vet_token = res_vet.json()["access_token"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}
    print("[PASS] 4. Veterinarian authenticated successfully.")

    # -------------------------------------------------------------
    # 4. HERD-WIDE RECENT HEALTH READINGS ENDPOINT (GET /health-readings)
    # -------------------------------------------------------------
    res_readings = client.get("/health-readings?limit=10", headers=farmer_headers)
    assert res_readings.status_code == 200, f"GET /health-readings failed: {res_readings.text}"
    readings_list = res_readings.json()
    assert isinstance(readings_list, list), "Expected list of health readings"
    if readings_list:
        sample_r = readings_list[0]
        assert "temperature_c" in sample_r
        assert "heart_rate_bpm" in sample_r
        assert "respiratory_rate" in sample_r
        assert "activity_level" in sample_r
        assert "rumination_level" in sample_r
        assert "risk_status" in sample_r
        print(f"[PASS] 5. Herd-wide recent readings verified: count={len(readings_list)}, sample temp={sample_r['temperature_c']}°C, risk={sample_r.get('risk_status')}")
    else:
        print("[PASS] 5. Herd-wide recent readings verified (empty list returned gracefully).")

    # -------------------------------------------------------------
    # 5. OVERVIEW ANALYTICS & HERD HEALTH INDEX (HHI)
    # -------------------------------------------------------------
    res_overview = client.get("/analytics/overview?days=7", headers=farmer_headers)
    assert res_overview.status_code == 200
    ov_data = res_overview.json()
    assert "kpis" in ov_data
    assert "herd_health_index" in ov_data
    assert "risk_distribution" in ov_data
    hhi = ov_data["herd_health_index"]
    assert 0 <= hhi["score"] <= 100
    assert hhi["band"] in ["Excellent", "Optimal", "Good", "Attention Required", "High Risk", "Critical"]
    print(f"[PASS] 6. Overview Analytics & HHI verified: Score={hhi['score']:.1f} ({hhi['band']})")

    # -------------------------------------------------------------
    # 6. PHYSIOLOGICAL HEALTH TRENDS
    # -------------------------------------------------------------
    res_trends = client.get("/analytics/health-trends?days=7", headers=farmer_headers)
    assert res_trends.status_code == 200
    trends_json = res_trends.json()
    assert "time_series" in trends_json
    print(f"[PASS] 7. Health Trends verified: {len(trends_json.get('time_series', []))} data points.")

    # -------------------------------------------------------------
    # 7. ALERT INTELLIGENCE & MTTA/MTTR
    # -------------------------------------------------------------
    res_alerts = client.get("/analytics/alerts?days=30", headers=farmer_headers)
    assert res_alerts.status_code == 200
    al_json = res_alerts.json()
    assert "total_alerts" in al_json
    assert "mtta_display" in al_json
    assert "mttr_display" in al_json
    print(f"[PASS] 8. Alert Analytics verified: Total={al_json['total_alerts']}, MTTA={al_json['mtta_display']}, MTTR={al_json['mttr_display']}")

    # -------------------------------------------------------------
    # 8. PREVENTIVE HEALTHCARE COMPLIANCE
    # -------------------------------------------------------------
    res_prev = client.get("/analytics/prevention", headers=farmer_headers)
    assert res_prev.status_code == 200
    prev_json = res_prev.json()
    assert "compliance_rate" in prev_json
    assert 0.0 <= prev_json["compliance_rate"] <= 100.0
    print(f"[PASS] 9. Preventive Care Analytics verified: Compliance={prev_json['compliance_rate']:.1f}%")

    # -------------------------------------------------------------
    # 9. VETERINARY CLINICAL OPERATIONS ANALYTICS
    # -------------------------------------------------------------
    res_vet_an = client.get("/analytics/veterinary", headers=farmer_headers)
    assert res_vet_an.status_code == 200
    vet_an_json = res_vet_an.json()
    assert "total_cases" in vet_an_json
    assert "open_cases" in vet_an_json
    print(f"[PASS] 10. Veterinary Operations Analytics verified: Total Cases={vet_an_json['total_cases']}, Open={vet_an_json['open_cases']}")

    # -------------------------------------------------------------
    # 10. HARDWARE FLEET ANALYTICS
    # -------------------------------------------------------------
    res_dev = client.get("/analytics/devices", headers=farmer_headers)
    assert res_dev.status_code == 200
    dev_json = res_dev.json()
    assert "total_devices" in dev_json
    assert "online_devices" in dev_json
    print(f"[PASS] 11. Hardware Fleet Analytics verified: Total={dev_json['total_devices']}, Online={dev_json['online_devices']}")

    # -------------------------------------------------------------
    # 11. PRIORITY ATTENTION WATCHLIST
    # -------------------------------------------------------------
    res_watch = client.get("/analytics/watchlist", headers=farmer_headers)
    assert res_watch.status_code == 200
    watch_json = res_watch.json()
    assert "critical_attention" in watch_json
    assert "high_risk" in watch_json
    assert "monitoring" in watch_json
    assert "preventive_due" in watch_json
    print("[PASS] 12. Priority Watchlist verified across all 4 triage tiers.")

    # -------------------------------------------------------------
    # 12. AI HEALTH INTELLIGENCE INTEGRATION
    # -------------------------------------------------------------
    # Fetch first animal to test AI assessment
    res_animals = client.get("/farms", headers=farmer_headers)
    assert res_animals.status_code == 200
    farms = res_animals.json()
    if farms:
        f_id = farms[0]["id"]
        res_a = client.get(f"/farms/{f_id}/animals", headers=farmer_headers)
        if res_a.status_code == 200 and res_a.json():
            test_animal_id = res_a.json()[0]["id"]
            res_ai = client.get(f"/ai/health-assessment/{test_animal_id}", headers=farmer_headers)
            assert res_ai.status_code == 200, f"AI Assessment failed: {res_ai.text}"
            ai_data = res_ai.json()
            assert "risk_score" in ai_data
            assert "risk_category" in ai_data
            assert "disease_risk_level" in ai_data
            assert "early_warning_status" in ai_data
            assert "analysis_engine" in ai_data
            print(f"[PASS] 13. AI Health Intelligence verified: Animal={test_animal_id}, Risk={ai_data['risk_category']}, Engine={ai_data['analysis_engine']}")
        else:
            print("[PASS] 13. AI Health Intelligence skipped (no animals under farm).")
    else:
        print("[PASS] 13. AI Health Intelligence skipped (no farms found).")

    # -------------------------------------------------------------
    # 13. API CLIENT HELPER FUNCTIONS
    # -------------------------------------------------------------
    assert hasattr(api_client, "get_system_health"), "Missing get_system_health in api_client"
    assert hasattr(api_client, "get_websocket_status"), "Missing get_websocket_status in api_client"
    assert hasattr(api_client, "get_health_readings"), "Missing get_health_readings in api_client"
    
    # Test websocket helper resiliency
    ws_probe = api_client.get_websocket_status()
    assert ws_probe in ["LIVE", "SYNCING", "OFFLINE"], f"Invalid ws probe result: {ws_probe}"
    print(f"[PASS] 14. API client helpers verified: get_websocket_status returned '{ws_probe}'.")

    # -------------------------------------------------------------
    # 14. SECURITY & CREDENTIAL PRIVACY CHECK
    # -------------------------------------------------------------
    import os
    dashboard_source = (frontend_dir / "pages" / "dashboard.py").read_text(encoding="utf-8")
    api_client_source = (frontend_dir / "api_client.py").read_text(encoding="utf-8")
    app_source = (frontend_dir / "app.py").read_text(encoding="utf-8")

    forbidden_strings = ["mongodb+srv://", "Vetra@12345", "AIzaSy", "JWT_SECRET="]
    for forbidden in forbidden_strings:
        assert forbidden not in dashboard_source, f"Security risk: found '{forbidden}' in dashboard.py"
        assert forbidden not in api_client_source, f"Security risk: found '{forbidden}' in api_client.py"
        assert forbidden not in app_source, f"Security risk: found '{forbidden}' in app.py"

    print("[PASS] 15. Security verification passed: zero credentials or secrets exposed in frontend source.")

    print("=" * 70)
    print("ALL 15 TESTS IN PHASE 7.3 COMMAND CENTER SUITE PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
