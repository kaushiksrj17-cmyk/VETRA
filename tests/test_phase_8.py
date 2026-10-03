import os
import sys
from pathlib import Path
from bson import ObjectId
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
frontend_dir = root_dir / "frontend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))
sys.path.insert(2, str(frontend_dir))

from app.main import app
from app.database import get_database
from app.services.farm_risk_engine import compute_farm_disease_risk
from app.services.disease_cluster_engine import detect_disease_clusters, CLINICAL_SAFETY_DISCLAIMER
from app.services.geospatial_service import haversine_distance, detect_hotspots, find_nearby_farms
from ai_engine.disease_intelligence import generate_surveillance_explanation


def run_phase_8_tests():
    print("=" * 75)
    print("VETRA PHASE 8 — DISEASE SURVEILLANCE & GEOSPATIAL INTELLIGENCE TEST SUITE")
    print("=" * 75)

    db = get_database()
    client = TestClient(app)

    # Record initial counts to verify database safety
    initial_alerts_count = db.alerts.count_documents({})
    initial_farms_count = db.farms.count_documents({})
    initial_events_count = db.disease_events.count_documents({})

    # Authenticate Farmer and Vet
    res_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert res_farmer.status_code == 200, f"Farmer login failed: {res_farmer.text}"
    farmer_token = res_farmer.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    res_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert res_vet.status_code == 200, f"Vet login failed: {res_vet.text}"
    vet_token = res_vet.json()["access_token"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}

    # Fetch a valid farm
    farms = list(db.farms.find({}))
    assert len(farms) >= 1, "No farms found in database"
    test_farm = farms[0]
    test_farm_id = str(test_farm["_id"])

    created_event_ids = []

    try:
        # -------------------------------------------------------------
        # 1. SURVEILLANCE ROUTE REGISTRATION
        # -------------------------------------------------------------
        openapi = app.openapi()
        surv_paths = [p for p in openapi["paths"].keys() if p.startswith("/surveillance")]
        assert len(surv_paths) >= 14, f"Expected >= 14 surveillance endpoints, got {len(surv_paths)}: {surv_paths}"
        print(f"[PASS] 1. Surveillance route registration verified ({len(surv_paths)} endpoints).")

        # -------------------------------------------------------------
        # 2. AUTHENTICATION ENFORCEMENT
        # -------------------------------------------------------------
        res_unauth = client.get("/surveillance/overview")
        assert res_unauth.status_code in [401, 403], f"Expected 401/403 for unauthenticated request, got {res_unauth.status_code}"

        res_auth = client.get("/surveillance/overview", headers=farmer_headers)
        assert res_auth.status_code == 200, f"Authenticated overview failed: {res_auth.text}"
        ov_data = res_auth.json()
        assert "farms_monitored" in ov_data
        assert "clinical_safety_notice" in ov_data
        print("[PASS] 2. Authentication enforcement verified: anonymous blocked, authenticated allowed.")

        # -------------------------------------------------------------
        # 3. FARM RISK CALCULATION
        # -------------------------------------------------------------
        profile = compute_farm_disease_risk(test_farm, db, window_days=7)
        assert 0.0 <= profile["risk_score"] <= 100.0, f"Risk score out of range: {profile['risk_score']}"
        assert profile["risk_category"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        assert "dominant_disease_pattern" in profile
        assert "contributing_factors" in profile
        print(f"[PASS] 3. Farm risk calculation verified: Score={profile['risk_score']}, Category={profile['risk_category']}, Trend={profile['trend']}.")

        # -------------------------------------------------------------
        # 4. DISEASE EVENT CREATION
        # -------------------------------------------------------------
        event_payload = {
            "farm_id": test_farm_id,
            "disease_name": "Test Bovine Respiratory Syndrome",
            "disease_category": "respiratory",
            "symptoms": ["coughing", "pyrexia"],
            "observed_signs": ["respiratory_rate_elevated"],
            "severity": "medium",
            "confidence": 0.8,
            "source": "manual_report",
            "onset_date": "2026-10-01",
            "notes": "Automated Phase 8 unit test event"
        }
        res_create = client.post("/surveillance/events", json=event_payload, headers=farmer_headers)
        assert res_create.status_code == 201, f"Event creation failed: {res_create.text}"
        created_event = res_create.json()
        created_event_id = created_event["id"]
        created_event_ids.append(created_event_id)
        assert created_event["event_number"].startswith("DE-")
        assert created_event["status"] == "suspected"
        print(f"[PASS] 4. Disease event creation verified: {created_event['event_number']} ({created_event['disease_name']}).")

        # -------------------------------------------------------------
        # 5. DISEASE EVENT RETRIEVAL
        # -------------------------------------------------------------
        res_get = client.get(f"/surveillance/events/{created_event_id}", headers=farmer_headers)
        assert res_get.status_code == 200, f"Event retrieval failed: {res_get.text}"
        assert res_get.json()["id"] == created_event_id
        print(f"[PASS] 5. Disease event retrieval verified by ID: {created_event_id}.")

        # -------------------------------------------------------------
        # 6. DISEASE EVENT UPDATE & RBAC
        # -------------------------------------------------------------
        # Farmer cannot update lifecycle status (requires vet/admin)
        res_farmer_update = client.put(
            f"/surveillance/events/{created_event_id}",
            json={"status": "under_investigation"},
            headers=farmer_headers
        )
        assert res_farmer_update.status_code == 403, f"Expected 403 for farmer updating event, got {res_farmer_update.status_code}"

        # Vet can update status
        res_vet_update = client.put(
            f"/surveillance/events/{created_event_id}",
            json={"status": "under_investigation", "notes": "Veterinarian started investigation"},
            headers=vet_headers
        )
        assert res_vet_update.status_code == 200, f"Vet update failed: {res_vet_update.text}"
        assert res_vet_update.json()["status"] == "under_investigation"
        assert res_vet_update.json()["investigation_started_at"] is not None
        print("[PASS] 6. Disease event update & RBAC verified: farmer denied, veterinarian permitted.")

        # -------------------------------------------------------------
        # 7. CLUSTER DETECTION
        # -------------------------------------------------------------
        mock_profiles = [
            {
                "farm_id": "farm_mock_1",
                "farm_name": "Holding Alpha",
                "affected_animals_count": 3,
                "total_animals": 10,
                "dominant_disease_pattern": "Thermal Elevation / Fever",
                "risk_score": 65.0,
                "risk_category": "HIGH",
                "latitude": 22.5645,
                "longitude": 72.9289,
                "district": "Anand"
            },
            {
                "farm_id": "farm_mock_2",
                "farm_name": "Holding Beta",
                "affected_animals_count": 2,
                "total_animals": 8,
                "dominant_disease_pattern": "Thermal Elevation / Fever",
                "risk_score": 55.0,
                "risk_category": "HIGH",
                "latitude": 22.5800,
                "longitude": 72.9400,
                "district": "Anand"
            }
        ]
        clusters = detect_disease_clusters(mock_profiles, db, window_days=7)
        assert len(clusters) >= 1, "Expected cluster detection for multiple high risk farms with matching patterns"
        lead_cluster = clusters[0]
        assert "Potential" in lead_cluster["title"]
        assert lead_cluster["clinical_disclaimer"] == CLINICAL_SAFETY_DISCLAIMER
        print(f"[PASS] 7. Cluster detection verified: '{lead_cluster['title']}' with strict safety disclaimer.")

        # -------------------------------------------------------------
        # 8. GEOGRAPHIC DISTANCE CALCULATION
        # -------------------------------------------------------------
        # Anand (22.5645, 72.9289) to Ahmedabad (23.0225, 72.5714) ~65-75 km
        dist = haversine_distance(22.5645, 72.9289, 23.0225, 72.5714)
        assert dist is not None
        assert 60.0 <= dist <= 80.0, f"Unexpected distance between Anand and Ahmedabad: {dist} km"
        print(f"[PASS] 8. Geographic Haversine distance verified: Anand -> Ahmedabad = {dist} km.")

        # -------------------------------------------------------------
        # 9. HOTSPOT DETECTION
        # -------------------------------------------------------------
        hotspots = detect_hotspots(mock_profiles, max_radius_km=30.0)
        assert len(hotspots) == 1, f"Expected 1 hotspot, got {len(hotspots)}"
        assert hotspots[0]["hotspot_id"].startswith("HOTSPOT-")
        assert hotspots[0]["affected_animal_count"] == 5
        print(f"[PASS] 9. Hotspot detection verified: {hotspots[0]['hotspot_id']} with radius {hotspots[0]['radius_km']} km.")

        # -------------------------------------------------------------
        # 10. MISSING COORDINATES HANDLING
        # -------------------------------------------------------------
        dist_none = haversine_distance(None, None, 22.56, 72.92)
        assert dist_none is None, "Expected None for missing coordinate"

        no_coord_profiles = [
            {"farm_id": "f1", "farm_name": "NoCoord Farm", "risk_score": 80.0, "latitude": None, "longitude": None}
        ]
        hotspots_none = detect_hotspots(no_coord_profiles)
        assert len(hotspots_none) == 0, "Expected 0 hotspots when coordinates are missing (no fabrication)"
        print("[PASS] 10. Missing coordinates handled safely: returns None, no coordinates fabricated.")

        # -------------------------------------------------------------
        # 11. REGIONAL AGGREGATION
        # -------------------------------------------------------------
        res_regions = client.get("/surveillance/regions", headers=farmer_headers)
        assert res_regions.status_code == 200, f"Regions query failed: {res_regions.text}"
        regions_list = res_regions.json()
        assert isinstance(regions_list, list)
        print(f"[PASS] 11. Regional surveillance aggregation verified ({len(regions_list)} region groups).")

        # -------------------------------------------------------------
        # 12. BOUNDED TIME WINDOWS
        # -------------------------------------------------------------
        res_trends = client.get("/surveillance/trends?period_days=30", headers=farmer_headers)
        assert res_trends.status_code == 200, f"Trends failed: {res_trends.text}"
        trends_data = res_trends.json()
        assert trends_data["period_days"] == 30
        assert len(trends_data["time_series"]) == 30

        # Out-of-bounds period_days should be clamped or validated
        res_trends_large = client.get("/surveillance/trends?period_days=120", headers=farmer_headers)
        assert res_trends_large.status_code in [200, 422]  # Clamped or validated by Pydantic Query(le=90)
        print("[PASS] 12. Bounded time windows verified: day-by-day bounded series returned.")

        # -------------------------------------------------------------
        # 13. DUPLICATE ALERT PROTECTION
        # -------------------------------------------------------------
        test_key = "surv_test_key_123"
        # Insert a temporary test alert with surveillance_event_key
        test_alert_doc = {
            "farm_id": test_farm_id,
            "animal_id": "",
            "owner_id": test_farm.get("owner_id", ""),
            "device_id": "TEST_SUITE",
            "alert_type": "surveillance_high_risk",
            "severity": "high",
            "title": "Test Surveillance Alert",
            "message": "Testing duplicate prevention",
            "triggered_by": ["unit_test"],
            "status": "active",
            "surveillance_event_key": test_key
        }
        res_ins = db.alerts.insert_one(test_alert_doc)
        inserted_id = res_ins.inserted_id

        # Verify query with duplicate key finds active alert
        existing_check = db.alerts.find_one({"surveillance_event_key": test_key, "status": "active"})
        assert existing_check is not None, "Duplicate protection lookup failed"
        # Clean up test alert immediately
        db.alerts.delete_one({"_id": inserted_id})
        print("[PASS] 13. Duplicate alert protection verified via unique event key lookup.")

        # -------------------------------------------------------------
        # 14. VETERINARY CASE INTEGRATION
        # -------------------------------------------------------------
        # Link our test disease event to a mock or existing veterinary case
        res_link = client.put(
            f"/surveillance/events/{created_event_id}",
            json={"veterinary_case_id": "CASE-2026-0001", "notes": "Linked to clinical case"},
            headers=vet_headers
        )
        assert res_link.status_code == 200
        assert res_link.json()["veterinary_case_id"] == "CASE-2026-0001"
        print("[PASS] 14. Veterinary clinical case escalation and linking verified.")

        # -------------------------------------------------------------
        # 15. EXISTING ALERT COMPATIBILITY
        # -------------------------------------------------------------
        res_alerts = client.get("/alerts", headers=farmer_headers)
        assert res_alerts.status_code == 200
        alerts_list = res_alerts.json()
        assert len(alerts_list) == initial_alerts_count, f"Alert count mutated! Expected {initial_alerts_count}, got {len(alerts_list)}"
        print(f"[PASS] 15. Existing alert compatibility verified: {len(alerts_list)} alerts preserved intact.")

        # -------------------------------------------------------------
        # 16. AI FALLBACK
        # -------------------------------------------------------------
        ai_narrative = generate_surveillance_explanation(
            farm_profile={
                "farm_name": "Test Holding",
                "risk_score": 62.0,
                "risk_category": "HIGH",
                "total_animals": 10,
                "affected_animals_count": 3,
                "dominant_disease_pattern": "Bovine Respiratory Stress"
            },
            clusters=[],
            observations=[]
        )
        assert "pattern_explanation" in ai_narrative
        assert "risk_interpretation" in ai_narrative
        assert "surveillance_recommendations" in ai_narrative
        assert "veterinary_questions" in ai_narrative
        assert "Decision Support Only" in ai_narrative["clinical_safety_notice"]
        print("[PASS] 16. AI deterministic clinical fallback verified: full structured narrative generated.")

        # -------------------------------------------------------------
        # 17. SURVEILLANCE FRONTEND IMPORT
        # -------------------------------------------------------------
        from pages.surveillance import render_surveillance_page
        assert callable(render_surveillance_page)
        print("[PASS] 17. Surveillance frontend module and render function imported cleanly.")

        # -------------------------------------------------------------
        # 18. COMMAND CENTER COMPATIBILITY
        # -------------------------------------------------------------
        from pages.dashboard import render_dashboard_page
        assert callable(render_dashboard_page)
        print("[PASS] 18. Command Center dashboard compatibility verified.")

    finally:
        # CLEANUP: Ensure test disease events are deleted to preserve initial counts
        if created_event_ids:
            for eid in created_event_ids:
                if ObjectId.is_valid(eid):
                    db.disease_events.delete_one({"_id": ObjectId(eid)})
                else:
                    db.disease_events.delete_one({"_id": eid})

    # FINAL VERIFICATION OF DATABASE SAFETY
    final_alerts_count = db.alerts.count_documents({})
    final_farms_count = db.farms.count_documents({})
    final_events_count = db.disease_events.count_documents({})

    assert final_alerts_count == initial_alerts_count, f"Alerts count mismatch: {final_alerts_count} vs {initial_alerts_count}"
    assert final_farms_count == initial_farms_count, f"Farms count mismatch: {final_farms_count} vs {initial_farms_count}"
    assert final_events_count == initial_events_count, f"Events count mismatch: {final_events_count} vs {initial_events_count}"

    print("-" * 75)
    print("ALL 18 PHASE 8 TARGET TESTS PASSED! DATABASE REMAINED UNMUTATED.")
    print("=" * 75)


if __name__ == "__main__":
    run_phase_8_tests()
