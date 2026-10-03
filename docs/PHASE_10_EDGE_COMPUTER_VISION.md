# VETRA Phase 10 — Edge Computer Vision & Automated Livestock Monitoring
## Architecture, Deployment & Technical Reference

---

### 1. Executive Summary

Phase 10 evolves VETRA from manual, asynchronous media uploads into a continuous, real-time edge computer vision and automated livestock health monitoring platform. 

```
CAMERA / EDGE DEVICE
        ↓
  Camera Registry
        ↓
Stream Ingestion Layer (RTSP / Mock / Webhook)
        ↓
Controlled Frame Sampler (Configurable FPS & Resolution)
        ↓
Edge Inference Adapter (Local OpenCV / Future Jetson / RPi)
        ↓
Phase 9 VisualModelAdapter (Deterministic Contour & Texture Analyzer)
        ↓
Visual Observation (Posture, Mobility, Coat, Anomalies)
        ↓
Temporal Visual Intelligence (Trajectory & Persistence)
        ↓
Multimodal Health Intelligence (Visual + IoT Telemetry + Clinical Rules)
        ↓
Alert Engine (30-Minute Cooldown & Deduplication)
        ↓
Disease Surveillance (Phase 8 Geospatial & Cluster Engine)
        ↓
Veterinary Workflow (Automated Clinical Triage & Case Escalation)
        ↓
WebSocket Distribution (Real-Time Push to Command Center)
        ↓
VETRA Live Monitoring UI (Streamlit Camera Monitoring Page)
```

Phase 10 provides full operational capabilities without requiring physical camera hardware during testing or staging, employing realistic simulated stream adapters and mock pipelines that are strictly marked with `[SIMULATION]`.

---

### 2. Camera Registry & Subsystem

#### 2.1 Collection: `cameras`
Each registered camera possesses a unique `camera_id` (format: `CAM-YYYY-XXXX`) and tracks operational configuration:
- `camera_id`: Unique identifier
- `camera_name`: Friendly display name
- `farm_id`: Linked farm ID (enforced via RBAC)
- `animal_id`: Optional target animal focus
- `pen_id`: Optional pen/shed identifier
- `camera_type`: `stationary_pen`, `cattle_shed`, `feeding_area`, `milking_area`, `quarantine_area`, `mobile`, `other`
- `connection_type`: `rtsp`, `http`, `webhook`, `mock`
- `stream_url_reference`: Secure URI / RTSP connection string
- `edge_device_id`: Associated edge processing node
- `status`: `online`, `offline`, `degraded`, `unknown`, `disabled`
- `enabled`: Boolean operational toggle
- `sampling_interval_seconds`: Configurable sampling rate (default: 5.0s, bounds: 1.0s – 3600.0s)
- `fps_target`: Target frame capture rate (default: 25.0)
- `resolution`: Max target resolution (e.g. `1920x1080`)
- `location_label`: Physical installation label
- `health`: Operational telemetry (frames received, dropped, inference latency, consecutive failures)

#### 2.2 Security & Credential Redaction
Stream URIs often contain sensitive authentication credentials (e.g., `rtsp://admin:pass@192.168.1.50/live`). 
- VETRA redacts all credentials before persisting or serializing in API responses via `redact_stream_url()`:
  - `rtsp://admin:secret@192.168.1.50:554/h264` → `rtsp://admin:***@192.168.1.50:554/h264`
- Raw passwords are never returned to the frontend or printed in logs.

---

### 3. Stream Ingestion Layer

#### 3.1 Abstraction: `CameraStreamAdapter`
The ingestion layer decouples stream protocol management from the application runtime via:
- `connect()`: Establishes stream connection
- `disconnect()`: Safely releases resources
- `is_connected()`: Reports connection health
- `read_frame()`: Non-blocking single frame capture with timeout protection
- `get_snapshot()`: Acquires raw JPEG/PNG image bytes
- `get_metadata()`: Reports resolution, connection status, and device metadata

#### 3.2 Concrete Adapters
1. **`RTSPCameraAdapter`**:
   - Uses OpenCV `cv2.VideoCapture` with non-blocking timeouts.
   - Robust failure handling: Invalid hostnames, broken RTSP streams, authentication failures, and network timeouts do NOT crash FastAPI.
   - Returns structured error states: `STATUS_TIMEOUT`, `STATUS_INVALID_STREAM`, `STATUS_OFFLINE`, `STATUS_DECODER_ERROR`.
2. **`MockCameraAdapter`**:
   - Generates synthetic test livestock frames using PIL with timestamp and clear `[SIMULATION]` banner.
   - Allows deterministic offline testing, staging, and demo environments without hardware.
