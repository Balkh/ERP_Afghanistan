# Hub Bundle Validation

## HTTP timing (Django test client, 10 iterations)

| min 2403.8 | max 2830.81 | avg **2617.41** | p95 2796.1 | samples: [2403.8, 2494.3, 2562.03, 2796.1, 2830.81] |

## Payload size (bytes)

| min 237.0 | max 13083.0 | avg **6637.5** | p95 13052.0 | samples: [237.0, 237.0, 237.0, 237.0, 237.0, 13005.0, 13014.0, 13036.0, 13052.0, 13083.0] |

## Keys

- Expected: `['health', 'stats', 'intelligence', 'signals', 'jobs', 'financial', 'inventory', 'operations', 'workflow_instances', 'workflows_pending', 'correlation_sources']`
- Missing observed: `[]`
- **keys_valid:** True

## View function timing

{'count': 5, 'min_ms': 0.17, 'max_ms': 1.3, 'avg_ms': 0.49, 'p95_ms': 0.53, 'samples_ms': [0.17, 0.2, 0.24, 0.53, 1.3]}

## Duplicate data check

```json
{
  "verified": false,
  "reason": "status_403"
}
```
