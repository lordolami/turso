# Upstream source audit

## Provenance

- Repository: [tursodatabase/turso](https://github.com/tursodatabase/turso).
- Existing user fork: [lordolami/turso](https://github.com/lordolami/turso), verified as a fork of that upstream.
- Audited revision: **017ea183c2a323a66d515448e4df464b6181bb36**, committed **2026-10-28T09:55:00Z**.
- Documentation branch: **codex/standalone-platform-docs**, based on the fetched upstream revision, without changing the existing fork's main branch.
- Application status: no Mira application implementation was present in the initial workspace. This change adds the specification and its validation artifacts.

Immutable line-level references and source hashes are maintained in [source-evidence.md](source-evidence.md) and [source-evidence.json](contracts/source-evidence.json). References below are repository-relative and refer to the audited revision.

## Findings that determine the design

| Evidence | Observed source behavior | Consequence |
|---|---|---|
| SRC-DIALECT | core/dialect/mod.rs and core/database.rs fix a dialect at database open and reject registry opens with another dialect | Persist provider/dialect in the catalog; do not promise interchangeable frontends on the same file |
| SRC-PG-OPEN | postgres/frontend/session.rs selects PostgresDialect and enables MVCC | Native integration must invoke the PostgreSQL frontend's open/session paths, not the generic SQLite Go driver |
| SRC-GO-OPEN | sdk-kit/src/rsapi.rs constructs SqliteDialect; bindings/go/driver_db.go uses that SDK | Adding a PostgreSQL network decoder around sql.Open("turso", ...) would not supply PostgreSQL semantics |
| SRC-STATIC | sdk-kit/Cargo.toml and sync/sdk-kit/Cargo.toml offer staticlib outputs | A static native integration is possible in principle, but the product's combined bridge and platform builds still need implementation |
| SRC-PG-LIB | postgres/frontend and postgres/server are Rust libraries without the proposed product C ABI | Add a narrow C ABI for PostgreSQL sessions and values; keep network policy and product lifecycle in Go |
| SRC-PG-SERVER | postgres/server/lib.rs shares one PgConnection through Arc<Mutex<_>>, uses NoopHandler at startup, and passes no TLS acceptor | Treat this server as a protocol reference, not a production multi-user endpoint ready to embed unchanged |
| SRC-AUTHORIZER | bindings/c/src/lib.rs explicitly returns SQLITE_ERROR for sqlite3_set_authorizer because core has no prepare-time hook | Implement engine-level resolved-operation authorization before exposing restricted SQL credentials |
| SRC-BACKUP | bindings/c/src/lib.rs has stub sqlite3_backup_* functions | Do not design recovery around an already-working SQLite backup API |
| SRC-MVCC | core/mvcc/persistent_storage/logical_log.rs documents logical-log truncation after checkpoint and distinct durability ordering | PITR needs native archive integration before history is discarded; a Go file watcher is insufficient |
| SRC-SYNC | cli/sync_server.rs has directory mode, namespace validation, pipeline and pull routes, finite open handles, and synchronous connection handling | Reuse protocol knowledge; replace admission, authentication, session ownership, retention, and lifecycle behavior |
| SRC-SYNC-GEN | the local sync server accepts only one logical generation in a relevant MVCC pull path | Restore, checkpoint generation transitions, and stale-client behavior require explicit implementation |
| SRC-MCP | cli/mcp_server.rs exposes a small SQLite tool set over stdio with one current connection | Build the product MCP server from the application operation registry; do not equate upstream MCP with full platform administration |
| SRC-FEATURES | default core feature flags differ from the CLI's flags; FTS is optional | The native build must record enabled compile-time features and runtime experimental flags |
| SRC-PG-FILES | PostgreSQL schema creation uses attached database files and a derived path | Treat a PG logical database as a file bundle; contain paths and coordinate backup/restore across its schema files |

## Engine and compiler structure

SQLite SQL is parsed under sqlite/parser and compiled by core/translate into the VDBE program executed under core/vdbe. Storage uses SQLite-compatible pages, B-trees, a pager, WAL coordination, and optional MVCC. The Dialect trait is an extensibility boundary for parsing, persisted schema interpretation, functions, and dialect-specific behavior; it is not an unrestricted Go plugin interface.

The PostgreSQL parser uses libpg_query, translates its parse tree to Turso's AST, and executes through the engine. postgres/frontend supplies additional session and catalog behavior. postgres/server speaks pgwire. The CLI's documentation explicitly says it does not generate SQLite SQL text as an intermediate language. Our design preserves this native path.

## Go binding audit

The Go module is turso.tech/database/tursogo. The checked-out bindings use purego and the platform-libs loader rather than cgo. The platform-libs dependency is pinned in bindings/go/go.mod; it must not be assumed to contain the same current native implementation merely because the Go source was updated.

The normal driver creates an engine database holder on each driver connection open; core has its own process-wide file registry. The product still needs a process-owned manager to control lifecycle, idle eviction, active references, database generations, budgets, and policy state. database/sql alone is not that manager.

PrepareContext prepares and finalizes a native statement to count parameters, then stores the SQL. Exec-family code can iterate over multiple statements and binds the supplied arguments only to the first statement. BeginTx ignores driver transaction options and issues BEGIN. These observations mean the product must define stricter query and transaction contracts rather than silently inheriting all driver choices.

The current native C header includes status values such as BUSY_SNAPSHOT and IOERR; the Go status enum inspected is a smaller set. The structs currently include page_codec/open_flags in both relevant sources, so this audit does not claim a demonstrated struct-offset mismatch. ABI validation still needs to compare generated headers, sizes, offsets, enum values, and actual linked versions.

## PostgreSQL audit

The compatibility reference is [postgres/COMPAT.md](../../postgres/COMPAT.md), not the marketing phrase PostgreSQL-compatible by itself. Supported syntax and protocol coverage are incomplete. Authentication, GRANT/REVOKE, PostgreSQL role enforcement, native RLS, logical replication, and many extension/server features are absent at this revision. Native catalog entries with hardcoded roles are not an authorization system.

Shared-session behavior in the reference wire server can leak parameters and transaction state between network clients. The product uses an independent native PgConnection for each logical client session. Platform identity is trusted out-of-band state; SQL-modifiable settings such as request.jwt.claims cannot establish identity or grant access.

COPY FROM a server filename can access the host filesystem through the frontend. Remote SQL principals must not get arbitrary file access. Operator-managed imports stage files under the installation and authorize a specific file handle or import object. The same policy applies to ATTACH, CSV virtual tables, extensions, and other file-capable functions.

## Durability, snapshots, and synchronization audit

The standard page-WAL path and MVCC path have different logs and checkpoint rules. The engine uses .db-wal and, in MVCC, .db-log; experimental multiprocess coordination can add .tshm. Older agent-guide passages about only WAL, one writer, or no multiprocess support are narrower or stale relative to current source and COMPAT. Source and dedicated mode-specific tests take precedence over those summaries.

CDC is configured per connection and records selected changes. It is not, by itself, a complete physical backup, a transactionally complete history of every DDL effect, or a proof that all connections were captured. The product must own connection creation and install its history/change requirements before executing user statements.

Sync partial page selection is a bandwidth optimization, not a row-level security boundary. A page can contain data outside the query that originally selected it. Raw-page or raw-log synchronization therefore requires permission to receive the whole database generation. Table-restricted principals use logical authorized queries/subscriptions, not physical page downloads.

The reference sync code is useful and more capable than a single-file demo: it has directory mode and multi-database routing. It still does not provide the product's complete security, admission, durable generation management, or interface parity. These are concrete integration tasks, not configuration flags.

## Existing cloud and libSQL claims

Turso Cloud provisioning, hosted recovery, managed durability, organization billing, and cloud networking are not automatically exported by linking this repository. They are excluded or, where a local equivalent is in scope, implemented as our own standalone service.

libSQL is a separate SQLite fork. Its FTS5/R*Tree/extension and indexed-vector claims cannot be assigned to the new Turso engine indiscriminately. [Capability matrix](capability-matrix.md) separates current Turso features, native integration gaps, and any required legacy compatibility work. No automatic fallback changes a database provider or file semantics.

## What this audit establishes

This is source-level evidence for architectural decisions. It establishes paths, APIs, current declarations, explicit stubs, and implementation gaps at one commit. It does not establish measured binary size, memory usage, security of a future server, cross-platform static-link success, or passing runtime compatibility. Those have separate [acceptance criteria](testing-and-acceptance.md).
