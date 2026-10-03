import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))

from app.main import app
from app.database import get_database


def test_alerts_compatibility():
    print("=" * 60)
    print("VETRA ALERT SCHEMA COMPATIBILITY VERIFICATION")
    print("=" * 60)

    db = get_database()
    client = TestClient(app)

    # 1. Login
    login_res = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 1. Farmer authentication successful.")

    # 2. Initial count check
    initial_count = db.alerts.count_documents({})
    assert initial_count == 4, f"Expected 4 alerts in DB, found {initial_count}"
    print(f"[PASS] 2. Verified initial database count: {initial_count} alerts.")

    # 3. GET /alerts
    print("\n--- Testing GET /alerts ---")
    r_all = client.get("/alerts", headers=headers)
    assert r_all.status_code == 200, f"GET /alerts failed: {r_all.text}"
    all_alerts = r_all.json()
    assert len(all_alerts) == 4, f"Expected 4 alerts returned, got {len(all_alerts)}"
    for a in all_alerts:
        print(f"  Alert ID: {a['id']} | Type: {a['alert_type']:<32} | Status: {a['status']:<12} | Title: {a['title']}")
    print(f"[PASS] 3. GET /alerts returned {len(all_alerts)} serialized alerts with status 200.")

    # 4. GET /alerts?status=active
    print("\n--- Testing GET /alerts?status=active ---")
    r_act = client.get("/alerts?status=active", headers=headers)
    assert r_act.status_code == 200, f"GET /alerts?status=active failed: {r_act.text}"
    act_alerts = r_act.json()
    assert len(act_alerts) == 3, f"Expected 3 active alerts, got {len(act_alerts)}"
    active_types = {a["alert_type"] for a in act_alerts}
    expected_active_types = {
        "preventive_vaccination",
        "preventive_deworming",
        "preventive_veterinary_follow_up"
    }
    assert active_types == expected_active_types, f"Active types mismatch: {active_types}"
    for a in act_alerts:
        print(f"  Active Alert: {a['alert_type']:<32} | Severity: {a['severity']:<8} | Due Date: {a.get('preventive_due_date')}")
    print("[PASS] 4. GET /alerts?status=active verified: all 3 preventive alerts are active.")

    # 5. GET /alerts?status=acknowledged
    print("\n--- Testing GET /alerts?status=acknowledged ---")
    r_ack = client.get("/alerts?status=acknowledged", headers=headers)
    assert r_ack.status_code == 200, f"GET /alerts?status=acknowledged failed: {r_ack.text}"
    ack_alerts = r_ack.json()
    assert len(ack_alerts) == 0, f"Expected 0 acknowledged alerts, got {len(ack_alerts)}"
    print("[PASS] 5. GET /alerts?status=acknowledged verified: 0 acknowledged alerts.")

    # 6. GET /alerts?status=resolved
    print("\n--- Testing GET /alerts?status=resolved ---")
    r_res = client.get("/alerts?status=resolved", headers=headers)
    assert r_res.status_code == 200, f"GET /alerts?status=resolved failed: {r_res.text}"
    res_alerts = r_res.json()
    assert len(res_alerts) == 1, f"Expected 1 resolved alert, got {len(res_alerts)}"
    assert res_alerts[0]["alert_type"] == "multiple_abnormal_signs"
    print(f"  Resolved Alert: {res_alerts[0]['alert_type']} | Title: {res_alerts[0]['title']}")
    print("[PASS] 6. GET /alerts?status=resolved verified: physiological alert is intact and resolved.")

    # 7. Final database count check (ensure duplicate protection & no unintended writes)
    final_count = db.alerts.count_documents({})
    assert final_count == 4, f"Alert count changed from {initial_count} to {final_count}!"
    print(f"\n[PASS] 7. Database integrity verified: alert count remained exactly {final_count}.")

    print("\n" + "=" * 60)
    print("ALL ALERT COMPATIBILITY CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    test_alerts_compatibility()
