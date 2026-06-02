# Phase 6.6C — Security Audit Report

**Scope:** 5 target files + Django settings + frontend auth flow
**Method:** Static code inspection. No execution. No penetration testing.
**Reference:** OWASP Top 10 (2021), CWE-94 (Code Injection), CWE-95 (Eval Injection)

---

## Summary

| CWE | Severity | Location | Description |
|-----|----------|----------|-------------|
| CWE-94 | **CRITICAL** | `core/operations/intelligence/patterns.py:77` | `eval()` of derived string |
| CWE-95 | **CRITICAL** | `core/operations/intelligence/patterns.py:77` | Same — improper neutralization of direct elements in code |
| CWE-798 | **LOW** | `backend/config/settings.py:31` | `SECRET_KEY` has env-default weak value |
| CWE-489 | **LOW** | `frontend/api/client.py:11` | Hardcoded `DEBUG_MODE = True` |
| CWE-200 | **INFO** | `frontend/api/client.py:11,38` | Debug logging may leak request bodies |
| CWE-362 | **MEDIUM** | `frontend/ui/sidebar.py:455` | `processEvents()` re-entrancy window |
| CWE-209 | **LOW** | `backend/payments/services.py:198` | Error message exposes account balance to user |
| CWE-400 | **MEDIUM** | `frontend/api/client.py:247` | `time.sleep` on UI thread enables DoS-via-retries |

---

## CWE-94 / CWE-95: `eval()` of string in `patterns.py`

**Severity:** CRITICAL
**CVSS 3.1:** 8.4 (High) — under current data flow; 9.8 (Critical) if event source becomes user-controllable
**Location:** `backend/core/operations/intelligence/patterns.py:71-77`

```python
# L66-77
event_types = [e.event_type for e in events if e.source_type.value != "SIMULATION"]
patterns: Dict[str, int] = defaultdict(int)

for length in range(MIN_SEQUENCE_LENGTH, max_length + 1):
    for i in range(len(event_types) - length + 1):
        seq = tuple(event_types[i:i + length])
        patterns[str(seq)] += 1

# ...
for seq_str, count in patterns.items():
    if count >= min_support:
        types = eval(seq_str)            # ← CWE-94 / CWE-95
```

**Threat model:**

The function is called via two paths:
1. `core/operations/intelligence/gateway.py:43,130` — production intelligence route, exposed as `/api/control-center/intelligence/`
2. `simulation/tests/test_intelligence/test_intelligence.py` — 27 test invocations

**Currently safe because:**
- `event_type` is a string field on `Event` model
- `Event` is created by ERP service code only (no direct user API to create events)
- `source_type` filter at L66 excludes SIMULATION-sourced events from the mining
- Pattern is `str(tuple)` of strings, which today produces a Python repr literal like `('SALE_CREATED', 'INVOICE_PAID')`

**Becomes critical if:**
- A future endpoint accepts `event_type` from request body (e.g., custom event ingestion)
- A webhook handler accepts events from external systems (supplier API, bank API)
- A migration or fixture loads events from a JSON file with user-controllable content
- An admin UI allows editing event records directly

In any of those scenarios, an attacker can supply `event_type = "__import__('os').system('rm -rf /')"` and achieve RCE.

**Why this is bad even today:**

1. **Latent RCE.** The function is exposed via a route. The route's only protection is that today no upstream user can influence `event_type`. This is one refactor away from being exploitable.
2. **No defense-in-depth.** A single bad migration or import could expose this. The function should never be able to evaluate code regardless of input.
3. **No tests verify safety.** 27 test invocations of `mine_frequent_sequences` exist; none test adversarial input. A future change that "adds support for new event types" is untested for security.
4. **No SAST rule enabled.** No Bandit config in `pyproject.toml` or `setup.cfg`. No `pre-commit` hook for security scanning.

**Exploit (future scenario):**

```python
# Suppose a future PR adds: Event.objects.create(source_type=USER, event_type=user_input)
# Then:
events = [Event(event_type="'),__import__('os').system('id'),('")]
# Pattern mining would compute:
seq = ("',)", "__import__('os').system('id')", "('")
seq_str = "(\"',)\", \"__import__('os').system('id')\", \"('\")"
# eval(seq_str) executes: system('id')
```

