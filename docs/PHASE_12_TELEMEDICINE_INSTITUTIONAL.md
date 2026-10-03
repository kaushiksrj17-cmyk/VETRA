# VETRA — Phase 12 Architecture & Technical Specification
## Veterinary Telemedicine, Institutional Reporting & Government Disease Surveillance Integration

---

### 1. Executive Summary

Phase 12 transforms VETRA from an automated on-farm monitoring and AI health forecasting engine into a structured veterinary and institutional collaboration platform. It bridges on-ground farmers, qualified veterinarians, clinical decision-support tooling, laboratory diagnostic documentation, and state-level institutional disease surveillance without fabricating live connections or biological records.

```
       [ IoT Sensors / Camera Monitoring / Multimodal AI / Predictive Forecasting ]
                                           │
                                           ▼
                                 [ Clinical Alerts ]
                                           │
                                           ▼
                                [ Veterinary Network ]
                             (Directory, Profiles, Status)
                                           │
                                           ▼
                                [ Clinical Cases ]
                         (Assigned, In-Review, Follow-up)
                                           │
                                           ▼
                          [ Telemedicine Consultation ]
                         (Live Notes, Shared Evidence)
                                           │
                                           ▼
                         [ Institutional Disease Event ]
                      (Draft ➔ Review ➔ Approved ➔ Submitted)
                                           │
                                           ▼
                       [ Institutional Adapter Architecture ]
                        • Default: NOT_CONFIGURED (Safe)
                        • Mock Adapter: Verification
                        • Export Formats: JSON, CSV, PDF
```

---

### 2. Subsystems Architecture

#### 2.1 Veterinary Network Subsystem
- **Purpose**: Directory of qualified veterinary professionals, specialization indexing, availability tracking, and regional assignment.
- **Collection**: `veterinary_profiles`
- **Identifier**: `VET-YYYY-XXXX`
- **Fields**:
  - `veterinarian_id`: System-assigned unique string.
  - `user_id`: Reference to VETRA system `users` document.
  - `name`: Full professional name.
  - `registration_reference`: Veterinary Council registration reference (`NOT_PROVIDED` when unverified, preventing fabricated credentials).
  - `specialization`: Clinical focus area (`general_practice`, `bovine_medicine`, `epidemiology`, etc.).
  - `qualifications`: Academic and professional credentials.
  - `experience_years`: Numeric experience.
  - `phone`, `email`: Contact details.
  - `service_regions`: Geographical regions supported.
  - `supported_species`: Species handled (`cattle`, `buffalo`, `goat`, `sheep`).
  - `availability_status`: Current status (`available`, `in_consultation`, `on_leave`, `emergency_only`, `offline`).
  - `consultation_modes`: Supported modalities (`in_person`, `telemedicine`, `farm_visit`, `emergency`, `follow_up`).
  - `organization`: Institutional affiliation.
  - `verification_status`: Accreditation review state (`unverified`, `pending`, `verified`).

#### 2.2 Telemedicine Consultation Subsystem
- **Purpose**: Scheduled and on-demand remote clinical assessments linking farmer complaints to multi-source evidence and veterinarian findings.
- **Collection**: `telemedicine_consultations`
- **Identifier**: `CONS-YYYY-XXXX`
- **Status Lifecycle**:
  `requested` ➔ `scheduled` ➔ `accepted` ➔ `in_progress` ➔ `completed` / `cancelled` / `no_show` / `follow_up_required`
- **Clinical Safety Notice**:
  > *"Telemedicine assessment may be limited when physical examination, laboratory testing, imaging, or on-site assessment is required. VETRA Telemedicine provides clinical decision-support and evidence communication; it does not replace urgent emergency surgical intervention."*
- **Evidence Sharing (Zero Duplication)**:
  References pre-existing database records via ID pointers:
  - `visual_evidence_ids` (Phase 9/10 media)
  - `health_reading_ids` (Phase 4 IoT telemetry)
  - `predictive_assessment_ids` (Phase 11 forecasts)
  - `surveillance_context` (Phase 8 cluster and geospatial indicators)
  - `case_id` (Phase 6.6 clinical cases)
- **Clinical Notes RBAC**:
  - Veterinarians: Authoritative subjective findings, objective findings, clinical assessment, treatment recommendations, and follow-up directives.
  - Farmers: Restricted to symptom observations, behavioral changes, feeding anomalies, and inquiry notes. Farmers are strictly prevented by API permissions and validation from recording medical diagnoses or formal assessments.

#### 2.3 Laboratory Result Reference Subsystem
- **Purpose**: Diagnostic evidence referencing without data fabrication.
- **Collection**: `laboratory_results`
- **Identifier**: `LAB-YYYY-XXXX`
- **Result Statuses**: `pending`, `negative`, `positive`, `inconclusive`, `invalid`, `not_available` (default: `not_available`).
- **Document Handling**: Adheres to Phase 9 secure storage standards: SHA-256 cryptographic verification, MIME whitelist (`application/pdf`, `image/jpeg`, `image/png`), path traversal protection, and RBAC-scoped document access.

