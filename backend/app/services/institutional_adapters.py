"""
backend/app/services/institutional_adapters.py
==============================================
VETRA Phase 12 & Phase 13 — Government & Institutional Reporting Integration Adapters.

CRITICAL INTEGRATION INTEGRITY MANDATE:
Do NOT claim that VETRA is connected to real government portals or state disease systems
unless a verified, authorized production API endpoint is configured and active.
Default development state is strictly: NOT_CONFIGURED.
All mock or test operations are explicitly marked: SIMULATION.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Literal, Optional
import uuid


class InstitutionalReportingAdapter(ABC):
    """Abstract Base Class for external governmental / institutional reporting integrations."""

    @abstractmethod
    def validate(self, report_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate institutional report schema conformity before transmission."""
        pass

    @abstractmethod
    def submit(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Transmit verified institutional health report to regulatory destination."""
        pass

    @abstractmethod
    def status(self, external_reference_id: str) -> dict[str, Any]:
        """Query acknowledgement or processing status of submitted report."""
        pass

    @abstractmethod
    def cancel(self, external_reference_id: str, reason: str) -> dict[str, Any]:
        """Transmit revocation or cancellation notice to destination."""
        pass

    @abstractmethod
    def get_health(self) -> dict[str, Any]:
        """Report adapter connectivity, credentials, and transmission readiness."""
        pass

    # Phase 13 Extended Interfaces
    @abstractmethod
    def validate_package(self, package_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate government data package schema and required fields."""
        pass

    @abstractmethod
    def submit_package(self, package_data: dict[str, Any]) -> dict[str, Any]:
        """Transmit approved government data package to regulatory destination."""
        pass

    @abstractmethod
    def check_status(self, submission_id: str) -> dict[str, Any]:
        """Query processing status of an external package submission."""
        pass

    @abstractmethod
    def retrieve_acknowledgement(self, submission_id: str) -> dict[str, Any]:
        """Retrieve formal institutional receipt or acknowledgement token."""
        pass


class MockInstitutionalAdapter(InstitutionalReportingAdapter):
    """
    Standard VETRA Institutional Reporting Adapter.
    By default operates in NOT_CONFIGURED state to guarantee zero fabrication of live government ties.
    Provides verified validation rules and mock transmission capabilities for testing.
    All simulated transmissions are explicitly labeled SIMULATION.
    """

    def __init__(self, state: Literal["NOT_CONFIGURED", "CONFIGURED", "CONNECTED", "ERROR"] = "NOT_CONFIGURED"):
        self._state = state
        self.adapter_id = "mock_gov_adapter"
        self.adapter_name = "VETRA National Animal Disease Reporting Adapter"
        self.system_type = "Government Disease Surveillance Exchange"
        self.category = "government_reporting"

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, new_state: Literal["NOT_CONFIGURED", "CONFIGURED", "CONNECTED", "ERROR"]):
        self._state = new_state

    def get_status(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_name": self.adapter_name,
            "system_type": self.system_type,
            "category": self.category,
            "status": self._state,
            "supports_live_submission": False,
            "disclaimer": "SIMULATION / Local Staging adapter; not connected to any live external government API.",
            "health": self.get_health()
        }

    # -------------------------------------------------------------
    # Phase 12 Legacy Compatibility
    # -------------------------------------------------------------
    def validate(self, report_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates report fields against national surveillance exchange standards."""
        errors = []
        if not report_data.get("title") and not report_data.get("summary"):
            errors.append("Missing mandatory report title or summary.")
        if not report_data.get("reporting_organization"):
            errors.append("Missing reporting organization identifier.")
        return len(errors) == 0, errors

    def submit(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Executes report submission or signals non-configured state."""
        now = datetime.now(timezone.utc).isoformat()
        report_id = report_data.get("report_id", "REP-UNKNOWN")

        if self._state == "NOT_CONFIGURED":
            return {
                "status": "pending_local_dispatch",
                "adapter_state": "NOT_CONFIGURED",
                "transmission_status": "SIMULATED_LOCAL_BUFFER",
                "submission_id": f"LOCAL-SUB-{uuid.uuid4().hex[:8].upper()}",
                "destination": "Local Institutional Buffer (External API Not Configured)",
                "acknowledged": False,
                "timestamp": now,
                "notice": "Government integration is NOT_CONFIGURED. Package buffered locally for institutional review.",
            }

        return {
            "status": "submitted",
            "adapter_state": self._state,
            "transmission_status": "SIMULATED_TRANSMISSION",
            "submission_id": f"GOV-TX-{uuid.uuid4().hex[:8].upper()}",
            "destination": "National Animal Health Surveillance Exchange (Simulated Sandbox)",
            "acknowledged": True,
            "timestamp": now,
            "notice": "Simulated institutional transmission completed successfully in staging environment [SIMULATION].",
        }

    def status(self, external_reference_id: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "external_reference_id": external_reference_id,
            "adapter_state": self._state,
            "delivery_status": "acknowledged" if self._state in ("CONFIGURED", "CONNECTED") else "held_locally",
            "last_verified": now,
        }

    def cancel(self, external_reference_id: str, reason: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "external_reference_id": external_reference_id,
            "cancelled": True,
            "reason": reason,
            "cancelled_at": now,
        }

    # -------------------------------------------------------------
    # Phase 13 Package Submission & Acknowledgement Methods
    # -------------------------------------------------------------
    def validate_package(self, package_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validates Government Data Package structure against national epidemiological data standards.
        Checks for package_id, schema_version, reporting_period, and approval state.
        """
        errors = []
        if not package_data.get("package_id"):
            errors.append("Missing required field: package_id")
        if not package_data.get("schema_version"):
            errors.append("Missing required field: schema_version")
        if not package_data.get("reporting_period"):
            errors.append("Missing required field: reporting_period")
        if not package_data.get("geographic_aggregation"):
            errors.append("Missing required field: geographic_aggregation")
        if package_data.get("approval_status") != "APPROVED":
            errors.append("Package cannot be submitted without authorized institutional approval (status must be APPROVED).")
        return len(errors) == 0, errors

    def submit_package(self, package_data: dict[str, Any]) -> dict[str, Any]:
        """
        Transmits government data package.
        Blocks submission and returns structured block details if adapter is NOT_CONFIGURED.
        In simulation/configured mode, returns simulated transmission metadata clearly labeled [SIMULATION].
        """
        now = datetime.now(timezone.utc).isoformat()
        package_id = package_data.get("package_id", "PKG-UNKNOWN")

        if self._state == "NOT_CONFIGURED":
            return {
                "success": False,
                "status": "BLOCKED",
                "adapter_state": "NOT_CONFIGURED",
                "transmission_status": "SUBMISSION_BLOCKED",
                "submission_id": None,
                "error": "Submission gate failed: External government adapter is NOT_CONFIGURED.",
                "timestamp": now,
                "is_simulation": True,
                "disclaimer": "No real government endpoint is configured. External dispatch blocked by safety gates."
            }

        sim_tx_id = f"SIM-GOV-{uuid.uuid4().hex[:8].upper()}"
        return {
            "success": True,
            "status": "SUBMITTED_SIMULATION",
            "adapter_state": self._state,
            "transmission_status": "SIMULATED_TRANSMISSION",
            "submission_id": sim_tx_id,
            "destination": "National Animal Disease Exchange [SIMULATION SANDBOX]",
            "acknowledged": True,
            "timestamp": now,
            "is_simulation": True,
            "notice": "Simulated government package transmission completed. Not a live regulatory filing [SIMULATION]."
        }

    def check_status(self, submission_id: str) -> dict[str, Any]:
        """Checks processing or receipt status for a submission ID."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "submission_id": submission_id,
            "adapter_state": self._state,
            "status": "PROCESSED_SIMULATION" if self._state in ("CONFIGURED", "CONNECTED") else "PENDING_LOCAL",
            "verified_at": now,
            "is_simulation": True
        }

    def retrieve_acknowledgement(self, submission_id: str) -> dict[str, Any]:
        """Retrieves acknowledgement token or receipt metadata."""
        now = datetime.now(timezone.utc).isoformat()
        if self._state == "NOT_CONFIGURED":
            return {
                "submission_id": submission_id,
                "has_acknowledgement": False,
                "acknowledgement_token": None,
                "status": "NOT_CONFIGURED",
                "notice": "Adapter not configured. No external acknowledgement exists."
            }

        return {
            "submission_id": submission_id,
            "has_acknowledgement": True,
            "acknowledgement_token": f"ACK-SIM-{uuid.uuid4().hex[:12].upper()}",
            "receipt_timestamp": now,
            "status": "ACKNOWLEDGED_SIMULATION",
            "is_simulation": True,
            "notice": "Simulated institutional acknowledgement [SIMULATION]."
        }

    def get_health(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "adapter_state": self._state,
            "category": self.category,
            "submission_enabled": self._state in ("CONFIGURED", "CONNECTED"),
            "configured_endpoints": {
                "disease_reporting_gateway": "NOT_CONFIGURED",
                "laboratory_exchange_feed": "NOT_CONFIGURED",
                "veterinary_authority_push": "NOT_CONFIGURED",
                "government_data_package_api": "NOT_CONFIGURED",
            },
            "last_health_check": datetime.now(timezone.utc).isoformat(),
            "safety_notice": "Production government surveillance API is not configured. Operates in local decision-support mode.",
        }


# Default active adapter instance (initialized to NOT_CONFIGURED)
default_institutional_adapter = MockInstitutionalAdapter(state="NOT_CONFIGURED")


def get_institutional_adapter() -> InstitutionalReportingAdapter:
    """Returns active institutional adapter."""
    return default_institutional_adapter


def get_adapter(adapter_id: str) -> Optional[InstitutionalReportingAdapter]:
    """Returns adapter by ID."""
    if adapter_id in ("mock_gov_adapter", "default"):
        return default_institutional_adapter
    return None


def get_all_adapters() -> list[InstitutionalReportingAdapter]:
    """Returns list of registered adapters."""
    return [default_institutional_adapter]
