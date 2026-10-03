# VETRA — SIH Live Demonstration Script
## Minute-by-Minute Live Presentation Runbook for Judges & Evaluators

**Platform:** VETRA Intelligent Livestock Health Platform  
**Document:** `docs/SIH_LIVE_DEMO_SCRIPT.md`  
**Version:** `15.0.0-SIH-FINAL`  
**Total Allocated Time:** 8 Minutes Demo + 4 Minutes Jury Q&A  

---

## 1. Live Demonstration Timeline & Speaker Cues

```
[00:00 - 01:00]  Login & Platform Overview
[01:00 - 02:00]  Command Center & Normal Baseline (Scenario 1)
[02:00 - 03:00]  IoT Telemetry Anomaly & AI Screening (Scenario 3)
[03:00 - 04:00]  Edge Computer Vision & Multimodal Fusion (Scenario 4)
[04:00 - 05:00]  Predictive Health Deterioration Curves (Scenario 5)
[05:00 - 06:00]  Veterinary Telemedicine Closed Loop (Scenario 6)
[06:00 - 07:00]  Cross-Farm Disease Surveillance Radar (Scenario 7)
[07:00 - 08:00]  Institutional Gate & 8 Safety Gates (Scenarios 8 & 9)
```

---

### Minute 0:00 – 01:00: Introduction & Authentication
- **On-Screen Action:**
  - Display the VETRA Login modal at `http://localhost:8501`.
  - Enter credentials: `farmer@vetra.demo` / `Vetra@12345`. Click **Sign In**.
- **Speaker Script:**
  > *"Respected members of the jury, in India’s dairy heartland, subclinical diseases like mastitis and bovine respiratory disease cost smallholder dairy farmers thousands of rupees before any visible symptoms appear. Today we present VETRA—an end-to-end intelligent livestock health platform that detects disease 24 to 36 hours before physical prostration, connects the farmer instantly to a registered veterinarian, and arms state authorities with real-time epidemiological radar. Notice that our platform enforces strict role-based security; we are logging in as a dairy cooperative farmer."*
- **Key Takeaway:** Enterprise RBAC, clean professional aesthetics, and clear problem definition.

---

### Minute 1:00 – 02:00: Command Center & Normal Baseline (Scenario 1)
- **On-Screen Action:**
  - Navigate to **Command Center** (`pages/dashboard.py`).
  - Highlight the top KPI strip: **Total Animals (11)**, **Herd Health Index (88.0)**, **Active Alerts (0)**.
  - Open **Animal Profile** for `COW-001 (Lakshmi)`.
  - Review stable vitals: Temp `38.6°C`, HR `72 bpm`, Rumination `82 min`.
- **Speaker Script:**
  > *"Here in the Command Center, the farmer sees real-time herd metrics at a glance. Our Herd Health Index—currently sitting at an optimal 88.0—synthesizes continuous sensor readings. Looking at Lakshmi (COW-001), our baseline Scenario 1 animal, her vitals show healthy homeostatic ranges. Her rumination rhythm confirms normal digestion, producing zero active alerts."*
- **Key Takeaway:** Real-time multi-sensor baseline monitoring and composite Herd Health Index.

---

### Minute 2:00 – 03:00: IoT Anomaly Injection & AI Multi-Vital Screening (Scenario 3)
- **On-Screen Action:**
  - Navigate to **Live Monitoring** (`pages/monitoring.py`).
  - In the terminal or simulator panel, trigger **Scenario 3** reading for `COW-003 (Nandi)`:
    `.\.venv\Scripts\python.exe -c "from simulator.iot_simulator import generate_sih_demo_reading; print(generate_sih_demo_reading(scenario=3))"`
  - Observe the real-time red alert banner flashing on the dashboard:
    `CRITICAL_FEVER_RESPIRATORY | Temp: 40.8°C | HR: 98 bpm | Rumination: -78%`.
  - Click on the alert to view the **AI Diagnostic Narrative**.
