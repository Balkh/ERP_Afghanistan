# PHARMACY ERP — OPERATIONAL MATURITY AUDIT REPORT

**Date:** 2026-05-10
**Scope:** Backend (Django/DRF) + Frontend (PySide6)
**Type:** Analysis & Assessment Only — No Implementation

---

## MATURITY SCORE OVERVIEW

| # | Category | Score | Classification |
|---|----------|-------|----------------|
| 1 | Crash Recovery | 4/10 | BASIC ONLY |
| 2 | Global Error Handling | 5/10 | PARTIALLY IMPLEMENTED |
| 3 | Structured Logging | 6/10 | PARTIALLY IMPLEMENTED |
| 4 | Audit Logging | 7/10 | PARTIALLY IMPLEMENTED |
| 5 | Backup & Restore | 7/10 | PARTIALLY IMPLEMENTED |
| 6 | Monitoring & Health Checks | 8/10 | PRODUCTION READY |
| 7 | Security & Permission Hardening | 6/10 | PARTIALLY IMPLEMENTED |
| 8 | Recovery & Fault Tolerance | 6/10 | PARTIALLY IMPLEMENTED |
| 9 | Deployment Hardening | 3/10 | BASIC ONLY |
| 10 | Operational Stability | 5/10 | PARTIALLY IMPLEMENTED |

**Overall Maturity: 5.7/10 — PARTIALLY IMPLEMENTED**

---

## WHAT ALREADY EXISTS

### 1. CRASH RECOVERY — 4/10 (BASIC ONLY)

**Backend:**
- ObservabilityMiddleware.process_exception() logs unhandled exceptions with full traceback (core/logging/middleware.py:130-153)
- LicenseMiddleware has broad except Exception returning 500 JSON error (licensing/middleware.py:80-86)
- TransactionService.execute_with_rollback() for savepoint-based recovery (core/services/transaction_service.py:37-70)
- Job runner with max runtime (3600s) and stuck job detection (30min) (jobs/services.py:26-27)
- BackgroundJob retry with exponential backoff: [1min, 5min, 15min, 30min] (jobs/services.py:116-141)

**Frontend:**
- MainWindow constructor wrapped in try/except with QMessageBox.critical (main.py:184-194)
- API client GET retries 3x with exponential backoff (api/client.py:157-178)
- Graceful dashboard failure with status subtitle update (dashboard.py:257-268)

**MISSING:**
- No sys.excepthook in frontend — unhandled Qt event-loop exceptions crash entire application
- No custom DRF exception handler — unhandled errors get DRF default formatting
- except: pass in 8+ locations (main_window.py:141,1061; login_screen.py:273,286-287; settings_screen.py:47; dashboard.py:281-282)
- No request timeout middleware — long-running requests can hang workers
- No page-level crash insulation — one sub-screen crash can take down entire app

---

### 2. GLOBAL ERROR HANDLING — 5/10 (PARTIALLY IMPLEMENTED)

**Backend:**
- Error code registry with 40+ codes (AUTH_001, FIN_*, INV_*) (core/api/errors.py)
- APIResponse.success()/.error()/.paginated() methods (core/api/responses.py)
- StandardizedJSONRenderer auto-wraps all responses (core/api/renderers.py)
- 101 transaction.atomic blocks covering all critical paths
- Bad request detection (400/401/403/422) in ObservabilityMiddleware (core/logging/middleware.py:82-94)

**Frontend:**
- Status code differentiation: 401->login, 403->toast, 5xx->retry (api/client.py:88-103)
- Error toasts via ToastManager in POST/PUT/DELETE (api/client.py:192-250)

**MISSING:**
- No DRF EXCEPTION_HANDLER configured in settings.py — errors not in standardized format
- Inconsistent view error patterns — mix of APIResponse.error(), raw dicts, and str(e)
- No request cancellation on navigation — pending requests execute callbacks on stale widgets

---

### 3. STRUCTURED LOGGING — 6/10 (PARTIALLY IMPLEMENTED)

