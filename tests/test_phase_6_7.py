import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend directory is first in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))

from app.main import app
from app.database import get_database
from app.services import analytics_service


def run_tests():
    print("=" * 70)
    print("VETRA PHASE 6.7 — ADVANCED DASHBOARDS & ANALYTICS TEST SUITE")
    print("=" * 70)

    db = get_database()
    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. AUTHENTICATE USERS
    # -------------------------------------------------------------
    res_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert res_farmer.status_code == 200, f"Farmer login failed: {res_farmer.text}"
    farmer_token = res_farmer.json()["access_token"]
    farmer_id = res_farmer.json()["user"]["id"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    print("[PASS] 1. Farmer authenticated successfully.")

    res_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert res_vet.status_code == 200, f"Vet login failed: {res_vet.text}"
    vet_token = res_vet.json()["access_token"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}
    print("[PASS] 2. Veterinarian authenticated successfully.")

    # -------------------------------------------------------------
    # 2. UNAUTHENTICATED ACCESS PROTECTION
    # -------------------------------------------------------------
    res_unauth = client.get("/analytics/overview")
    assert res_unauth.status_code in [401, 403], f"Expected 401/403 for unauthenticated request, got {res_unauth.status_code}"
    print("[PASS] 3. Unauthenticated requests blocked by security layer.")

    # -------------------------------------------------------------
    # 3. OVERVIEW ANALYTICS & HERD HEALTH INDEX (HHI)
    # -------------------------------------------------------------
    res_overview = client.get("/analytics/overview?days=7", headers=farmer_headers)
    assert res_overview.status_code == 200, f"Overview request failed: {res_overview.text}"
    ov_data = res_overview.json()
    assert "kpis" in ov_data, "Missing KPIs"
    assert "herd_health_index" in ov_data, "Missing HHI"
    assert "risk_distribution" in ov_data, "Missing risk distribution"

    hhi = ov_data["herd_health_index"]
    assert 0 <= hhi["score"] <= 100, f"HHI score out of bounds: {hhi['score']}"
    assert hhi["band"] in ["Excellent", "Optimal", "Good", "Attention Required", "High Risk", "Critical"], f"Invalid band: {hhi['band']}"
    assert len(hhi["contributing_positive"]) >= 1, "Expected positive factors"
    print(f"[PASS] 4. Overview Analytics verified: HHI Score={hhi['score']:.1f} ({hhi['band']}), Total Animals={ov_data['kpis']['total_animals']}")

    # -------------------------------------------------------------
    # 4. HEALTH TRENDS TIME-SERIES
    # -------------------------------------------------------------
    res_trends = client.get("/analytics/health-trends?days=7", headers=farmer_headers)
    assert res_trends.status_code == 200, f"Health trends request failed: {res_trends.text}"
    tr_data = res_trends.json()
    assert "period_days" in tr_data
    assert "time_series" in tr_data
    assert "averages" in tr_data
    assert "safe_zones" in tr_data
    print(f"[PASS] 5. Health Trends verified: {len(tr_data['time_series'])} aggregate telemetry points across 7 days.")

    # -------------------------------------------------------------
    # 5. ALERT ANALYTICS (MTTA / MTTR & SEVERITY)
    # -------------------------------------------------------------
    res_alerts = client.get("/analytics/alerts?days=30", headers=farmer_headers)
    assert res_alerts.status_code == 200, f"Alerts analytics request failed: {res_alerts.text}"
    al_data = res_alerts.json()
    assert "total_alerts" in al_data
    assert "severity_distribution" in al_data
    assert "mtta_display" in al_data
    assert "mttr_display" in al_data
    print(f"[PASS] 6. Alert Analytics verified: Total={al_data['total_alerts']}, MTTA={al_data['mtta_display']}, MTTR={al_data['mttr_display']}")

    # -------------------------------------------------------------
    # 6. PREVENTIVE HEALTHCARE COMPLIANCE
    # -------------------------------------------------------------
    res_prev = client.get("/analytics/prevention", headers=farmer_headers)
    assert res_prev.status_code == 200, f"Prevention analytics failed: {res_prev.text}"
    pr_data = res_prev.json()
    assert "compliance_rate" in pr_data
    assert 0.0 <= pr_data["compliance_rate"] <= 100.0, f"Compliance rate out of bounds: {pr_data['compliance_rate']}"
    assert "categories" in pr_data
    print(f"[PASS] 7. Preventive Analytics verified: Compliance Rate={pr_data['compliance_rate']:.1f}%, Completed={pr_data['completed_count']}, Due={pr_data['due_today_count']}")

    # -------------------------------------------------------------
    # 7. VETERINARY CLINICAL WORKLOAD
    # -------------------------------------------------------------
    res_vet_cases = client.get("/analytics/veterinary", headers=vet_headers)
    assert res_vet_cases.status_code == 200, f"Veterinary analytics failed: {res_vet_cases.text}"
    vt_data = res_vet_cases.json()
    assert "total_cases" in vt_data
    assert "open_cases" in vt_data
    assert "status_distribution" in vt_data
    print(f"[PASS] 8. Veterinary Analytics verified: Total Cases={vt_data['total_cases']}, Open={vt_data['open_cases']}")

    # -------------------------------------------------------------
    # 8. HARDWARE FLEET & TELEMETRY FRESHNESS
    # -------------------------------------------------------------
    res_dev = client.get("/analytics/devices", headers=farmer_headers)
    assert res_dev.status_code == 200, f"Device analytics failed: {res_dev.text}"
    dev_data = res_dev.json()
    assert "total_devices" in dev_data
    assert "online_devices" in dev_data
    assert "freshness_display" in dev_data
    print(f"[PASS] 9. Hardware Fleet Analytics verified: Online={dev_data['online_devices']}/{dev_data['total_devices']}, Freshness='{dev_data['freshness_display']}'")

    # -------------------------------------------------------------
    # 9. AI DISEASE RISK SCREENING
    # -------------------------------------------------------------
    res_disease = client.get("/analytics/disease-risk", headers=farmer_headers)
    assert res_disease.status_code == 200, f"Disease risk analytics failed: {res_disease.text}"
    dis_data = res_disease.json()
    assert "total_screened" in dis_data
    assert "disclaimer" in dis_data
    print(f"[PASS] 10. AI Disease Risk Screening verified: Screened={dis_data['total_screened']}, Patterns Detected={len(dis_data['suspected_patterns'])}")

    # -------------------------------------------------------------
    # 10. MULTI-FARM PERFORMANCE BENCHMARKS
    # -------------------------------------------------------------
    res_farms = client.get("/analytics/farms", headers=farmer_headers)
    assert res_farms.status_code == 200, f"Farm performance request failed: {res_farms.text}"
    farms_perf = res_farms.json()
    assert isinstance(farms_perf, list), "Expected list of farm performance items"
    print(f"[PASS] 11. Multi-farm Performance verified: {len(farms_perf)} farms benchmarked.")

    # -------------------------------------------------------------
    # 11. OPERATIONAL WATCHLIST
    # -------------------------------------------------------------
    res_watch = client.get("/analytics/watchlist", headers=farmer_headers)
    assert res_watch.status_code == 200, f"Watchlist failed: {res_watch.text}"
    watch_data = res_watch.json()
    assert "critical_attention" in watch_data
    assert "high_risk" in watch_data
    assert "monitoring" in watch_data
    assert "preventive_due" in watch_data
    print(f"[PASS] 12. Operational Watchlist verified: Critical={len(watch_data['critical_attention'])}, High Risk={len(watch_data['high_risk'])}, Monitoring={len(watch_data['monitoring'])}, Preventive Due={len(watch_data['preventive_due'])}")

    # -------------------------------------------------------------
    # 12. HERD HEALTH INDEX DEDUCTION FORMULA UNIT TEST
    # -------------------------------------------------------------
    hhi_perfect = analytics_service.get_herd_health_index(
        total_animals=10,
        healthy_count=10,
        monitoring_count=0,
        at_risk_count=0,
        critical_count=0,
        critical_alerts=0,
        high_alerts=0,
        active_alerts=0,
        overdue_preventive=0,
        open_cases=0,
        preventive_compliance=100.0,
        devices_online_pct=100.0
    )
    assert hhi_perfect["score"] == 100.0
    assert hhi_perfect["band"] in ["Excellent", "Optimal"]

    hhi_severely_impaired = analytics_service.get_herd_health_index(
        total_animals=10,
        healthy_count=2,
        monitoring_count=2,
        at_risk_count=3,
        critical_count=3,
        critical_alerts=3,
        high_alerts=2,
        active_alerts=5,
        overdue_preventive=4,
        open_cases=3,
        preventive_compliance=40.0,
        devices_online_pct=50.0
    )
    assert hhi_severely_impaired["score"] < 50.0
    assert hhi_severely_impaired["band"] in ["High Risk", "Critical"]
    print(f"[PASS] 13. HHI Mathematical Formula tested: Perfect Score={hhi_perfect['score']} (Optimal), Impaired Score={hhi_severely_impaired['score']} ({hhi_severely_impaired['band']})")

    print("=" * 70)
    print("ALL 13 TESTS IN PHASE 6.7 ADVANCED ANALYTICS SUITE PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
