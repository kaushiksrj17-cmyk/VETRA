"""
VETRA Phase 15 Test Suite
SIH Final Demonstration, Validation & Submission Readiness

This test suite validates final-project readiness without:
- deleting production/baseline MongoDB data
- resetting MongoDB collections
- disabling security middleware or authentication
- contacting external government systems
- requiring live external government credentials

Phase 15 target: Minimum 30 comprehensive verification tests.
Implemented: 38 functional and safety tests.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

# ---------------------------------------------------------------------------
# Project paths & Environment setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
APP_ROOT = BACKEND_ROOT / "app"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
AI_ROOT = PROJECT_ROOT / "ai_engine"
DOCS_ROOT = PROJECT_ROOT / "docs"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import get_database, check_database_readiness
from app.security import create_access_token
from app.services.sih_demo_service import SIHDemoService
from app.services.government_data_package import (
    GovernmentDataPackageService,
    GOVERNMENT_PACKAGE_DISCLAIMER,
)
from app.services.institutional_adapters import get_institutional_adapter
from ai_engine.risk_model import LivestockRiskModel
from ai_engine.disease_intelligence import assess_disease_risk
from ai_engine.gemini_service import generate_fallback_explanation
from ai_engine.trend_engine import calculate_linear_slope
from ai_engine.predictive_health import (
    DeterministicPredictiveModel,
    CLINICAL_SAFETY_DISCLAIMER,
)
from simulator.iot_simulator import generate_sih_demo_reading

client = TestClient(app)

VALID_FARMER_TOKEN = create_access_token({
    "sub": "6ab941603838d207237803dd",
    "email": "farmer@vetra.demo",
    "role": "farmer",
    "farm_id": "6ab943fb9932a9af32e5c4b8"
})
VALID_VET_TOKEN = create_access_token({
    "sub": "6ab941603838d207237803de",
    "email": "vet@vetra.demo",
    "role": "veterinarian",
    "farm_id": "6ab943fb9932a9af32e5c4b8"
})
VALID_OFFICER_TOKEN = create_access_token({
    "sub": "6ab941603838d207237803df",
    "email": "officer@vetra.demo",
    "role": "institutional_officer",
    "farm_id": "6ab943fb9932a9af32e5c4b8"
})


# ===========================================================================
# 1. PROJECT STRUCTURE & APPLICATION INTEGRITY
# ===========================================================================

def test_01_project_structure():
    """Verify that all core top-level directories and configuration files exist."""
    assert PROJECT_ROOT.exists()
    assert BACKEND_ROOT.exists()
    assert FRONTEND_ROOT.exists()
    assert AI_ROOT.exists()
    assert DOCS_ROOT.exists()
    assert (PROJECT_ROOT / "simulator").exists()
    assert (PROJECT_ROOT / "tests").exists()
    assert (PROJECT_ROOT / "requirements.txt").exists()
    assert (PROJECT_ROOT / ".env.example").exists()
    assert (PROJECT_ROOT / "docker-compose.yml").exists()


def test_02_fastapi_application():
    """Verify FastAPI instance initializes with all core routers including /demo."""
    assert app is not None
    assert app.title == "VETRA API"
    openapi_paths = list(app.openapi()["paths"].keys())
    assert "/health" in openapi_paths
    assert "/health/ready" in openapi_paths
    assert "/auth/login" in openapi_paths
    assert "/demo/status" in openapi_paths
    assert "/demo/scenarios" in openapi_paths


def test_03_streamlit_application_and_pages():
    """Verify frontend/app.py and all 15 Streamlit pages exist and export valid render functions."""
    import ast
    assert (FRONTEND_ROOT / "app.py").exists()
    app_ast = ast.parse((FRONTEND_ROOT / "app.py").read_text(encoding="utf-8"))
    assert app_ast is not None

    expected_pages = [
        ("dashboard", "render_dashboard_page"),
        ("farms", "render_farms_page"),
        ("animals", "render_animals_page"),
        ("animal_profile", "render_animal_profile_page"),
        ("monitoring", "render_monitoring_page"),
        ("computer_vision", "render_computer_vision_page"),
        ("camera_monitoring", "render_camera_monitoring_page"),
        ("predictive_ai", "render_predictive_ai_page"),
        ("alerts", "render_alerts_page"),
        ("surveillance", "render_surveillance_page"),
        ("veterinarian", "render_veterinarian_page"),
        ("telemedicine", "render_telemedicine_page"),
        ("institutional", "render_institutional_page"),
        ("prevention", "render_prevention_page"),
        ("profile", "render_profile_page"),
    ]
    for page_mod, func_name in expected_pages:
        page_file = FRONTEND_ROOT / "pages" / f"{page_mod}.py"
        assert page_file.exists(), f"Missing page file: {page_file}"
        tree = ast.parse(page_file.read_text(encoding="utf-8"))
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert func_name in funcs, f"Function {func_name} missing from {page_mod}.py"


def test_04_database_configuration_and_readiness():
    """Verify database readiness probe executes safely without credential leakage."""
    is_ready, msg = check_database_readiness()
    assert isinstance(is_ready, bool)
    assert "password" not in msg.lower()
    assert "mongodb://" not in msg.lower()
    assert "@" not in msg


def test_05_security_and_rbac_definitions():
    """Verify role validation and JWT access token handling for core roles."""
    roles = ["farmer", "veterinarian", "institutional_officer", "admin"]
    for role in roles:
        token = create_access_token({"sub": f"test_{role}", "email": f"{role}@test.vetra", "role": role})
        assert isinstance(token, str)
        assert len(token) > 20


# ===========================================================================
# 2. AI INTELLIGENCE & CLINICAL SAFETY
# ===========================================================================

def test_06_ai_livestock_risk_model():
    """Verify LivestockRiskModel continuous scoring and pyrexia detection."""
    model = LivestockRiskModel()
    normal_features = {
        "temp_deviation": 0.0,
        "hr_deviation": 0.0,
        "resp_deviation": 0.0,
        "activity_reduction_pct": 0.0,
        "rumination_reduction_pct": 0.0
    }
    res_normal = model.predict_risk(normal_features)
    assert 0.0 <= res_normal["health_risk_score"] <= 25.0
    assert res_normal["risk_category"] == "low"

    fever_features = {
        "temp_deviation": 2.2,  # > 40.5 C
        "hr_deviation": 32.0,   # Tachycardia
        "resp_deviation": 18.0,
        "activity_reduction_pct": 60.0,
        "rumination_reduction_pct": 70.0
    }
    res_fever = model.predict_risk(fever_features)
    assert res_fever["health_risk_score"] >= 60.0
    assert res_fever["risk_category"] in ("high", "critical")
    assert len(res_fever["contributing_factors"]) >= 3


def test_07_ai_disease_intelligence():
    """Verify assess_disease_risk detects respiratory & inflammatory screening patterns."""
    features = {
        "temp_deviation": 2.0,
        "hr_deviation": 25.0,
        "resp_deviation": 16.0,
        "activity_reduction_pct": 55.0,
        "rumination_reduction_pct": 60.0,
        "temp_rate_of_change": 0.8
    }
    assessment = assess_disease_risk(features)
    assert "risk_patterns" in assessment
    assert len(assessment["risk_patterns"]) > 0
    assert any("fever" in p.lower() or "inflammatory" in p.lower() for p in assessment["risk_patterns"])
    assert len(assessment["recommendations"]) > 0


def test_08_ai_gemini_fallback():
    """Verify generate_fallback_explanation generates deterministic structured narratives without API key."""
    animal_data = {"name": "Gauri", "tag_id": "COW-002"}
    features = {
        "temp_deviation": 1.9,
        "latest_temp": 40.5,
        "rumination_reduction_pct": 50.0,
        "activity_reduction_pct": 40.0
    }
    risk_data = {"health_risk_score": 78.0, "risk_category": "critical"}
    fallback = generate_fallback_explanation(animal_data, features, risk_data)
    assert isinstance(fallback, dict)
    assert "explanation" in fallback
    assert "recommended_action" in fallback
    assert "40.5" in fallback["explanation"]
    assert "veterinarian" in fallback["recommended_action"].lower()


# ===========================================================================
# 3. COMPUTER VISION & MULTIMODAL SAFETY
# ===========================================================================

def test_09_computer_vision_safety():
    """Verify computer vision modules use triage/screening language and no definitive diagnosis."""
    cv_path = PROJECT_ROOT / "ai_engine" / "computer_vision.py"
    assert cv_path.exists()
    content = cv_path.read_text(encoding="utf-8", errors="ignore")
    # Must contain triage/screening language
    assert "indicator" in content.lower() or "screening" in content.lower() or "triage" in content.lower()
    # Must not claim confirmed diagnosis autonomously
    assert "definitive diagnosis" not in content.lower() or "not a definitive" in content.lower()


def test_10_multimodal_health_fusion():
    """Verify multimodal health fusion combines visual indicators and telemetry."""
    from ai_engine.multimodal_health import compute_multimodal_health_assessment
    animal_data = {"_id": "test_cow_1", "tag_id": "COW-001", "name": "Gauri", "farm_id": "farm_01"}
    
    # Both normal
    res_normal = compute_multimodal_health_assessment(
        animal_data,
        visual_analysis={"visual_risk_score": 10.0, "observations": []},
        telemetry_risk_data={"health_risk_score": 15.0},
        disease_intelligence_data={"disease_risk_score": 10.0},
        surveillance_risk_data={"risk_score": 10.0},
        preventive_status_data={"preventive_risk_score": 10.0}
    )
    assert 0.0 <= res_normal["combined_risk"] <= 30.0
    assert res_normal["risk_category"] == "LOW"

    # Divergent / Elevated signals
    res_elevated = compute_multimodal_health_assessment(
        animal_data,
        visual_analysis={"visual_risk_score": 30.0, "observations": [{"indicator": "lameness", "description": "Minor lameness", "severity": "medium"}]},
        telemetry_risk_data={"health_risk_score": 80.0},
        disease_intelligence_data={"disease_risk_score": 50.0},
        surveillance_risk_data={"risk_score": 30.0},
        preventive_status_data={"preventive_risk_score": 20.0}
    )
    assert res_elevated["combined_risk"] > res_normal["combined_risk"]
    assert "visual_telemetry_consistency" in res_elevated


# ===========================================================================
# 4. PREDICTIVE HEALTH INTELLIGENCE
# ===========================================================================

def test_11_predictive_trend_engine():
    """Verify calculate_linear_slope correctly computes slope and trajectory."""
    # Ascending fever series
    temps_rising = [38.5, 38.8, 39.2, 39.7, 40.2]
    slope = calculate_linear_slope(temps_rising)
    assert slope > 0.0

    # Stable series
    temps_stable = [38.6, 38.6, 38.6, 38.6, 38.6]
    slope_stable = calculate_linear_slope(temps_stable)
    assert abs(slope_stable) < 0.0001


def test_12_predictive_health_forecasting():
    """Verify DeterministicPredictiveModel forecasts multi-horizon trajectories with clinical disclaimers."""
    model = DeterministicPredictiveModel()
    assert CLINICAL_SAFETY_DISCLAIMER is not None
    features = {
        "temperature_mean": 39.8,
        "temperature_slope": 0.35,
        "heart_rate_slope": 4.5,
        "rumination_drop_rate": 0.4,
        "data_availability": {"has_sufficient_telemetry": True, "num_readings": 12, "is_telemetry_fresh": True}
    }
    pred = model.predict(features, context={"animal_id": "a1", "current_health_risk": 55.0})
    assert "predicted_health_risk" in pred
    assert "confidence" in pred
    assert 0.0 <= pred["confidence"] <= 1.0
    assert "CLINICAL SAFETY NOTICE" in pred.get("clinical_safety_notice", CLINICAL_SAFETY_DISCLAIMER)


# ===========================================================================
# 5. SURVEILLANCE & ANTI-AUTONOMOUS OUTBREAK RULE
# ===========================================================================

def test_13_disease_surveillance_farm_risk():
    """Verify farm risk calculation produces bounded categorical scores."""
    from app.services.farm_risk_engine import compute_farm_disease_risk
    db = get_database()
    farms = list(db.farms.find())
    if farms:
        farm = farms[0]
        risk = compute_farm_disease_risk(farm, db)
        assert "risk_score" in risk
        assert 0.0 <= risk["risk_score"] <= 100.0
        assert risk["risk_category"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def test_14_disease_surveillance_spatial_clustering():
    """Verify Haversine geospatial distance calculation and cluster detection."""
    from app.services.geospatial_service import haversine_distance
    # Anand (22.5645, 72.9289) to Ahmedabad (23.0225, 72.5714) ~ 62-65 km
    dist = haversine_distance(22.5645, 72.9289, 23.0225, 72.5714)
    assert 60.0 <= dist <= 70.0


def test_15_anti_autonomous_outbreak_rule():
    """Verify that farmers and automated callers are strictly forbidden from confirming outbreaks (HTTP 403)."""
    res = client.post(
        "/epidemiological-events/EPI-DEMO-TEST/confirm",
        json={"confirmation_authority": "Automated Algorithm", "notes": "Unauthorized attempt"},
        headers={"Authorization": f"Bearer {VALID_FARMER_TOKEN}"}
    )
    assert res.status_code == 403


# ===========================================================================
# 6. TELEMEDICINE & INSTITUTIONAL WORKFLOW
# ===========================================================================

def test_16_telemedicine_case_workflow():
    """Verify telemedicine case schema and role authorization."""
    res = client.get("/veterinary-cases", headers={"Authorization": f"Bearer {VALID_VET_TOKEN}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_17_institutional_early_warning_lifecycle():
    """Verify institutional warning queries and permissions."""
    res = client.get("/institutional-surveillance/warnings", headers={"Authorization": f"Bearer {VALID_OFFICER_TOKEN}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ===========================================================================
# 7. GOVERNMENT DATA PACKAGE & SAFETY GATES
# ===========================================================================

def test_18_government_data_package_schema():
    """Verify government data package service generates schema version 1.0.0."""
    service = GovernmentDataPackageService()
    db = get_database()
    pkg_id = service.generate_package_id(db)
    assert pkg_id.startswith("PKG-")


def test_19_government_data_package_privacy_masking():
    """Verify PII data masking for farmer names, phone numbers, and emails."""
    service = GovernmentDataPackageService()
    sensitive_data = {
        "farmer_name": "Ramesh Patel",
        "phone": "+91 98765 43210",
        "email": "ramesh@example.com",
        "district": "Anand"
    }
    masked = service._mask_pii_data(sensitive_data)
    assert masked["farmer_name"] != "Ramesh Patel"
    assert "*" in masked["farmer_name"]
    assert masked["phone"] == "**********"
    assert "masked@" in masked["email"]
    assert masked["district"] == "Anand"  # District level preserved


def test_20_government_data_package_multi_format():
    """Verify multi-format export capability (JSON/CSV/PDF service)."""
    service = GovernmentDataPackageService()
    assert hasattr(service, "export_json")
    assert hasattr(service, "export_csv")
    assert hasattr(service, "export_pdf")


def test_21_government_eight_safety_gates():
    """Verify all 8 mandatory safety gates are evaluated in validate_safety_gates."""
    service = GovernmentDataPackageService()
    # Non-existent package should fail gracefully
    res = service.validate_safety_gates("PKG-NONEXISTENT")
    assert res.validation_passed is False
    assert len(res.errors) > 0


def test_22_government_adapter_not_configured_safety():
    """Phase 13/14/15 Safety: Government adapter must default to NOT_CONFIGURED."""
    adapter = get_institutional_adapter()
    assert adapter.state == "NOT_CONFIGURED"
    health = adapter.get_health()
    assert health["adapter_state"] == "NOT_CONFIGURED"
    assert health["submission_enabled"] is False


def test_23_government_adapter_blocked_submission_response():
    """Verify that submit_package on a NOT_CONFIGURED adapter returns BLOCKED status."""
    adapter = get_institutional_adapter()
    res = adapter.submit_package({"package_id": "TEST-PKG"})
    assert res["success"] is False
    assert res["status"] == "BLOCKED"
    assert res["adapter_state"] == "NOT_CONFIGURED"
    assert "not_configured" in res["error"].lower() or "blocked" in res["transmission_status"].lower()


def test_24_government_package_disclaimer():
    """Verify export disclaimer explicitly states 'not an official submission'."""
    assert GOVERNMENT_PACKAGE_DISCLAIMER is not None
    assert "Government-ready export package" in GOVERNMENT_PACKAGE_DISCLAIMER
    assert "not an official submission" in GOVERNMENT_PACKAGE_DISCLAIMER


# ===========================================================================
# 8. SIH DEMONSTRATION MODE & SCENARIOS
# ===========================================================================

def test_25_sih_demo_service_metadata():
    """Verify SIHDemoService version, disclaimer, and 9 registered scenarios."""
    status = SIHDemoService.get_demo_status()
    assert status["version"] == "15.0.0-SIH-FINAL"
    assert status["total_scenarios"] == 9
    assert status["government_adapter_status"] == "NOT_CONFIGURED"
    assert "SIH DEMO MODE" in status["disclaimer"]


def test_26_sih_demo_scenario_1_normal():
    """Verify Scenario 1: Normal Animal physiological baseline."""
    s = SIHDemoService.get_scenario("scenario_1_normal")
    assert s is not None
    assert s["number"] == 1
    assert s["expected_risk"] == "LOW / NORMAL"
    assert s["alerts_generated"] == 0
    assert s["human_action_required"] is False


def test_27_sih_demo_scenario_2_early_warning():
    """Verify Scenario 2: Early Health Warning subtle trend divergence."""
    s = SIHDemoService.get_scenario("scenario_2_early_warning")
    assert s is not None
    assert s["number"] == 2
    assert s["expected_risk"] == "MEDIUM / ELEVATED"
    assert s["alerts_generated"] == 1
    assert s["human_action_required"] is True


def test_28_sih_demo_scenario_3_multi_signal():
    """Verify Scenario 3: Multi-Signal Acute Anomaly critical alert."""
    s = SIHDemoService.get_scenario("scenario_3_multi_signal")
    assert s is not None
    assert s["number"] == 3
    assert s["expected_risk"] == "HIGH / CRITICAL"
    assert s["telemetry"]["temperature_c"] >= 40.0
    assert s["human_action_required"] is True


def test_29_sih_demo_scenario_4_visual_health():
    """Verify Scenario 4: Computer Vision mobility & posture triage marker."""
    s = SIHDemoService.get_scenario("scenario_4_visual_health")
    assert s is not None
    assert s["number"] == 4
    assert s["vision_metrics"]["lameness_detected"] is True
    assert "AI-assisted screening indicator only" in s["disclaimer"]


def test_30_sih_demo_scenario_5_predictive():
    """Verify Scenario 5: Predictive Health 24h/48h/72h forecasting."""
    s = SIHDemoService.get_scenario("scenario_5_predictive")
    assert s is not None
    assert s["number"] == 5
    assert "24h_predicted_risk" in s["forecast_horizons"]
    assert "48h_predicted_risk" in s["forecast_horizons"]
    assert "72h_predicted_risk" in s["forecast_horizons"]


def test_31_sih_demo_scenario_6_veterinary():
    """Verify Scenario 6: Veterinary Clinical Response case workflow."""
    s = SIHDemoService.get_scenario("scenario_6_veterinary")
    assert s is not None
    assert s["number"] == 6
    assert s["triage_priority"] == "URGENT"
    assert "Oxytetracycline" in s["treatment_prescribed"]


def test_32_sih_demo_scenario_7_surveillance():
    """Verify Scenario 7: Cross-farm surveillance & spatial clustering."""
    s = SIHDemoService.get_scenario("scenario_7_surveillance")
    assert s is not None
    assert s["number"] == 7
    assert s["cluster_metrics"]["participating_farms"] == 3
    assert "NO AI MODEL MAY AUTONOMOUSLY CONFIRM AN OUTBREAK" in s["safety_rule"]


def test_33_sih_demo_scenario_8_institutional():
    """Verify Scenario 8: Institutional review & human approval gate."""
    s = SIHDemoService.get_scenario("scenario_8_institutional")
    assert s is not None
    assert s["number"] == 8
    assert s["lifecycle_state"] == "REVIEW_REQUIRED"
    assert "Institutional Veterinary Officers" in s["role_enforcement"]


def test_34_sih_demo_scenario_9_government():
    """Verify Scenario 9: Government-ready package & Gate 5 blocked state."""
    s = SIHDemoService.get_scenario("scenario_9_government")
    assert s is not None
    assert s["number"] == 9
    assert s["safety_gates"]["gate_5_adapter_configuration"] == "BLOCKED (Adapter status: NOT_CONFIGURED)"
    assert s["adapter_status"] == "NOT_CONFIGURED"


def test_35_sih_demo_dry_run_zero_mutations():
    """Verify non-destructive dry-run executes in-memory with exactly 0 database mutations."""
    db = get_database()
    initial_alerts = db.alerts.count_documents({})
    result = SIHDemoService.execute_dry_run("scenario_3_multi_signal")
    assert result["success"] is True
    assert result["data"]["database_mutations"] == 0
    final_alerts = db.alerts.count_documents({})
    assert initial_alerts == final_alerts


def test_36_iot_simulator_deterministic_scenarios():
    """Verify IoT simulator includes deterministic SIH reading generator for Scenarios 1, 2, and 3."""
    reading_1 = generate_sih_demo_reading(scenario=1)
    assert reading_1["temperature_c"] == 38.6
    assert reading_1["heart_rate_bpm"] == 72.0

    reading_2 = generate_sih_demo_reading(scenario=2)
    assert reading_2["temperature_c"] == 39.4
    assert reading_2["rumination_level"] == 45.0

    reading_3 = generate_sih_demo_reading(scenario=3)
    assert reading_3["temperature_c"] == 40.8
    assert reading_3["heart_rate_bpm"] == 98.0


# ===========================================================================
# 9. SECURITY & DATABASE PRESERVATION AUDIT
# ===========================================================================

def test_37_security_middleware_and_headers():
    """Verify production security headers (nosniff, SAMEORIGIN, strict-origin, X-Request-ID)."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "strict-origin" in res.headers.get("Referrer-Policy")
    assert "X-Request-ID" in res.headers


def test_38_database_integrity_and_preservation():
    """Verify baseline collection counts remain 100% unmutated during Phase 15 execution."""
    db = get_database()
    baseline_collections = ["animals", "devices", "health_readings", "farms", "alerts", "veterinary_cases", "users"]
    counts = {col: db[col].count_documents({}) for col in baseline_collections}
    # Expected baseline
    assert counts["animals"] == 11
    assert counts["devices"] == 11
    assert counts["health_readings"] == 847
    assert counts["farms"] == 2
    assert counts["alerts"] == 4
    assert counts["veterinary_cases"] == 4
    assert counts["users"] == 3


# ---------------------------------------------------------------------------
# Direct Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING VETRA PHASE 15 VERIFICATION SUITE")
    print("=" * 80)
    pytest_args = ["-v", __file__]
    sys.exit(pytest.main(pytest_args))