- **Speaker Script:**
  > *"Now let's observe an acute clinical event. Sensor telemetry reports that Nandi (COW-003) has spiked a hyperthermic temperature of 40.8°C, accompanied by tachycardia and a drastic 78% collapse in rumination. VETRA’s multi-vital risk model immediately flags this as High-Risk (Score: 78.0) and generates an automated triage explanation. Notice our dual-tier architecture: if internet is available, Gemini enriches this narrative; if the farm is completely offline, our deterministic engine generates the exact same structured clinical advice without missing a beat."*
- **Key Takeaway:** Immediate multi-signal anomaly detection and resilient offline fallback AI.

---

### Minute 3:00 – 04:00: Edge Computer Vision & Multimodal Fusion (Scenario 4)
- **On-Screen Action:**
  - Navigate to **Visual Health** (`pages/computer_vision.py`).
  - Review the locomotion assessment for `COW-004 (Radha)` (Scenario 4).
  - Point to the visual triage markers: **Mobility Score: 3/5**, **Spinal Arch Deviation: 0.74**, **Stride Asymmetry: 28.5%**.
  - Highlight the mandatory safety disclaimer below the card.
- **Speaker Script:**
  > *"Sensors are powerful, but vision is non-invasive. As cattle exit the milking parlor, VETRA’s edge computer vision models analyze locomotion gait. Here for Radha (COW-004), the model detects a 28.5% stride asymmetry and pronounced spinal arching, indicating early digital dermatitis or hoof lesions. Notice our safety commitment: we explicitly label this an 'AI-assisted screening indicator'—never a definitive diagnosis—advising an immediate physical hoof exam."*
- **Key Takeaway:** Edge camera locomotion triage with clear clinical disclaimer boundaries.

---

### Minute 4:00 – 05:00: Predictive AI Deterioration Curves (Scenario 5)
- **On-Screen Action:**
  - Navigate to **Predictive AI** (`pages/predictive_ai.py`).
  - Select `COW-005 (Devi)` (Scenario 5).
  - Display the prospective 24h, 48h, and 72h risk forecast curves (`54.2% -> 72.8% -> 84.5%`).
  - Show the primary feature drivers: `rumination_velocity_decline` and `subfebrile_nocturnal_peaks`.
- **Speaker Script:**
  > *"VETRA does not simply react to illness—it predicts it. Devi (COW-005) currently appears superficially normal in the shed. However, our trend slope engine detected a subtle negative rumination velocity over the last 18 hours. Our predictive model forecasts an 84.5% probability of severe prostration within 72 hours unless preventive action is taken. This gives the dairy farmer a 48-hour golden window to administer supportive electrolytes and dietary buffers before clinical collapse."*
- **Key Takeaway:** Prospective 72-hour deterioration forecasting creating pre-emptive intervention windows.

---

### Minute 5:00 – 06:00: Closed-Loop Telemedicine & Veterinary Response (Scenario 6)
- **On-Screen Action:**
  - Log out as Farmer and log in as Veterinarian: `vet@vetra.demo` / `VetraVet@2026`.
  - Navigate to **Clinical Cases** / **Telemedicine** (`pages/veterinarian.py` & `pages/telemedicine.py`).
  - Open case `VET-DEMO-2026-001`.
  - Review the digital prescription (`Oxytetracycline 20mg/kg`, `Flunixin 2.2mg/kg`) and preventive biosecurity disinfection task.
- **Speaker Script:**
  > *"Logging in as Dr. Rajesh Sharma, our registered field veterinarian, we enter the Telemedicine triage portal. The vet reviews the animal’s 7-day vital curves, vision indicators, and predictive trajectory in one clean view. With two clicks, Dr. Sharma issues a digital prescription and automatically schedules a barn biosecurity protocol, closing the loop directly on the farmer's mobile interface."*
- **Key Takeaway:** Closed-loop telemedicine, digital prescriptions, and biosecurity synchronization.

---

### Minute 6:00 – 07:00: Cross-Farm Disease Surveillance Radar (Scenario 7)
- **On-Screen Action:**
  - Log in as Institutional Officer: `officer@vetra.demo` / `VetraGov@2026`.
  - Navigate to **Disease Surveillance** (`pages/surveillance.py`).
  - Display the Anand district geospatial cluster map (`CLUST-2026-GUJ-004`).
  - Show the 3 participating farms within a 5.0 km radius and the temporal spike indicator (`3.2 sigma`).
