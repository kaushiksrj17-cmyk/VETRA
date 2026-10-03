"""
VETRA Camera Simulator
======================
Simulates CCTV / IP camera streams, periodic frame sampling, network jitter,
and connection state transitions for testing and development.

IMPORTANT SAFETY NOTICE:
- This is a SIMULATION module.
- All generated frames, timestamps, and metrics are synthetic.
- Does NOT fabricate disease outbreaks or alter clinical diagnostic data.
"""

import argparse
import logging
from pathlib import Path
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any, Generator, Optional
import numpy as np

# Ensure root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.camera_ingestion import MockCameraAdapter, compute_frame_hash


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SIMULATION-CAM] %(message)s"
)
logger = logging.getLogger("camera_simulator")


class CameraSimulator:
    """
    Simulates a livestock shed / pen camera.
    Emits sampled frames, status telemetry, and latency metrics.
    """

    def __init__(
        self,
        camera_id: str = "CAM-SIM-01",
        farm_id: str = "FARM-SIM-01",
        sampling_interval_seconds: float = 5.0,
        animal_tag: str = "ANM-SIM-01",
        pen_id: str = "PEN-01",
        simulate_flakiness: bool = False
    ):
        self.camera_id = camera_id
        self.farm_id = farm_id
        self.sampling_interval_seconds = max(1.0, sampling_interval_seconds)
        self.animal_tag = animal_tag
        self.pen_id = pen_id
        self.simulate_flakiness = simulate_flakiness

        self.adapter = MockCameraAdapter(
            camera_id=camera_id,
            stream_url=f"mock://{camera_id}",
            sampling_interval_seconds=self.sampling_interval_seconds,
            animal_tag=animal_tag,
            pen_id=pen_id
        )
        self.is_running = False
        self.frames_emitted = 0
        self.consecutive_drops = 0

    def start(self) -> None:
        self.is_running = True
        self.adapter.connect()
        logger.info(
            f"[SIMULATION] CameraSimulator started: {self.camera_id} "
            f"(Interval: {self.sampling_interval_seconds}s, Pen: {self.pen_id})"
        )

    def stop(self) -> None:
        self.is_running = False
        self.adapter.disconnect()
        logger.info(f"[SIMULATION] CameraSimulator stopped: {self.camera_id}")

    def capture_sampled_frame(self) -> Optional[dict[str, Any]]:
        """
        Simulate sampling a single frame from the camera stream.
        Applies synthetic latency and optional simulated dropouts.
        """
        if not self.is_running:
            return None

        # Simulate intermittent network dropout if enabled
        if self.simulate_flakiness and random.random() < 0.15:
            self.consecutive_drops += 1
            logger.warning(
                f"[SIMULATION] Network jitter dropped frame for {self.camera_id} "
                f"({self.consecutive_drops} drops)"
            )
            return {
                "camera_id": self.camera_id,
                "status": "dropped",
                "reason": "simulated_network_timeout",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "frame_bytes": None,
                "frame_hash": None,
            }

        start_t = time.perf_counter()
        status_code, snapshot_bytes = self.adapter.get_snapshot()
        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

        if status_code != "connected" or snapshot_bytes is None:
            return {
                "camera_id": self.camera_id,
                "status": "error",
                "reason": status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "frame_bytes": None,
                "frame_hash": None,
            }

        self.frames_emitted += 1
        self.consecutive_drops = 0
        f_hash = compute_frame_hash(snapshot_bytes)
        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "camera_id": self.camera_id,
            "status": "connected",
            "frame_id": f"FRM-{self.camera_id}-{self.frames_emitted:06d}",
            "frame_bytes": snapshot_bytes,
            "frame_hash": f_hash,
            "latency_ms": latency_ms,
            "timestamp": now_iso,
            "animal_tag": self.animal_tag,
            "pen_id": self.pen_id,
            "is_simulation": True,
        }

    def stream_generator(self, max_frames: Optional[int] = None) -> Generator[dict[str, Any], None, None]:
        """Generator yielding sampled frames at the configured sampling interval."""
        self.start()
        count = 0
        try:
            while self.is_running:
                frame_data = self.capture_sampled_frame()
                if frame_data:
                    yield frame_data
                    count += 1
                    if max_frames and count >= max_frames:
                        break
                time.sleep(self.sampling_interval_seconds)
        finally:
            self.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VETRA Camera Simulator")
    parser.add_argument("--camera-id", default="CAM-SIM-01", help="Camera ID to simulate")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds")
    parser.add_argument("--count", type=int, default=3, help="Number of frames to emit")
    args = parser.parse_args()

    sim = CameraSimulator(camera_id=args.camera_id, sampling_interval_seconds=args.interval)
    logger.info(f"Running standalone simulation test for {args.count} frames...")
    for packet in sim.stream_generator(max_frames=args.count):
        logger.info(
            f"Emitted: {packet['status']} | Frame ID: {packet.get('frame_id')} "
            f"| Hash: {packet.get('frame_hash', '')[:12]}... | Latency: {packet.get('latency_ms')}ms"
        )
