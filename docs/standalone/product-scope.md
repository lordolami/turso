# Product scope and requirements

## Product statement

Mira is a portable, self-hosted SQL database platform operated by people and agents. A user downloads one executable for their platform, starts it on a computer, bare-metal machine, dedicated server, or VPS, and manages independent databases through a browser dashboard, CLI, API, and MCP.

The user owns deployment, data, accounts, backup destinations, and access policy. A machine can serve multiple applications, customers, tenants, teammates, and agents. Remote clients may connect over an operator-configured network. Standalone describes the deployment architecture; it does not mean one database, one client, offline-only operation, or a developer toy.

The positioning phrase is **a database LLVM that scales with you**. Within this scope, scale means using the machine efficiently, admitting many independent databases, supporting concurrent workloads, and allowing larger self-hosted hardware. It does not promise multi-machine write scaling.

## Binding scope decisions

| Requirement | Contract |
|---|---|
| SCOPE-001 | Application and platform services are written in Go; compiled database libraries are allowed dependencies. |
| SCOPE-002 | Deliver one application executable per supported OS/architecture; normal operating-system facilities are allowed. |
| SCOPE-003 | Include SQLite and PostgreSQL frontends explicitly, with per-dialect capability reporting. |
| SCOPE-004 | Include every standalone platform capability described below; workstreams are dependencies, not a reduced-feature first release. |
| SCOPE-005 | No vendor account, license quota service, or managed database subscription is required to start and use local functionality. This does not set the project's commercial license or pricing. |
| SCOPE-006 | Do not impose a vendor database-count cap. Expose operator-defined quotas separately from active-handle and resource budgets. |
| SCOPE-007 | Full MCP parity: an appropriately authorized agent can execute every application operation available to an equivalent human through another interface. |
| SCOPE-008 | Exclude NoSQL collections, document query language, MongoDB compatibility, managed hosting, clustering, sharding, distributed transactions, multi-region placement, infrastructure autoscaling, and billing. |
| SCOPE-009 | Retain JSON, JSONB, arrays, vector values, and text search as SQL/database capabilities. Excluding NoSQL does not remove these types or functions. |
| SCOPE-010 | Include synchronization against this installation; a synchronized client is not an additional database-server cluster member. |

## People and workflows

**Installation owner:** starts the server, creates organizations and databases, grants access, sets resource limits, manages encryption references, creates backups, restores data, and upgrades the installation.

**Application developer:** creates a database, chooses its dialect, edits schema, applies migrations, queries data, adds search indexes, configures application credentials, tests changes on a branch, and diagnoses query performance.

**Operator or teammate:** receives a bounded role, performs permitted administration, watches local health and capacity, reviews audit history, and runs assigned recovery or maintenance jobs.

**Agent:** connects through MCP with its own identity, discovers current capabilities, executes permitted workflows end to end, follows durable jobs, and returns usable connection information or results. An owner-authorized agent receives the complete application surface; destructive annotations do not impose an automatic human-confirmation step.

## Full standalone capability inventory

