from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.permissions import require_any_authenticated_user
from app.schemas.edge_device import (
    EdgeInferenceEventCreate,
    EdgeInferenceEventResponse,
)
from app.services.edge_monitoring_service import (
    ensure_edge_monitoring_indexes,
    get_camera_recent_events,
    process_edge_event,
)


router = APIRouter(
    prefix="/edge",
    tags=["Edge Inference & Webhooks"]
)


@router.on_event("startup")
def startup_event():
    ensure_edge_monitoring_indexes()


@router.post(
    "/events",
    response_model=EdgeInferenceEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest structured edge inference observations (Webhook/Agent)"
)
def ingest_edge_inference_event(
    payload: EdgeInferenceEventCreate,
    current_user: dict = Depends(require_any_authenticated_user)
):
    """
    Ingest edge inference event with automatic deduplication, bounded health updates,
    alert cooldown evaluation, and surveillance clustering.
    """
    return process_edge_event(payload, current_user)


@router.get(
    "/events/recent",
    summary="Retrieve recent bounded edge inference events"
)
def get_recent_edge_events_endpoint(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum events to return"),
    current_user: dict = Depends(require_any_authenticated_user)
):
    return get_camera_recent_events(camera_id=camera_id, limit=limit)
