# VETRA — Phase 14 Backup, Disaster Recovery & High Availability Runbook
## Enterprise Production Hardening

---

### 1. Objectives & Recovery Targets

VETRA stores critical livestock health biometrics, veterinary records, epidemiological surveillance packages, and audit trails. The disaster recovery strategy defines clear Recovery Point Objectives (RPO) and Recovery Time Objectives (RTO):

| Tier | Component | RPO (Max Data Loss) | RTO (Max Downtime) | Backup Frequency |
|---|---|---|---|---|
| **Tier 1: Core Database** | MongoDB Atlas (`animals`, `farms`, `users`, `veterinary_cases`, `epidemiological_events`) | < 1 hour | < 30 minutes | Continuous Oplog / Daily Snapshots |
| **Tier 2: Audit Logs** | MongoDB `audit_logs` collection | 0 (Immutable WORM retention) | < 15 minutes | Continuous Replication |
| **Tier 3: Media Artifacts** | Edge computer vision images & videos (`media/`) | < 24 hours | < 2 hours | Daily Cloud Storage Sync (S3/GCS) |
| **Tier 4: Application State** | Containers & configurations (`.env`, Dockerfiles) | Version-controlled (Git) | < 10 minutes | Infrastructure as Code |

---

### 2. MongoDB Atlas Backup & Restoration Architecture

#### 2.1 Continuous Cloud Backups
- **Atlas Cloud Backup**: Automated point-in-time recovery (PITR) enabled on the production replica set with a 35-day retention window.
- **Snapshot Retention Policy**:
  - Hourly snapshots retained for 2 days.
  - Daily snapshots retained for 30 days.
  - Weekly snapshots retained for 12 weeks.
  - Monthly snapshots retained for 12 months.

#### 2.2 Point-in-Time Restore (PITR) Procedure
1. Log in to the MongoDB Atlas Console.
2. Navigate to **Deployment** ➔ **Database** ➔ Target Cluster ➔ **Backup** tab.
3. Select **Restore** ➔ Choose **Point in Time**.
4. Select the exact timestamp prior to incident (e.g. data corruption or accidental mutation).
5. Specify the target cluster (restore to an isolated staging cluster first to verify data integrity).
6. Verify document counts against known baseline records (`animals`, `devices`, `health_readings`).
7. Update `MONGODB_URL` in production `.env` to point to restored cluster upon verification.

#### 2.3 Manual Logical Backup (`mongodump` & `mongorestore`)
For compliance, regulatory, or off-cloud archival:

```bash
# Export logical backup (excluding system collections)
mongodump --uri="$MONGODB_URL" --gzip --archive=/backups/vetra_backup_$(date +%Y%m%d_%H%M%S).archive.gz

# Restore from logical archive
mongorestore --uri="$MONGODB_URL" --gzip --archive=/backups/vetra_backup_20261002_000000.archive.gz --drop
```

> **WARNING**: The `--drop` flag will replace collections. NEVER execute `--drop` in production without verified offline archives and management authorization.

---

### 3. Media Artifact & File Storage Recovery

All computer vision analysis media is stored in `media/images/` and `media/videos/`.

#### 3.1 Backup Sync (Daily rsync or S3 Sync)
```bash
# Sync local media to secure cloud storage
aws s3 sync /app/media s3://vetra-production-media-backup/media --delete-excluded
# Or using rsync to a secondary backup server
rsync -avz --delete /app/media/ backupuser@backup.vetra.internal:/var/backups/vetra/media/
```

#### 3.2 Restoration
```bash
# Restore media directory
aws s3 sync s3://vetra-production-media-backup/media /app/media
chown -R vetra:vetra /app/media
```

---

### 4. Configuration & Environment Secret Recovery

- **Key Principle**: Raw production credentials (`.env`) must NEVER be committed to Git.
- **Vault Storage**: Production environment variables are stored in an enterprise secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault, or Google Secret Manager).
- **Template Reference**: In case of complete environment loss, initialize from `.env.example`:
  ```bash
  cp .env.example .env
  # Populate secrets from Vault
  ```

---

### 5. Deployment Rollback Procedure

If a release introduces regression or instability:

#### 5.1 Docker Rollback
```bash
# 1. Stop current containers
docker compose down

# 2. Check out previously verified stable tag
git checkout tags/v13.0.0-PROD-READY

# 3. Rebuild and launch containers
docker compose build --no-cache
docker compose up -d

# 4. Verify health endpoints
curl -f http://localhost:8000/health/ready
```

#### 5.2 Local Process Rollback
```powershell
# In PowerShell:
git checkout tags/v13.0.0-PROD-READY
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

### 6. Production Disaster Recovery Checklist

- [ ] MongoDB Atlas continuous backups active with PITR enabled.
- [ ] Production `.env` securely vaulted with access control restricted to authorized DevOps.
- [ ] Daily media synchronization job running and verified.
- [ ] Readiness endpoint (`/health/ready`) integrated with container orchestration liveness/readiness probes.
- [ ] Quarterly simulated disaster recovery exercise executed.
- [ ] Audit logs set to append-only / WORM compliance policy.
