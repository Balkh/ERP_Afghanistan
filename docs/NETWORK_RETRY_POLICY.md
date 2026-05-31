# Network Retry Policy — Pharmacy ERP API Client

**Effective:** Performance Stabilization Sprint V1  
**Module:** `frontend/api/client.py`

## Principles

1. **Fail fast on HTTP semantics** — The server responded; retrying the same request will not fix a 404 or 500.
2. **Retry only transport failures** — Connection drops, timeouts, and chunked-encoding errors may succeed on retry.
3. **Background fetches** — Intelligence workers use `background=True` (no global loading overlay).

## Retry matrix

| Condition | Retry? | Max attempts (default `retries=3`) |
|-----------|--------|----------------------------------|
| `ConnectionError`, `Timeout`, `ChunkedEncodingError` | Yes | 3 |
| Other `requests.RequestException` without status | Yes | 3 |
| HTTP **400–599** (`APIError` with `status_code`) | **No** | 1 (immediate return) |
| JSON body `success: false` | **No** | 1 |

## Removed behavior (Sprint V1)

- **No retry loop on HTTP 500** (previously retried up to 3× → ~24–30s UI freeze).
- **No `QApplication.processEvents()` during retry** on HTTP errors.

## Caller guidance

| Use case | Parameters |
|----------|------------|
| Foreground list/form load | `get(url)` default |
| Dashboard / Control Center thread | `get(url, background=True, retries=2)` |
| Workflow / Correlation workers | `background=True`, `retries=2` |
| User-critical save | `post()` — no automatic retry (unchanged) |

## User-visible errors

- Foreground: toast via `_show_error_toast`.
- Background: caller shows inline error state (Workflow/Correlation screens).

## Future (Sprint 2)

- Optional `Retry-After` for 503 with explicit config flag.
- Centralized circuit breaker for `/api/workflows/instances/` when consistently 500.