**Backend (7/10):**
- JSONFormatter with timestamp, level, request_id, user_id, traceback (core/logging/formatters.py:10-47)
- HumanFormatter for color-coded dev output (core/logging/formatters.py:50-79)
- Logger factory with RotatingFileHandler (10MB, 5 backups) (core/logging/logger.py)
- ObservabilityMiddleware — full request/response logging with UUID, duration, slow detection (core/logging/middleware.py:41-128)
- X-Request-ID header on all responses (core/logging/middleware.py:75)
- 10 named loggers: django, apps, erp.audit, erp.financial, erp.inventory, erp.security, erp.performance, erp.error, erp.api
- Production settings: separate file/error_file handlers, no console (settings_production.py:37-64)

**Frontend (1/10):**
- NO logging framework configured — all output via print() (20+ statements in main.py alone)
- logging.getLogger() in 4 files (base_screen.py, navigation_manager.py, notifications.py, base_widgets.py) but ZERO handlers
- DEBUG_MODE = True hardcoded in api/client.py:8
- No log files, no rotation, no log levels, no structured output

**CRITICAL ISSUE:**
- Duplicate logging configs: settings.py LOGGING dict AND core/logging/config.py both configure logging independently — potential double-output
- DatabaseAuditHandler.emit() silently fails on DB errors (core/logging/handlers.py:32-33)

---

### 4. AUDIT LOGGING — 7/10 (PARTIALLY IMPLEMENTED)

**Backend:**
- 3 audit models: AuditLog (core/models/audit.py), AuditLog (security/models.py), AuditTrail (audit/models.py)
- SecurityEvent with 9 event types and severity levels (security/models.py:144-195)
- AuditService.log_model_change() diffs old/new field values (audit/services/audit_service.py:65-97)
- AuditMiddleware logs API requests to AuditTrail (audit/services/audit_service.py:183-217)
- AuditService.cleanup_old_logs() with configurable retention (audit/services/audit_service.py:139-161)
- Security views write AuditLog for LOGIN/LOGOUT/PERMISSION_DENIED (security/views.py:88-266)

**Frontend:**
- AuthorizationAudit in role_manager.py stores decisions in memory (max 1000 entries, lost on restart)
- audit_screen.py reads backend audit logs view-only

**MISSING:**
- Triple audit models across core/security/audit — no consolidation, fragmented queries
- Frontend client-side audit has NO persistence — pure memory, lost on every restart
- AuthorizationFallback.log_async() is a stub with print() and comment "use proper async logging"
- No automated security event detection (brute force, SQL injection) despite models existing
- 6 occurrences of request.user.request.user.is_superuser in security/views.py (lines 518,562,595,617,682,709) — AttributeError bug

---

### 5. BACKUP & RESTORE — 7/10 (PARTIALLY IMPLEMENTED)

**Backend (9/10 — Production Ready):**
- Full BackupManager with tar.gz, Fernet/PBKDF2 encryption, SHA-256 checksums (backup/backup_system.py:282-414)
- RestoreService with dependency injection, provider abstraction, validation pipeline (backup/services/restore_service.py)
- BackupSchedule model: hourly/daily/weekly/monthly with retention (backup/models.py:105-145)
- BackupScheduler with daemon thread + cron-like scheduling (backup/backup_system.py:702-760)
- RestorePoint + RestoreValidation with 5 validation types (backup/models.py:218-314)
- Full CRUD API: /api/backup/records/, /api/backup/restore-points/, etc.
- Retention: max 30 backups, max 90 days, min 1GB free space

**Frontend (2/10):**
- Backup screen exists with "Create Backup" button and restore points table
- Settings screen has backup frequency/auto-backup toggles

**CRITICAL ISSUE:**
- backup_screen.py:104-115 — "Create Backup" button shows QMessageBox but NEVER calls any API!
- No restore UI — restore points listed but no restore button/action
- Backup settings stored locally in JSON — not synced to backend schedule config
- Thread-based scheduler incompatible with multi-worker WSGI deployments
- Default fallback password: 'default_backup_password_change_in_production' (backup_system.py:451)
- No Celery/cron integration

