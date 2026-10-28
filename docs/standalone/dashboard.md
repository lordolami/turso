# Browser dashboard and user flows

## Product behavior

Serve a compiled dashboard from the executable. The browser is an administration client of the same public application services. It has no direct filesystem or native database access and no privileged private mutation endpoint that MCP/API cannot use.

The dashboard is for the standalone installation. It does not contain cloud provisioning, cluster/node/shard administration, billing plans, or NoSQL collection screens.

## Navigation and screens

| Screen | Required actions and states |
|---|---|
| Setup/sign-in | Local bootstrap, owner creation, credential login, session expiry, disabled-account state |
| Instance overview | Build/native versions, health, database counts, active capacity, storage, current jobs, and local settings |
| Organizations/groups | Create and edit organization/group metadata, inspect ownership, members, defaults, and scoped databases |
| Databases | Search/filter/page all cataloged resources; create, inspect, rename labels, configure blocks/limits/protection, delete, recover |
| Database overview | Dialect/provider, generation, schema revision, size, active connections, history/sync status, capability reasons |
| SQL editor | Explicit database/dialect context, parameter binding, execution mode, result bounds, typed rows, cancellation, and transaction state |
| Data browser | Browse tables/views, filter/sort/page, display typed values, edit permitted rows using stable keys and conflict checks |
| Schema browser | Tables/columns/constraints/indexes/types/domains/sequences/views/triggers/materialized views; capability-aware DDL |
| PostgreSQL connection help | Tested client examples, endpoint/credential method, TLS settings, known compatibility limits |
| Search | Text/vector query inputs, selected index/type information, result limits, capability status, and index jobs |
| Templates/migrations | Create templates, inspect checksums, compare schema, plan/apply migrations, inspect per-database results |
| Data transfer | Upload/stage/validate imports, map CSV/JSON fields to SQL tables, request/download exports, inspect errors |
| Accounts/access | Principals, memberships, invitations, roles, grants, tokens, expiry/revocation, and credential creation |
| History/branches | Retained revisions, snapshots, independent branches, source lineage, comparisons, and retention dependencies |
| Backups/recovery | Local policies, schedules, artifacts, verification, restore-as-new or generation replacement, trash recovery |
| Sync/changes | Clients, generation/revision state, traffic, retention floor, revocation, authorized subscriptions |
| Maintenance | Integrity check, checkpoints, reindex/analyze/compact where supported, job impact and results |
| Observability | Query summaries, latency, resource budgets, errors, logs, audit records, diagnostic artifacts |
| Jobs | State/progress/events/results, cancellation, supported retry, restart reconciliation outcome |
| Agent access | MCP connection configuration, agent identities/grants, tool capabilities, and attributed audit history |
| Settings | Listener/TLS references, local paths, resource budgets, retention, extensions, and version-aware configuration reload |

## Database creation flow

Choose organization/group, display name, slug, provider/dialect, persistent or memory storage, optional template/snapshot, native feature flags, encryption reference, and operator limits. Explain incompatible combinations before submission. Submit one canonical create operation and follow its durable job. A ready state displays connection options appropriate to the selected dialect. A failed state preserves job diagnostics and does not display a usable connection string prematurely.

## SQL editor and data editing

Keep database ID, generation, dialect, transaction state, role/credential context, result snapshot, and pending edits visible. Do not reuse query results after the context changes. Parameters are separate typed inputs; paste does not interpolate them into SQL strings. A script is an explicit mode with per-statement outcomes.

Rows without a stable unique key are view-only unless the user supplies an explicit safe selection mechanism. For edits, use primary/unique keys and an optimistic row/version predicate where available; never update an arbitrary first row based on visual position. Distinguish SQL NULL, empty text, binary values, JSON null, numbers, and exact decimals. Large binary/text values are truncated visually with an explicit inspect/download action.

The UI requests ordinary authorization and displays operation effects. Do not force every action through an additional approval flow. Destructive operations still require their defined permission, target identity, and revision/deletion-protection checks. Client presentation choices do not replace server enforcement.

## Recovery and generation changes

Show source revision/time, required keys, target name, and whether the result is a new database or replaces a generation. Follow reconstruction/verification/publication as a job. When generation changes, close stale editor contexts and results explicitly. A failed restore leaves the previous generation usable where the lifecycle contract permits it.

## Empty, loading, failure, and permission states

Every list has empty/loading/partial/error states. Every job distinguishes queued/running/waiting/cancelling/cancelled/succeeded/failed/unknown commit state. Permission-denied differs from feature-unavailable and resource exhaustion. Do not show a spinner indefinitely when a native capability is missing. Provide request/job IDs and safe diagnostics in errors.

## Accessibility and usability

Keyboard navigation, semantic controls, visible focus, labeled fields, screen-reader status updates, contrast, responsive tables, and reduced-motion support are required. Long results are paginated or virtualized. Background refresh is bounded and does not repeatedly rerun expensive SQL. Secrets are shown only by explicit credential-issuance/rotation responses and never embedded in URLs or ordinary log panels by the application. The UI masks them outside the delivery view; an operating-system screenshot of an intentionally revealed secret cannot be prevented by the server.

## UI parity

Every mutation maps to an operation registry entry. Discovery may expose more low-level tools to CLI/MCP than one screen needs, but there must be a usable dashboard path for the corresponding human action or an explicit supported advanced-operation view. Schema/dialect limitations are described from server capabilities, not a duplicated static frontend assumption.