3. **`WebhookFrameAdapter`**:
   - Ingests pre-captured frames pushed from external edge cameras or push gateways.

---

### 4. Controlled Frame Sampling

Processing every RTSP frame (e.g., 25–30 FPS) causes excessive compute and memory consumption.
- **Configurable Interval**: Default `sampling_interval_seconds = 5.0` (1 frame every 5 seconds).
- **Enforced Safety Bounds**: `1.0s <= sampling_interval_seconds <= 3600.0s`. Zero and negative rates are rejected.
- **Resolution Clamping**: Clamped to maximum bounds (`max_frame_width = 1920`, `max_frame_height = 1080`) to guarantee predictable memory footprint.
- **Deterministic SHA-256 Hashing**: Every sampled frame is hashed via SHA-256 to enable tamper-evident audit trails, duplicate frame suppression, and event deduplication.

---

### 5. Edge Device Registry & Ingestion

#### 5.1 Collection: `edge_devices`
Tracks physical or simulated compute devices running near the cameras:
- `edge_device_id`: Unique identifier (format: `EDGE-YYYY-XXXX`)
- `device_name`: Friendly hostname or device label
- `device_type`: `raspberry_pi`, `jetson`, `mini_pc`, `server`, `simulator`
- `farm_id`: Linked farm ID
- `status`: `online`, `offline`, `degraded`, `disabled`
- `software_version` & `model_version`: Tracks deployment runtime
- `last_heartbeat`: Timestamp of latest heartbeat
- `camera_ids`: List of cameras attached to this device
- `capabilities`: Video codecs, accelerators (CPU, CUDA, Coral TPU)

#### 5.2 Dynamic Health Tiers
- **HEALTHY**: Heartbeat received within last 3 minutes.
- **DEGRADED**: Heartbeat older than 3 minutes (up to 10 minutes) or consecutive inference errors.
- **OFFLINE**: No heartbeat for > 10 minutes.
- **DISABLED**: Administratively disabled.

#### 5.3 Webhook Event Ingestion (`POST /edge/events`)
Asynchronous endpoint allowing edge agents to push inference results:
- Validates camera existence and ownership.
- Validates edge device credentials where registered.
- Validates timestamps, numerical bounds (`0.0 <= visual_risk_score <= 1.0`), and observation structure.
- Deterministic event deduplication: checks for matching `frame_hash` or `frame_id`.
  - Suppresses duplicate alerts, duplicate surveillance events, and duplicate clinical cases.
  - Returns `{"accepted": true, "deduplicated": true}`.

---

### 6. Edge Inference & Phase 9 CV Engine Reuse

#### 6.1 Inference Adapter Architecture (`ai_engine/edge_inference.py`)
- Defines `EdgeInferenceAdapter` abstract interface.
- Implements `LocalOpenCVInferenceAdapter`:
  - Directly reuses Phase 9 `DeterministicVisualAnalyzer` and `VisualModelAdapter`.
  - Reuses morphology, contour analysis, texture edge density, and animal physiological context.
  - Returns structured observations: posture, mobility, coat condition, surface anomalies, visual risk score.
- Future adapter placeholders:
  - `RaspberryPiInferenceAdapter`
  - `JetsonInferenceAdapter`
  - `RemoteInferenceAdapter`

#### 6.2 Temporal Visual Intelligence
- Evaluates visual findings across successive sampled frames over time.
- Identifies persistent concern patterns (e.g., prolonged recumbency, repeated abnormal posture, feeding inactivity).
- Classifies temporal trajectory: `stable`, `improving`, `deteriorating`, `persistent_visual_concern`, `insufficient_evidence`.
- Never escalates based on a single anomalous frame unless verified by persistence or multimodal corroboration.

#### 6.3 Multimodal Health Synthesis
- Integrates visual risk with IoT telemetry, disease intelligence, and preventive schedules via `compute_multimodal_health_assessment()`.
- Calculates combined risk score `[0..100]` with calibrated confidence and directional attribution.

---

### 7. Automated Alerts, Surveillance & Veterinary Escalation

#### 7.1 Alert Generation & 30-Minute Cooldown
- Candidate alert types:
  - `visual_health_risk`: Visual risk score >= 0.75 (high) or >= 0.85 (critical).
  - `repeated_abnormal_posture`: Persistent abnormal posture or recumbency.
  - `feeding_inactivity`: Prolonged absence from feeding zone.
  - `camera_offline` & `edge_device_offline`: Hardware failure alarms.