---

### 6. MONITORING & HEALTH — 8/10 (PRODUCTION READY)

**Backend:**
- Health endpoints: /api/health/, /api/health/db/, /api/health/system/, /api/ops/health/
- HealthMonitor with DB, system resources, background services checks (core/operations/health.py:16-159)
- ControlCenterAggregator for financial/inventory/HR/operations metrics (core/operations/control_center.py)
- RequestMetrics: bad/slow request tracking per endpoint/user/IP (core/operations/api_observability.py:25-80)
- Performance budgets: standard 500ms/1500ms, report 2000ms/5000ms (core/operations/guardrails.py:42-46)
- Slow request detection at 500ms threshold (core/logging/middleware.py:21-116)
- AlertManager: 4 severity levels, 8 categories, max 1000 alerts (core/operations/alerts.py)

**Frontend:**
- Connection monitoring: 5-second health check timer with status label (main_window.py:182-193)
- LoadingOverlay + LoadingSpinner for API operations (ui/components/loading_spinner.py)
- Status bar: connection status, user, time, device ID, license status
- Control center screen with 5-second auto-refresh (control_center_screen.py:448)

**MISSING:**
- All metrics are in-memory — alerts, request metrics, concurrency state LOST ON RESTART
- No external monitoring integration (Prometheus, Datadog, Sentry, Grafana)
- Alerts not persisted to database — no alert history across restarts
- Frontend timers not cleaned up on screen hide/close — potential memory leak
- LoadingOverlay transparent to mouse events — users can click behind it during loading

---

### 7. SECURITY & PERMISSIONS — 6/10 (PARTIALLY IMPLEMENTED)

**Backend:**
- JWTAuthentication with HS256, 24-hour tokens (security/authentication.py:9-70)
- RoleBasedPermission with superuser bypass (security/permissions.py:8-117)
- Full RBAC models: Role, Permission, UserRole (security/models.py)
- TenantMiddleware + StrictTenantMiddleware for multi-tenant isolation (core/multitenant/middleware.py)
- IsAuthenticated default on all DRF endpoints (settings.py:152)
- Production: HSTS (1yr), secure cookies, XSS filter, X-Frame-Options DENY (settings_production.py:78-86)

**Frontend:**
- License validation: RSA signing, device fingerprinting, tamper detection
- Login dialog: show-password, inline errors, attempt tracking
- Tamper detector: SHA-256 file integrity at startup

**CRITICAL ISSUES:**
- Plaintext session storage: login_screen.py:271 writes username:token to session.dat
- Hardcoded JWT token in dev mode (main.py:174) — genuine token in source
- 6x request.user.request.user bug (security/views.py:518,562,595,617,682,709)
- No token refresh mechanism — 24-hour expiry forces re-login
- No token blacklisting — Auth_007 error code exists but unimplemented
- RSA key auto-generation per installation — centrally-signed licenses impossible
- XOR obfuscation self-documented as "not for production use" (security/obfuscator.py:17)

---

### 8. RECOVERY & FAULT TOLERANCE — 6/10 (PARTIALLY IMPLEMENTED)

**Backend:**
- 101 transaction.atomic blocks across all critical services
- 11 select_for_update calls for row-level locking (core/operations/concurrency.py)
- JournalEngine.reverse_entry() — compensating transaction pattern (accounting/services/journal_engine.py:233-256)
- RestoreService.rollback() — snapshot-based rollback (backup/services/restore_service.py:337-354)
- ConcurrencyMonitor + RaceConditionDetector (core/operations/concurrency.py)

**Frontend:**
- GET retry with exponential backoff (api/client.py:157-178)
- Connection auto-recovery detection every 5 seconds (main_window.py:618-631)

**MISSING:**
- No retry for transient DB failures (deadlocks, serialization errors)
- No request queue for offline operations — data entry during disconnection is lost
- No data caching — all data re-fetched on every navigation
- No formal saga/choreography pattern for multi-step business processes
- No connection pooling (CONN_MAX_AGE not set for PostgreSQL)
- Frontend POST/PUT/DELETE have zero retry logic
- No state recovery after reconnect — screens don't auto-refresh

