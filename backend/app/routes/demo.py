"""
backend/app/routes/demo.py
==========================
VETRA SIH DEMONSTRATION & JUDGING ROUTES
Phase 15 — SIH Final Demonstration, Validation & Submission Readiness

Endpoints:
- GET  /demo/status           -> Demo system status, disclaimer, platform version
- GET  /demo/scenarios        -> List metadata for all 9 demonstration scenarios
- GET  /demo/scenarios/{id}   -> Retrieve complete deterministic scenario fixture
- POST /demo/scenarios/{id}/dry-run -> Execute non-destructive pipeline dry-run
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.services.sih_demo_service import SIHDemoService
from app.permissions import get_current_user

router = APIRouter()


@router.get("/status", response_model=Dict[str, Any])
async def get_demo_status():
    """
    Retrieve VETRA SIH Demo Mode status, version, and safety disclaimers.
    Accessible without authentication for easy judging verification and liveness checks.
    """
    return SIHDemoService.get_demo_status()


@router.get("/scenarios", response_model=List[Dict[str, Any]])
async def list_demo_scenarios():
    """
    List all 9 available demonstration scenarios.
    """
    return SIHDemoService.get_all_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=Dict[str, Any])
async def get_demo_scenario(scenario_id: str):
    """
    Get the full deterministic fixture for a specific scenario.
    """
    scenario = SIHDemoService.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return scenario


@router.post("/scenarios/{scenario_id}/dry-run", response_model=Dict[str, Any])
async def run_scenario_dry_run(scenario_id: str, current_user: dict = Depends(get_current_user)):
    """
    Execute an in-memory, zero-mutation dry-run through the VETRA pipeline.
    Requires authenticated user (farmer, vet, or admin).
    """
    result = SIHDemoService.execute_dry_run(scenario_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Execution failed."))
    return result
