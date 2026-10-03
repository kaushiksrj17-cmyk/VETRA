from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.config import settings
from app.database import connect_database, get_database, check_database_readiness
from app.logging_config import logger
from app.middleware import SecurityAndObservabilityMiddleware
from app.routes.auth import router as auth_router
from app.routes.farms import router as farm_router
from app.routes.animals import router as animal_router
from app.routes.health import router as health_router
from app.routes.devices import router as device_router
from app.routes.websocket import router as websocket_router
from app.routes.alerts import router as alert_router
from app.routes.ai_analytics import router as ai_router
from app.routes.prevention import router as prevention_router
from app.routes.veterinary_cases import router as veterinary_cases_router
from app.routes.analytics import router as analytics_router
from app.routes.surveillance import router as surveillance_router
from app.routes.visual_health import router as visual_health_router
from app.routes.cameras import router as camera_router
from app.routes.edge_devices import router as edge_device_router
from app.routes.edge_events import router as edge_events_router
from app.routes.predictive import router as predictive_router
from app.routes.veterinary_network import router as veterinary_network_router
from app.routes.telemedicine import router as telemedicine_router
from app.routes.laboratory import router as laboratory_router
from app.routes.institutional_reporting import router as institutional_reporting_router
from app.routes.epidemiological_events import router as epidemiological_events_router
from app.routes.institutional_surveillance import router as institutional_surveillance_router
from app.routes.government_packages import router as government_packages_router, integration_router
from app.routes.demo import router as demo_router


app = FastAPI(
    title="VETRA API",
    description="Intelligent Livestock Health & Disease Prevention Platform",
    version="1.0.0"
)

# 1. CORS Hardening
cors_origins = [o for o in settings.ALLOWED_ORIGINS if o]
allow_creds = True
if "*" in cors_origins:
    if settings.APP_ENV == "production":
        cors_origins = [o for o in cors_origins if o != "*"]
    else:
        allow_creds = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["http://localhost:8501"],
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 2. Security & Observability Middleware (Request ID, Headers, Rate Limiting, Logging)
app.add_middleware(SecurityAndObservabilityMiddleware)


# 3. Global Centralized Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id},
        headers=getattr(exc, "headers", None)
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "request_id": request_id}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=settings.DEBUG,
        extra={"request_id": request_id, "path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error" if not settings.DEBUG else str(exc),
            "request_id": request_id
        }
    )


@app.on_event("startup")
def startup_event():
    connect_database()
    prod_errors = settings.validate_production_settings()
    if prod_errors:
        for err in prod_errors:
            logger.warning(f"[CONFIG WARNING] {err}")
        if settings.APP_ENV == "production":
            raise RuntimeError(f"Production configuration validation failed: {'; '.join(prod_errors)}")


@app.get("/")
def root():
    return {
        "application": "VETRA",
        "status": "online",
        "version": "1.0.0"
    }



@app.get("/health")
def health():
    db_status = "connected"
    try:
        db = get_database()
        db.command("ping")
    except Exception:
        db_status = "disconnected"

    overall_status = "healthy" if db_status == "connected" else "degraded"
    return {
        "status": overall_status,
        "database": db_status,
        "backend": "online",
        "ai_engine": "operational",
        "predictive_ai": "operational",
        "visual_engine": "ready",
        "media_storage": "ready",
        "camera_subsystem": "ready",
        "edge_computing": "ready",
        "monitoring": "active",
        "analytics": "ready",
        "veterinary_network": "operational",
        "telemedicine": "operational",
        "laboratory_subsystem": "ready",
        "institutional_reporting": "ready",
        "institutional_adapter": "ready (NOT_CONFIGURED)",
        "surveillance_institutional": "operational",
        "government_adapter": "NOT_CONFIGURED",
        "version": "1.0.0"
    }


@app.get("/health/ready")
def health_ready(response: Response):
    """
    Readiness probe for container orchestrators (Kubernetes/Docker)
    verifying MongoDB readiness and configuration integrity without leaking secrets.
    """
    is_db_ready, db_msg = check_database_readiness()
    prod_errors = settings.validate_production_settings()

    is_ready = is_db_ready and (len(prod_errors) == 0 if settings.APP_ENV == "production" else True)
    response.status_code = 200 if is_ready else 503

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if is_db_ready else "disconnected",
        "checks": {
            "database": is_db_ready,
            "configuration": len(prod_errors) == 0,
            "environment": settings.APP_ENV
        },
        "version": "1.0.0"
    }



app.include_router(auth_router)
app.include_router(farm_router)
app.include_router(animal_router)
app.include_router(health_router)
app.include_router(device_router)
app.include_router(websocket_router)
app.include_router(alert_router)
app.include_router(ai_router)
app.include_router(prevention_router)
app.include_router(veterinary_cases_router)
app.include_router(analytics_router)
app.include_router(surveillance_router)
app.include_router(visual_health_router)
app.include_router(camera_router)
app.include_router(edge_device_router)
app.include_router(edge_events_router)
app.include_router(predictive_router)
app.include_router(veterinary_network_router)
app.include_router(telemedicine_router)
app.include_router(laboratory_router)
app.include_router(institutional_reporting_router)
app.include_router(epidemiological_events_router)
app.include_router(institutional_surveillance_router)
app.include_router(government_packages_router)
app.include_router(integration_router)
app.include_router(demo_router, prefix="/demo", tags=["SIH Demo"])