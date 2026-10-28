# Complete MCP operation of the platform

## Product contract

MCP is a first-class interface to the entire standalone platform. It has the same application operations and permissions as the API, CLI, and dashboard. An owner-authorized agent can manage everything within the database platform, including identities, data, schema, branches, backup/recovery, synchronization, configuration, diagnostics, jobs, and shutdown. Full platform control does not mean arbitrary operating-system shell access.

There is no mandatory separate human-confirmation step for each agent mutation. Permissions and configured policy determine authority. Tools declare their effects accurately so a client can present its own controls. A restricted agent receives the same restrictions as an equivalent human identity, not a hardcoded permanently read-only MCP surface.

## Protocol and SDK

The audited upstream CLI MCP server is a small SQLite tool set and is not the server implementation for this product. Use the official Go SDK with a pinned release and protocol conformance evidence. At documentation time, the official SDK compatibility table identifies v1.7.0+ with the 2026-07-28 protocol and earlier supported revisions. Pin the actual release and dependency graph during implementation.

The 2026-07-28 transport specification differs from older connection-scoped initialization models. Follow the SDK/specification for per-request metadata, protocol version detection, cancellation, pagination, caching, and backward compatibility. Do not copy an older initialize-only server loop and label it current. See the [versioned transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports), [tool specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), and [official Go SDK](https://github.com/modelcontextprotocol/go-sdk).

## Connection modes

**HTTP endpoint:** the running instance serves /mcp under configured authentication, listener, TLS, and origin policies. It is a self-hosted endpoint on the same machine, not a managed cloud service. Authorization is evaluated from the request's credential and current policy.

**Stdio proxy:** the same executable can run mira mcp --instance ... --credential ... as a client-launched subprocess. It authenticates to the already-running owner through the local control transport and exposes MCP on stdin/stdout. It does not open data files or create another engine-owning process. Protocol output is stdout-only; human diagnostics go to stderr.

**Embedding:** a supporting Go package can register the same operation handlers in another host, subject to the same ownership and policy requirements. This is a separate developer distribution, not an extra daemon users must install.

## Canonical tools

[operations.json](contracts/operations.json) is the proposed operation registry. Every public operation has an operation ID, MCP tool name, description, typed input/output schema, permission, resource selector, retry/idempotency behavior, job behavior, and read-only/destructive annotations. Generate HTTP/CLI/MCP bindings from that contract or validate manually implemented bindings against it.

Required tool families are:

| Family | Agent capabilities |
|---|---|
| Instance | Inspect capabilities/build, configure settings, inspect health, schedule shutdown |
| Organizations/groups | Create, inspect, update, delete, transfer permitted ownership, and manage defaults |
| Principals/membership | Manage people, agents, services, invitations, credentials, roles, and grants |
| Databases | Create/list/inspect/update/delete/recover/purge, inspect sessions and resources |
| SQL | Read, write, run supported scripts, manage explicit transactions, fetch results, cancel execution |
| Schema | Inspect objects, execute authorized DDL, manage indexes/types/views, apply templates/migrations, compare schemas |
| Search | Vector and text search, search-index management, and capability discovery |
| Data transfer | Upload a staged asset, validate/import it, request exports, inspect/download artifacts |
| History | Inspect retained revisions, create snapshots/branches, compare branches, manage retention |
| Backup/recovery | Configure policies, create/verify backups, restore databases or installation state |
| Sync/changes | Inspect/revoke clients, configure supported sync, manage subscriptions and cursors |
| Maintenance | Checkpoint, integrity check, analyze/reindex/compact through supported administrative methods |
| Observability | Inspect metrics, slow queries, audit/log records, diagnostic jobs, and resource pressure |
| Jobs | Inspect state/events/results, request cancellation, and retry only supported safe operations |
| Extensions | Inspect compatible modules, manage operator-trusted registration, and capability flags |

## Discovery and authority

Tool discovery is deterministic and filtered by authorized visibility. A tool being hidden is not its security enforcement; tools/call reauthenticates and reauthorizes. Cache keys for discovery include principal/scope/policy and capability versions. Never leak a database name through a schema resource when its principal cannot list that database.

Owner authority can invoke every registered service operation. Bootstrap/setup tools are available only through an explicit local bootstrap credential before an owner exists. The product does not require a human browser for an otherwise authorized agent workflow.

## Results and long work

Small results return structured content using the same canonical resource/error types as HTTP. Query rows are typed and bounded. Large exports, diagnostics, and long operations return a durable job ID and authorized artifact/result reference. The client polls job state or follows the protocol features actually negotiated; do not promise unsupported native MCP task APIs.

Job states are queued, running, waiting, cancelling, cancelled, succeeded, failed, and unknown_commit_state where relevant. Results include progress units when known, not invented completion percentages. Closing an MCP response stream cancels that request under the negotiated transport; it does not automatically undo an acknowledged durable job. jobs.cancel is the explicit durable-job cancellation operation.

## Resources and subscriptions

Expose authorized read resources for build/capability information, database/schema summaries, job results, and bounded diagnostic artifacts. Resource identifiers are opaque platform IDs, not host filesystem paths. Subscriptions use the negotiated protocol's supported mechanism and the application's authorized change service. Every resource read rechecks permission, expiry, and generation.

Resource contents, rows, SQL comments, imported files, and logs are untrusted data. They cannot grant new permissions or cause the service to execute hidden instructions. This is an application data boundary, not an invented approval step.

## Idempotency and errors

Tools carry application idempotency keys for supported mutations; a JSON-RPC request ID is not automatically a durable idempotency key. Duplicate create/restore requests with the same key return the same job/resource when payloads match. Reused keys with different normalized payloads fail explicitly. A generic SQL write is not advertised as idempotent without an atomic target-database receipt.

Application errors use isError with structured code, retryability, request/job IDs, resource context, and commit certainty. Invalid framing/unknown methods use protocol errors. Authentication failures never become successful tool results containing a text warning. Preserve safe SQLSTATE/native details where relevant.

## Full agent workflows

1. Inspect current capabilities, create a PostgreSQL database, apply supported schema/migrations, import staged data, create indexes, issue restricted application credentials, and return connection details.
2. Inspect slow queries, obtain available query plans, create an appropriate index under schema authority, and compare measured results.
3. Create a snapshot and branch, apply a migration on the branch, run checks, and export a migration result for explicit application to the original.
4. Configure a local backup policy, run a backup, verify it, restore into a new database, and check integrity.
5. Investigate sync lag, inspect a client's generation/revision, revoke a compromised credential, and verify that subsequent operations are denied.
6. Change a resource budget, follow maintenance jobs, and schedule a graceful server stop when authorized.

## Parity acceptance

Each operation is exercised through direct service tests and all declared interfaces with equivalent inputs and principal state. Compare effects, resource identity, errors, audit attribution, secret visibility, generation checks, and retry outcomes. An API-only management feature is a failed MCP parity requirement until exposed or explicitly classified as a transport-only framing action.
