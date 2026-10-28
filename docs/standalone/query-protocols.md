# Query execution and HTTP data protocol

## Scope and namespaces

Administrative operations use /api/v1. Data queries use /db/{database_id}/query and explicit session endpoints. A compatibility endpoint /db/{database_id}/v2/pipeline is provided only for client/protocol combinations covered by conformance tests. Existing client support is a tested capability, not inferred from a URL prefix.

The primary application result model is shared across HTTP, CLI, dashboard, and MCP. PostgreSQL uses its own wire encoding while preserving the same trusted principal, database identity, generation, authorization, cancellation, and accounting.

## Typed values

~~~json
{
  "sql": "SELECT id, name FROM customers WHERE id = ?",
  "parameters": [{"type": "integer", "value": "9223372036854775807"}],
  "mode": "read",
  "expected_generation_id": "019a0000-0000-7000-8000-000000000003",
  "max_rows": 100,
  "max_bytes": 1048576,
  "timeout_ms": 10000
}
~~~

This is a proposed HTTP body sent to /db/{database_id}/query; the route supplies database_id. Integers are decimal strings, not JSON floating-point numbers. Value tags distinguish null, integer, real, text, blob, numeric, json, array, and typed_text. Blobs are base64 encoded in JSON. Non-finite real values use NaN, +Infinity, and -Infinity strings and cannot become invalid JSON literals. PostgreSQL arrays carry element_type, dimensions, lower_bounds, and flattened typed elements; exact numeric text is preserved. Parameters are values only; object identifiers are validated/resolved separately.

Bindings must exactly match the prepared statement's parameter description. Reject missing/extra bindings and mixed named/positional ambiguity. The main query endpoint accepts one statement. An explicit script operation has separate script semantics, statement boundaries, and transaction policy. Do not inherit the Go driver's first-statement-only binding behavior for scripts.

The script endpoint is /db/{database_id}/script. Its statements array contains an individually prepared sql/parameters/mode object per statement, with atomic and failure_policy on the enclosing request. Atomic scripts require stop-on-error and use one target transaction; reject operations the dialect cannot execute transactionally. Non-atomic scripts report each committed/failed/skipped result and may continue only under the explicit continue policy. Reject transaction-control SQL that would conflict with the service-owned atomic transaction. Do not advertise a multi-statement script as one safely retryable write without a complete receipt strategy.

## Execution modes

| Mode | Contract |
|---|---|
| read | No writes or other forbidden effects through direct or indirect operations |
| write | Data mutations allowed only within granted actions; does not grant arbitrary DDL/file access |
| schema | Requested schema effects require schema permissions and a schema coordination lock |
| script | Explicit statement list; preflight each operation, define atomic/stop-on-error behavior, and report per-statement outcomes |

The mode is a requested maximum, not an assertion trusted from the client. Native resolved-action authorization determines actual effects. SELECT can invoke functions or virtual tables with side effects. EXPLAIN, PRAGMA, CTEs, triggers, and schema changes are classified by their real effects, not the leading text.

## Result envelope

~~~json
{
  "request_id": "019a0000-0000-7000-8000-000000000001",
  "query_id": "019a0000-0000-7000-8000-000000000004",
  "database_id": "019a0000-0000-7000-8000-000000000002",
  "generation_id": "019a0000-0000-7000-8000-000000000003",
  "columns": [{"name": "id", "type_name": "integer"}],
  "rows": [[{"type": "integer", "value": "42"}]],
  "affected_rows": "0",
  "commit_state": "not_started",
  "has_more": false,
  "cursor": null
}
~~~

Bounded synchronous results have maximum rows and encoded bytes. Larger results use streaming or an explicitly retained cursor. A cursor binds principal, database generation, schema/policy epoch, result snapshot, limits, and expiry. Paging a changing query by OFFSET is not a substitute for a retained snapshot cursor. If a snapshot expires or a restore changes generation, return cursor_expired/generation_changed and require a new query.

