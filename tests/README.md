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

## Bundled OpenD / updater

Python user-data coverage: `test_account_data.py` checks exact 64-bit account identity, explicit environment/currency, unknown-account rejection and context cleanup on error. `test_user_data.py` checks official watchlist import beyond 30 symbols, name persistence, stale responses, account-page navigation, cleared stale assets and background-thread responsiveness. The real SDK integration suite also reads synthetic official watchlist/account/funds/position protobuf replies and asserts it sends no unlock or place-order protocol. Credentials and real account data never enter these fixtures. Local read-only acceptance has additionally succeeded against a logged-in official OpenD; this is not a CI login or trade-execution test.

`runtime/Tests/OpenDRuntimeTests` contains separate native unit tests for numeric version ordering, untrusted redirects/path injection, the official fallback, atomic version selection, validation-failure preservation, rollback, downgrade rejection and cross-client update locking. `scripts/smoke-opend.py` verifies the bundled real publisher-signed OpenD, boots an isolated runtime store, checks wrong-version rejection, starts the official GUI executable for five seconds without credentials, stops only that owned process, and rejects a subsequently tampered signature. Both packaging jobs run these checks. It does not assert account login or quote delivery. The fixture-driven UI benchmark deliberately does not start OpenD; only disk measurements include the newly bundled gateway.

`UpdateAcceptanceTests` is an explicitly enabled network acceptance test: it downloads the genuine latest official archive, mounts its GUI DMG, verifies publisher/version/architecture, installs and atomically selects it in a temporary store, reuses the cached signed candidate, and verifies a failed rollback leaves it selected. It never logs in. Both macOS jobs enable it with `MOOMOO_OPEND_UPDATE_ACCEPTANCE=1`; ordinary local unit runs skip the ~400MB download.

## CI resolution and installers

`tests/unit/test_upstream_resolution.py` covers matched upgrades, unchanged hashes, pinned pull-request builds, downgrade and incompatible-version rejection, untrusted URLs/version injection, yanked distributions and malformed hashes. Both packaged executables expose `--sdk-check`, validating the actual SDK against embedded build metadata. `scripts/package-dmg.py` creates, checksum-verifies and mounts each DMG, checks the Applications shortcut, both bundle signatures and embedded SDK/OpenD identity. Release publication depends on both packaging jobs and report validation; a draft becomes public only after both installers and provenance/checksums are uploaded.

`tests/unit/test_release_publication.py` tests release preflight and draft publication independently of GitHub: missing/corrupt/invalid containers, mismatched source/version/architecture, absent signature and real-startup evidence, failed uploads, missing or incorrect-size uploaded assets, refusal to overwrite public releases, and the successful publication sequence. Both Linux CI validation jobs discover this suite. Each mounted DMG produces a `.validation.json` report bound to its SHA-256 and size; publication rechecks those bytes and identities before contacting GitHub. These mocked unit tests verify gating logic; real mount/signature/startup checks run separately on both Mac jobs.

```sh
python3 -m unittest discover -s tests/unit -v
```
