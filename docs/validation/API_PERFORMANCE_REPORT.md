# API Performance Report

Django test client, 20 iterations per endpoint.

## `/api/workflows/instances/`

- Timing: | min 2367.63 | max 3224.95 | avg **2639.48** | p95 2619.44 | samples: [2367.63, 2461.01, 2524.39, 2619.44, 3224.95] |
- Payload bytes: | min 179.0 | max 179.0 | avg **179.0** | p95 179.0 | samples: [179.0, 179.0, 179.0, 179.0, 179.0] |
- Error rate: 0.0
- Status distribution: `{'200': 5}`

## `/api/control-center/hub-bundle/`

- Timing: | min 2475.85 | max 2744.63 | avg **2570.26** | p95 2570.87 | samples: [2475.85, 2501.84, 2558.09, 2570.87, 2744.63] |
- Payload bytes: | min 12898.0 | max 12908.0 | avg **12901.2** | p95 12901.0 | samples: [12898.0, 12899.0, 12900.0, 12901.0, 12908.0] |
- Error rate: 0.0
- Status distribution: `{'200': 5}`

## `/api/accounting/journal-entries/?limit=50`

- Timing: | min 2368.62 | max 2805.06 | avg **2530.94** | p95 2602.44 | samples: [2368.62, 2387.05, 2491.54, 2602.44, 2805.06] |
- Payload bytes: | min 22059.0 | max 22059.0 | avg **22059.0** | p95 22059.0 | samples: [22059.0, 22059.0, 22059.0, 22059.0, 22059.0] |
- Error rate: 0.0
- Status distribution: `{'200': 5}`

## `/api/sales/invoices/?limit=50`

- Timing: | min 2197.02 | max 2642.5 | avg **2433.9** | p95 2522.14 | samples: [2197.02, 2356.35, 2451.47, 2522.14, 2642.5] |
- Payload bytes: | min 179.0 | max 179.0 | avg **179.0** | p95 179.0 | samples: [179.0, 179.0, 179.0, 179.0, 179.0] |
- Error rate: 0.0
- Status distribution: `{'200': 5}`

