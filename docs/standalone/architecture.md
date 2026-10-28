# System architecture

## Responsibilities

Go owns the executable entry point, configuration, listeners, platform catalog, accounts, authorization management, database handle manager, operation services, jobs, metrics, audit, HTTP API, PostgreSQL wire endpoint, MCP server/proxy, CLI, and dashboard delivery. A compiled native bridge owns Turso database objects, SQLite/PG frontend sessions, statement execution, storage integration, and the native enforcement points required for policy/history.

The browser UI is compiled to static assets and embedded in the Go executable. No application dependency downloads are required at runtime. The browser is the operator's existing browser. Native engine libraries are build inputs, not an additional user-installed database daemon.

~~~mermaid
flowchart TD
  UI[Browser dashboard] --> HTTP[Go HTTP adapter]
  CLI[CLI] --> LOCAL[Authenticated local control transport]
  MCP[MCP HTTP or stdio proxy] --> APP[Application services]
  HTTP --> APP
  LOCAL --> APP
  PG[PostgreSQL clients] --> WIRE[Go pgwire adapter]
  WIRE --> APP
  APP --> POLICY[Identity and authorization]
  APP --> CAT[Private platform catalog]
  APP --> JOB[Durable local jobs]
  APP --> MGR[Database and generation manager]
  MGR --> ABI[Versioned native bridge]
  ABI --> SQL[SQLite frontend]
  ABI --> PSQL[PostgreSQL frontend]
  SQL --> ENGINE[Turso execution and storage]
  PSQL --> ENGINE
  ENGINE --> FILES[Local generation files and history]
~~~

## Proposed source organization

These directories are proposed; this documentation change does not create an application skeleton.

~~~text
product/
  go.mod
  cmd/mira/
  internal/app/               configuration and lifecycle composition
  internal/catalog/           private metadata transactions and migrations
  internal/auth/              identity, credentials, sessions, key references
  internal/policy/            grants, compiled native policy, policy epochs
  internal/database/          IDs, generations, handles, admission, sessions
  internal/query/             typed parameters/results and transaction contracts
  internal/schema/            introspection, DDL, templates, migrations
  internal/history/           manifests, snapshots, retained commit history
  internal/recovery/          restore validation and generation replacement
  internal/sync/              authorized protocol orchestration and cursors
  internal/changes/           CDC publication and subscriptions
  internal/jobs/              durable single-process worker scheduler
  internal/metrics/           bounded statistics and diagnostics
  internal/audit/             attributed operation records
  internal/operations/        canonical service registry and contracts
  internal/transport/http/
  internal/transport/postgres/
  internal/transport/mcp/
  internal/transport/control/ Unix socket or Windows named pipe
  internal/ui/                embedded dashboard and help assets
  native/mira-engine/         minimal native API extensions and build integration
  native/include/             generated, versioned public C headers
  sdk/go/                    embedding/client adapter, distributed separately
  web/                       dashboard source and locked build dependencies
~~~

Keep upstream engine files in their existing locations. Generic authorization/history hooks belong in core; dialect semantics stay in the Dialect boundary and postgres/frontend. Do not place user, organization, HTTP, MCP, or platform billing concepts in engine storage code. This follows the upstream [agent guidelines](../../AGENTS.md).

## Single operation path

1. A transport validates message framing, size, type schema, and supported protocol version.
2. Authentication yields a trusted principal and credential identifier.
3. The operation registry resolves the requested application operation.
4. Authorization checks organization/resource visibility and required actions.
5. Input revision/idempotency checks precede side effects.
6. Admission reserves the relevant global, principal, and database budgets.
7. The service loads the catalog record and acquires the intended generation reference.
8. Native statements execute with an immutable compiled policy and generation identity.
9. Results are bounded and encoded; long operations create durable jobs.
10. Audit/metrics record outcome and commit certainty without leaking secret payloads.
11. References and budget reservations are released on success, failure, cancellation, and transport disconnect.

Adapters do not reimplement database creation or policy. A PostgreSQL message can involve several internal service calls but still shares the same database manager, principal, policy, and audit context. Cached statements include generation, dialect, native ABI, schema, and policy versions.

## Ownership and concurrency

There is one process owner for an installation directory. An OS lock prevents a second Mira server from opening it concurrently. CLI and stdio MCP connect to that owner; they do not open managed database files in helper processes. The native multiprocess feature remains an explicitly experimental engine capability, not the platform's ownership mechanism.

The catalog is private to application services. User SQL cannot ATTACH it or reference its tables. It has a bounded pool and an explicit migration version. Managed database sessions are independent native connections. One session serializes statement/I/O operations. Different sessions can execute concurrently subject to the engine's mode and the shared scheduler.

Long-lived transactions, open portals, result cursors, snapshots, and sync jobs retain generation references. Idle eviction applies only after references are released. No native pointer is used after generation closure; no deadline handler frees a statement while another thread is stepping it.

## Startup state machine

~~~text
unconfigured -> setup_available -> initializing -> opening_catalog
opening_catalog -> migrating_catalog -> reconciling_files -> starting_services -> ready
any startup state -> failed_with_diagnostics
ready -> draining -> closing -> stopped
~~~

- Validate configuration and resolve canonical data paths before any listener accepts user operations.
- Acquire the instance lock; read the instance identity and storage/catalog format versions.
- Refuse a newer unsupported catalog or storage version; never attempt an implicit destructive downgrade.
- Initialize native ABI, verify build manifest and required symbols, and run bounded self-checks.
- Open/migrate the catalog with a recoverable migration journal.
- Reconcile incomplete lifecycle jobs and generation manifests.
- Recover relevant history state before acknowledging new writes to a database that requires archival durability.
- Initialize identity/policy state; establish a local control endpoint whose access is tied to the operating-system account and application credential.
- Bind listeners only after configuration, authorization, and certificate checks succeed.
- Readiness becomes true after services can admit operations, not merely after a TCP socket opens.

First-owner setup listens on loopback and uses a one-time random bootstrap secret written to a protected local setup file. Successful setup consumes it atomically. A remote request cannot win a race to become owner. A local setup CLI can complete the same operation without a browser.

## Graceful shutdown

Mark the instance draining, reject new sessions/jobs that require continuing execution, and allow bounded in-flight work to finish. Cancel remaining statement execution through the native interrupt mechanism, wait for workers to relinquish handles, roll back incomplete transactions, flush required history/audit records, and checkpoint only under the storage contract. Close generation handles, catalog handles, listeners, and the process lock in that order. An OS termination during shutdown is handled by recovery, not by assuming cleanup always runs.

An owner-authorized MCP/API shutdown operation first creates and acknowledges a shutdown job. It must not terminate the response before recording whether shutdown was scheduled. The stdio proxy exits after its streams terminate; it does not automatically stop the database server.

## Feature reporting

Compute capabilities from linked native build features, dialect, per-database experimental flags, configured services, and implemented bridge operations. Report current capability state with reason codes. Examples include available, experimental_opt_in, bridge_missing, unsupported_dialect, disabled_by_operator, and verification_pending. A hidden button is not a sufficient unsupported-feature contract; APIs and MCP return the same reason.

## Architecture invariants

- No commercial database-count cap.
- One physical file bundle has one owning database identity and one immutable dialect.
- Every public path authenticates and authorizes before engine access.
- Every user connection observes required policy and change/history setup.
- Engine sessions and data directories are never shared accidentally across principals.
- A restore invalidates stale generation-bound sessions explicitly.
- Local process failure cannot turn a partially completed lifecycle job into an apparently complete database.
- Cloud and multi-machine coordination code are absent from this design.
