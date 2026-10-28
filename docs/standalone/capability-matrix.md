# Capability and integration matrix

## Meaning of status

This table separates the **product target** from **upstream implementation**. Existing source is not proof that a feature is safely exposed through a multi-user Go server. A feature is available to a user only when native implementation, bridge, policy, service, and protocol checks all succeed.

| Capability | Audited upstream state | Standalone implementation responsibility |
|---|---|---|
| Local/in-memory SQLite database | Present | Catalog registration, budgets, lifecycle, safe import/export, and Go integration |
| PostgreSQL AST/frontend | Present, experimental/partial | Native ABI, Go session owner, compatibility reporting, and tests |
| PostgreSQL wire endpoint | Reference server present | Go listener, TLS, authentication, routing to many databases, session isolation, cancellation |
| Database dialect | Fixed at open; registry enforces identity | Persist immutable dialect and reject mismatched connection requests |
| Go database/sql driver | Present; SQLite SDK path | Reuse the binding; extend native/Go APIs for PG and missing engine hooks |
| One downloadable executable | Current Go loader embeds and automatically extracts a native library; static outputs also exist | Package matching complete native payload, harden automatic loading, measure footprint; static cgo is optional |
| SQL CRUD, joins, constraints, functions | Substantial support, differences by dialect | Surface exact supported subset, typed values, cancellation, authorization |
| Views/materialized views | Available with feature/runtime conditions | Capability checks, invoker authorization, history/restore compatibility |
| Triggers | SQLite surface supported; PostgreSQL triggers absent in current matrix | Correct dialect reporting and indirect-action authorization |
| Arrays/custom types/domains/sequences | Substantial support with feature/dialect conditions | Correct encoding, introspection, validation, import/replay |
| Generated columns/WITHOUT ROWID | Experimental and partial | Explicit opt-in, exact restrictions, regression coverage |
| WAL and MVCC | Present; different storage/durability behavior | Per-database mode configuration, active-memory control, native history integration |
| Serializable isolation | Not a general engine guarantee; PG rejects serializable | Never label snapshot isolation serializable; reject unsupported requested levels |
| Native database authentication | No platform identity system | Go identity service plus trusted native principal context |
| PostgreSQL authentication/roles/RLS | Reference wire server trusts connections; role/RLS enforcement absent | Add product authentication and platform roles; do not advertise native PostgreSQL GRANT/RLS parity |
| Table/action authorization | No working core prepare-time authorizer | New generic native authorization hook and policy enforcement at all execution paths |
| CDC | Per-connection configuration present | Uniform setup, complete commit attribution, authorized publication, retention |
| Change subscriptions | Some engine/query subscription work experimental | Bounded application service with explicit availability and resume behavior |
| At-rest encryption | Present, experimental | Key references, per-connection setup, backup/history encryption, release qualification |
| Encryption key rotation | Not assumed by this audit | Explicit copy/re-encrypt/verify workflow if exposed; never call it an in-place native rekey without implementation |
| Native exact vector operations | Present | API representation, permissions, types, resource limits |
| Approximate vector indexing | Listed as a roadmap item for new Turso engine | Explicit new integration/implementation gap; no borrowed libSQL claim |
| Tantivy text search | Optional compile-time feature, experimental index method | Build flag, runtime opt-in, native lifetime and FTS artifact backup |
| SQLite FTS5/R*Tree | libSQL/SQLite claims do not imply new-engine parity | Report unavailable unless a selected provider actually supplies them |
| UUID/time/JSON/percentiles and other extensions | Built-in/optional/native-extension differences | Record bundled modules; allow compatible operator-trusted extensions only |
| Runtime SQLite .so/.dll compatibility | Turso-native extension interface differs | Never advertise arbitrary SQLite binary extension compatibility |
| Local sync client | Present through sync engine and Go bindings | Integrate supported client packages and local service endpoint |
| Local sync server | Present including directory mode, limited generations and production controls | Go request service/native protocol bridge, auth, retention, generation transitions, bounded clients |
| PostgreSQL physical sync | Not established by the inspected SQLite-oriented path | Dialect-preserving bootstrap/replay and tests are required; report unavailable until qualified |
| Local consistent backup | SQLite C backup functions are stubs | New snapshot bridge; coordinate WAL, MVCC, PG schema files, FTS, and encryption |
| PITR/archive | Cloud behavior is not a local core feature | Durable commit capture before truncation, archive manifests, replay, verification |
| Copy-on-write branches | Not a complete ready-made local platform API | Native versioned-storage integration and crash-safe manifests |
| Multi-database administration | Engine registry and sync directory mode are building blocks | Durable catalog, ownership, protected paths, generation manager, idle eviction |
| Full MCP administration | Upstream CLI has a small SQLite tool surface | New Go MCP interface generated from the entire operation registry |
| Dashboard/teams/templates/migrations/audit/jobs | Not supplied as this application | Build Go services and embedded UI |
| Legacy libSQL embedded replicas | A separate engine/project | Keep a separately identified compatibility requirement; do not silently substitute Turso Sync |
| Managed cloud, billing, sharding, cluster failover | Outside current product scope | Do not add endpoints, jobs, UI, or dependencies for these systems |

## Provider and dialect contract

The primary provider is turso. A database has dialect sqlite or postgres. A provider is an implementation boundary, not a cloud location. The main application cannot change the provider or dialect of an existing generation merely by changing a query parameter.

The prior feature inventory mixed new Turso and legacy libSQL features. Preserve that distinction in requirements. Any exact legacy replica or extension parity requires a separately pinned libSQL-compatible backend and build/verification evidence. Its integration is recorded as DEC-014; the current Turso fork alone does not implement that backend. Do not claim it is present, discard the compatibility requirement silently, or switch user files to another engine automatically.

## Capability response

Every database exposes a machine-readable capability result. Proposed example:

~~~json
{
  "provider": "turso",
  "dialect": "postgres",
  "engine_revision": "017ea183c2a323a66d515448e4df464b6181bb36",
  "capabilities": {
    "query.postgres": {"state": "experimental", "reason": "upstream_partial"},
    "authorization.table_actions": {"state": "verification_pending", "reason": "native_hook_required"},
    "sync.physical": {"state": "verification_pending", "reason": "dialect_replay_required"}
  }
}
~~~

This is a design illustration, not a current server response. Capability records include build feature identifiers, experimental flags, format versions, policy requirements, and links to precise compatibility entries. The server returns a feature_unavailable error rather than falling back to weaker semantics.

## Source of truth

Use the [audited SQLite matrix](../../COMPAT.md), [PostgreSQL matrix](../../postgres/COMPAT.md), [experimental feature documentation](../sql-reference/experimental-features.mdx), source evidence, and product conformance results together. If the marketing overview and current source disagree, investigate and record the difference. If source and a runtime result disagree, preserve the reproduction and update this audit.
