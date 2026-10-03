from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.permissions import require_any_authenticated_user
from app.schemas.camera import (
    CameraCreate,
    CameraHealthResponse,
    CameraResponse,
    CameraSummaryResponse,
    CameraTestConnectionResponse,
    CameraUpdate,
)
from app.services.camera_service import (
    create_camera,
    delete_camera,
    ensure_camera_indexes,
    get_camera_by_id,
    get_camera_health,
    get_camera_snapshot,
    get_camera_summary,
    get_cameras,
    test_camera_connection,
    update_camera,
)
from app.services.edge_monitoring_service import capture_and_analyze_camera_frame


router = APIRouter(
    prefix="/cameras",
    tags=["Camera Registry & Monitoring"]
)


@router.on_event("startup")
def startup_event():
    ensure_camera_indexes()


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new livestock camera"
)
def register_camera_endpoint(
    payload: CameraCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return create_camera(payload, current_user)


@router.get(
    "/summary",
    response_model=CameraSummaryResponse,
    summary="Get aggregated camera fleet summary"
)
def get_camera_summary_endpoint(
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_camera_summary(current_user)


@router.get(
    "/farm/{farm_id}",
    response_model=list[CameraResponse],
    summary="Get cameras belonging to a farm"
)
def get_cameras_by_farm_endpoint(
    farm_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_cameras(current_user, farm_id=farm_id)


@router.get(
    "/animal/{animal_id}",
    response_model=list[CameraResponse],
    summary="Get cameras monitoring a specific animal"
)
def get_cameras_by_animal_endpoint(
    animal_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_cameras(current_user, animal_id=animal_id)


@router.get(
    "",
    response_model=list[CameraResponse],
    summary="Query cameras with optional filters"
)
def get_cameras_endpoint(
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    animal_id: Optional[str] = Query(None, description="Filter by animal ID"),
    status: Optional[str] = Query(None, description="Filter by status (online/offline/degraded/disabled)"),
    camera_type: Optional[str] = Query(None, description="Filter by camera type"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_cameras(
        current_user,
        farm_id=farm_id,
        animal_id=animal_id,
        status_filter=status,
        camera_type=camera_type
    )


@router.get(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Get camera details by ID"
)
def get_camera_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_camera_by_id(camera_id, current_user)


@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Update camera settings or metadata"
)
def update_camera_endpoint(
    camera_id: str,
    payload: CameraUpdate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return update_camera(camera_id, payload, current_user)


@router.delete(
    "/{camera_id}",
    summary="Soft-delete or disable a camera"
)
def delete_camera_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return delete_camera(camera_id, current_user)


@router.post(
    "/{camera_id}/test-connection",
    response_model=CameraTestConnectionResponse,
    summary="Test camera stream responsiveness"
)
def test_camera_connection_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return test_camera_connection(camera_id, current_user)


@router.get(
    "/{camera_id}/health",
    response_model=CameraHealthResponse,
    summary="Get camera operational health and metrics"
)
def get_camera_health_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_camera_health(camera_id, current_user)


@router.get(
    "/{camera_id}/snapshot",
    summary="Capture and return a single JPEG snapshot"
)
def get_camera_snapshot_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    snapshot_bytes, media_type = get_camera_snapshot(camera_id, current_user)
    return Response(content=snapshot_bytes, media_type=media_type)


@router.post(
    "/{camera_id}/analyze",
    summary="Capture frame and execute live edge visual inference"
)
def analyze_camera_frame_endpoint(
    camera_id: str,
    current_user: dict = Depends(require_any_authenticated_user)
):
    return capture_and_analyze_camera_frame(camera_id, current_user)