---

### 9. DEPLOYMENT HARDENING — 3/10 (BASIC ONLY)

**Backend:**
- Settings separation: settings.py (dev) + settings_production.py (packaged) + settings_minimal.py
- python-decouple AutoConfig for env variable handling
- ConfigurationDriftDetector for config snapshot integrity (core/operations/stability.py:18-80)
- CORS configuration with configurable origins

**Frontend:**
- production_config.py with PyInstaller-aware path resolution for 6 resource types

**CRITICAL ISSUES:**
- No build/packaging scripts — no setup.py, pyproject.toml, requirements.txt, or .spec
- No Dockerfile for backend or frontend
- Default SECRET_KEY in code (settings.py:12)
- Default backup password in code (backup_system.py:451)
- No manage.py check --deploy or startup validation
- No production server config (Gunicorn/uWSGI)
- No dependency manifest for frontend
- .env.example exists but build process never enforces its use

---

### 10. OPERATIONAL STABILITY — 5/10 (PARTIALLY IMPLEMENTED)

**Backend:**
- operational_intelligence.py (1254 lines): RuleRegistry (20+ rules), anomaly detection, SLA monitoring, capacity forecasting
- SignalCoordinator: 10-min deduplication, severity override, signal merging (core/operations/signal_coordinator.py)
- GuardrailConfig: versioned (v1), 15-min alert cooldown, 5-min aggregation (core/operations/guardrails.py:42-68)
- ConfigurationDriftDetector: SHA-256 config integrity (core/operations/stability.py)

**Frontend:**
- Tamper detection at startup: SHA-256 file integrity (security/tamper_detector.py)
- License validation: RSA + device fingerprint + clock rollback detection

**MISSING:**
- No startup health verification — no check for pending migrations or service availability
- No dependency version pinning
- No migration safety checks before deploy
- No documented or automated rollback procedure
- All intelligence data is in-memory — rule state, anomaly history, SLA compliance LOST ON RESTART

---

## CRITICAL GAP ANALYSIS

| ID | Gap | Category | Risk | Impact |
|----|-----|----------|------|--------|
| G1 | No frontend sys.excepthook | Crash | CRITICAL | Any unhandled exception crashes the entire application |
| G2 | Backup screen "Create Backup" is a stub | Backup | CRITICAL | Users believe data is being backed up — it is not |
| G3 | Plaintext session.dat storage | Security | HIGH | JWT tokens extractable from filesystem |
| G4 | request.user.request.user bug (6x) | Security | HIGH | AttributeError on superuser-gating endpoints |
| G5 | No custom DRF exception handler | Error | HIGH | Non-standardized error responses |
| G6 | No frontend logging framework | Logging | HIGH | Zero debug trail, no crash forensics |
| G7 | No build/packaging scripts | Deploy | HIGH | Cannot produce reproducible builds |
| G8 | Default secrets in source code (3 places) | Security | HIGH | Production risk if env vars not set |
| G9 | Thread-based backup scheduler | Backup | MEDIUM | Duplicate schedulers across WSGI workers |
| G10 | No connection pooling | FT | MEDIUM | Not production-ready for PostgreSQL |
| G11 | All metrics/state in-memory | Monitor | MEDIUM | Operational history lost on restart |
| G12 | No retry for transient DB failures | FT | MEDIUM | Deadlock/error = 500 response |
| G13 | No token refresh | Security | MEDIUM | Forced re-login every 24 hours |
| G14 | RSA key auto-generation | Security | MEDIUM | Centrally-signed licenses impossible |
| G15 | Duplicate logging configs | Logging | LOW | Double-log output |

---

## RISK ANALYSIS

### HIGH-RISK FAILURE SCENARIOS

**Scenario 1: Unhandled Exception During Normal Operation**
Trigger: Any widget signal handler raises an exception (e.g., API callback on destroyed widget)
Result: Total application crash with raw traceback. User loses unsaved work.
Mitigation: Add sys.excepthook + error dialog + process restart (estimated 1 hour)