- **30-Minute Cooldown**:
  - `is_alert_in_cooldown()` verifies that no identical alert (`camera_id`, `animal_id`, `alert_type`) has been created within the last 30 minutes.
  - Prevents alert storms and notification fatigue.

#### 7.2 Disease Surveillance Integration
- Persistent or high-severity visual concerns (`visual_risk_score >= 0.70`) register an observation in `disease_observations`.
- Feeds into Phase 8 `disease_cluster_engine.py` for spatial and temporal cluster detection.
- Does NOT fabricate outbreaks; respects geospatial boundaries and requires multi-animal evidence.

#### 7.3 Veterinary Clinical Escalation
- If visual concern score >= 0.85, automatically generates an illness/emergency veterinary case in `veterinary_cases`.
- Includes complete visual evidence trail: camera ID, timestamp, frame hash, risk score, observations, and recommendations.
- Case status is set to `open` with `source: visual_analysis`.

---

### 8. Real-Time WebSocket Architecture

Reuses existing `websocket_manager.py` on `/ws/monitoring`:
- **`visual_inference`**: Broadcasts new edge inference results with visual risk scores.
- **`visual_alert`**: Broadcasts critical visual health alerts.
- **`camera_status`**: Broadcasts camera online/offline/degraded state changes.
- **`edge_device_status`**: Broadcasts edge node heartbeat and health transitions.
- Fully resilient: client connection drops or malformed payloads do not interrupt the event loop.

---

### 9. Frontend Integration

#### 9.1 Streamlit Page: `📹 Live Camera & Edge Intelligence` (`frontend/pages/camera_monitoring.py`)
Nine cohesive, SIH-grade sections:
1. **Fleet Summary KPIs**: Total cameras, online/degraded/offline counts, edge devices, visual alerts.
2. **Camera Filters & Controls**: Filter by farm, camera, type, status, and manual refresh.
3. **Camera Fleet Directory**: Table with status badges, resolution, sampling intervals, and last seen.
4. **Live Snapshot & On-Demand Inference**:
   - Single-frame capture (`GET /cameras/{id}/snapshot`).
   - On-demand edge inference execution (`POST /cameras/{id}/analyze`).
   - Frame hash audit verification.
5. **Recent Visual Inference Events**: Chronological feed of edge observations with risk badges.
6. **Edge Computing Fleet Health**: Hardware metrics, heartbeat freshness, software/model versions.
7. **Camera-to-Animal Surveillance Mapping**: Pen and animal association views.
8. **Automated Camera & Edge Alerts**: Active visual alerts with severity badges.
9. **Clinical Safety Mandate**: Prominent disclaimer emphasizing veterinary decision support.

#### 9.2 Command Center Dashboard Integration (`frontend/pages/dashboard.py`)
- Section 11: `Edge & Camera Intelligence`.
- Live summary metrics: Active Cameras, Fleet Health, Edge Nodes, Live Inferences, Active Visual Alerts.
- Quick navigation button directing operators directly to the Live Camera page.

---

### 10. Standalone Edge Agent & Camera Simulator

#### 10.1 Standalone Edge Agent (`simulator/edge_agent.py`)
- Operates independently from FastAPI on physical edge hardware (Raspberry Pi, Jetson, PC).
- Ingests camera streams, samples frames at configured intervals, performs local inference, and POSTs to `/edge/events`.
- **FIFO Offline Buffer**: Holds up to 100 events locally during network outages and flushes upon reconnection.
- **Exponential Backoff Reconnect**: Safe retry schedule (`[2s, 5s, 10s, 30s]`) to avoid request thundering.

#### 10.2 Camera Simulator (`simulator/camera_simulator.py`)
- Generates synthetic test livestock frames with simulated jitter, FPS targets, and status transitions.
- Strictly labeled `[SIMULATION]` to prevent accidental confusion with production farm data.

---

### 11. Security, RBAC & Clinical Safety

#### 11.1 RBAC Enforcement
- **Farmer**: Full access to own farm's cameras, edge devices, and snapshots. Cannot register or inspect foreign farm hardware.
- **Veterinarian**: Read-only access to cameras and visual evidence for clinical evaluation.
- **Admin**: Complete platform-wide configuration and monitoring access.

#### 11.2 Clinical Safety Mandate
- Camera inference is strictly a **decision-support screening mechanism**.
- The system **never** outputs definitive disease diagnoses (e.g. FMD, mastitis, anthrax) from visual feeds alone.
- Outputs calibrated clinical terminology: *"Visual observations are AI-assisted indicators and do not constitute a confirmed veterinary diagnosis. Veterinary examination is required."*
