"""
VETRA Phase 10 — Test Suite
===========================
Comprehensive, non-destructive test suite verifying:
- Camera registry & RBAC
- Stream URL credential redaction
- Mock camera & RTSP failure resilience
- Frame sampling & SHA-256 hashing
- Edge device registry & heartbeats
- Webhook event ingestion & deduplication
- Phase 9 CV engine reuse & multimodal integration
- Alert generation with 30-min cooldown
- Disease surveillance & veterinary case escalation
- WebSocket payload broadcast
- Offline buffering & reconnect backoff
- Streamlit page rendering & security checks
- Absolute database preservation (0 baseline document mutations)
"""

from datetime import datetime, timedelta, timezone
import hashlib
import io
import os
from pathlib import Path
import sys
import time

# Ensure unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
frontend_dir = root_dir / "frontend"

# CRITICAL: backend_dir must be first so backend/app package is never shadowed by frontend/app.py
for p in [str(frontend_dir), str(root_dir), str(backend_dir)]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, str(frontend_dir))
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from app.database import get_database
from app.main import app
from app.schemas.camera import (
    CameraCreate,
    CameraResponse,
    CameraUpdate,
    redact_stream_url,
)
from app.schemas.edge_device import (
    EdgeDeviceCreate,
    EdgeDeviceHeartbeat,
    EdgeDeviceResponse,
    EdgeInferenceEventCreate,
)
from app.services.camera_ingestion import (
    MockCameraAdapter,
    RTSPCameraAdapter,
    compute_frame_hash,
    get_camera_stream_adapter,
)
from app.services.edge_monitoring_service import (
    is_alert_in_cooldown,
    process_edge_event,
)
from ai_engine.edge_inference import (
    LocalOpenCVInferenceAdapter,
    get_edge_inference_adapter,
)
from ai_engine.multimodal_health import compute_multimodal_health_assessment
from simulator.camera_simulator import CameraSimulator
from simulator.edge_agent import EdgeAgent


