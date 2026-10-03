import random
import time
from datetime import datetime, timezone

import requests


# ============================================================
# VETRA IoT HEALTH MONITORING SIMULATOR
# ============================================================

API_URL = "http://127.0.0.1:8000"

DEVICE_ID = "VETRA-SIM-001"

ANIMAL_ID = "6ab94a566da27ccfb46d9dce"

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YWI5NDE2MDM4MzhkMjA3MjM3ODAzZGQiLCJlbWFpbCI6ImZhcm1lckB2ZXRyYS5kZW1vIiwicm9sZSI6ImZhcm1lciIsImV4cCI6MTc5MDYxNTg1OCwiaWF0IjoxNzkwNTI5NDU4fQ.XCB6WKcUs4JtYlyl33GsPAC9pTQTNn5q-GtlZjJ2u6s"

INTERVAL_SECONDS = 5

# Simulated starting battery
battery_level = 100.0


def generate_health_reading():
    """
    Generate realistic livestock health sensor values.
    """

    temperature = round(
        random.normalvariate(38.6, 0.25),
        2
    )

    heart_rate = round(
        random.normalvariate(72, 5),
        1
    )

    activity = round(
        max(
            0,
            min(
                100,
                random.normalvariate(78, 8)
            )
        ),
        1
    )

    rumination = round(
        max(
            0,
            min(
                100,
                random.normalvariate(82, 6)
            )
        ),
        1
    )

    respiratory_rate = round(
        random.normalvariate(24, 2),
        1
    )

    return {
        "animal_id": ANIMAL_ID,
        "device_id": DEVICE_ID,
        "temperature_c": temperature,
        "heart_rate_bpm": heart_rate,
        "activity_level": activity,
        "rumination_level": rumination,
        "respiratory_rate": respiratory_rate,
        "source": "simulator",
        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


def generate_predictive_scenario(
    scenario_type: str = "normal_stable",
    step: int = 0,
    animal_id: str = ANIMAL_ID,
    device_id: str = DEVICE_ID
):
    """
    Simulation test scenarios for prospective health trajectory validation.
    NOTE: These are simulation models for test fixtures and local dry-runs only.
    They are NEVER automatically injected into production database collections.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if scenario_type == "sensor_dropout":
        # Simulates complete device transmission drop
        return None

    if scenario_type == "missing_data":
        # Simulates telemetry packet with dropped sensor channels
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": 38.6,
            "heart_rate_bpm": None,
            "activity_level": 70.0,
            "rumination_level": None,
            "respiratory_rate": None,
            "source": "simulator_missing_data",
            "recorded_at": now_iso
        }

    if scenario_type == "rapid_deterioration":
        # Severe multi-vital divergence with steep slopes
        temp = round(38.6 + min(2.5, step * 0.40), 2)
        hr = round(72.0 + min(45.0, step * 6.0), 1)
        resp = round(22.0 + min(20.0, step * 3.5), 1)
        act = max(10.0, round(78.0 - (step * 15.0), 1))
        rum = max(10.0, round(82.0 - (step * 15.0), 1))
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": temp,
            "heart_rate_bpm": hr,
            "activity_level": act,
            "rumination_level": rum,
            "respiratory_rate": resp,
            "source": "simulator_rapid_deterioration",
            "recorded_at": now_iso
        }

    if scenario_type == "gradual_deterioration":
        # Steady downward trajectory over sequence
        temp = round(38.6 + min(1.2, step * 0.12), 2)
        hr = round(70.0 + min(18.0, step * 1.8), 1)
        resp = round(22.0 + min(10.0, step * 1.0), 1)
        act = max(35.0, round(75.0 - (step * 4.5), 1))
        rum = max(35.0, round(80.0 - (step * 4.5), 1))
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": temp,
            "heart_rate_bpm": hr,
            "activity_level": act,
            "rumination_level": rum,
            "respiratory_rate": resp,
            "source": "simulator_gradual_deterioration",
            "recorded_at": now_iso
        }

    # Default: normal_stable
    return {
        "animal_id": animal_id,
        "device_id": device_id,
        "temperature_c": round(random.normalvariate(38.6, 0.15), 2),
        "heart_rate_bpm": round(random.normalvariate(70.0, 3.0), 1),
        "activity_level": round(max(50.0, min(95.0, random.normalvariate(76.0, 4.0))), 1),
        "rumination_level": round(max(50.0, min(95.0, random.normalvariate(80.0, 4.0))), 1),
        "respiratory_rate": round(random.normalvariate(22.0, 1.5), 1),
        "source": "simulator_normal_stable",
        "recorded_at": now_iso
    }


def generate_sih_demo_reading(
    scenario: int = 1,
    step: int = 0,
    animal_id: str = ANIMAL_ID,
    device_id: str = DEVICE_ID
):
    """
    Deterministic SIH Demonstration Scenarios for judging & validation.
    Scenario 1: Normal animal (physiological baseline)
    Scenario 2: Early health warning (subtle abnormal trend, moderate risk)
    Scenario 3: Multi-signal acute anomaly (high fever, tachycardia, tachypnea, alert generation)
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if scenario == 1:
        # Scenario 1: Normal animal
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": 38.6,
            "heart_rate_bpm": 72.0,
            "activity_level": 78.0,
            "rumination_level": 82.0,
            "respiratory_rate": 24.0,
            "source": "sih_demo_scenario_1_normal",
            "recorded_at": now_iso
        }
    elif scenario == 2:
        # Scenario 2: Early health warning
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": 39.4,
            "heart_rate_bpm": 82.0,
            "activity_level": 42.0,
            "rumination_level": 45.0,
            "respiratory_rate": 28.0,
            "source": "sih_demo_scenario_2_early_warning",
            "recorded_at": now_iso
        }
    elif scenario == 3:
        # Scenario 3: Multi-signal health risk
        return {
            "animal_id": animal_id,
            "device_id": device_id,
            "temperature_c": 40.8,
            "heart_rate_bpm": 98.0,
            "activity_level": 20.0,
            "rumination_level": 18.0,
            "respiratory_rate": 38.0,
            "source": "sih_demo_scenario_3_multi_signal",
            "recorded_at": now_iso
        }
    else:
        return generate_predictive_scenario("normal_stable", step, animal_id, device_id)