## Transaction sessions

Create a transaction session explicitly. Bind it to the credential/principal and database generation. Return an opaque random session token; store only its hash where practical. Requests on one session are serialized. Sessions have idle and absolute deadlines and retain one connection.

~~~text
idle -> transaction_open -> committed
transaction_open -> failed_transaction -> rolled_back
transaction_open -> rolled_back
any live session -> expired | revoked | generation_changed
~~~

An unsupported isolation level returns unsupported_isolation. Snapshot isolation is not called serializable. A timed-out or disconnected transaction is interrupted and rolled back after the worker confirms native state. A failed PostgreSQL transaction follows its failed-transaction semantics; do not return a healthy connection until rollback/reset completes.

## Cancellation and retry

Each active execution has a principal-bound execution ID. query.cancel can interrupt that execution only with owner or matching-session authority. Canceling a request after commit may return committed or unknown_commit_state. Never claim a canceled transport proves rollback.

Administrative mutations use idempotency records. For SQL writes, request receipts must be committed inside the same target-database transaction as the write to offer an exactly-once result within the receipt retention contract. A catalog-only receipt cannot prove a user database committed. Until that mechanism exists for an operation, report uncertain outcomes explicitly and do not automatically replay a write.

Read retries are allowed only when they do not violate a requested snapshot/session contract. Retryable busy/conflict errors may restart a complete transaction if the application opted into that policy. Do not retry an arbitrary statement in the middle of a failed transaction.

## HTTP rules

- JSON requests use UTF-8 and strict schemas; reject unknown fields for mutation contracts.
- Responses include request ID, API version, resource revisions where relevant, and consistent error codes.
- Paginated administrative lists use stable ordering and opaque authenticated cursors.
- Conditional mutations require an expected revision or documented blind-write permission.
- File transfer uses staged asset IDs and streaming upload/download endpoints; SQL never receives an unchecked host filename.
- Limit request headers, compressed and decompressed bodies, SQL length, statement count, parameter bytes, execution time, result bytes, and idle streams.
- A slow client must not retain unbounded native memory or block unrelated database workers.
- Credential, database, and policy checks apply again at cursor continuation and transaction boundaries.

## Compatibility pipeline

The upstream server_proto types are the reference for the implemented Turso/libSQL-compatible pipeline subset. Its batch conditions, value encodings, connection/baton behavior, and error formats must be reproduced exactly for clients advertised as compatible. Close operations, unused batons, empty batches, conditional errors, affected rows, last insert IDs, and precision are explicit conformance cases.

An HTTP transaction baton is bound to an authenticated client and database. A load balancer/reverse proxy forwarding one standalone installation does not change its identity. Do not add routing concepts for a distributed cluster.

## Error model

| Application code | Typical HTTP result | Meaning |
|---|---|---|
| invalid_argument | 400 | Invalid schema, parameter, type, or request |
| unauthenticated | 401 | Missing, invalid, expired, or revoked credential |
| permission_denied | 403 | Authenticated but insufficient permission |
| not_found | 404 | Unknown or deliberately concealed resource |
| revision_conflict / idempotency_conflict | 409 | Stale expected state or reused key with different payload |
| feature_unavailable | 422 | Unsupported dialect/bridge/build/experimental capability |
| resource_exhausted | 429 or 503 | Explicit quota/rate exhaustion or temporary active capacity pressure |
| busy / transaction_conflict | 409 or 503 | Engine conflict with retry guidance |
| deadline_exceeded | 408 or 504 | Budget elapsed; commit state is reported separately |
| generation_changed / cursor_expired | 409 or 410 | Execution identity is no longer valid |
| io_error / corruption / internal_error | 500 or 503 | Preserve diagnostics and data-integrity state |

Return native/dialect details only when safe for that principal. PostgreSQL maps to SQLSTATE with detail fields. MCP reports application failures as tool errors with structured error data; protocol framing errors remain JSON-RPC errors. The job result stores the same canonical error.