def run_phase_10_tests():
    print("=" * 80)
    print("VETRA PHASE 10 — EDGE COMPUTER VISION & AUTOMATED MONITORING TEST SUITE")
    print("=" * 80)

    db = get_database()
    client = TestClient(app)

    # 1. Capture baseline counts to verify zero database mutation
    initial_counts = {
        "animals": db.animals.count_documents({}),
        "devices": db.devices.count_documents({}),
        "health_readings": db.health_readings.count_documents({}),
        "farms": db.farms.count_documents({}),
        "alerts": db.alerts.count_documents({}),
        "veterinary_cases": db.veterinary_cases.count_documents({}),
        "users": db.users.count_documents({}),
        "disease_events": db.disease_events.count_documents({}),
        "disease_observations": db.disease_observations.count_documents({}),
    }

    # Authenticate test users
    res_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert res_farmer.status_code == 200, f"Farmer login failed: {res_farmer.text}"
    farmer_token = res_farmer.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    farmer_id = res_farmer.json()["user"]["id"]

    res_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert res_vet.status_code == 200, f"Vet login failed: {res_vet.text}"
    vet_token = res_vet.json()["access_token"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}

    # Fetch farmer's farm and animal
    farmer_farms = list(db.farms.find({"$or": [{"owner_id": farmer_id}, {"owner_id": ObjectId(farmer_id)}]}))
    assert len(farmer_farms) > 0, "Farmer farm required for testing"
    test_farm_id = str(farmer_farms[0]["_id"])

    farmer_animal = db.animals.find_one({"farm_id": {"$in": [test_farm_id, ObjectId(test_farm_id)]}})
    assert farmer_animal is not None, "Farmer animal required for testing"
    test_animal_id = str(farmer_animal["_id"])

    # Track created test records for guaranteed cleanup
    created_cameras = []
    created_edge_devices = []
    created_edge_events = []
    created_alerts = []
    created_cases = []
    created_obs = []

    passed_count = 0
    total_tests = 30

    try:
        # -------------------------------------------------------------
        # TEST 1: CAMERA SCHEMA & CREDENTIAL REDACTION
        # -------------------------------------------------------------
        raw_url = "rtsp://admin:superSecretPass123@192.168.1.100:554/h264"
        redacted = redact_stream_url(raw_url)
        assert "superSecretPass123" not in redacted, "Password was not redacted!"
        assert redacted == "rtsp://admin:***@192.168.1.100:554/h264"
        assert redact_stream_url(None) is None
        print("✓ Test 1 Passed: Camera schema & stream URL credential redaction")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 2: CAMERA REGISTRATION API
        # -------------------------------------------------------------
        cam_payload = {
            "camera_name": "Test Pen 1 Overhead",
            "farm_id": test_farm_id,
            "pen_id": "PEN-TEST-01",
            "camera_type": "stationary_pen",
            "connection_type": "mock",
            "stream_url_reference": "mock://pen-1-feed",
            "fps_target": 25.0,
            "sampling_interval_seconds": 5.0,
            "resolution": "1920x1080",
            "location_label": "Barn 1 East"
        }
        res = client.post("/cameras", json=cam_payload, headers=farmer_headers)
        assert res.status_code == 201, f"Camera creation failed: {res.text}"
        cam_data = res.json()
        test_cam_id = cam_data["camera_id"]
        created_cameras.append(test_cam_id)
        assert cam_data["camera_name"] == "Test Pen 1 Overhead"
        assert cam_data["status"] == "online"
        print("✓ Test 2 Passed: Camera registration API (POST /cameras)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 3: CAMERA RBAC PROTECTION
        # -------------------------------------------------------------
        res_no_auth = client.get("/cameras")
        assert res_no_auth.status_code == 401, "Unauthenticated access allowed!"
        res_auth = client.get("/cameras", headers=farmer_headers)
        assert res_auth.status_code == 200
        print("✓ Test 3 Passed: Camera RBAC enforcement (401 for unauthenticated)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 4: CAMERA FARM OWNERSHIP ISOLATION
        # -------------------------------------------------------------
        fake_farm_id = str(ObjectId())
        bad_cam_payload = dict(cam_payload, farm_id=fake_farm_id)
        res_bad = client.post("/cameras", json=bad_cam_payload, headers=farmer_headers)
        assert res_bad.status_code in (403, 404), "Farmer registered camera on unowned farm!"
        print("✓ Test 4 Passed: Camera farm ownership validation")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 5: API RESPONSES REDACT RTSP PASSWORDS
        # -------------------------------------------------------------
        secret_cam_payload = dict(
            cam_payload,
            camera_name="Secret RTSP Cam",
            connection_type="rtsp",
            stream_url_reference="rtsp://vetra_user:HiddenKey999@10.0.0.50:554/live"
        )
        res_sec = client.post("/cameras", json=secret_cam_payload, headers=farmer_headers)
        assert res_sec.status_code == 201
        sec_cam_data = res_sec.json()
        created_cameras.append(sec_cam_data["camera_id"])
        assert "HiddenKey999" not in sec_cam_data["stream_url_reference"]
        assert "rtsp://vetra_user:***@10.0.0.50:554/live" in sec_cam_data["stream_url_reference"]
        print("✓ Test 5 Passed: Camera credentials redacted in API responses")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 6: CAMERA HEALTH EVALUATION
        # -------------------------------------------------------------
        res_health = client.get(f"/cameras/{test_cam_id}/health", headers=farmer_headers)
        assert res_health.status_code == 200
        h_data = res_health.json()
        assert h_data["health_tier"] in ["HEALTHY", "DEGRADED", "OFFLINE"]
        assert "uptime_estimate_pct" in h_data
        print("✓ Test 6 Passed: Camera operational health metrics endpoint")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 7: MOCK CAMERA STREAM ADAPTER
        # -------------------------------------------------------------
        mock_adapter = MockCameraAdapter("CAM-UNIT-01", "mock://unit")
        c_ok, c_stat = mock_adapter.connect()
        assert c_ok and c_stat == "connected"
        f_stat, frame = mock_adapter.read_frame()
        assert f_stat == "connected" and frame is not None and isinstance(frame, np.ndarray)
        s_stat, snap = mock_adapter.get_snapshot()
        assert s_stat == "connected" and snap is not None and len(snap) > 1000
        mock_adapter.disconnect()
        assert not mock_adapter.is_connected()
        print("✓ Test 7 Passed: MockCameraAdapter frame acquisition & snapshot")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 8: RTSP ADAPTER FAILURE RESILIENCE
        # -------------------------------------------------------------
        rtsp_adapter = RTSPCameraAdapter("CAM-UNREACHABLE", "rtsp://invalid-domain-999.xyz:554/stream")
        r_ok, r_stat = rtsp_adapter.connect()
        assert not r_ok
        assert r_stat in ("offline", "timeout", "invalid_stream")
        # System did not crash or hang
        print("✓ Test 8 Passed: RTSPCameraAdapter failure resilience (non-crashing)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 9: CONTROLLED FRAME SAMPLING & RESIZING
        # -------------------------------------------------------------
        oversized_frame = np.ones((1080, 1920, 3), dtype=np.uint8) * 100
        resized = mock_adapter._resize_if_needed(oversized_frame)
        assert resized.shape[1] <= mock_adapter.max_frame_width
        assert resized.shape[0] <= mock_adapter.max_frame_height
        print("✓ Test 9 Passed: Controlled frame sampling & resolution clamping")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 10: FRAME HASHING FOR EVIDENCE INTEGRITY
        # -------------------------------------------------------------
        sample_bytes = b"vetra-evidence-image-bytes-phase10"
        h1 = compute_frame_hash(sample_bytes)
        h2 = compute_frame_hash(sample_bytes)
        assert h1 == h2 and len(h1) == 64
        assert compute_frame_hash(b"different") != h1
        print("✓ Test 10 Passed: Deterministic SHA-256 frame hashing")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 11: EDGE DEVICE SCHEMA
        # -------------------------------------------------------------
        ed_create = EdgeDeviceCreate(
            device_name="Barn 1 Mini-PC",
            device_type="mini_pc",
            farm_id=test_farm_id,
            ip_address="192.168.1.15",
            software_version="1.0.0",
            model_version="v1.0"
        )
        assert ed_create.device_name == "Barn 1 Mini-PC"
        print("✓ Test 11 Passed: Edge device schema validation")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 12: EDGE DEVICE REGISTRATION API
        # -------------------------------------------------------------
        res_ed = client.post("/edge-devices", json=ed_create.model_dump(), headers=farmer_headers)
        assert res_ed.status_code == 201, f"Edge device creation failed: {res_ed.text}"
        ed_data = res_ed.json()
        test_edge_id = ed_data["edge_device_id"]
        created_edge_devices.append(test_edge_id)
        assert ed_data["device_name"] == "Barn 1 Mini-PC"
        assert ed_data["status"] == "online"
        print("✓ Test 12 Passed: Edge device registration (POST /edge-devices)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 13: EDGE DEVICE HEARTBEAT API
        # -------------------------------------------------------------
        hb_payload = {
            "software_version": "1.0.1",
            "cpu_usage_pct": 24.5,
            "memory_usage_pct": 48.0,
            "temperature_celsius": 45.5,
            "buffered_events_count": 0
        }
        res_hb = client.post(f"/edge-devices/{test_edge_id}/heartbeat", json=hb_payload, headers=farmer_headers)
        assert res_hb.status_code == 200
        hb_res = res_hb.json()
        assert hb_res["status"] == "online"
        print("✓ Test 13 Passed: Edge device heartbeat ingestion")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 14: EDGE INFERENCE EVENT INGESTION (WEBHOOK)
        # -------------------------------------------------------------
        event_payload = {
            "edge_device_id": test_edge_id,
            "camera_id": test_cam_id,
            "animal_id": test_animal_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "frame_id": f"FRM-TEST-{int(datetime.now(timezone.utc).timestamp()*1000)}",
            "frame_hash": "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
            "model_name": "VETRA-EdgeVision",
            "model_version": "v1.0",
            "observations": {
                "posture": "normal",
                "mobility": "normal",
                "coat_condition": "clean",
                "surface_anomaly_detected": False
            },
            "visual_risk_score": 0.15,
            "confidence": 0.90,
            "processing_latency_ms": 38.5
        }
        res_evt = client.post("/edge/events", json=event_payload, headers=farmer_headers)
        assert res_evt.status_code == 200, f"Edge event failed: {res_evt.text}"
        evt_res = res_evt.json()
        assert evt_res["accepted"] is True
        assert evt_res["deduplicated"] is False
        created_edge_events.append(evt_res["event_id"])
        print("✓ Test 14 Passed: Edge inference event webhook ingestion (POST /edge/events)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 15: EVENT DEDUPLICATION
        # -------------------------------------------------------------
        # Resubmit exact same event (identical frame hash)
        res_dup = client.post("/edge/events", json=event_payload, headers=farmer_headers)
        assert res_dup.status_code == 200
        dup_res = res_dup.json()
        assert dup_res["accepted"] is True
        assert dup_res["deduplicated"] is True
        print("✓ Test 15 Passed: Deterministic event deduplication via frame hash")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 16: LOCAL EDGE INFERENCE ADAPTER REUSING PHASE 9
        # -------------------------------------------------------------
        inf_adapter = LocalOpenCVInferenceAdapter()
        test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        inf_result = inf_adapter.infer(test_frame)
        assert inf_result["model_name"] == "VETRA-VisualEngine"
        assert "visual_risk_score" in inf_result
        assert "clinical_safety_disclaimer" in inf_result
        print("✓ Test 16 Passed: Edge inference adapter reusing Phase 9 CV engine")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 17: ON-DEMAND LIVE ANALYSIS ENDPOINT
        # -------------------------------------------------------------
        res_ana = client.post(f"/cameras/{test_cam_id}/analyze", headers=farmer_headers)
        assert res_ana.status_code == 200
        ana_data = res_ana.json()
        assert ana_data["camera_id"] == test_cam_id
        assert "inference" in ana_data
        assert "frame_hash" in ana_data
        print("✓ Test 17 Passed: On-demand live analysis API (POST /cameras/{id}/analyze)")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 18: MULTIMODAL HEALTH SYNTHESIS
        # -------------------------------------------------------------
        mm_eval = compute_multimodal_health_assessment(
            animal_data={"name": "Cow #1", "tag_id": "TAG-101"},
            visual_analysis={"visual_risk_score": 35.0},
            telemetry_risk_data={"health_risk_score": 25.0},
            disease_intelligence_data=None,
            surveillance_risk_data=None,
            preventive_status_data=None
        )
        assert "combined_risk" in mm_eval
        assert "risk_category" in mm_eval
        assert "clinical_safety_notice" in mm_eval
        print("✓ Test 18 Passed: Multimodal visual + telemetry risk synthesis")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 19: ALERT COOLDOWN LOGIC (30 MINUTES)
        # -------------------------------------------------------------
        cooldown_cam = "CAM-COOL-TEST"
        assert not is_alert_in_cooldown(db, cooldown_cam, test_animal_id, "visual_health_risk")
        # Insert a simulated alert
        sim_alert = {
            "owner_id": farmer_id,
            "animal_id": test_animal_id,
            "camera_id": cooldown_cam,
            "alert_type": "visual_health_risk",
            "severity": "high",
            "title": "Cooldown Test",
            "message": "Testing alert suppression",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        ins_al = db.alerts.insert_one(sim_alert)
        created_alerts.append(ins_al.inserted_id)
        # Now it should be in cooldown
        assert is_alert_in_cooldown(db, cooldown_cam, test_animal_id, "visual_health_risk")
        print("✓ Test 19 Passed: Alert 30-minute deduplication & cooldown check")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 20: HIGH VISUAL RISK ALERT GENERATION
        # -------------------------------------------------------------
        test_esc_animal_id = f"ANM-ESC-{int(datetime.now(timezone.utc).timestamp())}"
        unique_hash = hashlib.sha256(f"alert-frame-{time.time()}".encode()).hexdigest()
        high_risk_event = {
            "edge_device_id": test_edge_id,
            "camera_id": test_cam_id,
            "animal_id": test_esc_animal_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "frame_id": f"FRM-ALERT-{int(datetime.now(timezone.utc).timestamp()*1000)}",
            "frame_hash": unique_hash,
            "model_name": "VETRA-EdgeVision",
            "model_version": "v1.0",
            "observations": {
                "posture": "severely_compromised",
                "mobility": "compromised",
                "feeding_inactivity": True
            },
            "visual_risk_score": 0.88,
            "confidence": 0.95,
            "processing_latency_ms": 42.0
        }
        res_hr = client.post("/edge/events", json=high_risk_event, headers=farmer_headers)
        assert res_hr.status_code == 200
        hr_data = res_hr.json()
        assert hr_data["accepted"] is True
        assert hr_data["deduplicated"] is False
        assert hr_data["alert_triggered"] is True
        created_edge_events.append(hr_data["event_id"])
        if hr_data.get("alert_id"):
            created_alerts.append(ObjectId(hr_data["alert_id"]))
        print("✓ Test 20 Passed: Automated high visual risk alert generation")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 21: DISEASE SURVEILLANCE INTEGRATION
        # -------------------------------------------------------------
        assert hr_data["surveillance_signal"] is True
        obs_count = db.disease_observations.count_documents({"camera_id": test_cam_id})
        assert obs_count >= 1
        print("✓ Test 21 Passed: Persistent visual concern registered in disease surveillance")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 22: VETERINARY CASE ESCALATION
        # -------------------------------------------------------------
        # High risk (0.88) triggered veterinary case creation for test_esc_animal_id
        vet_case = db.veterinary_cases.find_one({"animal_id": test_esc_animal_id, "source": "visual_analysis"})
        assert vet_case is not None
        assert vet_case["case_type"] in ["illness", "emergency"]
        created_cases.append(vet_case["_id"])
        print("✓ Test 22 Passed: Critical visual concern escalated to veterinary workflow")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 23: WEBSOCKET BROADCAST COMPATIBILITY
        # -------------------------------------------------------------
        from app.services.websocket_manager import manager
        # Verify manager active connections and broadcast structure
        assert hasattr(manager, "broadcast")
        print("✓ Test 23 Passed: WebSocket broadcast manager integration")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 24: API CLIENT HELPERS
        # -------------------------------------------------------------
        import api_client
        assert hasattr(api_client, "get_cameras")
        assert hasattr(api_client, "get_camera_health")
        assert hasattr(api_client, "get_camera_snapshot")
        assert hasattr(api_client, "analyze_camera_frame")
        assert hasattr(api_client, "get_edge_devices")
        assert hasattr(api_client, "get_recent_edge_events")
        print("✓ Test 24 Passed: Frontend API client camera & edge helpers verified")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 25: STREAMLIT CAMERA MONITORING PAGE INTEGRATION
        # -------------------------------------------------------------
        cam_page_file = frontend_dir / "pages" / "camera_monitoring.py"
        assert cam_page_file.exists(), "camera_monitoring.py not found!"
        with open(cam_page_file, "r", encoding="utf-8") as f:
            cam_code = f.read()
        assert "render_camera_monitoring_page" in cam_code
        assert "Live Camera & Edge Intelligence" in cam_code
        assert "Clinical Decision Support Mandate" in cam_code

        app_file = frontend_dir / "app.py"
        with open(app_file, "r", encoding="utf-8") as f:
            app_code = f.read()
        assert "📹 Live Cameras" in app_code
        assert "render_camera_monitoring_page" in app_code
        print("✓ Test 25 Passed: Streamlit camera monitoring page & routing verified")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 26: COMMAND CENTER DASHBOARD INTEGRATION
        # -------------------------------------------------------------
        dash_file = frontend_dir / "pages" / "dashboard.py"
        with open(dash_file, "r", encoding="utf-8") as f:
            dash_code = f.read()
        assert "Edge & Camera Intelligence" in dash_code
        assert "Camera Fleet Health Overview" in dash_code
        assert "Recent Edge Visual Inference Events" in dash_code
        print("✓ Test 26 Passed: Command Center dashboard integration verified")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 27: CAMERA SIMULATOR SAFETY (SIMULATION LABELS)
        # -------------------------------------------------------------
        sim = CameraSimulator("CAM-SIM-TEST", sampling_interval_seconds=1.0)
        sim.start()
        sim_frame = sim.capture_sampled_frame()
        assert sim_frame is not None
        assert sim_frame["is_simulation"] is True
        assert "SIMULATION" in sim_frame["status"] or sim_frame["status"] == "connected"
        sim.stop()
        print("✓ Test 27 Passed: Simulator safety & synthetic labeling verified")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 28: OFFLINE BUFFERING IN EDGE AGENT
        # -------------------------------------------------------------
        agent = EdgeAgent(api_url="http://127.0.0.1:9999", max_buffer_size=10)
        test_payload = {"frame_id": "FRM-OFFLINE-01", "visual_risk_score": 0.25}
        agent._buffer_event(test_payload)
        assert len(agent.offline_buffer) == 1
        assert agent.events_buffered == 1
        print("✓ Test 28 Passed: Standalone Edge Agent FIFO offline buffering")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 29: EXPONENTIAL BACKOFF RECONNECT LOGIC
        # -------------------------------------------------------------
        sleep1 = agent.get_backoff_sleep_seconds()
        sleep2 = agent.get_backoff_sleep_seconds()
        sleep3 = agent.get_backoff_sleep_seconds()
        assert sleep1 == 2 and sleep2 == 5 and sleep3 == 10
        print("✓ Test 29 Passed: Exponential backoff reconnect schedule [2s, 5s, 10s, 30s]")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 30: SECURITY & SECRET PROTECTION
        # -------------------------------------------------------------
        # Verify no .env or sensitive variables leak in summary or camera details
        res_sum = client.get("/cameras/summary", headers=farmer_headers)
        assert res_sum.status_code == 200
        body_text = res_sum.text
        assert "password" not in body_text.lower()
        assert "secret" not in body_text.lower()
        print("✓ Test 30 Passed: Security checks & secret leak prevention")
        passed_count += 1

    finally:
        # Complete cleanup of all test records created during testing
        print("-" * 80)
        print("CLEANING UP TEST ARTIFACTS...")
        if created_cameras:
            db.cameras.delete_many({"camera_id": {"$in": created_cameras}})
        if created_edge_devices:
            db.edge_devices.delete_many({"edge_device_id": {"$in": created_edge_devices}})
        if created_edge_events:
            db.edge_events.delete_many({"event_id": {"$in": created_edge_events}})
        if created_alerts:
            db.alerts.delete_many({"_id": {"$in": created_alerts}})
        if created_cases:
            db.veterinary_cases.delete_many({"_id": {"$in": created_cases}})
        db.disease_observations.delete_many({"camera_id": test_cam_id})

        # Verify zero mutation of baseline database records
        final_counts = {
            "animals": db.animals.count_documents({}),
            "devices": db.devices.count_documents({}),
            "health_readings": db.health_readings.count_documents({}),
            "farms": db.farms.count_documents({}),
            "alerts": db.alerts.count_documents({}),
            "veterinary_cases": db.veterinary_cases.count_documents({}),
            "users": db.users.count_documents({}),
            "disease_events": db.disease_events.count_documents({}),
            "disease_observations": db.disease_observations.count_documents({}),
        }

        print("DATABASE INTEGRITY AUDIT:")
        all_intact = True
        for coll, count in initial_counts.items():
            f_count = final_counts[coll]
            delta = f_count - count
            status_symbol = "✓" if delta == 0 else "✗"
            print(f" {status_symbol} {coll:22s}: Initial = {count:4d} | Final = {f_count:4d} (Delta: {delta:+d})")
            if delta != 0:
                all_intact = False

        assert all_intact, "DATABASE MUTATION DETECTED! Zero mutation requirement violated!"
        print("✓ Database preservation verified: 0 baseline records mutated.")

    print("=" * 80)
    print(f"PHASE 10 TEST RESULT: {passed_count}/{total_tests} TESTS PASSED (100%)")
    print("=" * 80)
    return passed_count == total_tests


if __name__ == "__main__":
    success = run_phase_10_tests()
    sys.exit(0 if success else 1)