#### 2.4 Institutional Reporting & Surveillance Subsystem
- **Purpose**: Formal compilation of multi-farm, epidemiological, and disease event reports for qualified institutional review.
- **Collection**: `institutional_reports`
- **Identifier**: `REP-YYYY-XXXX`
- **Report Types**:
  - `disease_event`: Clinical infectious or contagious episode.
  - `animal_health_event`: Individual acute pathology or mortality.
  - `farm_health_summary`: Aggregated herd health snapshot.
  - `surveillance_summary`: Regional syndromic and anomaly overview.
  - `veterinary_case_summary`: Retrospective review of clinical cases.
  - `outbreak_candidate_review`: Statistical anomaly package compiled for qualified veterinary review.
    > *Disclaimer: "outbreak_candidate_review does NOT mean a confirmed outbreak. It signifies that an epidemiological review package has been prepared for qualified institutional assessment."*
- **Report Workflow**:
  `draft` ➔ `under_review` ➔ `approved` ➔ `submitted` ➔ `acknowledged` (or `rejected` / `cancelled`).
  Direct submission of unapproved reports is strictly blocked.

#### 2.5 Institutional Reporting Adapter Framework
- **Class**: `InstitutionalReportingAdapter` (Abstract Base Class)
- **Supported State Machine**:
  `NOT_CONFIGURED` (default) | `CONFIGURED` | `CONNECTED` | `ERROR`
- **Adapter Implementations**:
  - `MockInstitutionalAdapter`: System verification adapter registered with `adapter_id="mock_gov_adapter"`, display status `NOT_CONFIGURED`, live submission disabled.
- **Real-World Integration Rules**:
  - Zero fabricated government endpoints or URLs.
  - No claims of active external API connectivity unless an authentic authenticated endpoint is provided and validated.

---

### 3. Role-Based Access Control (RBAC) Matrix

| Operation | Farmer | Veterinarian | Admin | Institutional Officer |
|---|:---:|:---:|:---:|:---:|
| View Own Farm Telemedicine Cases | ✅ | ✅ (assigned) | ✅ | ✅ (redacted) |
| Request Telemedicine Consultation | ✅ | ❌ | ✅ | ❌ |
| Accept / Conduct Consultation | ❌ | ✅ | ✅ | ❌ |
| Post Farmer Observation Note | ✅ | ✅ | ✅ | ❌ |
| Post Veterinarian Diagnosis & Treatment | ❌ (403) | ✅ | ✅ | ❌ |
| Reference Laboratory Results | ❌ | ✅ | ✅ | ✅ |
| Draft Institutional Report | ❌ (403) | ✅ | ✅ | ✅ |
| Review Institutional Report | ❌ | ✅ | ✅ | ✅ |
| Approve Institutional Report | ❌ (403) | ❌ (403) | ✅ | ✅ |
| Submit Institutional Report | ❌ (403) | ❌ (403) | ✅ | ✅ |
| Cross-Farm Aggregated Reports | ❌ (isolated) | ✅ (assigned) | ✅ | ✅ (authorized) |

---

### 4. Privacy, PII Redaction & Data Protection

- **Tenant Isolation**: Cross-farm queries are strictly blocked. Farmers attempting to view or query reports, cases, or consultations from another `farm_id` receive an HTTP 403 Forbidden.
- **Export Redaction Engine**: When `redact_pii=true` is requested on institutional report exports:
  - Farm ID is replaced with `"[REDACTED_FARM_IDENTITY]"`.
  - Reporting User is replaced with `"[REDACTED_USER]"`.
  - Individual animal identifiers are anonymized.
- **Audit Logging**: Sensitive institutional actions (`report_created`, `report_reviewed`, `report_approved`, `report_submitted`, `consultation_created`, `consultation_accepted`) are logged in the `audit_logs` collection. Authentication secrets, passwords, and JWT tokens are stripped prior to persistence.

---

### 5. Notification Architecture

- **Abstraction**: `NotificationService` utilizing `NotificationProvider` interface.
- **Default Provider**: `MockNotificationProvider` running in development mode.
- **Labeling Standard**: All emitted notification messages are strictly prefixed with `[SIMULATION]`.
- **Duplicate Reminders Prevention**: Follow-up reminders integrate with the Phase 6 preventive alert synchronization engine, utilizing deterministic notification keys to guarantee single delivery.

---

### 6. AI Assistance Boundaries

- **Role of Gemini AI**: AI is strictly employed for text synthesis, drafting summaries, and organizing clinical evidence into structured formats.
- **Enforced Constraint**: All AI-assisted institutional reports remain strictly in `draft` state. Autonomous report approval or external submission by AI is programmatically prevented.
- **Proven Provenance**: Every generated report records distinct provenance distinguishing observed sensor telemetry, model predictions, veterinary clinical notes, and AI summary text.

---

### 7. Known Limitations & Roadmap

1. **External Gateway Connectivity**: External state and national government disease monitoring adapters remain in `NOT_CONFIGURED` state pending formal institutional memorandum of understanding (MoU) and API provisioning.
2. **Video Streaming Protocol**: Real-time telemedicine video leverages existing secure WebSocket signalling; WebRTC peer-to-peer data channel mesh is scheduled for Phase 14 enterprise hardening.
