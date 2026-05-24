# UI Thread Blocking Map - Phase 38

## Overview
This map identifies operations that execute on the main UI thread and cause interface freezing. 

## Classification Legend
- **CRITICAL**: Freezes UI or blocks event loop (> 1s).
- **HIGH**: Delays UI interaction (> 500ms).
- **MEDIUM**: Indirect blocking via chained calls.
- **LOW**: Background-safe but inefficient.

---

## Identified Blocking Operations

### 1. System Integrity Scan
- **File**: `frontend/ui/system/integrity_screen.py`
- **Function**: `IntegrityTestThread.run()`
- **Type**: `time.sleep(0.5)`
- **Severity**: **MEDIUM**
- **Context**: Worker Thread (Already off-loaded).
- **Analysis**: Uses `time.sleep` inside a `QThread`. This is safe for the UI thread but inefficient for the worker.

### 2. Startup Session Validation
- **File**: `frontend/main.py`
- **Function**: `check_session_valid()`
- **Type**: Synchronous `requests.get()`
- **Severity**: **HIGH**
- **Context**: **Main UI Thread (Startup)**
- **Analysis**: Performs a network call with a 3-second timeout before the `MainWindow` is even created. This blocks the initial application launch.

### 3. Startup Company Settings Loading
- **File**: `frontend/ui/main_window.py`
- **Function**: `_load_company_settings()`
- **Type**: Synchronous `api_client.get()`
- **Severity**: **HIGH**
- **Context**: **Main UI Thread (Constructor)**
- **Analysis**: Blocks the UI during `MainWindow` initialization to fetch company metadata.

### 4. API Client Retries
- **File**: `frontend/api/client.py`
- **Function**: `APIClient.get()`
- **Type**: `QApplication.processEvents()` in a retry loop.
- **Severity**: **MEDIUM**
- **Context**: **Main UI Thread**
- **Analysis**: While `processEvents()` prevents total freezing, it can lead to re-entrancy bugs and jittery UI during network instability.

### 5. Control Center Refresh
- **File**: `frontend/ui/control_tower/dashboard.py`
- **Function**: `_refresh()`
- **Type**: Multiple synchronous API calls (`get_snapshot`, `list_workflows`).
- **Severity**: **HIGH**
- **Context**: **Main UI Thread (Timer)**
- **Analysis**: Executed every 30 seconds. If the backend is slow, the entire UI freezes while fetching dashboard metrics.

### 6. License Periodic Validation
- **File**: `frontend/license/license_validator.py`
- **Function**: `_periodic_validation()`
- **Type**: Synchronous file I/O and RSA verification.
- **Severity**: **MEDIUM**
- **Context**: **Main UI Thread (QTimer)**
- **Analysis**: RSA signature verification is CPU-intensive. Executing it on the UI thread can cause noticeable micro-stutters.

### 7. Auth Manager Login (Misleading async)
- **File**: `frontend/security/auth_manager.py`
- **Function**: `login()`
- **Type**: Synchronous `api_client.post()` inside an `async` def.
- **Severity**: **CRITICAL**
- **Context**: **Main UI Thread**
- **Analysis**: The function is marked `async` but performs a blocking `requests.post()` via `api_client`. Since no `await` is used for the network call, it blocks the event loop.

---

## Summary of Risk
The most critical risks are the **Dashboard refresh** and **Startup session checks** which directly impact the perceived stability and responsiveness of the ERP under real-world network conditions.
