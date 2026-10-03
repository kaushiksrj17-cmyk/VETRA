from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from app.logging_config import logger


class ConnectionManager:
    """
    Manages active WebSocket connections for VETRA with safe exception handling,
    stale connection cleanup, and authentication context association.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_info: Optional[Dict[str, Any]] = None
    ):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = user_info or {}

    def disconnect(
        self,
        websocket: WebSocket
    ):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.warning(f"Failed to send personal WebSocket message: {str(exc)}")
            self.disconnect(websocket)

    async def broadcast(
        self,
        message: dict
    ):
        """
        Broadcast message to active subscribers with automatic stale connection pruning.
        """
        disconnected = []

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.debug(f"WebSocket client disconnected during broadcast: {str(exc)}")
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()