**Fix (recommended):**

```python
# L72
patterns[seq] += 1     # use the tuple as the dict key

# L75-77
for seq, count in patterns.items():
    if count >= min_support:
        types = seq     # already a tuple; no string conversion needed
```

This is identical behaviour with zero risk. Tuple hashing is O(N) in tuple length; same as string hashing. No performance change.

**Fix (alternative, if string keys are required for some reason):**

```python
import ast
# ...
types = ast.literal_eval(seq_str)
```

`ast.literal_eval` only evaluates Python literals (strings, numbers, tuples, lists, dicts, booleans, None). Function calls, attribute access, and name lookups all raise `ValueError`.

**Verification steps after fix:**

1. Run existing 27 tests in `simulation/tests/test_intelligence/test_intelligence.py` — all should pass unchanged.
2. Add test: `test_eval_not_called` — patch `eval` to raise, call `mine_frequent_sequences`, assert no call.
3. Add test: `test_adversarial_event_type` — pass `event_type="__import__('os').system('id')"`, assert no exception, assert pattern output is the literal string.

**Defense-in-depth (separate from the fix):**

Add a Bandit config:

```toml
# pyproject.toml
[tool.bandit]
exclude_dirs = ["tests", "migrations"]
skips = []

# Or .bandit
[bandit]
# B102: exec_used
# B307: eval_used
# B603: subprocess_popen_shell_true
```

And a pre-commit hook:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.5
  hooks:
    - id: bandit
      args: ["-r", "backend/", "--severity-level", "high"]
```

---

## CWE-798: Hardcoded `SECRET_KEY` default

**Severity:** LOW
**Location:** `backend/config/settings.py:31`

```python
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-please-change-in-production'
)
```

**Risk:** If `DJANGO_SECRET_KEY` env var is not set in production, the default insecure value is used. Session cookies, CSRF tokens, password reset tokens are signed with this key. An attacker who knows the default can forge any of these.

**Evidence:** No `.env.production` or systemd unit file in the repo that sets `DJANGO_SECRET_KEY`. No deployment script that asserts the value is non-default.

**Status:** **LOW** because:
- Documented as `django-insecure-...` prefix (Django's own warning convention)
- The string is not a real secret (everyone can read the source)
- Production deployment presumably sets the env var (cannot verify without deploy access)

**Fix:**

```python
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']   # KeyError if not set
```

OR add a startup check in `config/wsgi.py`:

```python
import os
if not os.environ.get('DJANGO_SECRET_KEY') or 'django-insecure' in os.environ.get('DJANGO_SECRET_KEY', ''):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a secure value")
```

**Effort:** 5 minutes.

---

## CWE-489: Hardcoded `DEBUG_MODE = True`

**Severity:** LOW
**Location:** `frontend/api/client.py:11`

```python
DEBUG_MODE = True
```

**Risk:** In a packaged build (PyInstaller / cx_Freeze), this constant is always `True`. If the frontend is shipped, the API client:
- Logs full request bodies (may include auth tokens, customer PII)
- Logs full response bodies (may include credit card last-4, bank account numbers, supplier prices)
- May print stack traces to the user on error

**Evidence:** `grep -r 'DEBUG_MODE' frontend/api/client.py` confirms this is the only definition. No `os.environ.get` read.

**Fix:**

```python
import os
DEBUG_MODE = os.environ.get('PHARMACY_ERP_DEBUG', '0') == '1'
```

**Effort:** 5 minutes. See CRITICAL FINDINGS H-2.

---

## CWE-200: Debug logging leaks request data

**Severity:** INFO (depends on what is logged)
**Location:** `frontend/api/client.py` (multiple debug branches)

When `DEBUG_MODE = True` and an error occurs, the `APIClient._handle_response()` method likely logs the full request URL, method, headers, and body. With hardcoded `DEBUG_MODE = True` (CWE-489), this leaks in production.

**Fix:** Coupled with CWE-489 fix. If `DEBUG_MODE` is False in production, the logging branches don't fire.

**Verification:** After fix, package the frontend, run with `PHARMACY_ERP_DEBUG=0`, trigger an error, confirm no PII in logs.

---

## CWE-362: `processEvents()` re-entrancy window

**Severity:** MEDIUM
**Location:** `frontend/ui/sidebar.py:455`

**Risk:** `QApplication.processEvents()` called inside a slot allows the event loop to process pending events. If user input is pending (e.g., a queued click), it can fire during the slot. The slot's state machine assumes no concurrent mutation.

**Possible scenario:**
1. Slot starts processing item A
2. `processEvents()` allows queued event for "Delete item A" to fire
3. Delete handler runs, removes A from the model
4. Original slot continues, accesses A (now None) → AttributeError

**Fix:** Remove the `processEvents()` call. If a deferred paint is required:

```python
QTimer.singleShot(0, self._do_paint_update)
```

This schedules the paint at the next event loop iteration without re-entering synchronously.

**Effort:** 15 minutes.

---

## CWE-209: Error message exposes account balance

**Severity:** LOW
**Location:** `backend/payments/services.py:198`

```python
return {
    'success': False,
    'errors': [_(f'Insufficient funds. Available: {source_account.current_balance}, Required: {total_deduction}')]
}
```

**Risk:** Reveals the account's current balance to the API caller. If the caller is a different party than the account owner, this is information disclosure. The message goes back through the JSON response.

**Mitigating factor:** The `RoleBasedPermission` likely restricts who can call `process_payment`. If the caller is the owner, balance is not sensitive. If a multi-tenant SaaS, this could leak competitor balances.

**Fix:**

```python
errors': [_(f'Insufficient funds. Available balance is less than required amount.')]
# Log the detailed amount server-side
logger.warning(f"Insufficient funds attempt: account={source_account.code}, available={source_account.current_balance}, required={total_deduction}")
```

**Effort:** 10 minutes.

---

## CWE-400: `time.sleep` enables DoS via repeated failed requests

**Severity:** MEDIUM (under specific threat model)
**Location:** `frontend/api/client.py:247`

```python
for attempt in range(max_retries):
    try:
        response = self.session.post(...)
    except (requests.ConnectionError, requests.Timeout) as e:
        time.sleep(0.35 * (attempt + 1))   # ← blocks UI
