# Full-scope implementation workstreams

These workstreams organize dependencies for the complete agreed standalone product. They are not a reduced-feature first version, and none adds NoSQL, managed cloud, distributed clustering, sharding, or billing.

## Dependency graph

~~~mermaid
flowchart TD
  S[Scope and source audit] --> B[Static native bridge and capability model]
  B --> A[Native authorization and identity context]
  B --> H[Native history and snapshot integration]
  B --> P[PostgreSQL frontend bridge]
  A --> D[Catalog, database manager, query services]
  P --> D
  H --> R[Branches, backups, PITR, generation recovery]
  D --> R
  D --> Y[Sync, CDC, subscriptions]
  R --> Y
  D --> O[Canonical operation registry]
  O --> I[HTTP, CLI, MCP, dashboard]
  Y --> I
  R --> I
  I --> Q[Full acceptance and platform qualification]
~~~

## W1: Repository and native dependency discipline

Maintain origin fork/upstream remotes, pin audited revisions, preserve licenses, record patches, and separate native engine changes from Go product code. Add the proposed combined native bridge without forking existing SQL parser semantics into Go. Generate version/feature/format manifests and ABI layout checks. Complete per-platform static-link qualification.

Outputs: build graph, generated header, combined native archive, cgo adapter, build manifest, native ownership tests. Acceptance: BUILD and native TEST requirements.

## W2: PostgreSQL as a first-class integration

Expose actual PgConnection operations through the ABI. Preserve dialect identity, schema-file manifests, exact values and SQLSTATE. Implement independent client sessions and a Go wire adapter with supported authentication/TLS/cancellation. Define supported client/protocol matrix and refuse unavailable features. Persist/reconcile PostgreSQL schema mappings across new sessions/restarts; the current connection-local ATTACH mechanism requires explicit review and integration.

Outputs: PG ABI/session manager, wire service, safe schema namespace/file resolver, compatibility matrix, client conformance results. Acceptance: PG-001..006.

## W3: Trust and native policy

Implement platform principals, credentials, local setup, memberships, grants, revocation epochs, local control transport, and encryption references. Add generic resolved-action enforcement to core and the native bridge. Include views/triggers/cascades/functions/vtabs/files and re-preparation. Keep PostgreSQL-specific role/session behavior outside core.

Outputs: identity/policy catalog, native policy compiler/hook, trust-context API, transport authentication, audit/redaction. Acceptance: AUTH, AUTHZ, and SEC requirements. Do not expose restricted SQL credentials before this boundary is tested.

## W4: Catalog and multi-database lifecycle

Implement catalog migrations and durable operation intents, UUID resource addressing, generation manifests, single-owner installation lock, lazy handles, per-session connections, pin/ref accounting, bounded admission, idle eviction, trash/purge/recovery, and restart reconciliation. Preserve no vendor database-count cap.

Outputs: catalog implementation, database/generation manager, job scheduler, idempotency semantics, active-resource metrics. Acceptance: DB, CAT, ORG, and relevant OPS requirements.

## W5: SQL, schema, data movement, and search

Implement typed queries/parameters/results, explicit transaction sessions, streaming/cursors, cancellation, script semantics, errors, schema inspection/DDL, templates, migrations, comparisons, import/export staging, supported function/type/index exposure, and extension policy. Add qualified vector indexing where the selected native provider lacks it; do not label roadmap code available. Keep FTS, arrays, and JSON SQL capabilities with accurate dialect status.

Outputs: application query/schema/search services, native capability bindings, typed contracts, client behavior tests. Acceptance: SQL, QUERY, SCHEMA, SEARCH, and DATA requirements.

## W6: History and consistent file bundles

Implement durable history hooks into WAL and MVCC commit/checkpoint paths, generation-aware revision indexes, a complete native snapshot API, PG multi-file coordination, extension/FTS artifact handling, immutable local objects, portable COW storage, manifest GC, encryption/key references, backup policies, PITR, and installation recovery.

Outputs: archive format, replay reader, native snapshot/COW interfaces, recovery/lifecycle integration, crash-injection proofs. Acceptance: HIST, BRANCH, and REC requirements. File watching, raw live-file copying, and CDC-only replay do not satisfy them.

## W7: Self-hosted sync and changes

Expose/reuse pinned sync protocol primitives, add authenticated multi-database routing through the manager, complete generation transitions and receipt/dedup behavior, bootstrap/sparse reads, bounded long polls, client retention, native dialect-preserving replay, managed all-connection CDC, and authorized subscriptions. Resolve the PostgreSQL and legacy-libSQL compatibility requirements explicitly.

Outputs: self-hosted sync service, client capability matrix, retention coordination, CDC/subscription APIs. Acceptance: SYNC and CHANGE requirements.

## W8: Full interface and agent parity

Implement canonical operation services and generate/validate their HTTP, CLI, and MCP bindings. Add the stdio proxy to the owner process, current/legacy MCP protocol support through the pinned SDK, typed discovery/results, resources/jobs/cancellation, and full owner authority. Build every dashboard screen against those same services, with capability/error states and accessibility.

Outputs: complete operation registry bindings, web assets embedded in the executable, CLI, MCP server/proxy, client examples. Acceptance: IFACE and MCP requirements. No manual confirmation requirement is introduced merely because the client is an agent.

## W9: Operation, resource efficiency, and release

Implement shared workers, fair admission, native+Go memory accounting, caches/handle eviction, metrics/query diagnostics/audit, local deployment/service helpers, configuration reload, graceful drain, catalog/native upgrades, and recovery runbooks. Qualify the full combined product under all declared features and supported platforms.

Outputs: reproducible release artifacts/evidence, measured footprint, full compatibility/performance/failure reports, operator documentation. Acceptance: OPS, BUILD, and TEST requirements.

## Definition of complete

Every scope requirement maps to implemented service/native behavior, declared interfaces, user documentation, capability reporting, failure behavior, and passed acceptance evidence. Every unresolved decision affecting correctness or the user promise is settled and recorded. The executable can be downloaded and used without a build toolchain, vendor account, or unmentioned runtime dependency. No feature is called complete because its UI or documentation exists alone.
