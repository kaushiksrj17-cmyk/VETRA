import os
from typing import Any, Optional, Tuple, Union
import requests

from session import get_token


def _resolve_base_url() -> str:
    """
    Resolve the backend API base URL with production-safe fallbacks:
    1. VETRA_API_URL environment variable (Render / Docker / Cloud)
    2. BACKEND_URL / API_URL environment variables
    3. Streamlit secrets (if running in Streamlit Cloud / Render with secrets)
    4. Default local development URL (http://127.0.0.1:8000)
    Ensures whitespace and trailing slashes are cleanly stripped.
    """
    env_url = (
        os.environ.get("VETRA_API_URL")
        or os.environ.get("BACKEND_URL")
        or os.environ.get("API_URL")
    )
    if env_url and env_url.strip():
        return env_url.strip().rstrip("/")

    try:
        import streamlit as st
        secret_url = (
            st.secrets.get("VETRA_API_URL")
            or st.secrets.get("BACKEND_URL")
            or st.secrets.get("API_URL")
        )
        if secret_url and str(secret_url).strip():
            return str(secret_url).strip().rstrip("/")
    except Exception:
        pass

    return "http://127.0.0.1:8000"


BASE_URL = _resolve_base_url()
REQUEST_TIMEOUT = 10


def _get_headers() -> dict[str, str]:
    """
    Generate HTTP headers including JWT bearer token if user is authenticated.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    token = get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_backend_health() -> bool:
    """
    Check if the FastAPI backend service is reachable.
    """
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_system_health() -> dict:
    """
    Query backend health check and return detailed status of all subsystems.
    """
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": data.get("status", "healthy"),
                "backend": data.get("backend", "online"),
                "database": data.get("database", "connected"),
                "ai_engine": data.get("ai_engine", "operational"),
                "visual_engine": data.get("visual_engine", "ready"),
                "media_storage": data.get("media_storage", "ready"),
                "camera_subsystem": data.get("camera_subsystem", "ready"),
                "edge_computing": data.get("edge_computing", "ready"),
                "monitoring": data.get("monitoring", "active"),
                "analytics": data.get("analytics", "ready"),
            }
        return {
            "status": "degraded",
            "backend": f"error_{response.status_code}",
            "database": "unknown",
            "ai_engine": "unknown",
            "visual_engine": "unknown",
            "media_storage": "unknown",
            "camera_subsystem": "unknown",
            "edge_computing": "unknown",
            "monitoring": "unknown",
            "analytics": "unknown",
        }
    except requests.RequestException:
        return {
            "status": "offline",
            "backend": "offline",
            "database": "unreachable",
            "ai_engine": "unreachable",
            "monitoring": "offline",
            "analytics": "unreachable",
        }


def get_websocket_status() -> str:
    """
    Safely probes the VETRA WebSocket monitoring endpoint.
    Returns: 'LIVE' if responsive, 'SYNCING' if HTTP is up but WS is slow/connecting,
    or 'OFFLINE' if backend is unreachable.
    Guaranteed never to throw or crash the UI.
    """
    if not check_backend_health():
        return "OFFLINE"

    try:
        from websockets.sync.client import connect

        ws_base = os.environ.get("VETRA_WS_URL")
        if ws_base and ws_base.strip():
            ws_url = ws_base.strip().rstrip("/") + "/ws/monitoring"
        elif BASE_URL.startswith("https://"):
            ws_url = "wss://" + BASE_URL[len("https://"):] + "/ws/monitoring"
        elif BASE_URL.startswith("http://"):
            ws_url = "ws://" + BASE_URL[len("http://"):] + "/ws/monitoring"
        elif BASE_URL.startswith("wss://") or BASE_URL.startswith("ws://"):
            ws_url = BASE_URL + "/ws/monitoring"
        else:
            ws_url = f"ws://{BASE_URL}/ws/monitoring"

        with connect(ws_url, open_timeout=0.8, close_timeout=0.5) as websocket:
            websocket.send("ping")
            response = websocket.recv(timeout=0.8)
            if "pong" in str(response).lower() or "alive" in str(response).lower():
                return "LIVE"
            return "SYNCING"
    except Exception:
        return "SYNCING"


def login(email: str, password: str) -> Tuple[bool, Union[dict, str]]:
    """
    Authenticate user and retrieve JWT token.
    """
    url = f"{BASE_URL}/auth/login"
    payload = {
        "email": email.strip().lower(),
        "password": password
    }
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code in [401, 403]:
            detail = response.json().get("detail", "Invalid email or password.")
            return False, detail
        else:
            return False, f"Login failed with status {response.status_code}."
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend. Please verify FastAPI is running."


def register(full_name: str, email: str, password: str) -> Tuple[bool, Union[dict, str]]:
    """
    Register a new farmer account.
    """
    url = f"{BASE_URL}/auth/register"
    payload = {
        "full_name": full_name.strip(),
        "email": email.strip().lower(),
        "password": password
    }
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            return True, response.json()
        elif response.status_code == 409:
            return False, "An account with this email address already exists."
        else:
            detail = response.json().get("detail", "Registration failed.")
            return False, str(detail)
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend. Please verify FastAPI is running."


def get_farms() -> list[dict]:
    """
    Retrieve all farms owned by the authenticated farmer.
    """
    url = f"{BASE_URL}/farms"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def create_farm(farm_data: dict) -> Tuple[bool, Union[dict, str]]:
    """
    Register a new farm under the authenticated farmer.
    """
    url = f"{BASE_URL}/farms"
    try:
        response = requests.post(url, json=farm_data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            return True, response.json()
        detail = response.json().get("detail", "Failed to create farm.")
        return False, str(detail)
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_animals(farm_id: Optional[str] = None) -> list[dict]:
    """
    Retrieve animals for a specific farm, or across all farmer's farms.
    """
    if farm_id:
        url = f"{BASE_URL}/farms/{farm_id}/animals"
        try:
            response = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
            return response.json() if response.status_code == 200 else []
        except requests.RequestException:
            return []
    else:
        # Fetch all animals across all user farms
        farms = get_farms()
        all_animals = []
        for farm in farms:
            f_id = farm.get("id")
            if f_id:
                url = f"{BASE_URL}/farms/{f_id}/animals"
                try:
                    res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
                    if res.status_code == 200:
                        all_animals.extend(res.json())
                except requests.RequestException:
                    pass
        return all_animals


def create_animal(farm_id: str, animal_data: dict) -> Tuple[bool, Union[dict, str]]:
    """
    Register a new animal under a farm.
    """
    url = f"{BASE_URL}/farms/{farm_id}/animals"
    try:
        response = requests.post(url, json=animal_data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code in [200, 201]:
            return True, response.json()
        detail = response.json().get("detail", "Failed to register animal.")
        return False, str(detail)
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_devices() -> list[dict]:
    """
    Retrieve all devices registered for the user.
    """
    url = f"{BASE_URL}/devices"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def get_health_readings(
    animal_id: Optional[str] = None,
    limit: int = 50,
    farm_id: Optional[str] = None
) -> list[dict]:
    """
    Retrieve historical health readings for a specific animal, or recent herd-wide readings.
    """
    if animal_id and animal_id != "all":
        url = f"{BASE_URL}/health-readings/animal/{animal_id}"
        params = {}
    else:
        url = f"{BASE_URL}/health-readings"
        params = {"limit": limit}
        if farm_id and farm_id != "all":
            params["farm_id"] = farm_id

    try:
        response = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    animal_id: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """
    Retrieve alerts filtered by status, severity, or animal ID.
    """
    url = f"{BASE_URL}/alerts"
    params = {"limit": limit}
    if status:
        params["status"] = status
    if severity:
        params["severity"] = severity
    if animal_id:
        params["animal_id"] = animal_id

    try:
        response = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def get_active_alerts(severity: Optional[str] = None, limit: int = 50) -> list[dict]:
    """
    Retrieve currently active alerts.
    """
    url = f"{BASE_URL}/alerts/active"
    params = {"limit": limit}
    if severity:
        params["severity"] = severity

    try:
        response = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []


def acknowledge_alert(alert_id: str) -> Tuple[bool, Union[dict, str]]:
    """
    Mark an active alert as acknowledged.
    """
    url = f"{BASE_URL}/alerts/{alert_id}/acknowledge"
    try:
        response = requests.put(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return True, response.json()
        detail = response.json().get("detail", "Failed to acknowledge alert.")
        return False, str(detail)
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def resolve_alert(alert_id: str) -> Tuple[bool, Union[dict, str]]:
    """
    Mark an alert as resolved.
    """
    url = f"{BASE_URL}/alerts/{alert_id}/resolve"
    try:
        response = requests.put(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return True, response.json()
        detail = response.json().get("detail", "Failed to resolve alert.")
        return False, str(detail)
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


# ====================================================
# AI HEALTH INTELLIGENCE & SURVEILLANCE
# ====================================================
def get_ai_assessment(animal_id: str) -> Optional[dict]:
    """
    Fetch comprehensive AI health risk analysis for an animal.
    """
    url = f"{BASE_URL}/ai/health-assessment/{animal_id}"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None


def get_surveillance_data() -> Optional[dict]:
    """
    Fetch population risk surveillance data.
    """
    url = f"{BASE_URL}/ai/surveillance"
    try:
        response = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None


# ====================================================
# PREVENTIVE CARE & VETERINARY RECORDS
# ====================================================
def get_vaccinations(animal_id: str) -> list[dict]:
    url = f"{BASE_URL}/prevention/animal/{animal_id}/vaccinations"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_vaccination(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/prevention/vaccinations"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in [200, 201]:
            return True, res.json()
        return False, res.json().get("detail", "Failed to save vaccination.")
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_deworming(animal_id: str) -> list[dict]:
    url = f"{BASE_URL}/prevention/animal/{animal_id}/deworming"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_deworming(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/prevention/deworming"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in [200, 201]:
            return True, res.json()
        return False, res.json().get("detail", "Failed to save deworming.")
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_treatments(animal_id: str) -> list[dict]:
    url = f"{BASE_URL}/prevention/animal/{animal_id}/treatments"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_treatment(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/prevention/treatments"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in [200, 201]:
            return True, res.json()
        return False, res.json().get("detail", "Failed to save treatment.")
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_vet_visits(animal_id: str) -> list[dict]:
    url = f"{BASE_URL}/prevention/animal/{animal_id}/vet-visits"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_vet_visit(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/prevention/vet-visits"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in [200, 201]:
            return True, res.json()
        return False, res.json().get("detail", "Failed to save visit.")
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_reminders() -> list[dict]:
    url = f"{BASE_URL}/prevention/reminders"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


# ====================================================
# ANIMAL QR IDENTITY
# ====================================================
def get_animal_qr(farm_id: str, animal_id: str) -> Optional[bytes]:
    url = f"{BASE_URL}/farms/{farm_id}/animals/{animal_id}/qr"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return res.content
        return None
    except requests.RequestException:
        return None


# ====================================================
# VETERINARY CASE MANAGEMENT
# ====================================================

def get_veterinary_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    case_type: Optional[str] = None,
    animal_id: Optional[str] = None,
    veterinarian_id: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    url = f"{BASE_URL}/veterinary-cases"
    params = {"limit": limit}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if case_type:
        params["case_type"] = case_type
    if animal_id:
        params["animal_id"] = animal_id
    if veterinarian_id:
        params["veterinarian_id"] = veterinarian_id

    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


get_cases = get_veterinary_cases


def get_veterinary_case(case_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/veterinary-cases/{case_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def create_veterinary_case(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-cases"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in [200, 201]:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create veterinary case.")
        return False, error_detail
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def update_veterinary_case(case_id: str, data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-cases/{case_id}"
    try:
        res = requests.put(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update case.")
        return False, error_detail
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def assign_veterinary_case(
    case_id: str,
    vet_id: str,
    vet_name: Optional[str] = None,
    notes: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-cases/{case_id}/assign"
    payload = {
        "veterinarian_id": vet_id,
        "veterinarian_name": vet_name,
        "notes": notes
    }
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to assign case.")
        return False, error_detail
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def update_case_status(case_id: str, status: str, notes: Optional[str] = None) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-cases/{case_id}/status"
    payload = {"status": status, "notes": notes}
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update case status.")
        return False, error_detail
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def resolve_veterinary_case(
    case_id: str,
    summary: Optional[str] = None,
    final_diagnosis: Optional[str] = None,
    recommendations: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-cases/{case_id}/resolve"
    payload = {
        "resolution_summary": summary,
        "final_diagnosis": final_diagnosis,
        "recommendations": recommendations
    }
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to resolve case.")
        return False, error_detail
    except requests.RequestException:
        return False, "Unable to connect to VETRA backend."


def get_cases_for_animal(animal_id: str) -> list[dict]:
    url = f"{BASE_URL}/veterinary-cases/animal/{animal_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_cases_for_veterinarian(vet_id: str) -> list[dict]:
    url = f"{BASE_URL}/veterinary-cases/veterinarian/{vet_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_veterinarians() -> list[dict]:
    url = f"{BASE_URL}/veterinary-cases/veterinarians/list"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


# ============================================================
# PHASE 6.7: ADVANCED DASHBOARDS & ANALYTICS CLIENT
# ============================================================

def get_analytics_overview(
    farm_id: Optional[str] = None,
    species: Optional[str] = None,
    days: int = 7
) -> dict:
    url = f"{BASE_URL}/analytics/overview"
    params = {"days": days}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    if species and species != "all":
        params["species"] = species
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_health_trends(
    farm_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    species: Optional[str] = None,
    days: int = 7
) -> dict:
    url = f"{BASE_URL}/analytics/health-trends"
    params = {"days": days}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    if animal_id and animal_id != "all":
        params["animal_id"] = animal_id
    if species and species != "all":
        params["species"] = species
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_alerts(
    farm_id: Optional[str] = None,
    days: int = 30
) -> dict:
    url = f"{BASE_URL}/analytics/alerts"
    params = {"days": days}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_prevention(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/analytics/prevention"
    params = {}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_veterinary(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/analytics/veterinary"
    params = {}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_devices(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/analytics/devices"
    params = {}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_disease_risk(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/analytics/disease-risk"
    params = {}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_analytics_farms() -> list[dict]:
    url = f"{BASE_URL}/analytics/farms"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_analytics_watchlist(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/analytics/watchlist"
    params = {}
    if farm_id and farm_id != "all":
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


# ============================================================
# PHASE 8: DISEASE SURVEILLANCE & GEOSPATIAL INTELLIGENCE
# ============================================================

def get_surveillance_overview(window_days: int = 7) -> dict:
    url = f"{BASE_URL}/surveillance/overview"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


get_surveillance_summary = get_surveillance_overview


def get_surveillance_farms(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/farms"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_farm(farm_id: str, window_days: int = 7) -> dict:
    url = f"{BASE_URL}/surveillance/farm/{farm_id}"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_surveillance_watchlist(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/watchlist"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_risk_map(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/risk-map"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_events(farm_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> list[dict]:
    url = f"{BASE_URL}/surveillance/events"
    params = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    if status:
        params["status"] = status
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_disease_event(payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/surveillance/events"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_msg = res.json().get("detail", "Failed to report disease event.") if res.headers.get("content-type") == "application/json" else res.text
        return False, error_msg
    except requests.RequestException as e:
        return False, str(e)


def update_disease_event(event_id: str, payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/surveillance/events/{event_id}"
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_msg = res.json().get("detail", "Failed to update disease event.") if res.headers.get("content-type") == "application/json" else res.text
        return False, error_msg
    except requests.RequestException as e:
        return False, str(e)


def get_disease_event(event_id: str) -> dict:
    url = f"{BASE_URL}/surveillance/events/{event_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_surveillance_clusters(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/clusters"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_hotspots(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/hotspots"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_regions(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/surveillance/regions"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_trends(period_days: int = 30) -> dict:
    url = f"{BASE_URL}/surveillance/trends"
    try:
        res = requests.get(url, params={"period_days": period_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_surveillance_observations(farm_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    url = f"{BASE_URL}/surveillance/observations"
    params = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def trigger_surveillance_analysis(farm_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/surveillance/analyze"
    params = {}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.post(url, params=params, headers=_get_headers(), timeout=15)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


# ============================================================
# PHASE 9: VISUAL HEALTH & MULTIMODAL INTELLIGENCE APIS
# ============================================================

def _get_upload_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def upload_and_analyze_image(
    animal_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str = "image/jpeg"
) -> Tuple[bool, Union[dict, str]]:
    """
    Upload and analyze an image for livestock visual health signs.
    """
    url = f"{BASE_URL}/visual-health/analyze-image"
    files = {"file": (filename, file_bytes, content_type)}
    data = {"animal_id": animal_id}
    try:
        res = requests.post(url, data=data, files=files, headers=_get_upload_headers(), timeout=30)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Analysis failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def upload_and_analyze_video(
    animal_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str = "video/mp4"
) -> Tuple[bool, Union[dict, str]]:
    """
    Upload and analyze a livestock video using controlled frame sampling.
    """
    url = f"{BASE_URL}/visual-health/analyze-video"
    files = {"file": (filename, file_bytes, content_type)}
    data = {"animal_id": animal_id}
    try:
        res = requests.post(url, data=data, files=files, headers=_get_upload_headers(), timeout=60)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Video analysis failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def get_visual_analyses(
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """
    Retrieve visual analyses history.
    """
    url = f"{BASE_URL}/visual-health/analyses"
    params: dict[str, Any] = {"limit": limit}
    if animal_id:
        params["animal_id"] = animal_id
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_visual_analysis(analysis_id: str) -> Optional[dict]:
    """
    Get a single visual analysis by ID.
    """
    url = f"{BASE_URL}/visual-health/analyses/{analysis_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def get_animal_visual_analyses(animal_id: str, limit: int = 50) -> list[dict]:
    """
    Retrieve visual analyses for a specific animal.
    """
    url = f"{BASE_URL}/visual-health/animal/{animal_id}"
    try:
        res = requests.get(url, params={"limit": limit}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_farm_visual_analyses(farm_id: str, limit: int = 50) -> list[dict]:
    """
    Retrieve visual analyses for a specific farm.
    """
    url = f"{BASE_URL}/visual-health/farm/{farm_id}"
    try:
        res = requests.get(url, params={"limit": limit}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_visual_observations(
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    indicator: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """
    Query extracted visual observations.
    """
    url = f"{BASE_URL}/visual-health/observations"
    params: dict[str, Any] = {"limit": limit}
    if animal_id:
        params["animal_id"] = animal_id
    if farm_id:
        params["farm_id"] = farm_id
    if indicator:
        params["indicator"] = indicator
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_animal_visual_trend(animal_id: str) -> dict:
    """
    Get chronological visual trajectory and comparison for an animal.
    """
    url = f"{BASE_URL}/visual-health/trends/{animal_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def create_multimodal_assessment(
    animal_id: str,
    visual_analysis_id: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    """
    Generate unified Multimodal Health Assessment.
    """
    url = f"{BASE_URL}/visual-health/multimodal-assessment"
    payload = {"animal_id": animal_id}
    if visual_analysis_id:
        payload["visual_analysis_id"] = visual_analysis_id
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Assessment generation failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def get_multimodal_assessment(assessment_id: str) -> Optional[dict]:
    """
    Retrieve multimodal assessment by ID.
    """
    url = f"{BASE_URL}/visual-health/multimodal/{assessment_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def escalate_visual_to_veterinary_case(
    analysis_id: str,
    notes: Optional[str] = None,
    priority: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    """
    Create a clinical case from visual health analysis.
    """
    url = f"{BASE_URL}/visual-health/{analysis_id}/veterinary-case"
    payload: dict[str, Any] = {}
    if notes:
        payload["notes"] = notes
    if priority:
        payload["priority"] = priority
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Case creation failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def escalate_visual_to_surveillance(
    analysis_id: str,
    notes: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    """
    Escalate visual findings into the disease surveillance engine.
    """
    url = f"{BASE_URL}/visual-health/{analysis_id}/surveillance-review"
    payload: dict[str, Any] = {}
    if notes:
        payload["notes"] = notes
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Surveillance escalation failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def get_visual_health_summary() -> dict:
    """
    Get summary KPIs for Visual Health subsystem.
    """
    url = f"{BASE_URL}/visual-health/summary"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_visual_analysis_media_url(analysis_id: str) -> str:
    """
    Get streaming URL for visual analysis media.
    """
    return f"{BASE_URL}/visual-health/analyses/{analysis_id}/media"


# ============================================================
# PHASE 10: CAMERA & EDGE COMPUTING API HELPERS
# ============================================================

def get_cameras(
    farm_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    status: Optional[str] = None,
    camera_type: Optional[str] = None
) -> list[dict]:
    """Retrieve list of cameras with optional filters."""
    url = f"{BASE_URL}/cameras"
    params = {}
    if farm_id:
        params["farm_id"] = farm_id
    if animal_id:
        params["animal_id"] = animal_id
    if status:
        params["status"] = status
    if camera_type:
        params["camera_type"] = camera_type

    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_camera(camera_id: str) -> Optional[dict]:
    """Retrieve camera metadata by ID."""
    url = f"{BASE_URL}/cameras/{camera_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def register_camera(payload: dict) -> Tuple[bool, Union[dict, str]]:
    """Register a new camera in the inventory."""
    url = f"{BASE_URL}/cameras"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 201:
            return True, res.json()
        error_detail = res.json().get("detail", "Camera registration failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def update_camera(camera_id: str, payload: dict) -> Tuple[bool, Union[dict, str]]:
    """Update camera configuration."""
    url = f"{BASE_URL}/cameras/{camera_id}"
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Camera update failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def delete_camera(camera_id: str) -> Tuple[bool, Union[dict, str]]:
    """Soft disable/delete a camera."""
    url = f"{BASE_URL}/cameras/{camera_id}"
    try:
        res = requests.delete(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        return False, "Failed to disable camera"
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def test_camera_connection(camera_id: str) -> Tuple[bool, Union[dict, str]]:
    """Test camera live stream connection."""
    url = f"{BASE_URL}/cameras/{camera_id}/test-connection"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Connection test failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_camera_health(camera_id: str) -> Optional[dict]:
    """Retrieve operational health metrics for a camera."""
    url = f"{BASE_URL}/cameras/{camera_id}/health"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def get_camera_summary() -> dict:
    """Retrieve fleet-wide camera metrics summary."""
    url = f"{BASE_URL}/cameras/summary"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_camera_snapshot(camera_id: str) -> Tuple[bool, Union[bytes, str]]:
    """Fetch on-demand single frame JPEG snapshot."""
    url = f"{BASE_URL}/cameras/{camera_id}/snapshot"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.content
        error_detail = res.json().get("detail", "Snapshot unavailable") if res.headers.get("content-type") == "application/json" else "Camera stream offline"
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def analyze_camera_frame(camera_id: str) -> Tuple[bool, Union[dict, str]]:
    """Trigger live capture and edge AI analysis for a camera."""
    url = f"{BASE_URL}/cameras/{camera_id}/analyze"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Analysis failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_edge_devices(
    farm_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None
) -> list[dict]:
    """List edge computing device nodes."""
    url = f"{BASE_URL}/edge-devices"
    params = {}
    if farm_id:
        params["farm_id"] = farm_id
    if device_type:
        params["device_type"] = device_type
    if status:
        params["status"] = status

    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_edge_device(device_id: str) -> Optional[dict]:
    """Retrieve edge device node details."""
    url = f"{BASE_URL}/edge-devices/{device_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def register_edge_device(payload: dict) -> Tuple[bool, Union[dict, str]]:
    """Register a new edge device node."""
    url = f"{BASE_URL}/edge-devices"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 201:
            return True, res.json()
        error_detail = res.json().get("detail", "Edge device registration failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network or server error: {str(e)}"


def get_edge_device_health(device_id: str) -> Optional[dict]:
    """Retrieve health statistics for an edge device."""
    url = f"{BASE_URL}/edge-devices/{device_id}/health"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def get_edge_device_summary() -> dict:
    """Retrieve edge device summary statistics."""
    url = f"{BASE_URL}/edge-devices/summary"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_recent_edge_events(camera_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Retrieve recent edge inference observations."""
    url = f"{BASE_URL}/edge/events/recent"
    params: dict[str, Any] = {"limit": limit}
    if camera_id:
        params["camera_id"] = camera_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def ingest_edge_event(payload: dict) -> Tuple[bool, Union[dict, str]]:
    """Submit an edge inference event via webhook."""
    url = f"{BASE_URL}/edge/events"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Event ingestion rejected") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


