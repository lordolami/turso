# Database lifecycle and resource ownership

## Resource states

~~~text
creating -> ready -> draining -> deleting -> trashed -> purging -> purged
creating -> failed
ready -> restoring -> ready (new generation)
ready -> migrating -> ready
ready -> unavailable -> ready after successful recovery
~~~

Every transition has an operation ID, catalog revision, expected generation, audit identity, and durable job where file work is involved. Failed jobs preserve enough diagnostics to reconcile or retry safely. A database record does not become ready merely because its directory exists.

## Creation

Input: organization/group, name/slug, provider, dialect, persistence mode, experimental options, encryption reference, template or snapshot seed, and optional operator quota settings. Provider/dialect are validated before reservation.

Authorize database.create, reserve name/ID and expected storage budget, commit a creating record and job, create a contained staging bundle, initialize native database/schema under the selected dialect, verify identity and required features, close/flush native handles, publish its generation, and mark ready. A retry with the same idempotency key returns the same database or job. A collision with another requested payload returns idempotency_conflict.

For in-memory databases, specify persistence=memory explicitly. Their identity/catalog metadata may persist, but content is lost on process exit. They cannot claim durable PITR or restart recovery. Refuse incompatible backup/history promises rather than inventing empty successful artifacts.

The history enabled-by-default setting applies only to capable persistent databases. Creating an in-memory database does not fail merely because that installation default is enabled; its effective capability/policy disables durable retained history and reports why. An explicit request requiring durable in-memory recovery is rejected. A supported one-time export of live memory contents remains distinct from restart durability.

## Database handle manager

Key handles by instance ID, database ID, generation ID, provider, dialect, encryption configuration digest, and native options digest. Opening is a single-flight operation: concurrent requests wait for one open attempt, not several competing file locks.

A handle entry stores open state, native database handle, connection count, active statements, pinned jobs, cache estimate, last-use monotonic time, policy/schema epochs, and the close reason. Do not hold the registry mutex while waiting for disk I/O, native open, or another session to finish.

Entry states are closed, opening, open, evicting, and failed_with_retry_after. Opening and eviction carry a generation counter to prevent an old completion from replacing a newer handle. Failure backoff applies to a resource, not every database on the server.

## Admission and eviction

1. Authorize and resolve catalog identity without opening the data file.
2. Reserve request and native-memory budgets.
3. Reuse or open the correct generation.
4. Create/acquire an independent connection whose policy is suitable for the principal.
5. Register a reference before exposing it to the caller.
6. Release references in a guaranteed cleanup path.

Evict only idle, unreferenced entries. A transaction, portal, query cursor, snapshot/history task, or sync operation pins its generation. Mark an eviction candidate first; new acquisitions either cancel eviction safely or wait for it to finish. Eviction finalizes all cached statements, closes connections, flushes required state, releases native database references, and updates accounting. If no entry is evictable, return an actionable capacity error or bounded wait.

Finite active-handle limits are essential for supporting a large catalog. The upstream sync handle map refuses opens after its configured capacity and has no general product idle-eviction policy; replace that behavior through this manager.

## Connection isolation

Never multiplex different principals through a native connection without a complete tested reset. Prefer principal-bound sessions. PostgreSQL sessions each own their PgConnection, prepared-statement/portal map, settings, authentication context, cancellation identity, and transaction state.

The pool key includes privilege/policy and generation identity. Returning a connection requires rollback of incomplete transactions, statement/portal cleanup, reset of temporary/session state, native policy replacement, and generation/schema checks. If any reset step fails, close the connection. A pool must not convert a database's dialect.

## Rename, configuration, and migrations

Renaming affects catalog display/routing labels and requires optimistic revision matching. Resource IDs and underlying paths stay stable. Changing block_reads/block_writes updates policy epochs and stops admitting newly forbidden operations. Deletion protection guards destructive lifecycle operations even for a role that can otherwise delete; an owner can change that setting through the explicit configuration operation.

Journal mode, encryption configuration, native experimental flags, or storage format changes may require draining connections and opening a new generation. They cannot be applied by silently changing a DSN in a shared pool. User SQL cannot bypass these product settings with a PRAGMA or frontend-specific command.

Migration records include dialect, exact source checksum, template/schema version, expected predecessor, applied outcome, and job ID. Execute migration work under a database schema lock and native authorization. On dialects/operations without full transactional DDL behavior, preserve the partial-failure state and recovery instructions. A group migration is a set of per-database results, not an atomic transaction across databases.

## Delete and recovery

Authorize, check deletion protection, record intent, stop new sessions, and drain/cancel active sessions according to the requested deadline. Close native handles before moving the bundle to trash. Keep database identity, manifests, key references, and recovery expiry in the catalog. Reuse of a deleted slug must not change the identity of existing tokens or recovery records.

Restore from trash is a new lifecycle job with explicit name-conflict handling and generation verification. Purge requires purge permission and cannot remove objects referenced by another branch/backup. Expired trash cleanup follows the same reference checks.

## Crash reconciliation

| Crash boundary | Required restart action |
|---|---|
| Intent committed, staging absent | Recreate staging or mark a retriable failure |
| Staging incomplete | Verify/clean only that job's contained files; keep old generation intact |
| Artifact published, catalog unfinished | Verify manifest and roll forward catalog publication |
| Catalog active generation changed, old bundle retained | Resume cleanup only after verifying live references |
| Delete draining interrupted | Reestablish policy block, reconcile sessions, finish deletion or report failure |
| Purge interrupted | Continue deleting unreferenced objects idempotently |

Instance restart invalidates ephemeral sessions and cursors. Durable jobs are recovered with a new in-process lease epoch. A job's attempt counter is not permission to repeat an uncertain SQL commit.