def ensure_authenticated():

    global ACCESS_TOKEN
    login_url = f"{API_URL}/auth/login"
    try:
        res = requests.post(
            login_url,
            json={"email": "farmer@vetra.demo", "password": "Vetra@12345"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if res.status_code == 200:
            ACCESS_TOKEN = res.json().get("access_token")
            return True
    except Exception:
        pass
    return False


def send_health_reading(reading):
    """
    Send health data to VETRA.
    """
    global ACCESS_TOKEN
    url = f"{API_URL}/health-readings"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=reading,
            headers=headers,
            timeout=10
        )

        if response.status_code in [401, 403]:
            if ensure_authenticated():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                response = requests.post(
                    url,
                    json=reading,
                    headers=headers,
                    timeout=10
                )

        if response.status_code in [200, 201]:

            print("\n[SENT] Health reading accepted")

            print(
                f"Temperature : "
                f"{reading['temperature_c']} °C"
            )

            print(
                f"Heart Rate  : "
                f"{reading['heart_rate_bpm']} BPM"
            )

            print(
                f"Activity    : "
                f"{reading['activity_level']}%"
            )

            print(
                f"Rumination  : "
                f"{reading['rumination_level']}%"
            )

            print(
                f"Respiratory : "
                f"{reading['respiratory_rate']} /min"
            )

            print(
                f"Time        : "
                f"{reading['recorded_at']}"
            )

            return True

        print("\n[HEALTH READING ERROR]")
        print("Status:", response.status_code)
        print("Response:", response.text)

        return False

    except requests.exceptions.RequestException as error:

        print("\n[CONNECTION ERROR]")
        print(error)

        return False


def send_device_heartbeat():
    """
    Tell VETRA that this device is currently online.

    The current device API uses PUT /devices/{device_id}
    where device_id means the MongoDB device document ID.
    Therefore this function first finds the registered
    device using GET /devices.
    """

    global battery_level

    try:

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # ----------------------------------------------------
        # Find the registered device
        # ----------------------------------------------------

        response = requests.get(
            f"{API_URL}/devices",
            headers=headers,
            timeout=10
        )

        if response.status_code in [401, 403]:
            if ensure_authenticated():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                response = requests.get(
                    f"{API_URL}/devices",
                    headers=headers,
                    timeout=10
                )

        if response.status_code != 200:
            print(
                "\n[HEARTBEAT ERROR] "
                f"Unable to get devices: "
                f"{response.status_code}"
            )
            print(response.text)
            return

        devices = response.json()

        target_device = None

        for device in devices:

            if device.get("device_id") == DEVICE_ID:
                target_device = device
                break

        if not target_device:

            print(
                "\n[HEARTBEAT ERROR] "
                f"Device {DEVICE_ID} was not found."
            )

            return

        mongo_device_id = target_device["id"]

        # ----------------------------------------------------
        # Simulate battery drain
        # ----------------------------------------------------

        battery_level = max(
            0,
            round(
                battery_level - 0.02,
                2
            )
        )

        # ----------------------------------------------------
        # Update device status
        # ----------------------------------------------------

        payload = {
            "battery_level": battery_level,
            "status": "online"
        }

        update_response = requests.put(
            f"{API_URL}/devices/{mongo_device_id}",
            json=payload,
            headers=headers,
            timeout=10
        )

        if update_response.status_code == 200:

            now = datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

            print(
                f"[HEARTBEAT] ONLINE | "
                f"Battery: {battery_level}% | "
                f"Last seen: {now}"
            )

        else:

            print(
                "\n[HEARTBEAT UPDATE ERROR]"
            )

            print(
                "Status:",
                update_response.status_code
            )

            print(
                "Response:",
                update_response.text
            )

    except requests.exceptions.RequestException as error:

        print(
            "\n[HEARTBEAT CONNECTION ERROR]"
        )

        print(error)


def main():

    print("=" * 60)
    print("VETRA IoT HEALTH MONITORING SIMULATOR")
    print("=" * 60)

    print(f"Device  : {DEVICE_ID}")
    print(f"Animal  : {ANIMAL_ID}")
    print(f"API     : {API_URL}")
    print(f"Interval: {INTERVAL_SECONDS} seconds")

    print("=" * 60)

    print("\nStarting simulator...")
    print("Press CTRL+C to stop.\n")

    while True:

        # ----------------------------------------------------
        # 1. Generate health data
        # ----------------------------------------------------

        reading = generate_health_reading()

        # ----------------------------------------------------
        # 2. Send health reading
        # ----------------------------------------------------

        health_success = send_health_reading(
            reading
        )

        # ----------------------------------------------------
        # 3. Send device heartbeat
        # ----------------------------------------------------

        if health_success:
            send_device_heartbeat()

        # ----------------------------------------------------
        # 4. Wait
        # ----------------------------------------------------

        time.sleep(
            INTERVAL_SECONDS
        )


if __name__ == "__main__":
    main()