# ============================================================
# PHASE 11: PREDICTIVE HEALTH INTELLIGENCE & FORECASTING
# ============================================================

def get_predictive_assessment(animal_id: str, forecast_window: Optional[int] = None) -> Optional[dict]:
    """Retrieve the latest prospective health risk forecast for an animal."""
    url = f"{BASE_URL}/predictive/animal/{animal_id}"
    params: dict[str, Any] = {}
    if forecast_window:
        params["forecast_window"] = forecast_window
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def analyze_animal_predictive(animal_id: str, forecast_window: int = 48, force_refresh: bool = False) -> Tuple[bool, Union[dict, str]]:
    """Trigger on-demand prospective health deterioration analysis for an animal."""
    url = f"{BASE_URL}/predictive/analyze/animal/{animal_id}"
    params = {
        "forecast_window_hours": forecast_window,
        "force_refresh": force_refresh
    }
    try:
        res = requests.post(url, params=params, headers=_get_headers(), timeout=15)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Analysis failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Connection error: {str(e)}"


def get_farm_predictive_summary(farm_id: str) -> Optional[dict]:
    """Retrieve herd-level prospective risk index and counts for a farm."""
    url = f"{BASE_URL}/predictive/farm/{farm_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def get_predictive_watchlist(farm_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Retrieve prioritized deterioration watchlist sorted by clinical triage urgency."""
    url = f"{BASE_URL}/predictive/watchlist"
    params: dict[str, Any] = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_predictive_high_risk(farm_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Retrieve only high or critical predicted risk animals."""
    url = f"{BASE_URL}/predictive/high-risk"
    params: dict[str, Any] = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_predictive_history(animal_id: str, limit: int = 20, forecast_window: Optional[int] = None) -> list[dict]:
    """Retrieve historical prospective assessments for an animal."""
    url = f"{BASE_URL}/predictive/history/{animal_id}"
    params: dict[str, Any] = {"limit": limit}
    if forecast_window:
        params["forecast_window"] = forecast_window
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_predictive_summary(farm_id: Optional[str] = None) -> dict:
    """Retrieve aggregate predictive statistics across farms/herd."""
    url = f"{BASE_URL}/predictive/summary"
    params: dict[str, Any] = {}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_predictive_trends(farm_id: Optional[str] = None, timeframe: str = "7d") -> dict:
    """Retrieve longitudinal risk forecast trends for Plotly charting."""
    url = f"{BASE_URL}/predictive/trends"
    params = {"timeframe": timeframe}
    if farm_id:
        params["farm_id"] = farm_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_predictive_model_status() -> dict:
    """Retrieve predictive model version, active adapter, and transparency metadata."""
    url = f"{BASE_URL}/predictive/model-status"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def escalate_predictive_case(
    assessment_id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    priority: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    """Escalate a prospective health deterioration finding into a clinical veterinary case."""
    url = f"{BASE_URL}/predictive/escalate/{assessment_id}"
    payload: dict[str, Any] = {}
    if title:
        payload["title"] = title
    if notes:
        payload["notes"] = notes
    if priority:
        payload["priority"] = priority
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Escalation failed") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


# ==============================================================================
# PHASE 12: VETERINARY NETWORK & DIRECTORY
# ==============================================================================

def create_veterinary_profile(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-network/profiles"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create profile") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_veterinary_profiles(
    specialization: Optional[str] = None,
    region: Optional[str] = None,
    availability_status: Optional[str] = None,
    available_only: bool = False
) -> list[dict]:
    url = f"{BASE_URL}/veterinary-network/profiles"
    params: dict[str, Any] = {"available_only": available_only}
    if specialization:
        params["specialization"] = specialization
    if region:
        params["region"] = region
    if availability_status:
        params["availability_status"] = availability_status
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_veterinary_profile(veterinarian_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/veterinary-network/profiles/{veterinarian_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def update_veterinary_profile(veterinarian_id: str, data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/veterinary-network/profiles/{veterinarian_id}"
    try:
        res = requests.put(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update profile") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_veterinary_availability() -> list[dict]:
    url = f"{BASE_URL}/veterinary-network/availability"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_veterinary_specializations() -> list[str]:
    url = f"{BASE_URL}/veterinary-network/specializations"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_veterinary_regions() -> list[str]:
    url = f"{BASE_URL}/veterinary-network/regions"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


# ==============================================================================
# PHASE 12: TELEMEDICINE & CLINICAL NOTES
# ==============================================================================

def create_telemedicine_consultation(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_telemedicine_consultations(
    status: Optional[str] = None,
    case_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    veterinarian_id: Optional[str] = None
) -> list[dict]:
    url = f"{BASE_URL}/telemedicine/consultations"
    params: dict[str, Any] = {}
    if status:
        params["status"] = status
    if case_id:
        params["case_id"] = case_id
    if animal_id:
        params["animal_id"] = animal_id
    if farm_id:
        params["farm_id"] = farm_id
    if veterinarian_id:
        params["veterinarian_id"] = veterinarian_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_telemedicine_consultation(consultation_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def update_telemedicine_consultation(consultation_id: str, data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}"
    try:
        res = requests.put(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def accept_telemedicine_consultation(
    consultation_id: str,
    scheduled_at: Optional[str] = None,
    notes: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/accept"
    payload: dict[str, Any] = {}
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    if notes:
        payload["notes"] = notes
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to accept consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def start_telemedicine_consultation(consultation_id: str) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/start"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to start consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def complete_telemedicine_consultation(
    consultation_id: str,
    clinical_summary: Optional[str] = None,
    veterinarian_notes: Optional[str] = None,
    recommendations: Optional[str] = None,
    follow_up_date: Optional[str] = None,
    follow_up_required: bool = False
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/complete"
    payload: dict[str, Any] = {"follow_up_required": follow_up_required}
    if clinical_summary:
        payload["clinical_summary"] = clinical_summary
    if veterinarian_notes:
        payload["veterinarian_notes"] = veterinarian_notes
    if recommendations:
        payload["recommendations"] = recommendations
    if follow_up_date:
        payload["follow_up_date"] = follow_up_date
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to complete consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def cancel_telemedicine_consultation(consultation_id: str, reason: Optional[str] = None) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/cancel"
    params = {"reason": reason} if reason else {}
    try:
        res = requests.post(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to cancel consultation") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def add_clinical_note(consultation_id: str, note_data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/notes"
    try:
        res = requests.post(url, json=note_data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to add clinical note") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_clinical_notes(consultation_id: str) -> list[dict]:
    url = f"{BASE_URL}/telemedicine/consultations/{consultation_id}/notes"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


# ==============================================================================
# PHASE 12: LABORATORY RESULTS
# ==============================================================================

def create_laboratory_result(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/laboratory/results"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to record lab result") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_laboratory_results(
    case_id: Optional[str] = None,
    animal_id: Optional[str] = None,
    farm_id: Optional[str] = None,
    result_status: Optional[str] = None
) -> list[dict]:
    url = f"{BASE_URL}/laboratory/results"
    params: dict[str, Any] = {}
    if case_id:
        params["case_id"] = case_id
    if animal_id:
        params["animal_id"] = animal_id
    if farm_id:
        params["farm_id"] = farm_id
    if result_status:
        params["status"] = result_status
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_laboratory_result(result_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/laboratory/results/{result_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


# ==============================================================================
# PHASE 12: INSTITUTIONAL REPORTING & INTEGRATION
# ==============================================================================

def create_institutional_report(data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports"
    try:
        res = requests.post(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_institutional_reports(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    farm_id: Optional[str] = None,
    severity: Optional[str] = None
) -> list[dict]:
    url = f"{BASE_URL}/institutional/reports"
    params: dict[str, Any] = {}
    if report_type:
        params["report_type"] = report_type
    if status:
        params["status"] = status
    if farm_id:
        params["farm_id"] = farm_id
    if severity:
        params["severity"] = severity
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_institutional_report(report_id: str) -> Optional[dict]:
    url = f"{BASE_URL}/institutional/reports/{report_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None


def update_institutional_report(report_id: str, data: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}"
    try:
        res = requests.put(url, json=data, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def review_institutional_report(report_id: str, reviewer_notes: Optional[str] = None) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}/review"
    payload = {"reviewer_notes": reviewer_notes} if reviewer_notes else {}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to review report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def approve_institutional_report(
    report_id: str,
    approval_notes: Optional[str] = None,
    digital_signature_reference: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}/approve"
    payload: dict[str, Any] = {}
    if approval_notes:
        payload["approval_notes"] = approval_notes
    if digital_signature_reference:
        payload["digital_signature_reference"] = digital_signature_reference
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to approve report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def submit_institutional_report(
    report_id: str,
    adapter_id: Optional[str] = None,
    submission_remarks: Optional[str] = None
) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}/submit"
    payload: dict[str, Any] = {}
    if adapter_id:
        payload["adapter_id"] = adapter_id
    if submission_remarks:
        payload["submission_remarks"] = submission_remarks
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to submit report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def cancel_institutional_report(report_id: str, reason: Optional[str] = None) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}/cancel"
    params = {"reason": reason} if reason else {}
    try:
        res = requests.post(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to cancel report") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_institutional_report_status(report_id: str) -> dict:
    url = f"{BASE_URL}/institutional/reports/{report_id}/status"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def export_institutional_report(
    report_id: str,
    format: str = "json",
    redact_pii: bool = False
) -> Tuple[bool, Union[str, bytes]]:
    url = f"{BASE_URL}/institutional/reports/{report_id}/export"
    params = {"format": format, "redact_pii": redact_pii}
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.text
        return False, "Failed to export report."
    except requests.RequestException as e:
        return False, f"Network error: {str(e)}"


def get_institutional_integrations() -> list[dict]:
    url = f"{BASE_URL}/institutional/integrations"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_integration_status(adapter_id: str) -> dict:
    url = f"{BASE_URL}/institutional/integrations/{adapter_id}/status"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


# ============================================================
# PHASE 13: GOVERNMENT & INSTITUTIONAL ADVANCED SURVEILLANCE
# ============================================================

def list_epidemiological_events(
    farm_id: Optional[str] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    review_state: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    url = f"{BASE_URL}/epidemiological-events"
    params: dict[str, Any] = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    if event_type:
        params["event_type"] = event_type
    if status:
        params["status"] = status
    if review_state:
        params["review_state"] = review_state
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_epidemiological_event(event_id: str) -> dict:
    url = f"{BASE_URL}/epidemiological-events/{event_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def create_epidemiological_event(payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/epidemiological-events"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create epidemiological event") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def update_epidemiological_event(event_id: str, payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/epidemiological-events/{event_id}"
    try:
        res = requests.put(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update epidemiological event") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def review_epidemiological_event(event_id: str, review_state: str, review_notes: str = "") -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/epidemiological-events/{event_id}/review"
    payload = {"review_state": review_state, "review_notes": review_notes}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to review event") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def confirm_epidemiological_event(event_id: str, confirmation_authority: str, notes: str = "") -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/epidemiological-events/{event_id}/confirm"
    payload = {"confirmation_authority": confirmation_authority, "confirmation_notes": notes}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to confirm event") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def dismiss_epidemiological_event(event_id: str, rationale: str = "") -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/epidemiological-events/{event_id}/dismiss"
    payload = {"dismissal_rationale": rationale}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to dismiss event") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def get_institutional_surveillance_overview(window_days: int = 7) -> dict:
    url = f"{BASE_URL}/institutional-surveillance/overview"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def list_institutional_warnings(
    farm_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    url = f"{BASE_URL}/institutional-surveillance/warnings"
    params: dict[str, Any] = {"limit": limit}
    if farm_id:
        params["farm_id"] = farm_id
    if severity:
        params["severity"] = severity
    if status:
        params["status"] = status
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def create_institutional_warning(payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional-surveillance/warnings"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to create warning") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def update_institutional_warning_status(warning_id: str, status_val: str, notes: str = "") -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/institutional-surveillance/warnings/{warning_id}/status"
    payload = {"status": status_val, "notes": notes}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to update warning status") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def get_institutional_clusters(window_days: int = 7) -> list[dict]:
    url = f"{BASE_URL}/institutional-surveillance/clusters"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_cross_farm_signals() -> list[dict]:
    url = f"{BASE_URL}/institutional-surveillance/cross-farm-signals"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_species_surveillance() -> list[dict]:
    url = f"{BASE_URL}/institutional-surveillance/species"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_surveillance_evidence_matrix(farm_id: Optional[str] = None, animal_id: Optional[str] = None) -> dict:
    url = f"{BASE_URL}/institutional-surveillance/evidence-matrix"
    params: dict[str, Any] = {}
    if farm_id:
        params["farm_id"] = farm_id
    if animal_id:
        params["animal_id"] = animal_id
    try:
        res = requests.get(url, params=params, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_institutional_geospatial_surveillance() -> dict:
    url = f"{BASE_URL}/institutional-surveillance/geospatial"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def get_institutional_trends(window_days: int = 14) -> dict:
    url = f"{BASE_URL}/institutional-surveillance/trends"
    try:
        res = requests.get(url, params={"window_days": window_days}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def generate_government_package(payload: dict) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/government-packages/generate"
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code in (200, 201):
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to generate package") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def list_government_packages(limit: int = 50) -> list[dict]:
    url = f"{BASE_URL}/government-packages"
    try:
        res = requests.get(url, params={"limit": limit}, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []


def get_government_package(package_id: str) -> dict:
    url = f"{BASE_URL}/government-packages/{package_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def export_government_package_json(package_id: str) -> dict:
    url = f"{BASE_URL}/government-packages/{package_id}/json"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def export_government_package_csv(package_id: str) -> Tuple[bool, Union[str, bytes]]:
    url = f"{BASE_URL}/government-packages/{package_id}/csv"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.text
        return False, "Failed to export CSV"
    except requests.RequestException as e:
        return False, str(e)


def export_government_package_pdf(package_id: str) -> Tuple[bool, Union[bytes, str]]:
    url = f"{BASE_URL}/government-packages/{package_id}/pdf"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.content
        return False, "Failed to export PDF"
    except requests.RequestException as e:
        return False, str(e)


def validate_government_package(package_id: str) -> dict:
    url = f"{BASE_URL}/government-packages/{package_id}/validate"
    try:
        res = requests.post(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def approve_government_package(package_id: str, notes: str = "") -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/government-packages/{package_id}/approve"
    payload = {"approval_notes": notes}
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", "Failed to approve package") if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def submit_government_package(package_id: str, adapter_id: str = "mock_gov_adapter", notes: Optional[str] = None) -> Tuple[bool, Union[dict, str]]:
    url = f"{BASE_URL}/government-packages/{package_id}/submit"
    payload: dict[str, Any] = {"adapter_id": adapter_id}
    if notes:
        payload["submission_notes"] = notes
    try:
        res = requests.post(url, json=payload, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        if res.status_code == 200:
            return True, res.json()
        error_detail = res.json().get("detail", res.json().get("message", "Submission blocked by safety gates")) if res.headers.get("content-type") == "application/json" else res.text
        return False, str(error_detail)
    except requests.RequestException as e:
        return False, str(e)


def get_government_adapter_status() -> dict:
    url = f"{BASE_URL}/institutional-integrations/status"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else {}
    except requests.RequestException:
        return {}


def list_available_adapters() -> list[dict]:
    url = f"{BASE_URL}/institutional-integrations/adapters"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
        return res.json() if res.status_code == 200 else []
    except requests.RequestException:
        return []









