"""
VETRA Edge Agent
================
Independent edge computing agent for on-premise livestock monitoring.
Runs continuously on edge hardware (Raspberry Pi, NVIDIA Jetson, or Mini-PC).

Pipeline:
Camera Stream -> Controlled Frame Sampler -> Local Inference ->
Event Builder -> Bounded Offline Buffer -> Reconnect Manager ->
VETRA Backend (POST /edge/events)
"""

import collections
import logging
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai_engine.edge_inference import get_edge_inference_adapter
from app.services.camera_ingestion import (
    MockCameraAdapter,
    compute_frame_hash,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [EDGE-AGENT] %(message)s"
)
logger = logging.getLogger("edge_agent")


# Configurable backoff retry intervals (seconds)
BACKOFF_SCHEDULE = [2, 5, 10, 30]


class EdgeAgent:
    """
    Standalone Edge Agent with local inference, offline FIFO buffering,
    and exponential backoff reconnect logic.
    """

    def __init__(
        self,
        edge_device_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        api_url: Optional[str] = None,
        sampling_interval_seconds: Optional[float] = None,
        max_buffer_size: int = 100,
        stream_adapter: Optional[Any] = None
    ):
        self.edge_device_id = edge_device_id or os.getenv("EDGE_DEVICE_ID", "EDGE-DEV-SIM")
        self.camera_id = camera_id or os.getenv("CAMERA_ID", "CAM-SIM-01")
        self.api_url = (api_url or os.getenv("VETRA_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.sampling_interval = max(
            1.0,
            float(sampling_interval_seconds or os.getenv("SAMPLING_INTERVAL_SECONDS", 5.0))
        )
        self.max_buffer_size = max_buffer_size

        # In-memory bounded FIFO queue for offline event buffering (retains metadata, not raw images)
        self.offline_buffer: collections.deque = collections.deque(maxlen=self.max_buffer_size)

        # Local inference runtime
        self.inference_adapter = get_edge_inference_adapter()

        # Camera stream input
        self.camera_adapter = stream_adapter or MockCameraAdapter(
            camera_id=self.camera_id,
            stream_url=f"mock://{self.camera_id}",
            sampling_interval_seconds=self.sampling_interval
        )

        self.is_running = False
        self.backoff_idx = 0
        self.frames_processed = 0
        self.events_transmitted = 0
        self.events_buffered = 0
        self.last_sync_success = False

    def start(self) -> None:
        self.is_running = True
        self.camera_adapter.connect()
        logger.info(
            f"EdgeAgent started [Device: {self.edge_device_id} | Camera: {self.camera_id} "
            f"| Target: {self.api_url} | Interval: {self.sampling_interval}s]"
        )

    def stop(self) -> None:
        self.is_running = False
        self.camera_adapter.disconnect()
        logger.info(f"EdgeAgent stopped. Buffer contains {len(self.offline_buffer)} items.")

    def run_single_cycle(self, auth_token: Optional[str] = None) -> Optional[dict[str, Any]]:
        """
        Executes one full edge cycle:
        1. Sample frame from camera
        2. Execute local inference
        3. Build structured event payload
        4. Attempt backend transmission or buffer offline
        5. Flush buffer if reconnected
        """
        # 1. Sample frame
        status_code, frame_arr = self.camera_adapter.read_frame()
        if status_code != "connected" or frame_arr is None:
            logger.warning(f"Frame capture failed with status: {status_code}")
            return None

        # Snapshot bytes for hashing
        _, snap_bytes = self.camera_adapter.get_snapshot()
        frame_hash = compute_frame_hash(snap_bytes or b"edge-dummy-bytes")

        # 2. Local inference
        start_t = time.perf_counter()
        inf_res = self.inference_adapter.infer(frame_arr)
        proc_latency = round((time.perf_counter() - start_t) * 1000.0, 2)
        self.frames_processed += 1

        # 3. Build structured event
        now_iso = datetime.now(timezone.utc).isoformat()
        frame_id = f"FRM-{self.camera_id}-{self.frames_processed:06d}"
        event_payload = {
            "edge_device_id": self.edge_device_id,
            "camera_id": self.camera_id,
            "animal_id": None,
            "captured_at": now_iso,
            "frame_id": frame_id,
            "frame_hash": frame_hash,
            "model_name": inf_res.get("model_name", "VETRA-EdgeVision"),
            "model_version": inf_res.get("model_version", "v1.0"),
            "observations": inf_res.get("observations", {}),
            "visual_risk_score": float(inf_res.get("visual_risk_score", 0.0)),
            "confidence": float(inf_res.get("confidence", 0.85)),
            "processing_latency_ms": proc_latency,
        }

        # 4. Transmit or buffer
        transmitted = self._send_event(event_payload, auth_token)
        if transmitted:
            self.events_transmitted += 1
            self.last_sync_success = True
            self.backoff_idx = 0  # reset backoff upon success
            # Flush offline buffer if we have pending backlogged events
            self._flush_offline_buffer(auth_token)
        else:
            self._buffer_event(event_payload)
            self.last_sync_success = False

        return event_payload

    def _send_event(self, payload: dict[str, Any], auth_token: Optional[str] = None) -> bool:
        """Attempt sending inference event to backend with safety timeout."""
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        endpoint = f"{self.api_url}/edge/events"
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=4.0)
            if resp.status_code in (200, 201):
                return True
            else:
                logger.warning(f"Backend rejected event: HTTP {resp.status_code} - {resp.text[:100]}")
                return False
        except Exception as e:
            logger.info(f"Backend unreachable at {endpoint} ({type(e).__name__}). Buffering locally.")
            return False

    def _buffer_event(self, payload: dict[str, Any]) -> None:
        """Buffer event metadata in bounded FIFO queue."""
        self.offline_buffer.append(payload)
        self.events_buffered += 1
        logger.info(f"Event buffered locally. Current offline queue: {len(self.offline_buffer)}/{self.max_buffer_size}")

    def _flush_offline_buffer(self, auth_token: Optional[str] = None) -> int:
        """Flush buffered events in chronological order when backend is reachable."""
        if not self.offline_buffer:
            return 0

        flushed = 0
        logger.info(f"Reconnected! Flushing {len(self.offline_buffer)} buffered events to backend...")
        while self.offline_buffer:
            item = self.offline_buffer[0]
            if self._send_event(item, auth_token):
                self.offline_buffer.popleft()
                flushed += 1
                self.events_transmitted += 1
            else:
                logger.warning("Backend became unreachable again during flush. Stopping backlog drain.")
                break
        return flushed

    def get_backoff_sleep_seconds(self) -> float:
        """Calculate next reconnect sleep interval using bounded exponential backoff schedule."""
        interval = BACKOFF_SCHEDULE[min(self.backoff_idx, len(BACKOFF_SCHEDULE) - 1)]
        self.backoff_idx = min(self.backoff_idx + 1, len(BACKOFF_SCHEDULE) - 1)
        return float(interval)


if __name__ == "__main__":
    agent = EdgeAgent(sampling_interval_seconds=2.0)
    logger.info("Executing 3 test cycles with simulated offline fallback...")
    for _ in range(3):
        agent.run_single_cycle()
        time.sleep(1.0)
    logger.info(
        f"Test completed. Transmitted: {agent.events_transmitted}, "
        f"Buffered: {agent.events_buffered}, Queue size: {len(agent.offline_buffer)}"
    )
