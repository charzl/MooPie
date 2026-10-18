# Test organization and scope

| Level | Location | Verified behavior |
| --- | --- | --- |
| Python unit | `apps/python/tests/unit` | Symbol validation, NaN/int64 conversion, candle merging, averages, repeatable fixture |
| Python integration | `apps/python/tests/integration` | Official SDK handshake, quotes and pushes, candles, reconnect, entitlement failures, UI filtering/selection/rendering, stale session protection, worker shutdown |
| Packaged smoke | `scripts/smoke-app.py` | Launch the actual `.app` executable, import Python SDK, render a valid PNG |
| Performance | `scripts/benchmark-app.py` | Three repetitions of the same fixture/workload; SDK-loaded startup, idle/replay CPU/RSS, update+snapshot timing |

Shared local protobuf test peer: `tests/support/mock_opend.py`. It binds only `127.0.0.1`, uses an ephemeral port, requires no credentials, and communicates with the official Python SDK. It intentionally fragments headers and coalesces a request reply with a push. Its synthetic wire messages follow the official SDK protobuf schema. It is not a substitute for a real OpenD/account acceptance test.

## Commands

Option-chain coverage includes inclusive date ranges, calendar-month boundaries, 30-day request windows, configurable underlying/type, cancellation during rate-limit waits, deduplicated contract identities and CSV/JSON export. Official SDK integration uses option expiration/chain protobuf replies from the local peer, checks transmitted date windows and PUT filters, and surfaces entitlement errors. UI integration checks numeric strike sorting, expiry filtering/export, stale-session rejection and background responsiveness. Python CI also builds and installs the wheel and checks both command-line entry points. Real logged-in OpenD checks remain local, separate from synthetic CI fixtures.

```sh
cd apps/python
python3 -m unittest discover -s tests/unit -v
python3 -m unittest discover -s tests/integration -v
```

CI stops packaging when any functional test fails. Package smoke tests must also pass before uploading artifacts. Performance measurements record fixture hashes, viewport dimensions and workload settings. CPU uses process user+system CPU time divided by phase wall time, where 100% means one core. RSS is externally sampled every 250 ms. UI timing is offscreen update+snapshot time, not display FPS or end-to-end network latency.

Current limits: no production OpenD authentication/permissions acceptance test, no trading/order tests, no screen-reader/accessibility audit or long-duration soak test. Those are required before treating the app as a complete replacement for the official desktop client. No real credentials belong in test fixtures or CI.

## Bundled OpenD / updater

Python user-data coverage: `test_account_data.py` checks exact 64-bit account identity, explicit environment/currency, unknown-account rejection and context cleanup on error. `test_user_data.py` checks official watchlist import beyond 30 symbols, name persistence, stale responses, account-page navigation, cleared stale assets and background-thread responsiveness. The real SDK integration suite also reads synthetic official watchlist/account/funds/position protobuf replies and asserts it sends no unlock or place-order protocol. Credentials and real account data never enter these fixtures. Local read-only acceptance has additionally succeeded against a logged-in official OpenD; this is not a CI login or trade-execution test.

`apps/python/tests/unit/test_opend_manager.py` covers numeric version ordering, untrusted redirects/path injection, the official fallback, atomic version selection, validation-failure preservation, rollback, downgrade rejection, installation locking and compatibility with existing version selections. The updater is part of the Python application; it needs no separate compiler or helper binary. `scripts/smoke-opend.py` exercises the packaged application's `opend` command in an isolated installation store, validates the genuine publisher-signed gateway, rejects wrong versions and tampered signatures, and starts its GUI for five seconds without credentials. It stops only its own process. The macOS packaging workflow runs these checks; they do not assert account login or quote delivery. The lightweight installer contains OpenD download metadata and installs the official gateway separately.

`UpdateAcceptanceTests` is an explicitly enabled network acceptance test: it downloads the genuine latest official archive, mounts its GUI DMG, verifies publisher/version/architecture, installs and atomically selects it in a temporary store, reuses the cached signed candidate, and verifies a failed rollback leaves it selected. It never logs in. The macOS packaging workflow enables it with `MOOMOO_OPEND_UPDATE_ACCEPTANCE=1`; ordinary local unit runs skip the ~400MB download.

## CI resolution and installers

`tests/unit/test_upstream_resolution.py` covers matched upgrades, unchanged hashes, pinned pull-request builds, downgrade and incompatible-version rejection, untrusted URLs/version injection, yanked distributions and malformed hashes. The packaged executable exposes `--sdk-check`, validating the actual SDK against embedded build metadata. `scripts/package-dmg.py` creates, checksum-verifies and mounts each DMG, checks the Applications shortcut, both bundle signatures and embedded SDK/OpenD identity. Release publication depends on packaging and report validation; a draft becomes public only after the installer and provenance/checksums are uploaded.

`tests/unit/test_release_publication.py` tests release preflight and draft publication independently of GitHub: missing/corrupt/invalid containers, mismatched source/version/architecture, absent signature and real-startup evidence, failed uploads, missing or incorrect-size uploaded assets, refusal to overwrite public releases, and the successful publication sequence. Both Linux CI validation jobs discover this suite. Each mounted DMG produces a `.validation.json` report bound to its SHA-256 and size; publication rechecks those bytes and identities before contacting GitHub. These mocked unit tests verify gating logic; real mount/signature/startup checks run separately in the macOS packaging workflow.

```sh
python3 -m unittest discover -s tests/unit -v
```