- **Speaker Script:**
  > *"Now we zoom out to district and state defense. When multiple independent dairy farms in the same tehsil experience synchronized thermal spikes within 48 hours, VETRA’s geospatial cluster engine discovers an emerging epidemiological cluster. Here in the Anand Dairy Corridor, 3 neighboring farms show elevated respiratory distress. State epidemiologists can immediately establish ring biosecurity before the disease spreads to neighboring talukas."*
- **Key Takeaway:** Haversine geospatial cluster radar identifying cross-farm disease spread in real time.

---

### Minute 7:00 – 08:00: Institutional Human Approval Gate & The 8 Safety Gates (Scenarios 8 & 9)
- **On-Screen Action:**
  - Navigate to **Institutional Health** (`pages/institutional.py`).
  - Show event `EPI-DEMO-2026-008` in `REVIEW_REQUIRED` state.
  - Demonstrate that only an Institutional Officer can advance it to `UNDER_REVIEW`.
  - Generate the **Government-Ready Package** (`GOV-PKG-2026-DEMO`).
  - Display the **8 Safety Gates** modal:
    Show Gates 1-4 PASSED, Gate 5 safely BLOCKED (`Adapter status: NOT_CONFIGURED`), and Gate 8 audit logged.
  - Download and open the generated PDF export with the PII-masked watermark:
    `"Government-ready export package — not an official submission."`
- **Speaker Script:**
  > *"Finally, we present VETRA’s crowning architectural achievement: Responsible National Integration. Under our Anti-Autonomous Outbreak Rule, no AI model can declare an epidemic; only an authenticated Institutional Veterinary Officer can confirm an event. When preparing national reports for NADRS or LIMS, our 8-Gate Safety Pipeline validates the schema, masks all farmer personal information, and verifies digital signatures. In this demonstration sandbox, Gate 5 halts transmission because the external government adapter is safely NOT_CONFIGURED. VETRA is robust, safe, 100% regression-verified across 271 automated tests, and ready to protect India's dairy economy. Thank you."*
- **Key Takeaway:** Programmatic safety gates, PII privacy shield, statutory export compliance, and ironclad human governance.

---

## 2. Anticipated Jury Questions & Authoritative Technical Answers

### Q1: What happens if farm internet drops or cellular connectivity fails?
> **Answer:**  
> *"VETRA is edge-native by design. Our edge gateway agents (`simulator/edge_agent.py`) run locally on low-cost on-farm hardware like a Raspberry Pi. The edge agent maintains an in-memory FIFO buffer queue, evaluates emergency thermal thresholds locally, and triggers on-farm auditory or beacon alarms. Once connectivity restores, it uses exponential backoff to sync buffered batches to MongoDB Atlas without data loss."*

### Q2: What if the Google Gemini API key expires or external cloud LLM services fail?
> **Answer:**  
> *"We adhere to a dual-tier AI architecture. All core risk scoring, trend slope calculations, and disease screenings are strictly deterministic mathematical models. If Gemini is unreachable, our `generate_fallback_explanation()` service immediately synthesizes deterministic, structured clinical summaries. In fact, our entire 271-test regression suite executes and passes completely offline with zero dependency on external LLM availability."*

### Q3: Could an errant AI prediction or sensor glitch trigger panic and falsely declare a national disease outbreak?
> **Answer:**  
> *"Architecturally impossible. We have built-in the Anti-Autonomous Outbreak Rule. Any automated call or unauthorized role attempting to confirm an epidemiological event receives an HTTP 403 Forbidden. Outbreak confirmation requires multi-stage verification by an authenticated Institutional Veterinary Officer, and all regulatory packages are checked by 8 mandatory safety gates before dispatch."*

### Q4: How is smallholder farmer privacy protected in state-level reports?
> **Answer:**  
> *"All exported statutory packages automatically pass through our cryptographic PII Privacy Shield (`GovernmentDataPackageService._mask_pii_data`). Farmer names and phone numbers are redacted, and exact farm coordinates are generalized to district/block administrative centroids. This gives epidemiologists the regional density information they need without exposing individual farmers to market discrimination."*
