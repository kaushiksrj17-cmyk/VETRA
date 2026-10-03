"""
VETRA Phase 12 - Veterinary Notification Subsystem

Provides notification abstraction and delivery provider interface.
Default is MockNotificationProvider, clearly labeled as [SIMULATION],
preventing uncontrolled email/SMS sending during development while supporting
live in-app alerts and WebSocket event dispatching.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("vetra.notifications")


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationEvent(str, Enum):
    NEW_CASE_ASSIGNED = "new_case_assigned"
    CONSULTATION_REQUESTED = "consultation_requested"
    CONSULTATION_ACCEPTED = "consultation_accepted"
    FOLLOW_UP_DUE = "follow_up_due"
    CRITICAL_ALERT = "critical_alert"
    PREDICTIVE_DETERIORATION = "predictive_deterioration"
    SURVEILLANCE_ESCALATION = "surveillance_escalation"
    INSTITUTIONAL_REPORT_STATUS = "institutional_report_status"


class NotificationMessage:
    def __init__(
        self,
        recipient_id: str,
        recipient_role: str,
        event_type: NotificationEvent,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        metadata: Optional[Dict[str, Any]] = None,
        is_simulation: bool = True
    ):
        self.recipient_id = recipient_id
        self.recipient_role = recipient_role
        self.event_type = event_type
        self.title = title
        self.message = message
        self.channel = channel
        self.metadata = metadata or {}
        self.is_simulation = is_simulation
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "recipient_role": self.recipient_role,
            "event_type": self.event_type.value if hasattr(self.event_type, "value") else str(self.event_type),
            "title": self.title,
            "message": self.message,
            "channel": self.channel.value if hasattr(self.channel, "value") else str(self.channel),
            "metadata": self.metadata,
            "is_simulation": self.is_simulation,
            "timestamp": self.timestamp,
        }


class NotificationProvider(ABC):
    @abstractmethod
    def send(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Dispatch notification through provider channel."""
        pass

    @abstractmethod
    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve historical dispatched notifications."""
        pass


class MockNotificationProvider(NotificationProvider):
    """
    Default simulation provider.
    Prepends [SIMULATION] to notifications and logs to an internal circular buffer.
    Prevents unauthorized or accidental email/SMS spam.
    """
    def __init__(self, max_history: int = 200):
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []

    def send(self, notification: NotificationMessage) -> Dict[str, Any]:
        data = notification.to_dict()
        data["title"] = f"[SIMULATION] {notification.title}"
        data["delivery_status"] = "SIMULATED_DELIVERED"
        data["provider"] = "MockNotificationProvider"
        data["disclaimer"] = "Simulation provider active; no live external SMS or email sent."

        self._history.insert(0, data)
        if len(self._history) > self.max_history:
            self._history = self._history[:self.max_history]

        logger.info(
            "Notification dispatched: [%s] to %s (%s): %s",
            data["event_type"],
            data["recipient_id"],
            data["recipient_role"],
            data["title"]
        )
        return data

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[:limit]


class NotificationService:
    def __init__(self, provider: Optional[NotificationProvider] = None):
        self.provider: NotificationProvider = provider or MockNotificationProvider()

    def dispatch(
        self,
        recipient_id: str,
        recipient_role: str,
        event_type: NotificationEvent,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create and dispatch a notification.
        Also attempts WebSocket broadcast if WebSocket manager is active.
        """
        notification = NotificationMessage(
            recipient_id=recipient_id,
            recipient_role=recipient_role,
            event_type=event_type,
            title=title,
            message=message,
            channel=channel,
            metadata=metadata,
            is_simulation=True
        )

        result = self.provider.send(notification)

        # Attempt WebSocket broadcast integration
        try:
            from app.services.websocket_manager import manager
            import asyncio

            ws_payload = {
                "type": "notification",
                "event": event_type.value if hasattr(event_type, "value") else str(event_type),
                "data": result
            }
            # If an event loop is running, schedule broadcast
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(manager.broadcast(ws_payload))
            except RuntimeError:
                pass
        except Exception:
            pass

        return result

    def get_recent_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.provider.get_logs(limit=limit)


# Singleton instance
notification_service = NotificationService()
