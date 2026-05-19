# Event Bus — Architecture Freeze Governance

## Status: LOCKED — FINALIZED

The Event System is **infrastructure, not a product**.
It is intentionally frozen. No architectural changes permitted.

## System Role

The Event Bus exists ONLY for:
1. Safe signal propagation
2. Lightweight module decoupling
3. Non-blocking observability
4. Audit-friendly traceability
5. Controlled business notifications

It is NOT responsible for:
- Business correctness
- Transaction coordination
- Distributed consistency
- Async workflow orchestration
- Core accounting/inventory integrity

## Hard Rules

### 1. Keep Monolithic Stability
- NO split into microservices
- NO distributed brokers (Kafka, RabbitMQ)
- NO external event infrastructure
- NO mandatory message queue dependency

### 2. Keep Event Bus Lightweight
- NO persistence-heavy queues
- NO retry orchestration engines
- NO workflow runtimes inside bus
- NO scheduling engines

### 3. Keep Event Flow Shallow
- `MAX_EVENT_DEPTH = 2` — never increase
- Events exceeding depth are either buffered (financial) or dropped (non-critical)
- Never create recursive event chains (A → B → A)

### 4. Keep Payloads Small
- Flat metadata only — no ORM objects, no binary
- Max 10KB payload — enforced at envelope build
- No nested relational graphs
- Payloads include `checksum` for integrity verification

### 5. Keep Fail-Open Design
- Event failures must NEVER rollback accounting
- Event failures must NEVER block API responses
- Event failures must NEVER block UI or inventory operations
- ERP core flow always wins — event bus is optional infrastructure

### 6. Handler Isolation
- Handlers must be stateless, isolated, lightweight
- No cross-module imports beyond `logging` and `core.events`
- No ORM queries, no API calls, no heavy computations
- No triggering of FINANCIAL_CRITICAL events from handlers
- Failures are caught, logged, and buffered — never propagated

### 7. Deterministic Envelope
Every event envelope MUST contain:
- `event_id` — unique UUID
- `correlation_id` — traces event chain
- `event_type` — category enum
- `priority` — integer priority
- `name` — event name
- `timestamp` — dispatch time
- `depth` — recursion depth
- `payload` — flat metadata dict
- `checksum` — `sha256(payload)[:16]`

### 8. Replay is Debug-Only
- Replay is NEVER automatic
- Replay is NEVER transactional
- Replay is NEVER business-authoritative
- Only triggered via management command (`replay_events --limit`)

## Forbidden Patterns

- **Event Bus as transaction coordinator** — accounting integrity belongs in services + DB transactions
- **Event Bus as permission engine** — RBAC is handled by security middleware
- **Event Bus as validation engine** — input validation belongs in serializers
- **Large objects in payloads** — no ORM models, no file content
- **Recursive event chains** — depth guard prevents infinite loops
- **Blocking API for event processing** — dispatch is synchronous but must be <2ms
- **Config/ENV-based architecture switching** — no broker/celery toggle

## Performance Contract

| Metric | Guarantee |
|---|---|
| Dispatch overhead | < 2ms |
| API latency increase | < 3% |
| Memory growth | Bounded (deques with maxlen) |
| Blocking IO in dispatch | Zero |
| Event storms | Impossible (depth=2, ring buffer) |

## Future Changes

Only permitted for:
- Bug fixes
- Security patches
- Performance optimizations (without architectural change)

Rejected if they:
- Increase complexity
- Add hidden coupling
- Increase dispatch latency
- Introduce distributed behavior
- Require new dependencies

## Ownership

- Event Bus code: `core/events/` — all files
- Governance violations: reject in code review
- This document: update only when explicitly directed by architecture decision

## Final Word

> *"The Event System is now infrastructure. It should become boring, predictable, stable, fast, and rarely changed. That is the definition of a successful enterprise infrastructure layer."*
