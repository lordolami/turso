# Self-hosted synchronization, CDC, and subscriptions

## Standalone meaning

The installation is the server endpoint for authorized clients. Clients keep local databases, perform local work, and exchange updates with this server. They are not cluster members, do not participate in server leader election, and do not turn the product into a distributed SQL database.

No Turso Cloud account is required for this product's endpoint. Client libraries remain separate packages with a documented server/protocol/dialect compatibility matrix.

## Upstream integration points

The inspected CLI sync implementation supports a single database and a directory-backed multi-database mode. Its routes include /v2/pipeline, /pull-updates, and database-prefixed equivalents. sync/engine/src/server_proto.rs defines page encodings, revision fields, protocol identity, incremental/replace-base behavior, batch requests, and logical-log range metadata. sync/engine/src/client_proto.rs defines logical replay frames and client identity fields.

The local reference server has finite handle admission, synchronous request handling, and a single-generation restriction in an MVCC logical pull path. It is not the finished secure multi-user product service. The Go server provides authenticated routing and admission, while a pinned native protocol bridge handles encoding/replay where appropriate. Do not duplicate private log formats in Go without versioned compatibility tests.

## Client and revision identity

Persist client ID, principal/credential identity, database ID, generation ID, protocol version, last acknowledged server revision, last submitted operation sequence, bootstrap state, and retention deadline. An offset is not globally unique across checkpoints/restores. Every revision carries or resolves a generation and format identity.

Restoring/replacing a server generation invalidates old cursors explicitly. A client receives replace_base_required or generation_changed with a supported rebootstrap path. Never interpret an old cursor against a new file that happens to have the same path or slug.

## Authentication and authorization

Check database connect and sync permissions for every operation. For physical pages or native log downloads, require authority to receive the entire database generation. A table-limited credential cannot safely receive pages that also contain other tables. Query-selected bootstrap is a transfer optimization and not proof of row isolation.

Credentials can be revoked while clients are offline. Recheck on reconnect and continuation. Revocation cannot erase plaintext already legitimately downloaded to a client device; document that limit. A new client cannot select a different database by forging its namespace, Host header, origin client ID, or revision.

## Bootstrap

1. Authorize and choose a stable snapshot/generation.
2. Negotiate supported dialect, protocol, encodings, and format versions.
3. Produce a bootstrap manifest with required size/hash/revision information.
4. Transfer the full snapshot, a configured prefix, or pages selected through a supported query bootstrap.
5. Keep immutable snapshot references alive until completion/expiry.
6. Resume through an opaque bootstrap cursor and verify chunk integrity.
7. Register the client's initial acknowledged revision only after successful bootstrap completion.

Sparse clients fetch missing pages against the same snapshot identity. The service must not mix pages from unrelated snapshots because a later request arrives after checkpoint. Expired snapshots trigger rebootstrap, not silent partial success.

## Push and pull

Push validates client identity, sequence/receipt, generation, authorization, transaction boundaries, sizes, and supported schema operations. Apply a logical transaction once under its durable identity; an application catalog receipt alone does not provide atomic deduplication with the target database. Record the corresponding target-database receipt in the same native commit or implement an equivalent proved mechanism.

Restricted uploads must replay through the same resolved native action checks as SQL, including indirect effects. Reject opaque physical/native mutations when the decoder cannot prove their allowed effects; a native-byte upload is not a permission bypass. A format requiring physical replacement can be used only with explicit full-generation replacement authority and full integrity/identity validation. Direct SQLite-file imports follow that same whole-generation rule, rather than treating a table-scoped data.import grant as authority over every table in a file.

Pull returns only complete committed changes from a retained revision. Keep long-poll workers and output buffers bounded. Disconnect ends the request; it does not discard a committed push. Preserve transaction order and provide an explicit acknowledgement protocol so retry/replay is deterministic.

Use the documented last-push-wins semantics for the compatible sync path, with clear constraint/schema failure behavior. Do not describe it as conflict-free distributed SQL or promise arbitrary custom conflict strategies without implementation. A pull that reapplies pending local work must preserve the native engine's atomic rollback-and-replay behavior.

Compatible client SDKs also retain the upstream mutation transform facility where implemented: a client callback sees typed before/after/update information and returns keep, skip, or a parameterized rewrite. The [official client guide](https://turso.tech/blog/building-local-first-apps-the-complete-guide-to-offline-first-database-sync) documents the last-push-wins default and transform approach. The native sync engine contains apply_transformation paths, but that does not prove every language binding exposes them. Qualify the Go client bridge and publish a binding-by-binding matrix. Transformed statements still require normal server authorization and constraints. No arbitrary callback uploaded through MCP executes as server-side OS code. Test update/delete conflicts, NULL primary keys, rowid shadowing, schema changes, callback failures, retries, and pull-time replay; a last-push-wins label alone does not settle every edge case.

Client-local synchronized files must be owned exclusively by the sync SDK. Opening them simultaneously with an ordinary embedded connection or external SQLite tool can checkpoint/change the WAL and invalidate sync revision assumptions. Server-managed files remain owned by the server manager; client SDK ownership rules do not require the server to use a client-local file as its authoritative store.

## PostgreSQL synchronization boundary

The current SQLite-oriented sync path is not proof that PostgreSQL schema text, attached schema bundles, types, and native session behavior can be replayed correctly. PostgreSQL sync remains a required integration obligation with a capability gate: preserve dialect at bootstrap and replay, cover schemas/types/DDL/arrays/materialized views, and verify against the PostgreSQL frontend. Exposing bytes through the same HTTP route does not establish correctness.

Legacy libSQL embedded-replica semantics also remain distinct from local-first Turso Sync. Advertise each only for a provider/protocol combination that is actually implemented and tested.

## CDC completeness

CDC is configured per connection upstream. The managed session factory must install the required capture mode before any user statement executes. Protect internal capture tables and generation/revision metadata from unauthorized mutation. Capture records for a transaction become visible to subscribers only after commit; rollback emits no committed changes.

Platform history and user subscriptions are separate consumers. CDC does not replace complete WAL/MVCC archival. Do not include secret bind values or unrelated tables in a principal's change stream merely because a database-wide CDC table exists.

## Subscription contract

A subscription binds principal, database generation, authorized object set, filter/query definition, schema/policy epoch, resume cursor, and limits. Results may be database change events or supported live query changes; report which capability is used.

Provide monotonically ordered event IDs within the declared stream, transaction grouping, bounded queue length, retention expiry, heartbeat/liveness behavior, and explicit overflow/resync_required. Do not silently drop changes while claiming a complete stream. A slow consumer is disconnected or moved to a resumable retained cursor according to policy.

Schema changes can invalidate a filter/query; publish schema_changed and require revalidation. Credential revocation terminates future delivery. A generation replacement terminates old subscriptions and describes how to subscribe again.

## Cleanup and diagnostics

Expose client bootstrap/revision state, pending transfers, last push/pull times, traffic, retained-history floor, queue pressure, and checkpoint status. Never expose another principal's raw credential or document values through diagnostics. Retention cleanup respects active bootstrap, snapshot, restore, and client references, with an explicit maximum client retention policy to prevent unbounded storage.
