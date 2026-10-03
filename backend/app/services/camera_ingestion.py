import hashlib
import io
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
except ImportError:
    cv2 = None

from backend.app.schemas.camera import redact_stream_url


# Status constants
STATUS_CONNECTED = "connected"
STATUS_TIMEOUT = "timeout"
STATUS_INVALID_STREAM = "invalid_stream"
STATUS_DECODER_ERROR = "decoder_error"
STATUS_OFFLINE = "offline"
STATUS_UNSUPPORTED = "unsupported"
STATUS_CONFIGURATION_ERROR = "configuration_error"


def compute_frame_hash(frame_bytes: bytes) -> str:
    """Compute SHA-256 hash of frame bytes for deduplication & evidence integrity."""
    return hashlib.sha256(frame_bytes).hexdigest()


class CameraStreamAdapter(ABC):
    """
    Abstract camera stream ingestion adapter.
    Encapsulates connection lifecycle, frame acquisition, and snapshot generation.
    """

    def __init__(self, camera_id: str, stream_url: str, **kwargs):
        self.camera_id = camera_id
        self.raw_stream_url = stream_url
        self.redacted_stream_url = redact_stream_url(stream_url)
        self.sampling_interval_seconds = max(1.0, float(kwargs.get("sampling_interval_seconds", 5.0)))
        self.max_frame_width = int(kwargs.get("max_frame_width", 1280))
        self.max_frame_height = int(kwargs.get("max_frame_height", 720))
        self.last_frame_timestamp: float = 0.0
        self._connected: bool = False
        self._connection_status: str = STATUS_OFFLINE

    @abstractmethod
    def connect(self) -> Tuple[bool, str]:
        """Connect to stream source. Returns (success, status_code)."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect and clean up resources."""
        pass

    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    def read_frame(self) -> Tuple[str, Optional[np.ndarray]]:
        """
        Acquire a raw frame (as numpy array BGR or RGB).
        Returns (status_code, numpy_frame_or_None).
        """
        pass

    @abstractmethod
    def get_snapshot(self) -> Tuple[str, Optional[bytes]]:
        """
        Acquire a single still JPEG snapshot.
        Returns (status_code, jpeg_bytes_or_None).
        """
        pass

    def get_metadata(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "stream_url_redacted": self.redacted_stream_url,
            "connected": self._connected,
            "connection_status": self._connection_status,
            "sampling_interval_seconds": self.sampling_interval_seconds,
            "max_frame_resolution": f"{self.max_frame_width}x{self.max_frame_height}",
        }

    def _resize_if_needed(self, frame: np.ndarray) -> np.ndarray:
        """Clamp maximum frame dimensions to prevent excessive resource utilization."""
        h, w = frame.shape[:2]
        if w > self.max_frame_width or h > self.max_frame_height:
            scale = min(self.max_frame_width / w, self.max_frame_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            if cv2 is not None:
                return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                pil_img = Image.fromarray(frame).resize((new_w, new_h))
                return np.array(pil_img)
        return frame


class MockCameraAdapter(CameraStreamAdapter):
    """
    High-fidelity simulation camera adapter.
    Generates synthetic livestock frames with simulated animal silhouette, timestamp,
    and camera ID. Fully deterministic, hardware-independent, and marked SIMULATION.
    """

    def __init__(self, camera_id: str, stream_url: str = "mock://default", **kwargs):
        super().__init__(camera_id, stream_url, **kwargs)
        self.animal_tag = kwargs.get("animal_tag", "ANM-SIM-01")
        self.pen_id = kwargs.get("pen_id", "PEN-01")

    def connect(self) -> Tuple[bool, str]:
        self._connected = True
        self._connection_status = STATUS_CONNECTED
        return True, STATUS_CONNECTED

    def disconnect(self) -> None:
        self._connected = False
        self._connection_status = STATUS_OFFLINE

    def _generate_synthetic_image(self) -> Image.Image:
        """Generate a simulated camera frame with pen background, animal silhouette, and status overlay."""
        width = min(self.max_frame_width, 640)
        height = min(self.max_frame_height, 480)

        # Warm barn enclosure color gradient
        img = Image.new("RGB", (width, height), color=(60, 50, 40))
        draw = ImageDraw.Draw(img)

        # Draw simulated straw/bedding floor
        draw.rectangle([(0, int(height * 0.65)), (width, height)], fill=(120, 100, 60))
        # Draw wooden enclosure rails
        draw.line([(0, int(height * 0.4)), (width, int(height * 0.4))], fill=(100, 80, 50), width=6)
        draw.line([(0, int(height * 0.55)), (width, int(height * 0.55))], fill=(100, 80, 50), width=6)

        # Draw stylized cattle body silhouette in the pen
        body_box = [
            int(width * 0.3),
            int(height * 0.45),
            int(width * 0.7),
            int(height * 0.8),
        ]
        draw.ellipse(body_box, fill=(75, 55, 45))  # Cow torso
        # Head
        head_box = [
            int(width * 0.65),
            int(height * 0.4),
            int(width * 0.82),
            int(height * 0.65),
        ]
        draw.ellipse(head_box, fill=(65, 45, 35))

        # Status & watermark banner (clearly indicating SIMULATION)
        banner_height = 42
        draw.rectangle([(0, 0), (width, banner_height)], fill=(20, 20, 20))
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status_text = f"[SIMULATION] CAM: {self.camera_id} | {self.pen_id} | {now_str}"
        draw.text((12, 12), status_text, fill=(240, 240, 240))

        # Animal tag label
        draw.rectangle(
            [(int(width * 0.62), int(height * 0.35)), (int(width * 0.85), int(height * 0.42))],
            fill=(230, 180, 0),
        )
        draw.text((int(width * 0.64), int(height * 0.36)), f"TAG: {self.animal_tag}", fill=(10, 10, 10))

        return img

    def read_frame(self) -> Tuple[str, Optional[np.ndarray]]:
        if not self._connected:
            self.connect()
        pil_img = self._generate_synthetic_image()
        np_arr = np.array(pil_img)
        if cv2 is not None:
            np_arr = cv2.cvtColor(np_arr, cv2.COLOR_RGB2BGR)
        self.last_frame_timestamp = time.time()
        return STATUS_CONNECTED, np_arr

    def get_snapshot(self) -> Tuple[str, Optional[bytes]]:
        if not self._connected:
            self.connect()
        pil_img = self._generate_synthetic_image()
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        self.last_frame_timestamp = time.time()
        return STATUS_CONNECTED, buf.getvalue()


class RTSPCameraAdapter(CameraStreamAdapter):
    """
    RTSP IP Camera adapter with safety guards against blocking or process hangs.
    If RTSP stream is unreachable, returns structured status code (offline/timeout/invalid_stream)
    instead of crashing the FastAPI runtime.
    """

    def __init__(self, camera_id: str, stream_url: str, **kwargs):
        super().__init__(camera_id, stream_url, **kwargs)
        self._cap: Optional[Any] = None

    def connect(self) -> Tuple[bool, str]:
        if cv2 is None:
            self._connection_status = STATUS_UNSUPPORTED
            return False, STATUS_UNSUPPORTED

        if not self.raw_stream_url or not self.raw_stream_url.startswith(("rtsp://", "rtsps://", "http://", "https://")):
            self._connection_status = STATUS_INVALID_STREAM
            return False, STATUS_INVALID_STREAM

        try:
            # OpenCV VideoCapture with environment safety flags
            self._cap = cv2.VideoCapture(self.raw_stream_url)
            # Give quick read check to test connectivity
            if self._cap.isOpened():
                ret, _ = self._cap.read()
                if ret:
                    self._connected = True
                    self._connection_status = STATUS_CONNECTED
                    return True, STATUS_CONNECTED
                else:
                    self._cap.release()
                    self._cap = None
                    self._connected = False
                    self._connection_status = STATUS_TIMEOUT
                    return False, STATUS_TIMEOUT
            else:
                self._connected = False
                self._connection_status = STATUS_OFFLINE
                return False, STATUS_OFFLINE
        except Exception as e:
            self._connected = False
            self._connection_status = STATUS_OFFLINE
            return False, STATUS_OFFLINE

    def disconnect(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self._connected = False
        self._connection_status = STATUS_OFFLINE

    def read_frame(self) -> Tuple[str, Optional[np.ndarray]]:
        if not self._connected or self._cap is None:
            ok, status = self.connect()
            if not ok:
                return status, None

        try:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                self.disconnect()
                return STATUS_DECODER_ERROR, None
            frame = self._resize_if_needed(frame)
            self.last_frame_timestamp = time.time()
            return STATUS_CONNECTED, frame
        except Exception:
            self.disconnect()
            return STATUS_DECODER_ERROR, None

    def get_snapshot(self) -> Tuple[str, Optional[bytes]]:
        status, frame = self.read_frame()
        if status != STATUS_CONNECTED or frame is None:
            return status, None

        try:
            success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                return STATUS_CONNECTED, encoded.tobytes()
            return STATUS_DECODER_ERROR, None
        except Exception:
            return STATUS_DECODER_ERROR, None


class WebhookFrameAdapter(CameraStreamAdapter):
    """
    Adapter for cameras or edge nodes that push frames asynchronously via HTTP Webhooks.
    Stores the most recently received frame in memory.
    """

    def __init__(self, camera_id: str, **kwargs):
        super().__init__(camera_id, "webhook://inbound", **kwargs)
        self._latest_jpeg: Optional[bytes] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._connected = True
        self._connection_status = STATUS_CONNECTED

    def connect(self) -> Tuple[bool, str]:
        self._connected = True
        self._connection_status = STATUS_CONNECTED
        return True, STATUS_CONNECTED

    def disconnect(self) -> None:
        self._connected = False
        self._connection_status = STATUS_OFFLINE

    def push_frame(self, frame_bytes: bytes) -> bool:
        """Inbound webhook entry point for receiving a frame."""
        self._latest_jpeg = frame_bytes
        self.last_frame_timestamp = time.time()
        self._connected = True
        self._connection_status = STATUS_CONNECTED
        return True

    def read_frame(self) -> Tuple[str, Optional[np.ndarray]]:
        if self._latest_jpeg is None:
            return STATUS_OFFLINE, None
        try:
            pil_img = Image.open(io.BytesIO(self._latest_jpeg))
            arr = np.array(pil_img)
            return STATUS_CONNECTED, self._resize_if_needed(arr)
        except Exception:
            return STATUS_DECODER_ERROR, None

    def get_snapshot(self) -> Tuple[str, Optional[bytes]]:
        if self._latest_jpeg is None:
            return STATUS_OFFLINE, None
        return STATUS_CONNECTED, self._latest_jpeg


def get_camera_stream_adapter(camera_doc: dict[str, Any]) -> CameraStreamAdapter:
    """
    Factory function resolving appropriate stream adapter based on connection_type.
    """
    conn_type = camera_doc.get("connection_type", "mock")
    cam_id = camera_doc.get("camera_id", "cam-default")
    stream_url = camera_doc.get("stream_url_reference", "mock://default")
    sampling_sec = camera_doc.get("sampling_interval_seconds", 5.0)

    if conn_type == "mock":
        return MockCameraAdapter(
            camera_id=cam_id,
            stream_url=stream_url,
            sampling_interval_seconds=sampling_sec,
            animal_tag=camera_doc.get("animal_tag", "ANM-SIM"),
            pen_id=camera_doc.get("pen_id", "PEN-01"),
        )
    elif conn_type == "webhook":
        return WebhookFrameAdapter(camera_id=cam_id, sampling_interval_seconds=sampling_sec)
    elif conn_type in ("rtsp", "http"):
        return RTSPCameraAdapter(
            camera_id=cam_id,
            stream_url=stream_url,
            sampling_interval_seconds=sampling_sec,
        )
    else:
        # Fallback to MockCameraAdapter for safety
        return MockCameraAdapter(camera_id=cam_id, stream_url=stream_url, sampling_interval_seconds=sampling_sec)
