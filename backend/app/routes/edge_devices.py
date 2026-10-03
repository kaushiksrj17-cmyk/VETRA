from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.permissions import require_any_authenticated_user
from app.schemas.edge_device import (
    EdgeDeviceCreate,
    EdgeDeviceHealthResponse,
    EdgeDeviceHeartbeat,
    EdgeDeviceResponse,
    EdgeDeviceSummaryResponse,
    EdgeDeviceUpdate,
)
from app.services.edge_device_service import (
    create_edge_device,
    ensure_edge_device_indexes,
    get_edge_device_by_id,
    get_edge_device_health,
    get_edge_device_summary,
    get_edge_devices,
    record_heartbeat,
    update_edge_device,
)


router = APIRouter(
    prefix="/edge-devices",
    tags=["Edge Device Management"]
)


@router.on_event("startup")
def startup_event():
    ensure_edge_device_indexes()


@router.post(
    "",
    response_model=EdgeDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new edge computing device node"
)
def register_edge_device_endpoint(
    payload: EdgeDeviceCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return create_edge_device(payload, current_user)


@router.get(
    "/summary",
    response_model=EdgeDeviceSummaryResponse,
    summary="Aggregate edge device fleet metrics"
)
def get_edge_devices_summary_endpoint(
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_edge_device_summary(current_user)


@router.get(
    "",
    response_model=list[EdgeDeviceResponse],
    summary="List edge devices with optional filtering"
)
def get_edge_devices_endpoint(
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by operational status"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_edge_devices(
        current_user,
        farm_id=farm_id,
        device_type=device_type,
        status_filter=status
    )


@router.get(
    "/{device_id}",
    response_model=EdgeDeviceResponse,
    summary="Get edge device details by ID"
)
def get_edge_device_endpoint(
    device_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_edge_device_by_id(device_id, current_user)


@router.put(
    "/{device_id}",
    response_model=EdgeDeviceResponse,
    summary="Update edge device configuration"
)
def update_edge_device_endpoint(
    device_id: str,
    payload: EdgeDeviceUpdate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return update_edge_device(device_id, payload, current_user)


@router.post(
    "/{device_id}/heartbeat",
    summary="Ingest periodic edge node heartbeat"
)
def record_heartbeat_endpoint(
    device_id: str,
    payload: EdgeDeviceHeartbeat,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return record_heartbeat(device_id, payload, current_user)


@router.get(
    "/{device_id}/health",
    response_model=EdgeDeviceHealthResponse,
    summary="Get edge device operational health tier"
)
def get_edge_device_health_endpoint(
    device_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_edge_device_health(device_id, current_user)
