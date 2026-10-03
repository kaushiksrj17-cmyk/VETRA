# VETRA — Intelligent Livestock Health, Early Detection, Prevention and Management Platform

[![Version](https://img.shields.io/badge/version-15.0.0--SIH--FINAL-blue.svg)](file:///d:/VETRA/docs/PHASE_15_COMPLETION_AUDIT.md)
[![Tests](https://img.shields.io/badge/tests-271%2F271%20passing-brightgreen.svg)](file:///d:/VETRA/docs/VETRA_TESTING_EVIDENCE.md)
[![Security](https://img.shields.io/badge/security%20audit-10%2F10%20passed-success.svg)](file:///d:/VETRA/scripts/security_audit.py)
[![Streamlit UI](https://img.shields.io/badge/streamlit%20pages-15%2F15%20clean-blueviolet.svg)](file:///d:/VETRA/tests/test_all_streamlit_pages.py)
[![Docker](https://img.shields.io/badge/docker-hardened%20non--root-2496ED.svg)](file:///d:/VETRA/docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3.11-3776AB.svg)](https://www.python.org)
[![MongoDB](https://img.shields.io/badge/database-MongoDB%20Atlas-47A248.svg)](https://www.mongodb.com)

---

## 1. Overview

**VETRA** is an enterprise-grade, end-to-end intelligent livestock healthcare and disease surveillance platform engineered for the **Smart India Hackathon (SIH) Grand Finale**. It resolves the critical challenges of early subclinical disease detection, rural veterinary accessibility, and regional epizootic containment in India's livestock economy.

By synthesizing **continuous IoT multi-vital telemetry**, **on-farm edge computer vision**, **prospective predictive AI**, **closed-loop telemedicine**, and **district-level epidemiological surveillance**, VETRA empowers smallholder dairy farmers and state animal husbandry authorities with early intervention capabilities 24 to 36 hours before physical prostration occurs.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            VETRA PLATFORM LIFECYCLE                          │
└──────────────────────────────────────────────────────────────────────────────┘
  IoT Sensors + Edge Cameras   ──►   Dual-Tier AI Intelligence (Deterministic + GenAI)
             │                                          │
             ▼                                          ▼
   Subclinical Anomaly Alert   ──►   Veterinary Telemedicine & Digital Prescription
             │                                          │
             ▼                                          ▼
   Cross-Farm Geospatial Radar ──►   Institutional Governance (8 Mandatory Safety Gates)
             │                                          │
             ▼                                          ▼
   NADRS / LIMS Package Export ──►   Ring Biosecurity & National Epizootic Defense
```

---

## 2. Key Capabilities & Innovations

1. **Continuous Multi-Vital IoT Ingestion:** Real-time monitoring of Core Body Temperature, Heart Rate, Respiration Rate, 3-Axis Rumination Minutes, and Locomotion Activity.
2. **Edge Computer Vision Locomotion Triage:** Headless OpenCV analysis evaluating locomotion scores (1 to 5), stride asymmetry, and spinal arching as cattle exit milking parlors.
3. **Dual-Tier AI with Deterministic Fallback:** 100% operational uptime guaranteed. Mathematical risk scoring and linear regression trends operate completely offline; Google Gemini enriches clinical narratives when connected.
4. **Prospective 72-Hour Health Forecasting:** Predicts health trajectory shifts across 24h, 48h, and 72h horizons, opening a pre-emptive window for metabolic buffering.
5. **Closed-Loop Veterinary Telemedicine:** Triage queue, longitudinal vital graphs, video/chat tele-consultation, and digital prescriptions updating farm preventive calendars.
6. **Preventive Protocol Management:** Automated scheduling for national vaccinations (FMD, HS, BQ, Brucellosis), deworming, biosecurity disinfection, and quarantine logging.
7. **Haversine Geospatial Cluster Radar:** Automatically discovers cross-farm disease outbreaks within configurable radii (e.g., 3 farms / 5 km with $>3.0\sigma$ temporal surge).
8. **Anti-Autonomous Outbreak Rule:** Programmatic HTTP 403 Forbidden preventing any AI model or automated script from declaring an epidemic. Outbreak confirmation requires human Institutional Veterinary Officer authentication.
9. **8-Gate Statutory Interoperability:** Generates PII-masked, certified export packages conforming to National Animal Disease Reporting System (NADRS) and LIMS / WOAH standards.

---

## 3. System Architecture & Tech Stack

- **Backend:** FastAPI (Python 3.11), Uvicorn ASGI, Pydantic v2, PyMongo, WebSockets.
- **Frontend:** Streamlit Command Center with 15 specialized operational modules.
- **Database:** MongoDB Atlas with connection pooling (5–50), compound unique indexes, and immutable SHA-256 audit ledger.
- **AI & Analytics:** Scikit-Learn, NumPy, OpenCV (Headless), Google GenAI SDK (Gemini).
- **Containerization:** Multi-stage Docker images running as non-root user `vetra` (UID 1000) over isolated bridge network `vetra-net`.

For complete architectural specifications, see [VETRA Final Architecture](file:///d:/VETRA/docs/VETRA_FINAL_ARCHITECTURE.md).

---

## 4. Quick Start Guide

### Prerequisites
- Python 3.11
- Active MongoDB connection (or local replica set)
- Docker & Docker Compose (optional for containerized deployment)

### Mode A: Local Development Setup
1. **Clone and enter repository:**
   ```powershell
   cd D:\VETRA
   ```
2. **Set up virtual environment & install dependencies:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Configure environment:**
   ```powershell
   cp .env.example .env
   # Supply MONGODB_URL and JWT_SECRET in .env
   ```
4. **Launch FastAPI Backend (Terminal 1):**
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. **Launch Streamlit Frontend (Terminal 2):**
   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run frontend\app.py
   ```
6. **Access Application:**
   - **Frontend UI:** `http://localhost:8501`
   - **API Documentation (Swagger):** `http://localhost:8000/docs`
   - **Health Probe:** `http://localhost:8000/health`

### Mode B: Production Docker Compose Setup
```bash
docker compose up -d --build
```
Both containers execute with dedicated non-root users and automated health checks.

---

## 5. Demo Credentials

VETRA enforces strict Role-Based Access Control (RBAC). Use these pre-seeded credentials for evaluation:

| Role | Email | Password | Primary Capabilities |
|---|---|---|---|
| **Farmer** | `farmer@vetra.demo` | `Vetra@12345` | Herd vitals, animal health cards, alerts, telemedicine requests |
| **Veterinarian** | `vet@vetra.demo` | `VetraVet@2026` | Clinical triage, digital prescriptions, lab results, tele-consultation |
| **Institutional Officer** | `officer@vetra.demo` | `VetraGov@2026` | District outbreak radar, warning lifecycle, government package certification |
| **Administrator** | `admin@vetra.demo` | `VetraAdmin@2026` | Full platform command center, IoT orchestration, security audit logs |

For a complete guide to the 9 demonstration scenarios, see [SIH Demo Guide](file:///d:/VETRA/docs/SIH_DEMO_GUIDE.md).

---

## 6. Automated Testing & Verification Evidence

VETRA is 100% verified with zero regressions across all 15 development phases:

```powershell
# 1. Run Master Regression Runner (All 11 Baseline Suites + Phase 15 Pytest Suite)
.\.venv\Scripts\python.exe .\scripts\run_all_phase_tests.py
# Result: 271 / 271 PASSED (100% PASS, 0 FAILURES, 0 REGRESSIONS)

# 2. Run Phase 15 Verification Suite (via pytest)
.\.venv\Scripts\python.exe -m pytest .\tests\test_phase_15.py -v
# Result: 38 / 38 PASSED (9.20s)

# 3. Run Streamlit Headless Page Verification (All 15 Pages)
.\.venv\Scripts\python.exe .\tests\test_all_streamlit_pages.py
# Result: 15 / 15 PAGES PASSED (0 EXCEPTIONS)

# 4. Run Automated Security & Hardening Audit
.\.venv\Scripts\python.exe .\scripts\security_audit.py
# Result: 10 PASSED | 0 WARNINGS | 0 FAILURES
```

---

## 7. Documentation Index

Comprehensive engineering and operational documentation is available in `docs/`:

- [SIH Demonstration & Evaluation Guide](file:///d:/VETRA/docs/SIH_DEMO_GUIDE.md) — Walk-through of the 9 demo scenarios and judging cues.
- [SIH Problem-Solution Mapping](file:///d:/VETRA/docs/SIH_PROBLEM_SOLUTION_MAPPING.md) — Technical requirements traceability matrix.
- [VETRA Innovations & Differentiators](file:///d:/VETRA/docs/VETRA_INNOVATION_AND_DIFFERENTIATORS.md) — What sets VETRA apart in agritech AI.
- [VETRA Final Architecture](file:///d:/VETRA/docs/VETRA_FINAL_ARCHITECTURE.md) — 7-layer component architecture and container topology.
- [VETRA Complete Feature Matrix](file:///d:/VETRA/docs/VETRA_FEATURE_MATRIX.md) — Catalog of 37 production capabilities across all 15 phases.
- [Empirical Testing Evidence](file:///d:/VETRA/docs/VETRA_TESTING_EVIDENCE.md) — Detailed test execution logs and 0-mutation proof.
- [Final Production Deployment Checklist](file:///d:/VETRA/docs/VETRA_FINAL_DEPLOYMENT_CHECKLIST.md) — Pre-flight operational runbook.
- [SIH Presentation Pitch Deck](file:///d:/VETRA/docs/SIH_PRESENTATION_CONTENT.md) — 10-slide outline for the grand finale jury.
- [SIH Live Demo Script & Jury Q&A](file:///d:/VETRA/docs/SIH_LIVE_DEMO_SCRIPT.md) — Minute-by-minute presentation runbook.
- [SIH Demo Troubleshooting Runbook](file:///d:/VETRA/docs/SIH_DEMO_TROUBLESHOOTING.md) — Emergency live recovery procedures.
- [Phase 15 Completion Audit Report](file:///d:/VETRA/docs/PHASE_15_COMPLETION_AUDIT.md) — Official Phase 15 sign-off audit.

---

## 8. Regulatory & Clinical Safety Statements

1. **Clinical Screening Notice:** VETRA’s AI models perform non-invasive triage screening and risk prioritization. They explicitly do not issue unilateral clinical diagnoses. Physical examination and prescription remain the exclusive responsibility of registered veterinary practitioners.
2. **Statutory Outbreak Gate:** No automated algorithm, IoT sensor, or farmer account can confirm an epidemiological disease outbreak. Official confirmation is programmatically restricted to authenticated Institutional Veterinary Officers.
3. **Statutory Export Disclaimer:** All generated regulatory export packages bear the official watermark:  
   `"Government-ready export package — not an official submission."`

---

## 9. License & SIH 2026 Declaration

Developed for the **Smart India Hackathon (SIH) 2026**.  
*All rights reserved by the VETRA Engineering Team.*
