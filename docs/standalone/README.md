# Standalone database platform specification

**Working name:** Mira. This name follows the workspace name and is not a final branding decision.

**Status:** proposed product and implementation contracts, grounded in an upstream source audit. This documentation does not claim that the Go application or its additional services already exist.

**Scope:** a self-hosted, single-machine SQL database platform delivered as one application executable. Go owns the product, administration, networking, dashboard delivery, and agent interface. Compiled Turso libraries supply database execution. SQLite and PostgreSQL are both first-class integrations. Users may create as many databases as their hardware and their own configured resource policies support; there is no vendor-imposed database-count quota.

No NoSQL/document frontend, managed cloud service, distributed cluster, sharding, distributed transaction coordinator, payment system, or infrastructure autoscaler is included. A remotely reachable server on the user's bare metal or VPS remains within scope. Self-hosted client synchronization is within scope and does not imply a distributed database cluster.

The upstream audit is fixed to [017ea183c2a323a66d515448e4df464b6181bb36](https://github.com/tursodatabase/turso/commit/017ea183c2a323a66d515448e4df464b6181bb36), committed on 2026-10-28. Source references and evidence records are in [the audit](upstream-audit.md) and [source evidence](source-evidence.md).

Mira's project folder contains this documentation and its maintenance tools. Turso's source is kept in a separate checkout, locally at ../turso-engine. Upstream references use pinned web links. The checker works without engine source and explicitly reports source verification skipped when that checkout is unavailable; set MIRA_TURSO_SOURCE to verify against another location. Source-derived regeneration requires the audited checkout.

## Read this specification

| Document | What it settles |
|---|---|
| [Product scope and requirements](product-scope.md) | User promises, exclusions, personas, and requirement identifiers |
| [Upstream audit](upstream-audit.md) | What the checked-out code provides and what it does not |
| [Capability matrix](capability-matrix.md) | Feature status by dialect and implementation responsibility |
| [System architecture](architecture.md) | Components, ownership, startup, request flow, shutdown |
| [Native bridge](native-bridge.md) | Go/native ABI, handles, values, errors, cancellation, and callbacks |
| [Catalog and filesystem](catalog-and-storage.md) | Persistent metadata, directory layout, identities, and consistency |
| [Storage and event formats](storage-formats.md) | Exact manifest fields, archive framing, COW blocks, receipts, and event envelopes |
| [Database lifecycle](database-lifecycle.md) | Creation, deletion, restore, handles, pooling, and operation states |
| [Query and HTTP protocols](query-protocols.md) | Typed values, SQL execution, transactions, paging, and errors |
| [PostgreSQL integration](postgresql.md) | Dialect, wire protocol, authentication, session isolation, and compatibility |
| [Security and authorization](security.md) | Identities, tokens, policy enforcement, filesystem boundaries, and audit |
| [History, branching, and recovery](history-and-recovery.md) | Snapshots, local commit history, COW branches, PITR, and retention |
| [Synchronization and changes](sync-and-changes.md) | Offline clients, protocol compatibility, CDC, and subscriptions |
| [MCP and agent operation](mcp.md) | Full platform parity, transports, tools, jobs, resources, and agent examples |
| [API and CLI contracts](api-and-cli.md) | The canonical operation registry and interface mappings |
| [Dashboard](dashboard.md) | Every screen, user flow, state, and accessibility requirement |
| [Configuration and deployment](configuration-and-deployment.md) | Settings, local/bare-metal/VPS deployment, service management, and networking |
| [Resource and performance design](performance.md) | Many databases, memory accounting, scheduling, and measurement criteria |
| [Testing and acceptance](testing-and-acceptance.md) | Correctness, compatibility, failure injection, and requirement acceptance |
| [Build and release](build-and-release.md) | Single-executable builds, toolchains, native dependencies, and release evidence |
| [Operations runbooks](operations.md) | Daily operation, backup, restore, upgrades, disk pressure, and recovery |
| [Implementation workstreams](implementation-workstreams.md) | Full-scope dependency graph and concrete engineering tasks |
| [Decisions and unresolved questions](decisions.md) | Accepted scope, proposed technical decisions, risks, and evidence gates |
| [Source evidence](source-evidence.md) | Source paths, immutable links, hashes, and audit observations |
| [Validation report](validation-report.md) | Checks actually performed on this documentation package |

## Machine-readable design contracts

- [Operation registry](contracts/operations.json): proposed application operations, typed inputs, permissions, interface exposure, and job behavior.
- [Catalog schema](contracts/catalog.sql): proposed installation catalog, including lifecycle jobs and durable operation records.
- [Configuration schema](contracts/config.schema.json) and [example configuration](examples/mira.config.json).
- [Requirements](contracts/requirements.json): product requirements, owning documents, and acceptance obligations.
- [Source evidence records](contracts/source-evidence.json): upstream files and observed evidence at the audited revision.
- [Complete upstream compatibility-table inventory](contracts/upstream-capabilities.json): every status-bearing SQLite and PostgreSQL table entry, with source lines and original qualifications.
- [Native bridge declaration](contracts/mira_engine.h): proposed ABI, not an implemented or linkable library.
- [MCP client example](examples/mcp-client.json): proposed connection configuration.

These contracts describe what to implement. They are not generated documentation for a running Mira service. Example Mira commands, endpoints, and native symbols are explicitly proposed interfaces.

## Terminology and interpretation

- **Instance:** one running Mira server process owning one installation directory on one machine.
- **Database:** an independently identified data resource with an immutable engine provider and dialect, potentially consisting of several engine-owned files.
- **Generation:** a concrete storage incarnation of a database; restore replaces a generation without silently reusing old sessions.
- **Session:** a principal-bound, database-generation-bound execution context.
- **Job:** a durable platform operation that can outlive a request.
- **Native:** compiled database code packaged with the Go application and loaded in its process; the product is not a rewrite of Turso in Go.
- **One file:** one application executable to distribute. Persistent data, automatically materialized native-library cache, optional operator-supplied certificates, and backups are separate runtime files. No-extraction static linking is not a user requirement.
- **No database-count cap:** the product imposes no commercial count limit. Bounded active handles and ordinary machine limits still apply.
- **Target / proposed:** a requirement or design we must implement and verify.
- **Observed:** a behavior or symbol inspected in the audited upstream source. A source inspection is not a passed runtime test.

## Documentation verification

Run the repository-local documentation checker from the repository root:

~~~text
python tools/check_standalone_docs.py
~~~

The checker validates local links, contract consistency, SQL catalog syntax against an independent SQLite parser, configuration examples, source hashes, and scope exclusions. It does not prove Turso compatibility, compile the proposed application, or substitute for the acceptance suite.

The inventories are generated with `python tools/generate_standalone_contracts.py`. Edit their operation/requirement definitions there, regenerate, and review the resulting contracts together. Resource-specific attributes, policies, and extension definitions are explicitly versioned payloads whose detailed service validators must be implemented alongside each capability; the registry is not presented as a complete OpenAPI specification.
