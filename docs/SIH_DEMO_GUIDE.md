# VETRA — SIH Demonstration & Evaluation Guide
## Phase 15: Grand Finale Submission & Demonstration Protocol

**Platform Version:** `VETRA 15.0.0-SIH-FINAL`  
**Target Event:** Smart India Hackathon (SIH) Grand Finale  
**Domain:** Intelligent Livestock Health, Early Detection, Prevention, and Epidemiological Surveillance  

---

## 1. Executive Demonstration Overview

VETRA is an end-to-end intelligent livestock health management platform engineered to resolve the triple challenge of Indian dairy and livestock husbandry:
1. **Subclinical Disease Invisibility:** Undetected early mastitis, bovine respiratory disease (BRD), and metabolic disorders costing dairy farmers over ₹15,000 per animal per lactation.
2. **Rural Veterinary Access Gap:** Low veterinarian-to-cattle ratio in rural panchayats leading to delayed treatment and emergency mortality.
3. **Delayed Outbreak Intelligence:** Fragmented district surveillance resulting in delayed containment of infectious transboundary diseases (e.g., Lumpy Skin Disease, Foot & Mouth Disease).

VETRA addresses this through a unified stack combining **real-time IoT vital telemetry**, **on-farm edge computer vision**, **predictive trend intelligence**, **closed-loop telemedicine**, and **district-level epidemiological surveillance** equipped with strict **human-in-the-loop regulatory safety gates**.

---

## 2. Demo User Credentials & Role Definitions

VETRA enforces strict Role-Based Access Control (RBAC). For judging and demonstration, pre-seeded credential sets represent all tiers of the livestock healthcare ecosystem:

| Role | Email | Password | Primary Interface / Capabilities |
|---|---|---|---|
| **Farmer** | `farmer@vetra.demo` | `Vetra@12345` | Herd vitals, animal health cards, live IoT alerts, telemedicine requests, preventive calendar |
| **Veterinarian** | `vet@vetra.demo` | `VetraVet@2026` | Clinical triage queue, diagnostic prescription, lab integration, tele-consultation video/chat, AI draft review |
| **Institutional Officer** | `officer@vetra.demo` | `VetraGov@2026` | District outbreak radar, geospatial hotspot clustering, warning lifecycle, government package certification |
| **Administrator** | `admin@vetra.demo` | `VetraAdmin@2026` | Full platform command center, IoT device orchestration, security audit logs, adapter configuration |

---

## 3. The 9 SIH Demonstration Scenarios

VETRA includes 9 deterministic, isolated demonstration scenarios accessible via the `/demo/scenarios` API and interactive Streamlit Command Center. Each scenario represents a distinct clinical, visual, predictive, or institutional lifecycle state:

### Scenario 1: Normal Animal — Optimal Physiological Baseline
- **Subject:** `COW-001 (Lakshmi)` | Gir Cow | Lactating
- **Telemetry:** Temp: `38.6°C`, Heart Rate: `72 bpm`, Respiration: `24 bpm`, Activity: `78`, Rumination: `82`
- **Herd Health Index (HHI):** `88.0` (Excellent)
- **Clinical State:** Physiological homeostasis. Zero active alerts. Rumination rhythm demonstrates optimal digestive fermentation.
- **Demonstration Keynote:** Highlights baseline multi-sensor normal ranges and stable real-time charting.

### Scenario 2: Early Health Warning — Subtle Trajectory Shift
- **Subject:** `COW-002 (Gauri)` | Sahiwal Cow | Dry Period
- **Telemetry:** Temp: `39.4°C` (sub-febrile), HR: `82 bpm`, Resp: `28 bpm`, Activity: `-46%`, Rumination: `-45%`
- **Herd Health Index (HHI):** `62.0` (Elevated Risk)
- **Clinical State:** Early prodromal stage of subclinical mastitis/metritis 18 to 24 hours before clinical fever onset.
- **Triggered Action:** Generates amber priority notification; recommends supportive hydration and scheduled exam.

### Scenario 3: Multi-Signal Acute Anomaly — High-Risk Clinical Alert
- **Subject:** `COW-003 (Nandi)` | Kankrej Bull | Adult
- **Telemetry:** Temp: `40.8°C` (hyperthermia), HR: `98 bpm` (tachycardia), Resp: `38 bpm` (tachypnea), Rumination: `-78%`
- **Herd Health Index (HHI):** `28.0` (Critical)
- **Clinical State:** Acute systemic inflammatory response / Bovine Respiratory Disease (BRD).
- **Triggered Action:** Red-tier emergency alert dispatched; automated draft clinical case prepared for veterinary triage; Gemini fallback clinical narrative generated.

### Scenario 4: Edge Computer Vision — Mobility & Posture Triage Marker
- **Subject:** `COW-004 (Radha)` | Holstein-Friesian Cross
- **Vision Metrics:** Mobility Score: `3/5`, Stride Asymmetry: `28.5%`, Spinal Arch Deviation: `0.74`
- **Confidence:** `88.0%`
- **Clinical State:** Visual lameness screening marker.
- **Safety Disclaimer:** *"AI-assisted screening indicator only — requires on-site physical hoof examination by veterinarian."*
- **Triggered Action:** Prompts preventive footbath protocol and physical veterinary examination.

### Scenario 5: Predictive Health — Prospective Trajectory Forecasting
- **Subject:** `COW-005 (Devi)` | Jersey Cow
- **Forecast Horizons:** 24h Risk: `54.2%` | 48h Risk: `72.8%` | 72h Risk: `84.5%`
- **Trajectory:** `DETERIORATING` (Slope: `+0.42 sigma/day`)
- **Key Predictors:** Rumination decline velocity and nocturnal subfebrile thermal spikes.
- **Clinical Value:** Enables pre-emptive metabolic buffering 48 hours prior to acute collapse.

