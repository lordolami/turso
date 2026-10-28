# Resource management and lightweight operation

## Promise and measurement

The product targets PocketBase-like download-and-run simplicity and an efficient standalone footprint. This is not a measured claim of the same binary size, idle RSS, or throughput. The PostgreSQL grammar/frontend, FTS, encryption, native runtimes, and all required services have real size and memory costs.

Measure the actual combined executable and process. Go heap metrics alone omit native page caches, MVCC versions, extension allocations, and some thread stacks. A Go memory limit is not a whole-process/native memory limit.

Source-repository size is not a runtime measurement. A dependency fork, its examples, tests, and other language bindings do not automatically become part of the linked/embedded release. Conversely, importing a small Go wrapper still includes its selected native payload. Compare executable/download bytes, materialized library/cache bytes, cold and warm startup, idle RSS, active native memory, threads, and handles for the actual full feature set. Static linking and embedded-library loading must be evaluated by those same measures; neither is a synonym for lightweight.

## Many databases

Distinguish cataloged databases, open native database holders, live connections, active statements, active transactions, and pinned storage generations. A user can create many cataloged databases without keeping them all open. Database count has no vendor cap; ordinary hardware limits and optional owner policies still apply.

Lazy-open database handles, single-flight concurrent opens, evict idle unreferenced generations, and keep idle pools small or closed. Do not create a goroutine, native connection, page cache, or background checkpoint task for every dormant catalog entry. Maintenance discovers work through the shared scheduler.

## Budgets

| Budget | Accounting and enforcement |
|---|---|
| Process RSS | Observe OS process memory plus native allocation counters; admission responds before exhaustion |
| Go heap | Separate memory target and allocation profiling; do not mistake it for native usage |
| Native memory | Database caches, MVCC rows, statements, FTS, buffers, extension allocations |
| File descriptors/handles | Reserve for catalog, listeners, logs, control endpoint, and recovery; account for PG schema files/sidecars |
| Connections | Global and per-principal/database budgets; idle and transaction deadlines |
| Queries | Active execution slots plus bounded pending queue |
| Results | Row/value/encoded-byte/stream-buffer limits |
| History/storage | Retention references, free-space reserve, archive/backup growth, staged uploads |
| Background work | Separate bounded work class so backup/indexing does not starve query admission |
| Sync/subscriptions | Concurrent bootstrap, retained bytes, long polls, per-client queue and cursor retention |

Proposed config examples are defaults for implementation discussion, not evidence of capacity. Native counters are required for reliable whole-process control; if a counter is unavailable, report its estimate/coverage rather than presenting a precise false total.

## Scheduling

Use shared worker/admission pools with fairness across principals and databases. A large analytical query or index build cannot occupy every foreground slot indefinitely. Account for native execution and I/O time, not only time spent in Go. Connections serialize their own state; independent connections can proceed when the engine mode permits.

Queue waits honor request deadlines and cancellation. A full queue returns resource_exhausted with safe retry guidance. Native worker blocking does not create unlimited Go goroutines waiting on a single file. Background tasks checkpoint and yield at safe engine boundaries; throttling never splits a transaction into partially acknowledged work.

## Streaming and caches

Stream rows, imports, exports, backup objects, and diagnostic artifacts. Bound both compressed and uncompressed bytes. A stalled client eventually releases or expires its retained snapshot. Backpressure propagates to the producer without unbounded queues.

Cache policy includes per-database and global ceilings. Cache keys include generation, schema/policy revision, dialect, and native build identity where relevant. Invalidate or revalidate on restore/schema changes/revocation. FTS and vector indexes declare memory/storage costs and build jobs. Avoid caching every full query result or full raw SQL text indefinitely.

## Required benchmark matrix

Record cold start, warm start, setup completion, download/executable size, disk footprint, idle CPU/RSS, thread/handle counts, catalog list/create speed, and shutdown time. Test catalog sizes of 1, 100, 1,000, and 10,000 databases as workloads to measure, not advertised supported maxima. Vary active fractions independently.

Exercise SQLite and PostgreSQL with prepared/unprepared reads and writes; WAL versus MVCC; short versus long transactions; hot/cold caches; high conflict rates; mixed principal quotas; vector/FTS workloads; import/export; history enabled/disabled; snapshots/PITR; sync bootstrap; and dashboard/MCP activity. Measure p50/p95/p99 latency, throughput, native/Go memory, CPU, I/O, errors, and archive growth.

Run leak/stability checks over repeated database open/evict/close, PgConnection create/drop, statement cancellation, backup/restore, and subscription reconnect cycles. Idle memory must stabilize after GC/native release under the documented retention policy. A benchmark never trades away fsync/history guarantees or authorization to produce a better number.

## Acceptance reporting

Publish hardware, OS/filesystem, native revision, feature flags, configuration, dataset, client versions, and durability settings alongside results. Report failed cases and confidence limits. No fixed footprint or performance number is promised by this documentation-only change.