| Area | User-visible scope | Requirements |
|---|---|---|
| Installation | First-owner setup; configuration validation; local and network listeners; instance identity; graceful shutdown; diagnostics | INST-001..004 |
| Databases | Create/list/get/update logical labels; choose provider/dialect; in-memory and persistent storage; block reads/writes; deletion protection; delete and recover | DB-001..008 |
| Organization | Organizations, groups, ownership, memberships, invitations, role assignments, per-group defaults | ORG-001..004 |
| Catalog | Stable resource IDs; paginated lookup; revisions; generation references; durable operation state; installation backup | CAT-001..004 |
| SQLite | Supported SQL, compatible files, SQL functions, types, constraints, indexes, triggers, views, introspection, and explicit experimental options | SQL-001..004 |
| PostgreSQL | Grammar/AST frontend, schema semantics, catalog emulation, wire endpoint, prepared statements, typed parameters/results, isolated sessions, authentication, and advertised compatibility | PG-001..006 |
| Query execution | Parameterized execution; explicit transaction sessions; bounded results; cancellation; query classification; dialect-specific errors; connection inspection | QUERY-001..006 |
| Schema administration | Object inspection; DDL; templates; migration history/checksums; schema comparison; group migration jobs; capability checks | SCHEMA-001..004 |
| Search/types | JSON/JSONB and arrays; supported custom types/domains/sequences; exact vectors; indexed vector integration; full-text matching/ranking/highlighting; compatible extensions | SEARCH-001..004 |
| Data movement | SQLite-file import/export; dialect-specific SQL dump; CSV/JSON data transfer; bounded uploads and downloads; validation and checksums | DATA-001..003 |
| Identity | Platform accounts, agent/service principals, local credentials, sessions, scoped database/group credentials, expiry and revocation, external JWT/JWKS | AUTH-001..005 |
| Authorization | Resolved table/action grants; schema grants; organization roles; consistent enforcement through every interface; no SQL bypass through indirect effects | AUTHZ-001..005 |
| Security | TLS; configurable listener exposure; IP/network policies; path containment; protected secret references; at-rest encryption support; extension policy | SEC-001..005 |
| History | Commit capture; consistent snapshots; immutable local archive; timestamp/revision mapping; retained-history validation | HIST-001..004 |
| Branches | Consistent clone; copy-on-write sharing; independent branch writes; historical branch; comparison; explicit migration application | BRANCH-001..003 |
| Recovery | Local backup policies; PITR; deleted-resource recovery; restore verification; generation switch; catalog/installation recovery; retention cleanup | REC-001..006 |
| Sync | Self-hosted endpoint; client bootstrap; push/pull; resumable revisions; partial pages; conflicts; revocation; retention; checkpoints; client status | SYNC-001..006 |
| Changes | All-connection CDC; authorized commit notifications; resume cursors; bounded subscriptions; capability-aware live query support | CHANGE-001..004 |
| Operations | Durable jobs; leases for workers within the process; retries/cancellation; maintenance; audit; observability; storage/resource limits | OPS-001..006 |
| Interfaces | Browser dashboard; CLI; HTTP administration; SQL-over-HTTP; PostgreSQL endpoint; MCP stdio proxy and HTTP endpoint; supporting client packages | IFACE-001..006 |
| MCP | Complete operation registry; principal-filtered discovery; typed schemas; useful structured results; durable jobs/resources; cancellation; audit attribution | MCP-001..006 |
| Delivery | Embedded UI/docs; native static integration; per-platform artifacts; reproducible version manifest; notices; upgrade/recovery instructions | BUILD-001..005 |
| Verification | Differential SQL tests; policy adversarial tests; ABI checks; multi-client isolation; crash/restore tests; many-database resource tests; interface parity | TEST-001..006 |

The exact requirement records, acceptance obligations, and owning chapters are in [requirements.json](contracts/requirements.json). Requirements cover product behavior rather than every internal function name.

## Important boundaries

### Dialect is a database property

The engine shares storage/execution machinery, but the audited registry fixes a dialect for each opened database. A PostgreSQL database must be opened through the PostgreSQL frontend. The dashboard and API can manage both dialects; that does not imply that arbitrary SQLite clients can open PostgreSQL-created schema files or that a connection can switch parser semantics mid-transaction. Cross-dialect conversion is an explicit import/migration operation with compatibility checks.

### Local platform accounts are not application-user authentication

Accounts, teams, tokens, and JWKS authenticate people, agents, and applications to the database platform. This scope does not quietly add PocketBase-style end-user signup collections, OAuth callback hosting for arbitrary apps, application file uploads, an email marketing service, or a generated application CRUD backend.

### Count and capacity are different

Cataloged databases may exceed simultaneously open databases. Users see catalog counts, configured active budgets, current usage, and actionable capacity errors. Dormant databases do not retain a connection pool, page cache, or worker thread merely because their catalog row exists. Creation can fail on ordinary resource exhaustion; the product must not call a bounded number of open handles an unlimited active-workload guarantee.

### Supporting dependencies are explicit

Client SDKs are installed in client applications. Certificates and keys may be operator-supplied files. An optional external identity provider is a connection chosen by the operator; local credentials remain usable without it. Invitations have a local redeem-code flow so email delivery is not required. Backups target local paths or mounted storage in this scope; managed object-storage service provisioning is excluded.

## Product acceptance

A release may claim a capability only after its native bridge, authorization, API/CLI/MCP behavior, dashboard representation, failure behavior, and tests agree. Every unavailable feature must have a stable capability status and a precise error. A large inventory of proposed features is not evidence of a functioning product, PostgreSQL feature parity, a fixed binary size, or production reliability.
