# Source evidence and complete upstream table inventory

This audit is fixed to upstream commit `017ea183c2a323a66d515448e4df464b6181bb36`. Each record below links to an immutable source location. The machine-readable records include SHA-256 hashes of the local audited files. Source inspection establishes implementation facts and gaps; it does not establish a passed runtime test.

The [complete extracted compatibility-table inventory](contracts/upstream-capabilities.json) preserves every status-bearing row from both upstream compatibility documents, with dialect, section, headers, notes, original text, and immutable line link. This covers individual SQL statements, expressions, functions, C APIs, opcodes, types, extensions, and PostgreSQL feature rows rather than substituting a short marketing feature list. Upstream prose qualifications still apply. In particular, declarations and optimistic compatibility rows can disagree with implementation stubs; the inspected source wins.

The [product capability matrix](capability-matrix.md) maps these engine facilities to the standalone product. Unsupported upstream features are recorded as gaps, not advertised as existing product support. The required product capabilities remain governed by [scope](product-scope.md) and [decisions](decisions.md).

## Inspected implementation boundaries

| Record | Source | Observation |
|---|---|---|
| SRC-001 | [core/dialect/mod.rs:28](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/dialect/mod.rs#L28) | Dialect abstraction owns parsing and frontend-dependent behavior. |
| SRC-002 | [core/database.rs:1099](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/database.rs#L1099) | The registry rejects opening an existing database with a different dialect. |
| SRC-003 | [postgres/frontend/session.rs:46](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/frontend/session.rs#L46) | The PostgreSQL frontend opens a real PostgresDialect database. |
| SRC-004 | [postgres/frontend/session.rs:1001](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/frontend/session.rs#L1001) | PostgreSQL namespaces may use separate schema files. |
| SRC-005 | [postgres/server/lib.rs:29](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/server/lib.rs#L29) | The bundled wire server does not provide the platform authentication boundary. |
| SRC-006 | [postgres/server/lib.rs:46](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/server/lib.rs#L46) | The sample server stores a shared PostgreSQL connection; product sessions require isolation. |
| SRC-007 | [postgres/frontend/auth_functions.rs:62](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/frontend/auth_functions.rs#L62) | SQL settings supply auth helper claims and cannot be trusted as platform principal identity. |
| SRC-008 | [postgres/COMPAT.md:8](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/postgres/COMPAT.md#L8) | PostgreSQL compatibility is explicitly partial; syntax acceptance is not semantic completeness. |
| SRC-009 | [bindings/go/go.mod:8](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/bindings/go/go.mod#L8) | The existing Go binding uses a dynamic native integration dependency. |
| SRC-010 | [bindings/go/driver_db.go:140](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/bindings/go/driver_db.go#L140) | Existing transaction handling is reference code to audit rather than an assumed product contract. |
| SRC-011 | [sdk-kit/src/rsapi.rs:24](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sdk-kit/src/rsapi.rs#L24) | The inspected SDK open path chooses the SQLite dialect. |
| SRC-012 | [sdk-kit/turso.h:27](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sdk-kit/turso.h#L27) | The native status set includes statuses the product must map explicitly. |
| SRC-013 | [sdk-kit/Cargo.toml:19](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sdk-kit/Cargo.toml#L19) | The SDK declares a static archive target; combined product linking still needs qualification. |
| SRC-014 | [sync/sdk-kit/Cargo.toml:16](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sync/sdk-kit/Cargo.toml#L16) | The sync SDK can build a native static archive. |
| SRC-015 | [bindings/c/src/lib.rs:1027](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/bindings/c/src/lib.rs#L1027) | The C authorizer is unimplemented and returns an error. |
| SRC-016 | [bindings/c/src/lib.rs:1977](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/bindings/c/src/lib.rs#L1977) | SQLite backup API entry points are stubs in the audited C binding. |
| SRC-017 | [core/connection_hooks.rs:8](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/connection_hooks.rs#L8) | Connection hooks are not a resolved native authorization mechanism. |
| SRC-018 | [core/storage/wal.rs:58](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/storage/wal.rs#L58) | Physical WAL/checkpoint code must participate in retained-history integration. |
| SRC-019 | [core/mvcc/persistent_storage/logical_log.rs:10](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/mvcc/persistent_storage/logical_log.rs#L10) | MVCC logical-log checkpoint/truncation ordering differs from the page WAL path. |
| SRC-020 | [core/cdc.rs:14](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/cdc.rs#L14) | CDC capture modes exist; all-connection management and retention remain product work. |
| SRC-021 | [cli/sync_server.rs:48](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/cli/sync_server.rs#L48) | The bundled sync server supports bounded directory-based database handles. |
| SRC-022 | [cli/sync_server.rs:271](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/cli/sync_server.rs#L271) | Self-hosted sync route primitives exist in the CLI server. |
| SRC-023 | [sync/engine/src/database_replay_generator.rs:27](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sync/engine/src/database_replay_generator.rs#L27) | Client replay has SQLite identity semantics that require explicit frontend qualification. |
| SRC-024 | [sync/engine/src/database_sync_engine.rs:21](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sync/engine/src/database_sync_engine.rs#L21) | Client transformation hooks support keep, skip, and rewrite paths; SDK exposure must be qualified separately. |
| SRC-025 | [cli/mcp_server.rs:270](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/cli/mcp_server.rs#L270) | A CLI MCP implementation exists but does not supply full platform operation parity. |
| SRC-026 | [sdk-kit/README.md:12](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/sdk-kit/README.md#L12) | Page codecs transform bytes and do not alone provide complete COW filesystem semantics. |
| SRC-027 | [core/Cargo.toml:59](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/core/Cargo.toml#L59) | FTS is an optional native dependency with packaging and footprint implications. |
| SRC-028 | [Cargo.toml:192](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/Cargo.toml#L192) | The release profile aborts on panic; catch_unwind cannot promise recovery from it. |
| SRC-029 | [COMPAT.md:704](https://github.com/tursodatabase/turso/blob/017ea183c2a323a66d515448e4df464b6181bb36/COMPAT.md#L704) | The compatibility inventory must be checked against actual source implementation. |

## Evidence limits

The audit followed the engine, frontend, SDK, durability, sync, and CLI entry points and the repository's contributor/agent guides. It does not claim every source line in this large repository was read. The compatibility inventory preserves upstream assertions, including limitations, without treating them as our own executed conformance results. External sources are listed separately in the JSON and are not covered by local source hashes. The upstream revision predates the proposed product contracts; none of the new Mira interfaces is attributed to upstream.
