# Application operation, API, and CLI contracts

## Canonical registry

[operations.json](contracts/operations.json) is the full proposed application-operation inventory. It is a design contract, not a claim that endpoints are implemented. Each entry defines:

- id and description;
- domain and permission;
- HTTP method/path and CLI path;
- MCP tool name and effect annotations;
- typed input/output schemas;
- resource binding, durable-job behavior, and idempotency contract;
- capability requirement where an operation depends on native/dialect support.

No cloud, node membership, shard, infrastructure, billing, or NoSQL collection operation belongs in this registry. Generic list/get/update/delete patterns do not make their resource names implicit: each operation remains individually listed for parity and permission review.

Shared JSON Schema definitions live once under the registry document's root $defs. When extracting a tool's input_schema or output_schema for an SDK/validator, materialize those definitions into that extracted schema's $defs so local references resolve. This keeps the reviewed inventory compact without duplicating the same type definitions for every tool.

## Common request context

The application layer receives request ID, principal ID, credential ID, effective scopes, interface, source address/control endpoint, deadline, idempotency key, expected revision, resolved database/generation, and audit correlation. Context is trusted transport output; body fields cannot impersonate another principal.

Input schemas distinguish missing from null. For updates, absent means unchanged and explicit null clears only nullable fields. Reject unknown fields, invalid enums, oversized strings, incompatible dialect/options, and mismatched path/body IDs. Text labels and SQL identifiers use different validation rules.

## Resource representation

Resource IDs are UUID strings; timestamps are UTC integer microseconds encoded as decimal strings when JSON precision matters. Revisions are monotonic integers per catalog resource. A database response includes id, organization_id, group_id, name, slug, provider, dialect, persistence, state, active_generation_id, schema_revision, read/write blocks, deletion protection, quota overrides, capability status, and created/updated revisions/times. List responses contain items, next_cursor, and snapshot/list revision where applicable.

Job responses include id, type, principal/credential references, resource IDs, state, attempt/lease epoch, progress unit/current/total when meaningful, error, commit_state, result/artifact references, and timestamps. Public responses never contain internal filesystem paths or native handles. Administrative diagnostics may reveal configured local paths only under explicit authority.

## Optimistic concurrency and idempotency

Mutation requests that overwrite configuration/ownership/policy carry expected_revision. A stale revision returns revision_conflict with the caller-visible current revision. Deletion and restore bind the expected generation as well as resource revision.

For supported administrative mutations, require/provide a request idempotency key with normalized operation payload digest and principal/resource scope. HTTP accepts Idempotency-Key; CLI/client SDK supplies it explicitly or generates one for a single invocation; MCP exposes it as typed input. Record durable state before starting file work. The same key/payload returns the existing outcome. Keys are retained through the declared retry window and cannot be reused for a different payload.

Credential/invitation secret delivery additionally follows the protected, expiring issuance-envelope rule in [security](security.md). Ordinary resource idempotency does not justify storing plaintext secrets in receipts or exposing them through jobs.result.

Generic SQL uses the [query contract](query-protocols.md). It is not automatically safe to retry because an administrative idempotency table exists.

## File transfer and artifacts

Create an upload session with expected media type, size limit, digest if known, and intended operation. Stream chunks to staging; validate final bytes; publish an asset ID. Imports consume an authorized completed asset. Download/export operations return expiring artifact references and checksum/size metadata, with credentials required at download. MCP streams or references these through supported client mechanisms rather than inserting megabytes into a model response.

Imports validate dialect, schema names, encoding, target generation, required extensions/types, and file containment. SQLite file import inspects identity/format before opening. SQL script import defines atomic/partial semantics. CSV/JSON import uses selected tables and typed mapping; it does not add a NoSQL document database.

## CLI behavior

The executable is both server and administrative client. Proposed command families are serve, setup, instance, organizations, groups, principals, credentials, grants, databases, query, sessions, schema, templates, migrations, imports, exports, history, snapshots, branches, backups, recovery, sync, subscriptions, maintenance, metrics, audit, logs, diagnostics, jobs, extensions, and mcp.

Except serve and explicit offline recovery commands, the CLI talks to the owner process through the local control transport or configured HTTP endpoint. It does not open live database files. Offline repair/restore refuses to run while an instance lock is held. Standard machine-readable output is available with --output json; human tables are a presentation format. Errors have stable exit-code families and include request/job IDs. Secret values are not printed by ordinary list/get commands.

The registry specifies exact operation-level CLI paths. All Mira examples are proposed commands until implemented. Do not replace upstream tursodb or tursopg commands silently.

## Jobs and asynchronous operations

Return accepted job metadata for backup, restore, branch/copy, large imports/exports, integrity checks, compaction, group migrations, diagnostic bundles, and graceful shutdown where applicable. Each job records durable intent and restart reconciliation rules. A cancellation request moves to cancelling until the worker reaches a safe boundary; cancelled does not mean previously committed work was undone.

Retries are operation-specific. Read/verify work can restart against a retained immutable snapshot. Lifecycle jobs reconcile manifests. An uncertain transaction cannot be retried through jobs.retry until its receipt/outcome is known or an explicit recovery decision is recorded.

## Versioning

Version the HTTP contract, operation registry, catalog schema, native ABI, archive format, and advertised capabilities independently. API additive changes must not reinterpret an existing field. Changes to typed values, permission semantics, or resource identity require explicit version handling. An older client receives supported capabilities and errors instead of a silently weakened contract.

## Required validation

The documentation checker verifies unique operation IDs, HTTP method/path combinations, CLI paths, MCP tool names, permissions, schema shape, job behavior, and scope exclusions. Application acceptance additionally tests every operation's authorization, expected revision, idempotency, errors, native effects, audit, and declared interface parity.
