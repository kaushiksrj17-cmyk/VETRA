import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from app.services.websocket_manager import manager
from app.security import decode_access_token
from app.config import settings
from app.logging_config import logger


router = APIRouter(
    tags=["Real-Time Monitoring"]
)


@router.websocket("/ws/monitoring")
async def monitoring_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    authenticated_user = None

    # 1. If token is passed via query parameter, validate it
    if token:
        try:
            authenticated_user = decode_access_token(token)
        except Exception:
            # Reject invalid or malformed token with WS 1008 Policy Violation
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired authentication token"
            )
            return

    # 2. Enforce authentication if configured for production
    if settings.WEBSOCKET_AUTH_REQUIRED and not authenticated_user:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication token required"
        )
        return

    # 3. Accept connection and record metadata
    await manager.connect(websocket, user_info=authenticated_user)

    try:
        while True:
            raw_message = await websocket.receive_text()

            # Heartbeat handling
            if raw_message.strip().lower() == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "message": "VETRA WebSocket is alive"
                })
                continue

            # In-band authentication message support
            try:
                data = json.loads(raw_message)
                if isinstance(data, dict) and data.get("type") == "auth":
                    auth_token = data.get("token")
                    if auth_token:
                        try:
                            authenticated_user = decode_access_token(auth_token)
                            manager.connection_metadata[websocket] = authenticated_user
                            await websocket.send_json({
                                "type": "auth_ack",
                                "status": "authenticated",
                                "role": authenticated_user.get("role")
                            })
                        except Exception:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Invalid authentication token"
                            })
                            await websocket.close(
                                code=status.WS_1008_POLICY_VIOLATION,
                                reason="Invalid authentication token"
                            )
                            break
            except (json.JSONDecodeError, ValueError):
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.debug(f"WebSocket session closed: {str(exc)}")
        manager.disconnect(websocket)