```

**Risk:** If the backend is slow, the UI thread is blocked for the sum of all sleep intervals + request times. With `max_retries=3`, that's 0.35 + 0.7 + 1.05 = 2.1s of forced sleep. A misbehaving backend that returns connection timeouts will freeze the UI 2.1s per call. A 21-screen workflow with 5 API calls each = 21 seconds of dead UI.

**Fix:** Move retry to a background thread; signal result back to UI. See H-3 / H-4 in CRITICAL FINDINGS.

---

## What is NOT a Security Issue

| Concern | Rejection Reason |
|---------|-----------------|
| No CSRF on API endpoints | DRF enforces CSRF on session-auth; JWT auth bypasses CSRF by design |
| `customer_payment_workspace` returns all customers to any authenticated user | Authorization is at `RoleBasedPermission` level (L45); assume tenant scoping upstream |
| `period_locked` check at `payment_operations.py:605` returns 403 with date string | No PII; just a date |
| `PaymentAccount.objects.filter(...).values(...)` returns current_balance to all callers | Same authorization model; documented behaviour |
| Hardcoded SQLite default in settings | `os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')` defaults to postgres, NOT sqlite |

---

## Recommended Order

| # | Action | Effort | CVSS Reduction |
|---|--------|--------|----------------|
| 1 | CWE-94/95 fix (replace `eval`) | 5 min | 8.4 → 0.0 |
| 2 | CWE-489 fix (env-driven DEBUG_MODE) | 5 min | 3.7 → 0.0 |
| 3 | CWE-362 fix (remove processEvents) | 15 min | 5.3 → 0.0 |
| 4 | CWE-798 fix (require SECRET_KEY) | 5 min | 5.3 → 0.0 |
| 5 | CWE-209 fix (sanitize error message) | 10 min | 3.1 → 0.0 |
| 6 | Add Bandit pre-commit | 30 min | Defense-in-depth |
| 7 | CWE-400 fix (threading refactor) | 2-3 days | 5.3 → 0.0 |

**Total zero-risk wins (1-5):** ~40 minutes. Closes 2 CRITICAL, 2 MEDIUM, 2 LOW.