**Scenario 2: Data Loss via Non-Functional Backup**
Trigger: Operator trusts the "Backup initiated" message and assumes data is safe
Result: No backup ever created despite visual confirmation
Mitigation: Wire backup_screen.py to actual API call (estimated 2 hours)

**Scenario 3: Credential Leak via session.dat**
Trigger: Any process with filesystem access reads session.dat
Result: Valid JWT token extracted; full API access for 24 hours; no token blacklisting
Mitigation: Encrypt stored token + use httpOnly cookies (estimated 3 hours)

**Scenario 4: Authorization Bypass via request.user.request.user Bug**
Trigger: Non-superuser accesses protected endpoint
Result: AttributeError thrown instead of permission check — inconsistent behavior
Mitigation: Fix 6 occurrences (estimated 1 hour)

### OPERATIONAL VULNERABILITIES

- No offline-fallback: Network outage during data entry = lost work
- No operation queue: Actions during disconnection are silently dropped
- No migration guard: Deployments with pending migrations may silently fail
- In-memory state: Process restart loses all alert history, metrics, intelligence data

---

## PRIORITY ROADMAP

### Priority 1: CRITICAL (Safety + Trust) — ~6 hours total

1. Add frontend sys.excepthook + error dialog with restart option (G1 — ~1hr)
2. Fix backup_screen.py to call API and show real progress (G2 — ~2hr)
3. Fix request.user.request.user bug in 6 locations (G4 — ~1hr)
4. Add custom DRF EXCEPTION_HANDLER for standardized errors (G5 — ~2hr)

### Priority 2: HIGH (Security + Observability) — ~12 hours total

5. Add proper frontend logging: file handler, rotation, structured output (G6 — ~4hr)
6. Replace plaintext session storage with encrypted/secure storage (G3 — ~3hr)
7. Add JWT token refresh mechanism (G13 — ~4hr)
8. Remove default secrets from code; enforce env vars at startup (G8 — ~1hr)

### Priority 3: MEDIUM (Operational Resilience) — ~15 hours total

9. Add retry for transient DB failures (deadlocks, serialization) (G12 — ~3hr)
10. Add persistent alert/metrics storage to database (G11 — ~6hr)
11. Add request timeout middleware (— ~2hr)
12. Add connection pooling for PostgreSQL (G10 — ~2hr)
13. Consolidate logging configs (G15 — ~2hr)

### Priority 4: LOW (Maturity + Hardening) — ~36 hours total

14. Consolidate triple audit models into single system (G15 — ~8hr)
15. Create build/packaging scripts + Dockerfiles (G7 — ~16hr)
16. Replace thread scheduler with Celery/cron (G9 — ~8hr)
17. Add startup validation checks (— ~4hr)
18. Fix RSA key generation for central signing (G14 — ~4hr)

Total estimated effort: ~69 hours across 18 items

---

## APPENDIX: KEY FILE REFERENCE

| File | Issue | Line(s) |
|------|-------|---------|
| frontend/main.py | No sys.excepthook; app.exec() unprotected | 196-197 |
| frontend/main.py | Hardcoded JWT token | 174 |
| frontend/ui/system/backup_screen.py | Create Backup is a stub | 104-115 |
| frontend/ui/auth/login_screen.py | Plaintext session storage | 271 |
| frontend/api/client.py | POST/PUT/DELETE have no retry | 180-241 |
| backend/security/views.py | request.user.request.user bug (x6) | 518, 562, 595, 617, 682, 709 |
| backend/config/settings.py | Duplicate logging config | 179-264 vs core/logging/config.py |
| backend/backup/backup_system.py | Default fallback password | 451 |
| backend/config/settings.py | No custom DRF EXCEPTION_HANDLER | 146-168 |
| backend/licensing/license_service.py | Auto-generates RSA keys per install | 56 |
| backend/core/operations/alerts.py | Alerts are in-memory only | 63-186 |
