"""
tests/test_all_streamlit_pages.py
=================================
Headless verification suite for all 15 VETRA Streamlit modules.
Ensures every page can be imported and executed headlessly with 0 exceptions.

Modules verified:
 1. Command Center                   (pages.dashboard.render_dashboard_page)
 2. Farms                            (pages.farms.render_farms_page)
 3. Animals                          (pages.animals.render_animals_page)
 4. Animal Profile                   (pages.animal_profile.render_animal_profile_page)
 5. Live Monitoring                  (pages.monitoring.render_monitoring_page)
 6. Visual Health                    (pages.computer_vision.render_computer_vision_page)
 7. Live Camera & Edge Intelligence  (pages.camera_monitoring.render_camera_monitoring_page)
 8. Predictive Health Intelligence   (pages.predictive_ai.render_predictive_ai_page)
 9. Alerts                           (pages.alerts.render_alerts_page)
10. Disease Surveillance             (pages.surveillance.render_surveillance_page)
11. Clinical Cases                   (pages.veterinarian.render_veterinarian_page)
12. Telemedicine                     (pages.telemedicine.render_telemedicine_page)
13. Institutional Health             (pages.institutional.render_institutional_page)
14. Preventive Health                (pages.prevention.render_prevention_page)
15. Profile                          (pages.profile.render_profile_page)
"""

from pathlib import Path
import sys
import unittest.mock as mock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

root_dir = Path(__file__).resolve().parent.parent
frontend_dir = root_dir / "frontend"
backend_dir = root_dir / "backend"

for p in [str(frontend_dir), str(root_dir), str(backend_dir)]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, str(frontend_dir))
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))


def run_all_streamlit_page_tests():
    print("=" * 80)
    print("VETRA STREAMLIT HEADLESS RENDERING TEST SUITE (14/14)")
    print("=" * 80)

    import streamlit as st
    import requests

    def mock_request_response(url="", *args, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}

        # 1. Analytics endpoints return structured analytics dicts
        if "/analytics/" in url:
            resp.json.return_value = {
                "total_alerts": 0,
                "active_alerts": 0,
                "resolved_alerts": 0,
                "severity_breakdown": {},
                "kpis": {
                    "total_animals": 1,
                    "healthy_animals": 1,
                    "animals_under_monitoring": 0,
                    "high_risk_animals": 0,
                    "critical_animals": 0,
                    "active_alerts": 0,
                    "critical_alerts": 0,
                    "open_veterinary_cases": 0,
                    "preventive_actions_due": 0,
                    "preventive_compliance": 100.0,
                    "devices_online": 1,
                    "total_devices": 1
                },
                "risk_distribution": {
                    "low": {"count": 1},
                    "medium": {"count": 0},
                    "high": {"count": 0},
                    "critical": {"count": 0}
                },
                "herd_health_index": {"score": 88.0, "status": "Good"},
                "points": [],
                "data": [],
                "compliance_rate": 100.0,
                "completed_actions": 0,
                "due_actions": 0,
                "total_cases": 0,
                "open_cases": 0,
                "total_devices": 1,
                "online_devices": 1,
                "offline_devices": 0,
                "critical": [],
                "high_risk": [],
                "monitoring": [],
                "preventive_due": []
            }
            resp.text = "{}"
            return resp

        # 1.5 Endpoint returning animals list (enables full Animal Profile rendering)
        if "/animals" in url:
            resp.json.return_value = [{
                "id": "6ab94a566da27ccfb46d9dce",
                "tag_id": "COW-001",
                "name": "Lakshmi",
                "species": "Cattle",
                "breed": "Gir",
                "farm_id": "6ab943fb9932a9af32e5c4b8",
                "status": "healthy"
            }]
            resp.text = "[]"
            return resp

        # 2. Endpoint returning lists
        if any(x in url for x in [
            "readings", "/farms", "/devices", "/alerts", "/cases",
            "/profiles", "/consultations", "/results", "/reports", "/clusters",
            "/hotspots", "/regions", "/observations", "/events", "/actions"
        ]):
            resp.json.return_value = []
            resp.text = "[]"
            return resp

        # 3. General status/health/summary endpoints return dicts
        if any(x in url for x in ["/health", "/summary", "/overview", "/status", "/trends", "/matrix"]):
            resp.json.return_value = {
                "status": "healthy",
                "backend": "online",
                "database": "connected",
                "ai_engine": "operational",
                "score": 88.0,
                "window_days": 7,
                "total_cameras": 0,
                "online_cameras": 0
            }
            resp.text = "{}"
            return resp

        resp.json.return_value = []
        resp.text = "[]"
        return resp

    mock_user = {
        "id": "6ab941603838d207237803dd",
        "user_id": "6ab941603838d207237803dd",
        "role": "admin",
        "full_name": "Dr. Administrator",
        "email": "admin@vetra.demo",
        "farm_id": "6ab943fb9932a9af32e5c4b8"
    }

    pages_to_test = [
        ("1. Command Center", "pages.dashboard", "render_dashboard_page"),
        ("2. Farms", "pages.farms", "render_farms_page"),
        ("3. Animals", "pages.animals", "render_animals_page"),
        ("4. Animal Profile", "pages.animal_profile", "render_animal_profile_page"),
        ("5. Live Monitoring", "pages.monitoring", "render_monitoring_page"),
        ("6. Visual Health", "pages.computer_vision", "render_computer_vision_page"),
        ("7. Live Camera & Edge", "pages.camera_monitoring", "render_camera_monitoring_page"),
        ("8. Predictive AI", "pages.predictive_ai", "render_predictive_ai_page"),
        ("9. Alerts", "pages.alerts", "render_alerts_page"),
        ("10. Disease Surveillance", "pages.surveillance", "render_surveillance_page"),
        ("11. Clinical Cases", "pages.veterinarian", "render_veterinarian_page"),
        ("12. Telemedicine", "pages.telemedicine", "render_telemedicine_page"),
        ("13. Institutional Health", "pages.institutional", "render_institutional_page"),
        ("14. Preventive Health", "pages.prevention", "render_prevention_page"),
        ("15. Profile", "pages.profile", "render_profile_page"),
    ]

    passed = 0

    with mock.patch("session.get_user_info", return_value=mock_user), \
         mock.patch("requests.get", side_effect=mock_request_response), \
         mock.patch("requests.post", side_effect=mock_request_response), \
         mock.patch("requests.put", side_effect=mock_request_response), \
         mock.patch("requests.delete", side_effect=mock_request_response), \
         mock.patch("time.sleep", return_value=None), \
         mock.patch("streamlit.rerun", return_value=None):

        for label, mod_path, func_name in pages_to_test:
            try:
                mod = __import__(mod_path, fromlist=[func_name])
                func = getattr(mod, func_name)
                assert callable(func), f"{func_name} in {mod_path} is not callable"
                func()
                print(f"[PASS] {label}: Rendered cleanly with 0 exceptions.")
                passed += 1
            except Exception as e:
                print(f"[FAIL] {label}: Raised exception: {type(e).__name__}: {str(e)}")
                raise

    print("=" * 80)
    print(f"STREAMLIT VERIFICATION: {passed} / 15 PAGES PASSED (0 EXCEPTIONS)")
    print("=" * 80)
    return passed == 15


if __name__ == "__main__":
    success = run_all_streamlit_page_tests()
    sys.exit(0 if success else 1)