### Scenario 6: Veterinary Clinical Response — Telemedicine Loop
- **Case Reference:** `VET-DEMO-2026-001`
- **Assigned Clinician:** Dr. Rajesh Sharma, MVSc (Lic. #VET-GUJ-4482)
- **Intervention:** Clinical triage, digital prescription (Oxytetracycline 20mg/kg IM, Flunixin 2.2mg/kg IV), preventive biosecurity disinfection for Barn B.
- **Workflow State:** `IN_TREATMENT` -> Closed-loop feedback into farm preventive record.

### Scenario 7: Cross-Farm Disease Surveillance & Geospatial Hotspotting
- **Cluster Reference:** `CLUST-2026-GUJ-004` (Anand Dairy Corridor)
- **Syndromic Cluster:** Bovine Thermal Elevation & Respiratory Complex
- **Metrics:** 3 neighboring farms involved, 6 affected bovines within a 5.0 km radius, `3.2-sigma` temporal surge.
- **Mandatory Safety Rule:** *"NO AI MODEL MAY AUTONOMOUSLY CONFIRM AN OUTBREAK. HUMAN EPIDEMIOLOGIST REVIEW MANDATORY."*

### Scenario 8: Institutional Early Warning & Human Approval Gate
- **Event Reference:** `EPI-DEMO-2026-008`
- **Lifecycle Transition:** `SIGNAL` -> `SUSPECT` -> `REVIEW_REQUIRED` -> `UNDER_REVIEW`
- **Enforcement:** Programmatic HTTP 403 Forbidden blocking any farmer or automated background task from confirming outbreaks. Only authorized Institutional Veterinary Officers hold signing authority.

### Scenario 9: Government-Ready Export Package & The 8 Safety Gates
- **Package Reference:** `GOV-PKG-2026-DEMO`
- **Compliance:** National Animal Disease Reporting System (NADRS) & LIMS / WOAH compatible schema.
- **Privacy Masking:** Farmer names masked (`R****h P***l`), phone numbers redacted (`**********`), coordinates generalized to district administrative centroids.
- **Multi-Format Export:** Available in structured JSON, audit CSV, and formal signed PDF report.
- **Safety Gate 5 Sandbox Status:** Adapter state defaults to `NOT_CONFIGURED`. Live network dispatch is safely halted at Gate 5, preventing accidental or unauthorized external transmissions during demonstrations.

---

## 4. End-to-End Live Demonstration Walk-Through

For an optimal 8-minute presentation to the SIH Jury, follow this sequential path:

```
[1. Farmer Authentication]
       │
       ▼
[2. Command Center Overview] ──► KPI Metrics & Herd Health Index (88.0)
       │
       ▼
[3. Live IoT Monitoring] ──────► Real-time simulated telemetry feeds (Temp, HR, Rumination)
       │
       ▼
[4. Anomaly Trigger] ──────────► Scenario 3: Acute Fever spike (40.8°C) & Rumination collapse
       │
       ▼
[5. AI Health Analysis] ───────► Multi-vital Risk Model (Score: 78.0) + Gemini Diagnostic Narrative
       │
       ▼
[6. Edge Computer Vision] ─────► Mobility score 3/5, posture arching, non-definitive disclaimer
       │
       ▼
[7. Predictive Health] ────────► 24h/48h/72h prospective deterioration forecast curve
       │
       ▼
[8. Veterinary Triage] ────────► Telemedicine case creation, prescription, preventive scheduling
       │
       ▼
[9. Regional Surveillance] ────► Cross-farm geospatial clustering (3 farms, 5km radius)
       │
       ▼
[10. Institutional Gate] ──────► Human officer confirmation gate (Anti-autonomous rule)
       │
       ▼
[11. Statutory Package] ───────► PII-masked NADRS export package with Gate 5 blocked safety
```

---

## 5. IoT Simulator Quick Reference

The VETRA IoT Simulator (`simulator/iot_simulator.py`) generates deterministic and continuous telemetry streams without requiring physical collars during testing:

- **Launch Continuous Telemetry:**
  ```powershell
  .\.venv\Scripts\python.exe simulator\iot_simulator.py --continuous --interval 2
  ```
- **Direct Scenario Verification:**
  ```powershell
  .\.venv\Scripts\python.exe -c "from simulator.iot_simulator import generate_sih_demo_reading; print(generate_sih_demo_reading(scenario=3))"
  ```
- **WebSocket Feed:**
  Active at `/ws/telemetry` with token query authentication.

---

## 6. Regulatory & Clinical Safety Statements

Every presenter must emphasize VETRA’s dual safety commitments to the judges:

1. **Clinical Screening Notice:**  
   VETRA’s AI models (Risk Model, Disease Intelligence, Computer Vision, Predictive AI) perform triage screening and risk prioritization. They explicitly do not issue unilateral clinical diagnoses. Physical examination and prescription remain the exclusive prerogative of registered veterinarians.
2. **Statutory Outbreak Gate:**  
   No automated algorithm, farmer, or system daemon can classify or submit an official epidemiological disease outbreak. Official confirmation requires human Institutional Veterinary Officer authentication and digital signing.
3. **Statutory Package Disclaimer:**  
   All generated regulatory export files bear the official watermark:  
   `"Government-ready export package — not an official submission."`
