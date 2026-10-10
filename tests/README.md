# Test organization and scope

| Level | Location | Verified behavior |
| --- | --- | --- |
| Python unit | `apps/python/tests/unit` | Symbol validation, NaN/int64 conversion, candle merging, averages, repeatable fixture |
| Python integration | `apps/python/tests/integration` | Official SDK handshake, quotes and pushes, candles, reconnect, entitlement failures, UI filtering/selection/rendering, stale session protection, worker shutdown |
| Swift/C++ unit | `apps/swift-cpp/Tests/MooCoreTests` | SDK request validation, market identity, numeric conversion |
| Swift/C++ integration | `apps/swift-cpp/Tests/MooIntegrationTests` | Official SDK transport against a local protobuf peer, fragmented/coalesced replies, quote and candle pushes, reconnect, entitlement errors, UI model/rendering and disconnect |
| Packaged smoke | `scripts/smoke-app.py` | Launch the actual `.app` executable, import Python SDK, render a valid PNG |
| Performance | `scripts/benchmark-app.py` | Three repetitions of the same fixture/workload; SDK-loaded startup, idle/replay CPU/RSS, update+snapshot timing |

Shared local protobuf test peer: `tests/support/mock_opend.py`. It binds only `127.0.0.1`, uses an ephemeral port, requires no credentials, and communicates with the real official SDKs. It intentionally fragments headers and coalesces a request reply with a push. Its synthetic wire messages follow the vendored official protobuf schema. It is not a substitute for a real OpenD/account acceptance test.

## Commands

```sh
cd apps/python
python3 -m unittest discover -s tests/unit -v
python3 -m unittest discover -s tests/integration -v
```

```sh
swift test --package-path apps/swift-cpp --filter 'BridgeTests|MarketTests'
swift test --package-path apps/swift-cpp --filter SDKIntegrationTests
```

CI stops packaging when any functional test fails. Package smoke tests must also pass before uploading artifacts. Performance reports validate fixture hashes, viewport dimensions and workload settings before comparing metrics. CPU uses process user+system CPU time divided by phase wall time, where 100% means one core. RSS is externally sampled every 250 ms. UI timing is offscreen update+snapshot time, not display FPS or end-to-end network latency.

Current limits: no production OpenD authentication/permissions acceptance test, no trading/order tests, no screen-reader/accessibility audit or long-duration soak test. Those are required before treating the app as a complete replacement for the official desktop client. No real credentials belong in test fixtures or CI.
