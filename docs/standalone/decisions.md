# Decisions, risks, and unresolved engineering

## Confirmed product decisions

| Decision | Status and basis |
|---|---|
| DEC-001: Standalone self-hosted product | Confirmed by the user; one machine/installation can serve remote clients and many databases |
| DEC-002: Go application | Confirmed by the user; native database libraries remain build dependencies |
| DEC-003: One executable | Confirmed product target; data/config/backups are separate runtime files |
| DEC-004: SQLite and PostgreSQL | Confirmed; PostgreSQL is an explicit frontend, not a footnote |
| DEC-005: No NoSQL | Confirmed exclusion; retain JSON/vector/array/text-search SQL capabilities |
| DEC-006: No cloud/distributed scope | Confirmed exclusion for current work; no clustering, sharding, distributed transactions, managed service, or billing |
| DEC-007: No vendor database-count cap | Confirmed; operator quotas and physical capacity remain explicit |
| DEC-008: Complete MCP | Confirmed; authorized agents can perform all platform operations with human-equivalent permissions |

## Proposed implementation decisions

These are concrete design recommendations based on inspected source. They remain subject to implementation evidence; documenting them is not a claim that feasibility has been proved on every platform.

| Decision | Proposal | Evidence/gate |
|---|---|---|
| DEC-009: Reuse and extend Go bindings | Prefer the existing purego/bundled native loading route; add missing native APIs; static cgo remains an optional measured alternative | Pinned Go loader already bundles its engine; no-extraction/static linking was an assistant-added restriction, not a user requirement |
| DEC-010: Fixed database dialect | Persist immutable provider/dialect; no arbitrary per-request parser switching on one file | core Dialect and registry enforce fixed identity |
| DEC-011: Identity/recovery | Private catalog, per-principal credentials, local bootstrap and OS-authorized owner recovery | Specify recovery material/key custody and test local trust boundaries |
| DEC-012: Engine authorization | Generic resolved-action hook and immutable native policy context | Existing sqlite3_set_authorizer refuses because core hook is absent |
| DEC-013: Local history/COW | Native commit/snapshot/archive integration and portable manifest-backed branch storage | WAL/MVCC truncation plus missing backup API; prove crash/locking/filesystem semantics |
| DEC-014: Legacy libSQL parity | Preserve an explicit compatibility requirement; separately pin/integrate a provider only if exact legacy behavior is retained | libSQL is a different project; do not claim it is supplied by this fork or silently substitute sync/vector/extension semantics |
| DEC-015: PostgreSQL wire | Implement Go endpoint over actual native PG sessions; use upstream server as a reference | Current server shares state and trusts clients; product needs per-client auth/session isolation |
| DEC-016: MCP protocol | Pin official Go SDK with current protocol and declared legacy revisions | Official 2026-07-28 specification and SDK compatibility table; execute conformance before advertising |
| DEC-017: Catalog durability | Private SQLite-dialect catalog, schema migrations, lifecycle intents and reconciliation | Cross-file/catalog operations are not one atomic SQL transaction |
| DEC-018: PostgreSQL schema inventory | Persist safe namespace/file mapping and attach each session correctly; snapshot the bundle consistently | Current frontend creates connection-local attached schema files; persistent multi-session behavior needs integration tests |
| DEC-019: Indexed vectors | New explicit implementation/integration where native engine lacks it | New-engine README lists approximate vector indexing as roadmap; do not borrow libSQL's claim |
| DEC-020: Runtime budgets | Separate catalog count, active handles, native memory, Go memory, and background work | Engine allocates native caches/MVCC state; Go heap limits are insufficient |

## Unresolved details that must be settled in code

1. Exact native payload composition and minimal symbol/export strategy that includes PG parser/frontend, sync, FTS, encryption, and required extensions without duplicate engine code.
2. Full-feature Go/native build and loader qualification per target; compare static linking only where justified, especially PostgreSQL grammar and native crypto/compiler requirements on Windows.
3. Complete authorizer event/action model, invoker semantics, runtime dynamic effects, and prepared-plan revocation behavior.
4. Snapshot/history archive ordering for WAL and MVCC and coordinated PG schema bundles, including crash recovery between native commit and archive publication.
5. Portable COW I/O semantics and whether some target filesystems need a qualified fallback while retaining honest capability reporting.
6. Dialect-preserving PostgreSQL sync, schema replay, and format negotiation; current SQLite-oriented primitives are not sufficient evidence.
7. Exact legacy libSQL compatibility commitment/provider. This remains visible rather than silently adding a second engine or deleting the requirement.
8. Selected approximate-vector-index implementation, format, memory behavior, authorization, and snapshot/restore integration.
9. Pinned password hashing/SCRAM/credential library choices and parameters, independent of PostgreSQL SQL role semantics.
10. Owner recovery/key custody mechanism, installation cloning identity, and credential behavior after whole-installation restore.
11. Measured resource defaults, supported hardware/filesystems, and qualified client/protocol matrix.

These questions are engineering obligations, not a request to reduce the feature set. Implementations must record the chosen answer and evidence before claiming the corresponding capability. Ask the user only when a product preference or external credential/ownership decision is actually needed; routine technical verification should proceed within the agreed scope.

## Principal risks and mitigations

| Risk | Required treatment |
|---|---|
| Presenting a PG wire listener as complete PostgreSQL | Publish exact compatibility; execute real frontend/client tests |
| Incomplete SQL policy | Implement native resolved-effect checks before issuing restricted credentials |
| Incorrect backup/PITR claims | Native commit integration, complete bundle manifests, replay verification, crash injection |
| Same file opened under competing dialects/processes | Fixed catalog identity, one process owner, native registry checks |
| Cross-client PG state | Independent sessions and adversarial concurrency tests |
| Missing native memory accounting | Native counters plus OS process metrics and admission budgets |
| Sync pages leaking table-restricted data | Full-generation physical permission; logical authorized query path for narrower scopes |
| Full MCP only in marketing | Canonical registry and automated parity/authorization checks for every operation |
| Feature inventory mixing engines/statuses | Source-pinned capability records and explicit gaps |
| Unmeasured lightweight claim | Measure final combined artifact/RSS/workloads and report conditions |

## Changes to this specification

Update requirements, operation/config/native contracts, owning chapters, and acceptance checks together. Record whether a change follows a user scope decision, source revision update, or measured implementation finding. Do not silently reintroduce NoSQL/cloud/distributed features or impose a database-count cap under an implementation detail.
