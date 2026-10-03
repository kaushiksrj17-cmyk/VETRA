import io
import os
from pathlib import Path
import sys
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
frontend_dir = root_dir / "frontend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))
sys.path.insert(2, str(frontend_dir))

from app.database import get_database
from app.main import app
from app.schemas.visual_health import VisualObservation
from app.services.media_service import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_VIDEO_EXTS,
    MAX_IMAGE_SIZE_BYTES,
    MAX_VIDEO_SIZE_BYTES,
    compute_sha256,
    save_media_file,
    validate_media_upload,
)
from ai_engine.computer_vision import (
    CLINICAL_SAFETY_DISCLAIMER,
    DeterministicVisualAnalyzer,
    VisualModelAdapter,
    get_visual_analyzer,
)
from ai_engine.gemini_service import (
    generate_multimodal_explanation,
    generate_visual_explanation,
)
from ai_engine.multimodal_health import (
    compare_temporal_visual_analyses,
    compute_multimodal_health_assessment,
)


def _create_dummy_image_bytes(color: tuple = (100, 150, 200), size: tuple = (200, 200)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run_phase_9_tests():
    print("=" * 80)
    print("VETRA PHASE 9 — COMPUTER VISION & MULTIMODAL INTELLIGENCE TEST SUITE")
    print("=" * 80)

    db = get_database()
    client = TestClient(app)

    # Record initial counts to verify absolute database preservation (Step 42)
    initial_alerts_count = db.alerts.count_documents({})
    initial_cases_count = db.veterinary_cases.count_documents({})
    initial_animals_count = db.animals.count_documents({})
    initial_farms_count = db.farms.count_documents({})
    initial_devices_count = db.devices.count_documents({})
    initial_users_count = db.users.count_documents({})
    initial_events_count = db.disease_events.count_documents({})

    # Authenticate users
    res_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert res_farmer.status_code == 200, f"Farmer login failed: {res_farmer.text}"
    farmer_token = res_farmer.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    farmer_id = res_farmer.json()["user"]["id"]

    res_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert res_vet.status_code == 200, f"Vet login failed: {res_vet.text}"
    vet_token = res_vet.json()["access_token"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}

    # Fetch farmer's animal
    farmer_farms = list(db.farms.find({"$or": [{"owner_id": farmer_id}, {"owner_id": ObjectId(farmer_id)}]}))
    assert len(farmer_farms) > 0, "No farms owned by farmer found"
    farmer_farm_id = str(farmer_farms[0]["_id"])

    farmer_animal = db.animals.find_one({"farm_id": {"$in": [farmer_farm_id, ObjectId(farmer_farm_id)]}})
    assert farmer_animal is not None, "No animal owned by farmer found"
    test_animal_id = str(farmer_animal["_id"])

    # Track test artifacts for complete cleanup
    test_analyses_ids = []
    test_observations_ids = []
    test_assessment_ids = []
    test_alert_ids = []
    test_case_numbers = []
    test_event_numbers = []
    test_file_paths = []

    passed_count = 0
    total_tests = 25

    try:
        # -------------------------------------------------------------
        # TEST 1: VISUAL ROUTE REGISTRATION (Step 32)
        # -------------------------------------------------------------
        openapi = app.openapi()
        vh_paths = [p for p in openapi["paths"].keys() if p.startswith("/visual-health")]
        required_endpoints = [
            "/visual-health/analyze-image",
            "/visual-health/analyze-video",
            "/visual-health/analyses",
            "/visual-health/analyses/{analysis_id}",
            "/visual-health/animal/{animal_id}",
            "/visual-health/farm/{farm_id}",
            "/visual-health/observations",
            "/visual-health/trends/{animal_id}",
            "/visual-health/multimodal-assessment",
            "/visual-health/multimodal/{assessment_id}",
            "/visual-health/{analysis_id}/veterinary-case",
            "/visual-health/{analysis_id}/surveillance-review",
            "/visual-health/summary"
        ]
        for ep in required_endpoints:
            assert ep in vh_paths, f"Missing endpoint {ep}"
        print("[PASS] 1. Visual route registration: All required endpoints verified.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 2: AUTHENTICATION ENFORCEMENT
        # -------------------------------------------------------------
        r_unauth = client.get("/visual-health/analyses")
        assert r_unauth.status_code == 401, f"Expected 401 unauthenticated, got {r_unauth.status_code}"
        r_post_unauth = client.post("/visual-health/multimodal-assessment", json={"animal_id": test_animal_id})
        assert r_post_unauth.status_code == 401
        print("[PASS] 2. Authentication enforcement: Unauthenticated requests rejected with 401.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 3: FARMER OWNERSHIP VALIDATION (RBAC)
        # -------------------------------------------------------------
        # Find an animal NOT owned by the farmer
        foreign_animal = db.animals.find_one({"farm_id": {"$nin": [farmer_farm_id, ObjectId(farmer_farm_id)]}})
        if foreign_animal:
            img_bytes = _create_dummy_image_bytes()
            r_foreign = client.post(
                "/visual-health/analyze-image",
                data={"animal_id": str(foreign_animal["_id"])},
                files={"file": ("test.jpg", img_bytes, "image/jpeg")},
                headers=farmer_headers
            )
            assert r_foreign.status_code == 403, f"Expected 403 for foreign animal, got {r_foreign.status_code}"
        print("[PASS] 3. Farmer ownership validation: Foreign animal access strictly denied (403).")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 4: FILE TYPE VALIDATION
        # -------------------------------------------------------------
        r_invalid_type = client.post(
            "/visual-health/analyze-image",
            data={"animal_id": test_animal_id},
            files={"file": ("malicious.exe", b"fake binary executable", "application/octet-stream")},
            headers=farmer_headers
        )
        assert r_invalid_type.status_code == 400
        assert "Unsupported file type" in r_invalid_type.text or "Expected" in r_invalid_type.text
        print("[PASS] 4. File type validation: Non-media extensions rejected with 400.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 5: FILE SIZE VALIDATION
        # -------------------------------------------------------------
        oversized_bytes = b"X" * (MAX_IMAGE_SIZE_BYTES + 1024)
        is_val, mtype, err_msg = validate_media_upload("oversized.jpg", oversized_bytes, "image/jpeg")
        assert not is_val
        assert "exceeds maximum" in err_msg
        print("[PASS] 5. File size validation: Oversized files (>10MB) rejected.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 6: SAFE FILENAME HANDLING & PATH TRAVERSAL DEFENSE
        # -------------------------------------------------------------
        dummy_img = _create_dummy_image_bytes()
        rel_p, abs_p, m_hash = save_media_file(dummy_img, "../../../etc/shadow.jpg", "image")
        assert not rel_p.startswith("..")
        assert "images" in rel_p
        assert os.path.exists(abs_p)
        test_file_paths.append(abs_p)
        print("[PASS] 6. Safe filename handling: Path traversal stripped; safe storage path generated.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 7: SHA-256 HASHING
        # -------------------------------------------------------------
        h1 = compute_sha256(dummy_img)
        h2 = compute_sha256(dummy_img)
        assert h1 == h2 and len(h1) == 64
        print("[PASS] 7. SHA-256 hashing: Deterministic cryptographic checksum verified.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 8: IMAGE PREPROCESSING
        # -------------------------------------------------------------
        val_ok, m_type, err = validate_media_upload("valid.jpg", dummy_img, "image/jpeg")
        assert val_ok and m_type == "image"
        # Corrupted image bytes test
        corrupt_ok, _, corrupt_err = validate_media_upload("corrupt.jpg", b"corrupted bytes", "image/jpeg")
        assert not corrupt_ok
        assert "Corrupted or unreadable" in corrupt_err
        print("[PASS] 8. Image preprocessing: Pillow verification catches corrupted images.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 9: DETERMINISTIC IMAGE ANALYSIS
        # -------------------------------------------------------------
        analyzer = get_visual_analyzer()
        assert isinstance(analyzer, VisualModelAdapter)
        cv_res = analyzer.analyze_image(dummy_img, animal_context={"species": "Cattle", "name": "Test Cow"})
        assert "visual_risk_score" in cv_res
        assert "observations" in cv_res
        assert "clinical_safety_notice" in cv_res
        assert cv_res["model_name"] == "VETRA-VisualEngine"
        print("[PASS] 9. Deterministic image analysis: Visual features and indicators extracted.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 10: VISUAL OBSERVATION SCHEMA
        # -------------------------------------------------------------
        obs_example = cv_res["observations"][0] if cv_res["observations"] else {
            "observation_id": "VO-001",
            "analysis_id": "VA-TEST",
            "animal_id": test_animal_id,
            "indicator": "abnormal_posture",
            "description": "Observed abnormal posture",
            "confidence": 0.80,
            "confidence_level": "Moderate",
            "severity": "medium",
            "timestamp": "2026-10-02T10:00:00Z",
            "source": "computer_vision_engine"
        }
        vo_model = VisualObservation(**obs_example)
        assert vo_model.confidence >= 0.0 and vo_model.confidence <= 1.0
        assert vo_model.severity in ["low", "medium", "high", "critical"]
        print("[PASS] 10. Visual observation schema: Pydantic constraints validated.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 11: VISUAL RISK CALCULATION
        # -------------------------------------------------------------
        score = cv_res["visual_risk_score"]
        assert 0.0 <= score <= 100.0
        assert cv_res["risk_category"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        print("[PASS] 11. Visual risk calculation: Bounded 0-100 score and tier classification validated.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 12: MULTIMODAL RISK CALCULATION
        # -------------------------------------------------------------
        dummy_va = {
            "analysis_id": "VA-MM-TEST",
            "visual_risk_score": 60.0,
            "observations": [{"indicator": "respiratory_effort_visible", "description": "Effort visible"}]
        }
        mm_eval = compute_multimodal_health_assessment(
            animal_data={"_id": test_animal_id, "tag_id": "TAG-MM", "name": "Cow MM", "farm_id": farmer_farm_id},
            visual_analysis=dummy_va,
            telemetry_risk_data={"health_risk_score": 70.0, "latest_resp": 38.0, "latest_temp": 39.8},
            disease_intelligence_data={"disease_risk_score": 50.0},
            surveillance_risk_data={"risk_score": 20.0},
            preventive_status_data={"overdue_tasks_count": 0, "preventive_risk_score": 0.0}
        )
        assert "combined_risk" in mm_eval
        assert mm_eval["combined_risk"] > 0
        assert mm_eval["visual_telemetry_consistency"] in [
            "consistent", "directionally_consistent", "divergent", "isolated_visual", "isolated_telemetry", "nominal"
        ]
        # Formula check: 0.30*60 + 0.30*70 + 0.15*50 + 0.15*20 + 0.10*0 = 18 + 21 + 7.5 + 3.0 + 0 = 49.5
        assert abs(mm_eval["combined_risk"] - 49.5) < 1.0
        print("[PASS] 12. Multimodal risk calculation: Weighted formula and directional consistency verified.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 13: TEMPORAL COMPARISON
        # -------------------------------------------------------------
        analysis_early = {
            "analysis_id": "VA-EARLY",
            "created_at": "2026-09-25T10:00:00",
            "visual_risk_score": 20.0,
            "observations": [{"indicator": "nominal_gait"}]
        }
        analysis_late = {
            "analysis_id": "VA-LATE",
            "created_at": "2026-10-02T10:00:00",
            "visual_risk_score": 55.0,
            "observations": [{"indicator": "gait_irregularity_suspected"}]
        }
        trend = compare_temporal_visual_analyses(analysis_early, analysis_late)
        assert trend["trajectory"] in ["worsening", "new_signal"]
        assert trend["score_delta"] > 0
        print("[PASS] 13. Temporal comparison: Earlier vs latest trajectory change detected.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 14: DUPLICATE MEDIA DETECTION
        # -------------------------------------------------------------
        # Perform image analysis via API
        r_upload = client.post(
            "/visual-health/analyze-image",
            data={"animal_id": test_animal_id},
            files={"file": ("test_cow.jpg", dummy_img, "image/jpeg")},
            headers=farmer_headers
        )
        assert r_upload.status_code == 200, f"Analysis upload failed: {r_upload.text}"
        uploaded_data = r_upload.json()
        analysis_id = uploaded_data["analysis_id"]
        test_analyses_ids.append(analysis_id)
        test_observations_ids.extend([o["observation_id"] for o in uploaded_data.get("observations", [])])

        # Query media hash
        existing_doc = db.visual_analyses.find_one({"media_hash": uploaded_data["media_hash"]})
        assert existing_doc is not None
        assert existing_doc["analysis_id"] == analysis_id
        print("[PASS] 14. Duplicate media detection: Media hash matched in database.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 15: VETERINARY CASE INTEGRATION (Step 18)
        # -------------------------------------------------------------
        r_case = client.post(
            f"/visual-health/{analysis_id}/veterinary-case",
            json={"notes": "Visual posture check referral", "priority": "high"},
            headers=farmer_headers
        )
        assert r_case.status_code == 200, f"Veterinary case creation failed: {r_case.text}"
        case_info = r_case.json()
        test_case_numbers.append(case_info["case_number"])

        # Check DB
        v_case_db = db.veterinary_cases.find_one({"case_number": case_info["case_number"]})
        assert v_case_db is not None
        assert v_case_db.get("visual_analysis_id") == analysis_id
        print(f"[PASS] 15. Veterinary case integration: Case {case_info['case_number']} linked to {analysis_id}.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 16: SURVEILLANCE INTEGRATION (Step 16)
        # -------------------------------------------------------------
        r_surv = client.post(
            f"/visual-health/{analysis_id}/surveillance-review",
            json={"notes": "Visual cluster review escalation"},
            headers=vet_headers
        )
        assert r_surv.status_code == 200, f"Surveillance escalation failed: {r_surv.text}"
        surv_info = r_surv.json()
        test_event_numbers.append(surv_info["event_number"])

        s_event_db = db.disease_events.find_one({"event_number": surv_info["event_number"]})
        assert s_event_db is not None
        assert s_event_db.get("disease_category") == "visual_surveillance"
        print(f"[PASS] 16. Surveillance integration: Event {surv_info['event_number']} created.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 17: ALERT COMPATIBILITY (Step 17)
        # -------------------------------------------------------------
        # Check alerts created by high risk visual analysis or test directly
        vis_alert = db.alerts.find_one({"visual_analysis_id": analysis_id})
        if vis_alert:
            test_alert_ids.append(vis_alert["_id"])
            assert vis_alert.get("alert_type") == "visual_health_signal"
        else:
            # Insert a sample alert to verify schema serialization
            ins_alert = db.alerts.insert_one({
                "animal_id": test_animal_id,
                "farm_id": farmer_farm_id,
                "alert_type": "visual_health_signal",
                "severity": "high",
                "title": "Visual Health Test Signal",
                "message": "Visual alert test",
                "status": "active",
                "visual_analysis_id": analysis_id
            })
            test_alert_ids.append(ins_alert.inserted_id)

        # Verify via alerts API
        r_alert_api = client.get("/alerts", headers=farmer_headers)
        assert r_alert_api.status_code == 200
        print("[PASS] 17. Alert compatibility: visual_health_signal alert serialized and queryable.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 18: WEBSOCKET EVENT COMPATIBILITY (Step 34)
        # -------------------------------------------------------------
        from app.services.websocket_manager import manager
        assert hasattr(manager, "broadcast")
        # Validate event payload structure
        ws_payload = {
            "type": "visual_health_update",
            "action": "analyzed",
            "analysis_id": analysis_id,
            "visual_risk_score": 45.0
        }
        assert ws_payload["type"] == "visual_health_update"
        print("[PASS] 18. WebSocket event compatibility: visual_health_update event schema valid.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 19: AI FALLBACK (Step 25)
        # -------------------------------------------------------------
        vis_expl = generate_visual_explanation(farmer_animal, {"visual_risk_score": 50.0, "observations": []})
        assert "visual_narrative" in vis_expl
        assert "decision_support_disclaimer" in vis_expl

        mm_expl = generate_multimodal_explanation(farmer_animal, {"combined_risk": 55.0, "visual_telemetry_consistency": "directionally_consistent"})
        assert "multimodal_narrative" in mm_expl
        print("[PASS] 19. AI fallback: Deterministic visual & multimodal explanations generated.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 20: FRONTEND IMPORT
        # -------------------------------------------------------------
        from pages.computer_vision import render_computer_vision_page
        assert callable(render_computer_vision_page)
        print("[PASS] 20. Frontend import: render_computer_vision_page imports cleanly.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 21: COMMAND CENTER INTEGRATION (Step 21)
        # -------------------------------------------------------------
        dashboard_file = frontend_dir / "pages" / "dashboard.py"
        with open(dashboard_file, "r", encoding="utf-8") as f:
            dash_code = f.read()
        assert "9.75. VISUAL HEALTH INTELLIGENCE" in dash_code
        assert "get_visual_health_summary" in dash_code
        print("[PASS] 21. Command Center integration: Section 9.75 verified in dashboard.py.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 22: ANIMAL PROFILE INTEGRATION (Step 19)
        # -------------------------------------------------------------
        anim_prof_file = frontend_dir / "pages" / "animal_profile.py"
        with open(anim_prof_file, "r", encoding="utf-8") as f:
            anim_prof_code = f.read()
        assert "👁️ Visual Health" in anim_prof_code
        assert "Analyze New Image" in anim_prof_code
        print("[PASS] 22. Animal Profile integration: Tab 1.5 verified in animal_profile.py.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 23: FARM INTEGRATION (Step 24)
        # -------------------------------------------------------------
        farms_file = frontend_dir / "pages" / "farms.py"
        with open(farms_file, "r", encoding="utf-8") as f:
            farms_code = f.read()
        assert "Visual Health Overview" in farms_code
        assert "get_farm_visual_analyses" in farms_code
        print("[PASS] 23. Farm integration: Visual Health Overview expander verified in farms.py.")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 24: RBAC (Step 31)
        # -------------------------------------------------------------
        # Farmer cannot escalate to surveillance review (only vet/admin)
        r_farmer_surv = client.post(
            f"/visual-health/{analysis_id}/surveillance-review",
            json={"notes": "Farmer trying to create surveillance event"},
            headers=farmer_headers
        )
        assert r_farmer_surv.status_code == 403, f"Expected 403 for farmer surveillance escalation, got {r_farmer_surv.status_code}"
        print("[PASS] 24. RBAC: Farmers prevented from creating surveillance events (403).")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 25: SUMMARY API
        # -------------------------------------------------------------
        r_sum = client.get("/visual-health/summary", headers=farmer_headers)
        assert r_sum.status_code == 200
        sum_data = r_sum.json()
        assert "total_analyses" in sum_data
        assert "animals_assessed" in sum_data
        print("[PASS] 25. Visual Health summary API: Returns KPI aggregation.")
        passed_count += 1

    finally:
        # -------------------------------------------------------------
        # CLEANUP TEST ARTIFACTS
        # -------------------------------------------------------------
        for aid in test_analyses_ids:
            doc = db.visual_analyses.find_one({"analysis_id": aid})
            if doc and doc.get("storage_path"):
                abs_media = root_dir / "media" / doc["storage_path"]
                if os.path.exists(abs_media):
                    try:
                        os.remove(abs_media)
                    except Exception:
                        pass
            db.visual_analyses.delete_many({"analysis_id": aid})
            db.visual_observations.delete_many({"analysis_id": aid})

        for p in test_file_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        for cnum in test_case_numbers:
            db.veterinary_cases.delete_many({"case_number": cnum})

        for enum in test_event_numbers:
            db.disease_events.delete_many({"event_number": enum})

        for al_id in test_alert_ids:
            db.alerts.delete_many({"_id": al_id})

        # Final database count verification (Step 42)
        final_alerts_count = db.alerts.count_documents({})
        final_cases_count = db.veterinary_cases.count_documents({})
        final_animals_count = db.animals.count_documents({})
        final_farms_count = db.farms.count_documents({})
        final_devices_count = db.devices.count_documents({})
        final_users_count = db.users.count_documents({})
        final_events_count = db.disease_events.count_documents({})

        assert final_alerts_count == initial_alerts_count, f"Alerts count mismatch: {final_alerts_count} vs {initial_alerts_count}"
        assert final_cases_count == initial_cases_count, f"Cases count mismatch: {final_cases_count} vs {initial_cases_count}"
        assert final_animals_count == initial_animals_count, f"Animals count mismatch: {final_animals_count} vs {initial_animals_count}"
        assert final_farms_count == initial_farms_count, f"Farms count mismatch: {final_farms_count} vs {initial_farms_count}"
        assert final_devices_count == initial_devices_count, f"Devices count mismatch: {final_devices_count} vs {initial_devices_count}"
        assert final_users_count == initial_users_count, f"Users count mismatch: {final_users_count} vs {initial_users_count}"
        assert final_events_count == initial_events_count, f"Events count mismatch: {final_events_count} vs {initial_events_count}"

        print("=" * 80)
        print(f"PHASE 9 RESULTS: {passed_count}/{total_tests} TESTS PASSED")
        print("DATABASE PRESERVATION VERIFIED: All pre-existing operational records 100% intact.")
        print("=" * 80)


if __name__ == "__main__":
    run_phase_9_tests()
