# Verification and acceptance specification

## Evidence levels

Keep these levels distinct: proposed behavior, source-inspected behavior, unit-tested behavior, integration-tested behavior, platform-qualified behavior, and measured production behavior. This documentation change supplies the first two levels plus documentation/contract checks recorded in [validation-report.md](validation-report.md). It does not supply an implemented Mira server.

The requirements registry assigns an owning document and acceptance obligation to every requirement. The operations registry defines the entire public service surface. Neither a passing documentation checker nor a successful native compile proves the product's runtime correctness.

## Mandatory acceptance matrix

| Area | Minimum test obligations |
|---|---|
| Setup | Local bootstrap only; two competing setup requests; consumed/expired token; failed initialization; no owner takeover after restart |
| Installation lock | Second server refuses ownership; CLI/MCP proxy attaches to owner; stale metadata does not bypass active OS lock |
| Catalog | Schema migrations, FK behavior, optimistic revisions, duplicate names, checksum mismatch, restart after partial migration |
| Database creation | Persistent/memory; both dialects; each create crash boundary; same-key retry; different-payload idempotency conflict |
| Database count | Many cataloged/mostly dormant databases without an artificial vendor cap; bounded active handles with idle eviction |
| Lifecycle | Rename without moving identity; block reads/writes; deletion protection; drain; trash restore; purge; slug reuse |
| Native ABI | Version/size/offset/enum checks; unknown flags/status; stale handles; allocation ownership; callbacks; repeated lifetime stress |
| Native I/O | Yield during open/prepare/step/finalize; no missing rows; no duplicate side effects; bounded cancellation and cleanup |
| SQLite | Existing upstream conformance plus product bridge values, transactions, resource limits, policy, and history |
| PostgreSQL | Actual PG frontend use; independent sessions; dialect mismatches; types/arrays/decimal; SQLSTATE; simple/extended protocol |
| PG authentication | Password/SCRAM or selected method; TLS; wrong database/user; expired/revoked credential; malformed startup/cancel packets |
| PG sessions | Search_path/custom settings/sequence values/portals/transactions isolated across concurrent clients |
| Query | Exact parameter binding, one-statement mode, explicit script behavior, large values, int64 precision, result cursors, deadlines |
| Transactions | Snapshot/isolation claims; unsupported levels rejected; commit certainty; disconnect races; target-database receipts |
| Authorization | Direct/indirect effects, view/trigger/cascade, function/vtab/file access, prepared-plan invalidation, cross-principal reuse |
| Path security | Traversal, links/reparse points, device paths, schema names, COPY/ATTACH/CSV, upload/download IDs |
| Encryption | Native feature modes plus each artifact type; key loss; wrong key; archive/catalog/FTS coverage; restart/restore |
| Migrations | Checksum/predecessor checks, per-database schema lock, transactional and partial-failure cases, group result accounting |
| Search | Exact vector oracle; selected index oracle and recall contract; FTS query/tokenizer behavior; indexing while writes occur |
| Snapshots | WAL/MVCC independently; live write boundaries; PG schema bundles; FTS artifacts; encrypted data |
| History | Complete committed transaction boundaries, fsync/archive ordering, log truncation, checkpoint generations, history gaps |
| Branching | Independent writes; true COW object sharing; parent deletion; reference GC; historical revision correctness |
| PITR | Before/at/after commit targets; incomplete/corrupt archives; missing keys; replace versus restore-as-new; session invalidation |
| Backups | Interrupted writes, completed-marker ordering, checksums, schedules/timezones, retention references, restore verification |
| Sync | Bootstrap/push/pull; reconnect/dedup; sparse pages; conflicts; generation changes; offline revoke; WAL/MVCC transitions |
| Sync security | Database-wide physical permission, page selector does not isolate rows, foreign namespace/Host/revision rejection |
| CDC/subscriptions | Every connection captured; rollback excluded; commit order; filter authorization; overflow; resume expiry; revoke |
| Jobs | Restart reconciliation, safe cancellation, bounded retries, uncertain commit handling, lease epoch and result retention |
| Audit | Interface/actor attribution, redaction, incomplete operation state, no secret values in diagnostics |
| HTTP/CLI/MCP parity | Every declared operation, same permission/effect/error/revision/idempotency behavior across interfaces |
| MCP protocol | Negotiated protocol versions, schema discovery, input/output validation, pagination, error classes, transport cancellation |
| MCP authority | Owner agent completes all workflows; restricted agent cannot bypass through query, file, job, or resource interfaces |
| Dashboard | End-to-end operations, context changes, typed data, stale generation, empty/error states, accessibility/keyboard flows |
| Performance | Combined binary/RSS/native memory, dormant databases, active cache budgets, fairness, backpressure, long-running stability |
| Release | Offline startup, dependency inspection, OS/filesystem/client matrix, upgrades, rollback boundaries, license notices |

## Existing upstream harnesses

Use the narrowest applicable upstream harness and preserve imported oracles:

~~~text
make -C sqlite/conformance run-rust ARGS='--snapshot-filter __never__'
make -C postgres/conformance run
make -C postgres/conformance run-postgres
cargo test -p core_tester --test leak_tests
~~~

These are upstream development commands, not commands run successfully by this documentation change. PostgreSQL comparison requires a real reference server or its documented Docker harness. Do not alter pristine upstream .sql/.out files merely to make the fork pass.

Core native changes add regressions to existing SQL/integration/simulator harnesses and run required formatting/lint checks for the files actually changed. The Go application additionally needs service, transport, FFI lifetime, loader/extraction, and end-to-end tests; any optional cgo adapter receives its own qualification. Race detectors do not automatically observe every native race; use native sanitizers/instrumentation where supported.

## Failure injection

Inject disk-full, short writes, fsync failures, corrupt/truncated frames, delayed I/O, process termination, network disconnect, expired credentials, stale generations, stalled clients, allocation failures, and clock jumps for schedules/expiry. Kill at every durable lifecycle and history boundary. Check post-restart invariants against a reference state and record whether the last operation committed, rolled back, or is unresolved.

Test permission changes while statements are prepared, stepping, yielding, producing rows, committing, queued as jobs, or resuming sync. Authorization correctness is not established by testing only direct table SELECTs.

## Generated interface checks

For every operation registry entry, verify method/path and input schema, permission and scope binding, MCP name/annotations, CLI invocation, capability gating, response schema, secret redaction, idempotency contract, job semantics, and audit events. A transport-only upload framing endpoint may be a protocol binding around a registry operation; explain such exceptions explicitly rather than omitting the feature from MCP.

## Release evidence bundle

Store native revision/patches, Go and native toolchain versions, enabled features, executable digest, dependency/SBOM/license inventory, capability matrix, conformance outcomes, failure-injection results, performance data, client/OS/filesystem qualification, and upgrade/restore results. Known failures are part of the evidence. Advertising a capability requires its declared acceptance obligations to be satisfied.
